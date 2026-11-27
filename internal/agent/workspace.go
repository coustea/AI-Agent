// Package agent 的零信任虚拟文件系统后端（实现 Eino adk/filesystem.Backend）。
//
// 职责：
//   - 在 Eino 官方 local.Backend 外提供多租户虚拟路径映射：
//     /workspace -> 当前会话物理目录（可读写），/skills -> 全局技能目录（严格只读）；
//   - 统一执行四重安全校验：Principal 身份检查、路径清洗与挂载前缀精确匹配、目录包含判断、符号链接防逃逸；
//   - 强制小步读写配额（读上限 200 行，写上限 220 行 / 12 KB，grep 上限 200 条），并对外脱敏宿主机物理路径。
//
// 并发安全：workspace 实例仅保存不可变的 skillsRoot 与官方无状态 local.Backend，可跨并发会话共享；
// 每次操作通过 ctx 中的 Principal 动态解析当前会话的物理根目录。
package agent

import (
	"cmp"
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"

	local "github.com/cloudwego/eino-ext/adk/backend/local"
	adkfs "github.com/cloudwego/eino/adk/filesystem"
)

const (
	// 模型文件工具只见虚拟路径，物理目录在每次操作时由 Principal 动态解析。
	MountWorkspace = "/workspace"
	MountSkills    = "/skills"

	maxReadLines  = 200
	maxWriteLines = 220
	maxWriteBytes = 12 << 10 // 12 KB
)

var (
	ErrPathDenied    = errors.New("path is outside the allowed sandbox")
	ErrReadOnly      = errors.New("挂载点只读")
	ErrWriteTooLarge = errors.New("单次写入超出体积上限")
)

// workspacePathError 对外展示虚拟路径，并通过 Unwrap 保留底层哨兵错误供 errors.Is 分类。
type workspacePathError struct {
	path string
	err  error
}

func (e *workspacePathError) Error() string {
	if e.path == "" {
		return e.err.Error()
	}
	return fmt.Sprintf("%s: %v", e.path, e.err)
}

func (e *workspacePathError) Unwrap() error { return e.err }

// formatWorkspaceError 为 toolGuard 提供面向模型的自愈修复建议，且绝不泄露物理路径。
func formatWorkspaceError(err error) (string, bool) {
	var pathErr *workspacePathError
	if !errors.As(err, &pathErr) {
		return "", false
	}
	switch {
	case errors.Is(pathErr, ErrPathDenied):
		return "路径不可访问：" + pathErr.Error() + "。请使用 /workspace 或 /skills 中的路径。", true
	case errors.Is(pathErr, ErrReadOnly):
		return "目录只读，禁止修改：" + pathErr.Error() + "。/skills 目录严格只读，如需修改请先复制到 /workspace。", true
	case errors.Is(pathErr, ErrWriteTooLarge):
		return "写入被拒绝：" + pathErr.Error() + "。请将内容拆分为多个职责单一的小模块文件，或先写入框架再使用 edit_file 分段补充。", true
	default:
		return "文件操作未完成：" + pathErr.Error() + "。请检查路径后继续。", true
	}
}

type workspace struct {
	backend    adkfs.Backend
	skillsRoot string
}

// newWorkspace 初始化共享文件系统后端；此处仅确保总根目录存在，具体会话目录由 Harness.Prepare 创建。
func newWorkspace(workspaceRoot, skillsRoot string) (adkfs.Backend, error) {
	workspaceRoot = cmp.Or(strings.TrimSpace(workspaceRoot), DefaultWorkspaceDir)
	skillsRoot = cmp.Or(strings.TrimSpace(skillsRoot), DefaultSkillsDir)

	absWS, err := filepath.Abs(workspaceRoot)
	if err != nil {
		return nil, fmt.Errorf("解析目录失败: %w", err)
	}
	if err := os.MkdirAll(absWS, 0o755); err != nil {
		return nil, fmt.Errorf("创建目录失败: %w", err)
	}
	absSkills, err := filepath.Abs(skillsRoot)
	if err != nil {
		return nil, fmt.Errorf("解析技能目录失败: %w", err)
	}
	// 官方 local.Backend 直接操作物理路径，因此所有方法必须先经 mapPath 校验后才能委托。
	backend, err := local.NewBackend(context.Background(), &local.Config{})
	if err != nil {
		return nil, err
	}
	return &workspace{backend: backend, skillsRoot: absSkills}, nil
}

