package tutor

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	adkfs "github.com/cloudwego/eino/adk/filesystem"
)

// Agent 视角的虚拟根路径。
const (
	// MountWorkspace 会话工作目录，可读写
	MountWorkspace = "/workspace"
	// MountOffload 工具结果卸载目录，可读写
	MountOffload = "/offload"
	// MountSkills 技能目录，只读
	MountSkills = "/skills"
)

// ErrPathDenied 表示路径越界或不允许访问。
var ErrPathDenied = errors.New("path is outside the allowed sandbox")

// ErrReadOnly 表示对只读挂载点做了写操作。
var ErrReadOnly = errors.New("mount is read-only")

// Sandbox 实现 adk/filesystem.Backend，把 Agent 的虚拟路径映射到宿主机目录。
//
// 三个挂载点：
//   - /workspace  → {WorkspaceDir}/{uid}/{sid}   可读写
//   - /.offload   → {OffloadDir}/{uid}/{sid}     可读写
//   - /skills     → {SkillsDir}                  只读
//
// 其余路径一律拒绝。所有路径都经过 Clean + 前缀校验 + 符号链接解析，
// 防止 ../ 逃逸与软链接逃逸。
type Sandbox struct {
	workspace string
	offload   string
	skills    string
}

// NewSandbox 创建沙箱。三个目录都会被创建（skills 除外，它应已存在）。
func NewSandbox(workspace, offload, skills string) (*Sandbox, error) {
	absWorkspace, err := filepath.Abs(workspace)
	if err != nil {
		return nil, fmt.Errorf("解析工作目录失败: %w", err)
	}
	absOffload, err := filepath.Abs(offload)
	if err != nil {
		return nil, fmt.Errorf("解析卸载目录失败: %w", err)
	}

	var absSkills string
	if strings.TrimSpace(skills) != "" {
		absSkills, err = filepath.Abs(skills)
		if err != nil {
			return nil, fmt.Errorf("解析技能目录失败: %w", err)
		}
	}

	if err := os.MkdirAll(absWorkspace, 0o755); err != nil {
		return nil, fmt.Errorf("创建工作目录失败: %w", err)
	}
	if err := os.MkdirAll(absOffload, 0o755); err != nil {
		return nil, fmt.Errorf("创建卸载目录失败: %w", err)
	}

	return &Sandbox{
		workspace: absWorkspace,
		offload:   absOffload,
		skills:    absSkills,
	}, nil
}

// mapPath 把虚拟路径解析成宿主机真实路径，并做越界校验。
//
// 校验顺序：
//  1. Clean 归一化，去掉 ".." 等相对成分；
//  2. 拒绝 Clean 后仍以 ".." 开头的路径；
//  3. 前缀匹配挂载点，得到宿主路径；
//  4. 对父目录做 EvalSymlinks，防止软链接指向沙箱外；
//  5. 最后再次确认结果仍在该挂载点下。
//
// 返回的 readOnly 表示该挂载点是否只读。
func (s *Sandbox) mapPath(virtual string, needWrite bool) (host string, readOnly bool, err error) {
	if strings.TrimSpace(virtual) == "" {
		virtual = MountWorkspace
	}

	// 统一用 / 分隔，兼容 Windows 风格输入。
	cleaned := path.Clean(strings.ReplaceAll(virtual, "\\", "/"))
	if strings.HasPrefix(cleaned, "..") {
		return "", false, fmt.Errorf("%w: %s", ErrPathDenied, virtual)
	}
	if !strings.HasPrefix(cleaned, "/") {
		// 相对路径统一视为相对 /workspace，符合 Agent 的直觉。
		cleaned = path.Join(MountWorkspace, cleaned)
	}

	var root string
	switch {
	case cleaned == MountWorkspace || strings.HasPrefix(cleaned, MountWorkspace+"/"):
		root = s.workspace
		rel := strings.TrimPrefix(cleaned, MountWorkspace)
		rel = strings.TrimPrefix(rel, "/")
		return s.resolve(root, rel, false, needWrite)

	case cleaned == MountOffload || strings.HasPrefix(cleaned, MountOffload+"/"):
		root = s.offload
		rel := strings.TrimPrefix(cleaned, MountOffload)
		rel = strings.TrimPrefix(rel, "/")
		return s.resolve(root, rel, false, needWrite)

	case cleaned == MountSkills || strings.HasPrefix(cleaned, MountSkills+"/"):
		if s.skills == "" {
			return "", false, fmt.Errorf("%w: 技能目录未配置", ErrPathDenied)
		}
		rel := strings.TrimPrefix(cleaned, MountSkills)
		rel = strings.TrimPrefix(rel, "/")
		return s.resolve(s.skills, rel, true, needWrite)

	default:
		return "", false, fmt.Errorf("%w: %s", ErrPathDenied, virtual)
	}
}

