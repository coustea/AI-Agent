package agent

import (
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

// Agent 视角的两个虚拟挂载点。
const (
	MountWorkspace = "/workspace"
	MountSkills    = "/skills"
)

// 虚拟文件系统边界哨兵错误。
var (
	ErrPathDenied = errors.New("path is outside the allowed sandbox")
	ErrReadOnly   = errors.New("挂载点只读")
)

// workspacePathError 包装带虚拟路径的文件错误，供 toolGuard 识别并转为模型可读反馈。
type workspacePathError struct {
	path string
	err  error
}

// Error 返回以虚拟路径为前缀的错误文本，不暴露宿主机路径。
func (e *workspacePathError) Error() string {
	if e.path == "" {
		return e.err.Error()
	}
	return fmt.Sprintf("%s: %v", e.path, e.err)
}

// Unwrap 暴露底层哨兵错误（如 ErrPathDenied、ErrReadOnly、fs.ErrNotExist）。
func (e *workspacePathError) Unwrap() error { return e.err }

// formatWorkspaceError 将虚拟文件系统路径错误转为模型可读提示，供 ToolGuard 复用。
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
	default:
		return "文件操作未完成：" + pathErr.Error() + "。请检查路径后继续。", true
	}
}

// workspace 实现 Eino adkfs.Backend：按 runPrincipal 将虚拟路径映射到宿主机隔离目录并防逃逸，
// 真实文件 IO 委托给官方 eino-ext local.Backend。
type workspace struct {
	backend    adkfs.Backend
	skillsRoot string
}

// newWorkspace 初始化工作区根目录与只读技能根路径，并构造底层官方 local.Backend。
func newWorkspace(workspaceRoot, skillsRoot string) (adkfs.Backend, error) {
	if strings.TrimSpace(workspaceRoot) == "" {
		workspaceRoot = DefaultWorkspaceDir
	}
	if strings.TrimSpace(skillsRoot) == "" {
		skillsRoot = DefaultSkillsDir
	}
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
	backend, err := local.NewBackend(context.Background(), &local.Config{})
	if err != nil {
		return nil, err
	}
	return &workspace{backend: backend, skillsRoot: absSkills}, nil
}

// mapPath 将虚拟路径解析为宿主机安全路径，校验挂载边界、只读限制与软链接逃逸。
func (w *workspace) mapPath(ctx context.Context, virtual string, needWrite bool) (string, error) {
	if strings.TrimSpace(virtual) == "" {
		virtual = MountWorkspace
	}
	run, err := mustPrincipal(ctx)
	if err != nil {
		return "", err
	}

	cleaned := path.Clean(strings.ReplaceAll(virtual, "\\", "/"))
	if strings.HasPrefix(cleaned, "..") {
		return "", &workspacePathError{path: virtual, err: ErrPathDenied}
	}
	if !strings.HasPrefix(cleaned, "/") {
		cleaned = path.Join(MountWorkspace, cleaned)
	}

	mounts := []struct {
		prefix   string
		root     string
		readOnly bool
	}{
		{MountWorkspace, run.Workspace, false},
		{MountSkills, w.skillsRoot, true},
	}
	for _, m := range mounts {
		if cleaned != m.prefix && !strings.HasPrefix(cleaned, m.prefix+"/") {
			continue
		}
		if m.root == "" {
			return "", &workspacePathError{path: cleaned, err: ErrPathDenied}
		}
		rel := strings.TrimPrefix(strings.TrimPrefix(cleaned, m.prefix), "/")
		return resolveUnder(m.root, rel, cleaned, m.readOnly, needWrite)
	}
	return "", &workspacePathError{path: virtual, err: ErrPathDenied}
}