// mapPath 将虚拟路径解析为宿主机安全物理路径，依次校验身份、挂载前缀、只读权限、目录包含与软链接目标。
func (w *workspace) mapPath(ctx context.Context, virtual string, needWrite bool) (string, error) {
	if strings.TrimSpace(virtual) == "" {
		virtual = MountWorkspace
	}
	run, err := PrincipalFrom(ctx)
	if err != nil {
		return "", err
	}

	// 虚拟路径统一使用 POSIX 斜杠，先 Clean 再拦截 ".." 穿越。
	cleaned := path.Clean(strings.ReplaceAll(virtual, "\\", "/"))
	if strings.HasPrefix(cleaned, "..") {
		return "", &workspacePathError{path: virtual, err: ErrPathDenied}
	}
	if !strings.HasPrefix(cleaned, "/") {
		// 相对路径一律锚定到当前会话 /workspace，避免受服务进程 cwd 影响。
		cleaned = path.Join(MountWorkspace, cleaned)
	}

	// 挂载点必须精确相等或紧跟斜杠，防止 /workspace-evil 绕过前缀检查。
	prefix, root := MountWorkspace, run.Workspace
	switch {
	case cleaned == MountWorkspace || strings.HasPrefix(cleaned, MountWorkspace+"/"):
	case cleaned == MountSkills || strings.HasPrefix(cleaned, MountSkills+"/"):
		prefix, root = MountSkills, w.skillsRoot
	default:
		return "", &workspacePathError{path: virtual, err: ErrPathDenied}
	}
	if root == "" {
		return "", &workspacePathError{path: cleaned, err: ErrPathDenied}
	}
	if needWrite && prefix == MountSkills {
		return "", &workspacePathError{path: cleaned, err: ErrReadOnly}
	}

	rel := strings.TrimPrefix(strings.TrimPrefix(cleaned, prefix), "/")
	host := filepath.Join(root, filepath.FromSlash(rel))
	if inside, err := isInside(root, host); err != nil {
		return "", &workspacePathError{path: cleaned, err: err}
	} else if !inside {
		return "", &workspacePathError{path: cleaned, err: ErrPathDenied}
	}
	if err := checkSymlink(root, host); err != nil {
		return "", &workspacePathError{path: cleaned, err: err}
	}
	return host, nil
}

// isInside 以路径段而非字符串前缀判断包含关系，防止 /a/b-other 被误判在 /a/b 内。
func isInside(root, target string) (bool, error) {
	rel, err := filepath.Rel(root, target)
	if err != nil {
		return false, fmt.Errorf("%w: %v", ErrPathDenied, err)
	}
	return rel == "." || (rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))), nil
}

// checkSymlink 沿目标路径向上找到最近已存在的节点，解析符号链接后校验真实目标仍落在沙箱根内。
func checkSymlink(root, host string) error {
	probe := host
	var probeInfo os.FileInfo
	for {
		if info, err := os.Lstat(probe); err == nil {
			probeInfo = info
			break
		}
		parent := filepath.Dir(probe)
		if parent == probe {
			break
		}
		probe = parent
	}
	resolved, err := filepath.EvalSymlinks(probe)
	if err != nil {
		if probeInfo != nil && probeInfo.Mode()&os.ModeSymlink != 0 {
			if errors.Is(err, fs.ErrNotExist) {
				return fs.ErrNotExist
			}
			return fmt.Errorf("%w: %v", ErrPathDenied, err)
		}
		if os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("%w: %v", ErrPathDenied, err)
	}
	// 根目录本身也可能位于软链接之下（如 macOS /var -> /private/var），双方均取真实路径再比较。
	realRoot := root
	if r, err := filepath.EvalSymlinks(root); err == nil {
		realRoot = r
	}
	if inside, err := isInside(realRoot, resolved); err != nil {
		return err
	} else if !inside {
		return fmt.Errorf("%w: 符号链接指向沙箱外", ErrPathDenied)
	}
	return nil
}