// resolve 在给定根下解析相对路径，并做符号链接与前缀双重校验。
func (s *Sandbox) resolve(root, rel string, readOnly, needWrite bool) (string, bool, error) {
	if needWrite && readOnly {
		return "", readOnly, fmt.Errorf("%w: %s", ErrReadOnly, root)
	}

	// rel 已经过 Clean，但再检查一次 "../" 前缀，防住 path.Join 的边界情况。
	if rel != "" {
		normalized := path.Clean("/" + rel)
		if normalized == "/.." || strings.HasPrefix(normalized, "/../") {
			return "", readOnly, fmt.Errorf("%w: %s", ErrPathDenied, rel)
		}
	}

	host := filepath.Join(root, filepath.FromSlash(rel))

	// 前缀校验：host 必须落在 root 内。
	// 用 filepath.Rel 而非字符串 HasPrefix，避免 "/root2" 被 "/root" 误判为子目录。
	inside, err := isInside(root, host)
	if err != nil {
		return "", readOnly, err
	}
	if !inside {
		return "", readOnly, fmt.Errorf("%w: %s", ErrPathDenied, rel)
	}

	// 符号链接校验：对已存在的最深父目录做 EvalSymlinks，
	// 确保软链接不会把我们带出沙箱。
	if err := s.checkSymlink(root, host); err != nil {
		return "", readOnly, err
	}

	return host, readOnly, nil
}

// isInside 判断 target 是否位于 root 之内（含 root 本身）。
func isInside(root, target string) (bool, error) {
	rel, err := filepath.Rel(root, target)
	if err != nil {
		return false, fmt.Errorf("%w: %v", ErrPathDenied, err)
	}
	if rel == "." {
		return true, nil
	}
	if rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return false, nil
	}
	return true, nil
}

// checkSymlink 沿父目录链解析符号链接，确认最终位置仍在 root 内。
func (s *Sandbox) checkSymlink(root, host string) error {
	// 找到已存在的最深祖先目录（目标文件本身可能还不存在）。
	probe := host
	for {
		if _, err := os.Lstat(probe); err == nil {
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
		// 路径不存在属于正常情况（新建文件），不视为越界。
		if os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("%w: %v", ErrPathDenied, err)
	}

	// root 本身也可能是软链接（如 /tmp → /private/tmp），先解析它再比较。
	realRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		realRoot = root
	}

	inside, err := isInside(realRoot, resolved)
	if err != nil {
		return err
	}
	if !inside {
		return fmt.Errorf("%w: 符号链接指向沙箱外", ErrPathDenied)
	}
	return nil
}

// denyMessage 把沙箱拒绝转成给模型的说明文本。
//
// 为什么返回文本而不是 error：eino 会把工具返回的 error 升级为节点错误，
// 导致整轮对话失败。而「读取了不该读的路径」是模型可以自行纠正的常规情况，
// 把拒绝原因作为工具结果反馈给模型，它就能换一个合法路径重试——
// 这既不降低安全性（仍然坚决不执行越界操作），又不会中断对话。
func (s *Sandbox) denyMessage(err error) string {
	switch {
	case errors.Is(err, ErrReadOnly):
		return "操作被拒绝：该路径为只读挂载点（/skills），不能写入。请改为写入 /workspace/ 下的文件。"
	case errors.Is(err, ErrPathDenied):
		return "操作被拒绝：" + err.Error() +
			"。只能访问 /workspace（可读写）、/.offload（可读写）与 /skills（只读）。" +
			"请改用这些目录下的合法路径，不要尝试访问系统路径。"
	default:
		return "操作失败：" + err.Error()
	}
}