// resolveUnder 在指定挂载根下拼接相对路径，强制校验只读、目录穿越与软链接目标。
func resolveUnder(root, rel, virtual string, readOnly, needWrite bool) (string, error) {
	if needWrite && readOnly {
		return "", &workspacePathError{path: virtual, err: ErrReadOnly}
	}
	if rel != "" {
		normalized := path.Clean("/" + rel)
		if normalized == "/.." || strings.HasPrefix(normalized, "/../") {
			return "", &workspacePathError{path: virtual, err: ErrPathDenied}
		}
	}
	host := filepath.Join(root, filepath.FromSlash(rel))
	if inside, err := isInside(root, host); err != nil {
		return "", &workspacePathError{path: virtual, err: err}
	} else if !inside {
		return "", &workspacePathError{path: virtual, err: ErrPathDenied}
	}
	if err := checkSymlink(root, host); err != nil {
		return "", &workspacePathError{path: virtual, err: err}
	}
	return host, nil
}

// isInside 判断 target 是否严格位于 root 目录内（含 root 自身）。
func isInside(root, target string) (bool, error) {
	rel, err := filepath.Rel(root, target)
	if err != nil {
		return false, fmt.Errorf("%w: %v", ErrPathDenied, err)
	}
	return rel == "." || (rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))), nil
}

// checkSymlink 向上找到最近存在的祖先并解析软链接，防止通过软链接或悬空软链接逃逸沙箱。
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
		// 悬空软链接必须拒绝写入，避免沿其目标在沙箱外建文件。
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

// LsInfo 列出虚拟目录（默认 /workspace）或单个文件的元信息，并将返回路径还原为虚拟路径。
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
		if st, err := os.Lstat(filepath.Join(host, name)); err == nil {
			rows[i].IsDir, rows[i].Size, rows[i].ModifiedAt = st.IsDir(), st.Size(), st.ModTime().Format(time.RFC3339)
		}
	}
	return rows, nil
}

// Read 只读校验后委托官方 local.Backend 读取文件内容。
func (w *workspace) Read(ctx context.Context, req *adkfs.ReadRequest) (*adkfs.FileContent, error) {
	if req == nil {
		return nil, fmt.Errorf("Read: 请求为空")
	}
	host, err := w.mapPath(ctx, req.FilePath, false)
	if err != nil {
		return nil, err
	}
	if _, err := os.Stat(host); err != nil {
		return nil, wrapPathError(err, host, req.FilePath)
	}
	mapped := *req
	mapped.FilePath = host
	out, err := w.backend.Read(ctx, &mapped)
	return out, wrapPathError(err, host, req.FilePath)
}

// Write 校验写权限（拒绝 /skills）后委托官方 local.Backend 写出文件。
func (w *workspace) Write(ctx context.Context, req *adkfs.WriteRequest) error {
	if req == nil {
		return fmt.Errorf("Write: 请求为空")
	}
	host, err := w.mapPath(ctx, req.FilePath, true)
	if err != nil {
		return err
	}
	mapped := *req
	mapped.FilePath = host
	return wrapPathError(w.backend.Write(ctx, &mapped), host, req.FilePath)
}

// Edit 校验写权限（拒绝 /skills）后委托官方 local.Backend 执行局部替换。
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

// GrepRaw 在虚拟目录下搜索内容，最多返回 200 条匹配并将宿主机路径还原为虚拟路径。
func (w *workspace) GrepRaw(ctx context.Context, req *adkfs.GrepRequest) ([]adkfs.GrepMatch, error) {
	if req == nil || req.Pattern == "" {
		return nil, fmt.Errorf("Grep: pattern 不能为空")
	}
	root := req.Path
	if root == "" {
		root = MountWorkspace
	}
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

// GlobInfo 按 glob 模式枚举匹配文件，逐条复检软链接边界并跳过目录。
func (w *workspace) GlobInfo(ctx context.Context, req *adkfs.GlobInfoRequest) ([]adkfs.FileInfo, error) {
	if req == nil || req.Pattern == "" {
		return nil, fmt.Errorf("Glob: pattern 不能为空")
	}
	root := req.Path
	if root == "" {
		root = MountWorkspace
	}
	root = path.Clean(root)
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

// wrapPathError 将宿主机文件错误转换为虚拟路径错误，避免宿主机绝对路径进入模型上下文。
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