// LsInfo 列出目录或单个文件元数据，全部路径转换为虚拟挂载路径返回。
func (w *workspace) LsInfo(ctx context.Context, req *adkfs.LsInfoRequest) ([]adkfs.FileInfo, error) {
	target := MountWorkspace
	if req != nil && strings.TrimSpace(req.Path) != "" {
		target = req.Path
	}
	host, err := w.mapPath(ctx, target, false)
	if err != nil {
		return nil, err
	}
	info, err := os.Stat(host)
	if err != nil {
		return nil, wrapPathError(err, host, target)
	}
	if !info.IsDir() {
		return []adkfs.FileInfo{{Path: target, Size: info.Size(), ModifiedAt: info.ModTime().Format(time.RFC3339)}}, nil
	}
	rows, err := w.backend.LsInfo(ctx, &adkfs.LsInfoRequest{Path: host})
	if err != nil {
		return nil, wrapPathError(err, host, target)
	}
	for i := range rows {
		name := rows[i].Path
		rows[i].Path = path.Join(target, name)
		// 官方 local.LsInfo 仅返回文件名，这里补齐目录标记、大小与修改时间。
		if st, err := os.Lstat(filepath.Join(host, name)); err == nil {
			rows[i].IsDir, rows[i].Size, rows[i].ModifiedAt = st.IsDir(), st.Size(), st.ModTime().Format(time.RFC3339)
		}
	}
	return rows, nil
}

// Read 按行分页读取文件，强制收紧单次读取上限为 maxReadLines（200 行）。
func (w *workspace) Read(ctx context.Context, req *adkfs.ReadRequest) (*adkfs.FileContent, error) {
	if req == nil {
		return nil, fmt.Errorf("Read: 请求为空")
	}
	host, err := w.mapPath(ctx, req.FilePath, false)
	if err != nil {
		return nil, err
	}
	mapped := *req
	mapped.FilePath = host
	if mapped.Offset <= 0 {
		mapped.Offset = 1
	}
	if mapped.Limit <= 0 || mapped.Limit > maxReadLines {
		mapped.Limit = maxReadLines
	}
	out, err := w.backend.Read(ctx, &mapped)
	return out, wrapPathError(err, host, req.FilePath)
}

// Write 校验可写挂载与单次体积上限（220 行 / 12 KB），倒逼模型采用小步模块化落盘。
func (w *workspace) Write(ctx context.Context, req *adkfs.WriteRequest) error {
	if req == nil {
		return fmt.Errorf("Write: 请求为空")
	}
	host, err := w.mapPath(ctx, req.FilePath, true)
	if err != nil {
		return err
	}
	lines := strings.Count(req.Content, "\n") + 1
	if len(req.Content) > maxWriteBytes || lines > maxWriteLines {
		return &workspacePathError{
			path: req.FilePath,
			err: fmt.Errorf("%w（当前 %d 行 / %d 字节，单次上限 %d 行 / %d 字节）",
				ErrWriteTooLarge, lines, len(req.Content), maxWriteLines, maxWriteBytes),
		}
	}
	mapped := *req
	mapped.FilePath = host
	return wrapPathError(w.backend.Write(ctx, &mapped), host, req.FilePath)
}