// LsInfo 列出目录内容。
func (s *Sandbox) LsInfo(_ context.Context, req *adkfs.LsInfoRequest) ([]adkfs.FileInfo, error) {
	target := MountWorkspace
	if req != nil && strings.TrimSpace(req.Path) != "" {
		target = req.Path
	}

	host, _, err := s.mapPath(target, false)
	if err != nil {
		return []adkfs.FileInfo{{
			Path:  s.denyMessage(err),
			IsDir: false,
			Size:  0,
		}}, nil
	}

	entries, err := os.ReadDir(host)
	if err != nil {
		return nil, err
	}

	infos := make([]adkfs.FileInfo, 0, len(entries))
	for _, e := range entries {
		info, err := e.Info()
		if err != nil {
			continue
		}
		virtual := path.Join(target, e.Name())
		infos = append(infos, adkfs.FileInfo{
			Path:       virtual,
			IsDir:      e.IsDir(),
			Size:       info.Size(),
			ModifiedAt: info.ModTime().Format(time.RFC3339),
		})
	}

	sort.Slice(infos, func(i, j int) bool { return infos[i].Path < infos[j].Path })
	return infos, nil
}

// Read 读取文件内容，支持按行偏移与上限。
func (s *Sandbox) Read(_ context.Context, req *adkfs.ReadRequest) (*adkfs.FileContent, error) {
	if req == nil {
		return nil, fmt.Errorf("Read: 请求为空")
	}

	host, _, err := s.mapPath(req.FilePath, false)
	if err != nil {
		// 返回说明文本而非 error，让模型能自行纠正路径。
		return &adkfs.FileContent{Content: s.denyMessage(err)}, nil
	}

	data, err := os.ReadFile(host)
	if err != nil {
		return nil, err
	}

	content := string(data)

	// Offset/Limit 只在需要时按行切分，避免大文件全量内存拷贝后再丢弃。
	if req.Offset > 1 || req.Limit > 0 {
		lines := strings.Split(content, "\n")

		start := req.Offset - 1
		if start < 0 {
			start = 0
		}
		if start > len(lines) {
			start = len(lines)
		}

		end := len(lines)
		if req.Limit > 0 && start+req.Limit < end {
			end = start + req.Limit
		}

		content = strings.Join(lines[start:end], "\n")
	}

	return &adkfs.FileContent{Content: content}, nil
}

// Write 写入文件，自动创建父目录。
func (s *Sandbox) Write(_ context.Context, req *adkfs.WriteRequest) error {
	if req == nil {
		return fmt.Errorf("Write: 请求为空")
	}

	host, _, err := s.mapPath(req.FilePath, true)
	if err != nil {
		return err
	}

	if err := os.MkdirAll(filepath.Dir(host), 0o755); err != nil {
		return err
	}
	return os.WriteFile(host, []byte(req.Content), 0o644)
}

// Edit 精确替换文件中的字符串。
func (s *Sandbox) Edit(_ context.Context, req *adkfs.EditRequest) error {
	if req == nil {
		return fmt.Errorf("Edit: 请求为空")
	}
	if req.OldString == "" {
		return fmt.Errorf("Edit: old_string 不能为空")
	}
	if req.OldString == req.NewString {
		return fmt.Errorf("Edit: old_string 与 new_string 相同")
	}

	host, _, err := s.mapPath(req.FilePath, true)
	if err != nil {
		return err
	}

	data, err := os.ReadFile(host)
	if err != nil {
		return err
	}

	content := string(data)
	count := strings.Count(content, req.OldString)
	if count == 0 {
		return fmt.Errorf("Edit: 未找到待替换内容")
	}
	if count > 1 && !req.ReplaceAll {
		return fmt.Errorf("Edit: 待替换内容出现 %d 次，需设置 replace_all 或提供更精确的片段", count)
	}

	var updated string
	if req.ReplaceAll {
		updated = strings.ReplaceAll(content, req.OldString, req.NewString)
	} else {
		updated = strings.Replace(content, req.OldString, req.NewString, 1)
	}

	return os.WriteFile(host, []byte(updated), 0o644)
}