// Edit 复用官方精确局部替换语义，仅补充写权限校验与错误路径脱敏。
func (w *workspace) Edit(ctx context.Context, req *adkfs.EditRequest) error {
	if req == nil {
		return fmt.Errorf("Edit: 请求为空")
	}
	host, err := w.mapPath(ctx, req.FilePath, true)
	if err != nil {
		return err
	}
	mapped := *req
	mapped.FilePath = host
	return wrapPathError(w.backend.Edit(ctx, &mapped), host, req.FilePath)
}

// GrepRaw 委托官方正则检索，截断至最多 200 条命中并将结果路径还原为虚拟路径。
func (w *workspace) GrepRaw(ctx context.Context, req *adkfs.GrepRequest) ([]adkfs.GrepMatch, error) {
	if req == nil || req.Pattern == "" {
		return nil, fmt.Errorf("Grep: pattern 不能为空")
	}
	root := cmp.Or(req.Path, MountWorkspace)
	host, err := w.mapPath(ctx, root, false)
	if err != nil {
		return nil, err
	}
	if _, err := os.Stat(host); err != nil {
		return nil, wrapPathError(err, host, root)
	}
	mapped := *req
	mapped.Path = host
	rows, err := w.backend.GrepRaw(ctx, &mapped)
	if err != nil {
		return nil, wrapPathError(err, host, root)
	}
	if len(rows) > 200 {
		rows = rows[:200]
	}
	for i := range rows {
		rel, err := filepath.Rel(host, rows[i].Path)
		if err != nil {
			return nil, err
		}
		if rel == "." {
			rows[i].Path = root
		} else {
			rows[i].Path = path.Join(root, filepath.ToSlash(rel))
		}
	}
	return rows, nil
}

// GlobInfo 委托官方通配匹配，并对每个命中项重新过一遍 mapPath 以防符号链接越界。
func (w *workspace) GlobInfo(ctx context.Context, req *adkfs.GlobInfoRequest) ([]adkfs.FileInfo, error) {
	if req == nil || req.Pattern == "" {
		return nil, fmt.Errorf("Glob: pattern 不能为空")
	}
	root := path.Clean(cmp.Or(req.Path, MountWorkspace))
	host, err := w.mapPath(ctx, root, false)
	if err != nil {
		return nil, err
	}
	if _, err := os.Stat(host); err != nil {
		return nil, wrapPathError(err, host, root)
	}
	mapped := *req
	mapped.Path = host
	absolute := strings.HasPrefix(req.Pattern, "/")
	if absolute {
		prefix := strings.TrimRight(root, "/") + "/"
		if !strings.HasPrefix(req.Pattern, prefix) {
			return nil, &workspacePathError{path: root, err: fmt.Errorf("glob pattern 必须在指定目录内")}
		}
		mapped.Pattern = strings.TrimPrefix(req.Pattern, prefix)
	}
	rows, err := w.backend.GlobInfo(ctx, &mapped)
	if err != nil {
		return nil, wrapPathError(err, host, root)
	}
	out := make([]adkfs.FileInfo, 0, len(rows))
	for _, row := range rows {
		virtual := path.Join(root, row.Path)
		file, err := w.mapPath(ctx, virtual, false)
		if err != nil {
			continue
		}
		info, err := os.Stat(file)
		if err != nil || info.IsDir() {
			continue
		}
		row.Size, row.ModifiedAt = info.Size(), info.ModTime().Format(time.RFC3339)
		if absolute {
			row.Path = virtual
		}
		out = append(out, row)
	}
	return out, nil
}

// wrapPathError 保留常见标准文件错误语义，并将错误文本中的物理根目录替换为虚拟路径。
func wrapPathError(err error, host, virtual string) error {
	if err == nil {
		return nil
	}
	switch {
	case errors.Is(err, fs.ErrNotExist):
		return &workspacePathError{path: virtual, err: fs.ErrNotExist}
	case errors.Is(err, fs.ErrPermission):
		return &workspacePathError{path: virtual, err: fs.ErrPermission}
	default:
		return errors.New(strings.ReplaceAll(err.Error(), host, virtual))
	}
}

var _ adkfs.Backend = (*workspace)(nil)