// GrepRaw 在目录内按正则搜索。
func (s *Sandbox) GrepRaw(ctx context.Context, req *adkfs.GrepRequest) ([]adkfs.GrepMatch, error) {
	if req == nil || req.Pattern == "" {
		return nil, fmt.Errorf("Grep: pattern 不能为空")
	}

	pattern := req.Pattern
	if req.CaseInsensitive {
		pattern = "(?i)" + pattern
	}
	re, err := regexp.Compile(pattern)
	if err != nil {
		return nil, fmt.Errorf("Grep: 正则无效: %w", err)
	}

	root := MountWorkspace
	if strings.TrimSpace(req.Path) != "" {
		root = req.Path
	}

	hostRoot, _, err := s.mapPath(root, false)
	if err != nil {
		return []adkfs.GrepMatch{{Content: s.denyMessage(err), Path: root, Line: 0}}, nil
	}

	var matches []adkfs.GrepMatch

	walkErr := filepath.WalkDir(hostRoot, func(p string, d os.DirEntry, err error) error {
		if err != nil {
			return nil // 跳过不可读项，不让单个文件中断整个搜索
		}
		if d.IsDir() {
			// 跳过 .git 等噪音目录
			if name := d.Name(); name == ".git" || name == "node_modules" {
				return filepath.SkipDir
			}
			return nil
		}
		if req.FileType != "" && !strings.HasSuffix(d.Name(), "."+strings.TrimPrefix(req.FileType, ".")) {
			return nil
		}

		data, err := os.ReadFile(p)
		if err != nil {
			return nil
		}
		// 二进制文件跳过：含 NUL 字节即视为二进制。
		if strings.ContainsRune(string(data), '\x00') {
			return nil
		}

		rel, _ := filepath.Rel(hostRoot, p)
		virtual := path.Join(root, filepath.ToSlash(rel))

		for i, line := range strings.Split(string(data), "\n") {
			if !re.MatchString(line) {
				continue
			}
			matches = append(matches, adkfs.GrepMatch{
				Content: line,
				Path:    virtual,
				Line:    i + 1,
			})
			if len(matches) >= 200 {
				return io.EOF // 用 EOF 提前结束遍历
			}
		}
		return nil
	})

	if walkErr != nil && !errors.Is(walkErr, io.EOF) {
		return nil, walkErr
	}

	return matches, nil
}

// GlobInfo 按 glob 模式匹配文件路径。
func (s *Sandbox) GlobInfo(_ context.Context, req *adkfs.GlobInfoRequest) ([]adkfs.FileInfo, error) {
	if req == nil || req.Pattern == "" {
		return nil, fmt.Errorf("Glob: pattern 不能为空")
	}

	root := MountWorkspace
	if strings.TrimSpace(req.Path) != "" {
		root = req.Path
	}

	hostRoot, _, err := s.mapPath(root, false)
	if err != nil {
		return []adkfs.FileInfo{{Path: s.denyMessage(err)}}, nil
	}

	var infos []adkfs.FileInfo

	walkErr := filepath.WalkDir(hostRoot, func(p string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			if name := d.Name(); name == ".git" || name == "node_modules" {
				return filepath.SkipDir
			}
			return nil
		}

		rel, _ := filepath.Rel(hostRoot, p)
		virtual := path.Join(root, filepath.ToSlash(rel))

		// 用 path.Match 匹配虚拟路径；同时支持按 basename 匹配的常见写法。
		matched, _ := path.Match(req.Pattern, virtual)
		if !matched {
			matched, _ = path.Match(req.Pattern, path.Base(virtual))
		}
		if !matched {
			return nil
		}

		info, err := d.Info()
		if err != nil {
			return nil
		}
		infos = append(infos, adkfs.FileInfo{
			Path:       virtual,
			IsDir:      false,
			Size:       info.Size(),
			ModifiedAt: info.ModTime().Format(time.RFC3339),
		})
		return nil
	})

	if walkErr != nil {
		return nil, walkErr
	}

	sort.Slice(infos, func(i, j int) bool { return infos[i].Path < infos[j].Path })
	return infos, nil
}

// 编译期断言：确保 Sandbox 满足 filesystem.Backend。
var _ adkfs.Backend = (*Sandbox)(nil)

// WorkspaceRoot 返回宿主机工作目录路径，供测试与日志使用。
func (s *Sandbox) WorkspaceRoot() string { return s.workspace }

// OffloadRoot 返回宿主机卸载目录路径。
func (s *Sandbox) OffloadRoot() string { return s.offload }
