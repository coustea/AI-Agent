package memory

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// 标准模块化记忆文件名
const (
	FilePreferences = "preferences.md" // 个人偏好与习惯（日常习惯、沟通风格、关注重点）
	FileProject     = "project.md"     // 工作区与任务背景（核心目标、上下文背景、关键约定）
	FileLearnings   = "learnings.md"   // 经验总结与知识沉淀（已解决问题、用户反馈、备忘笔记）
)

// GlobalDir 返回用户主目录下的全局记忆存储目录 (~/.tide/memory)
func GlobalDir() string {
	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		return filepath.Join(".", ".tide", "memory")
	}
	return filepath.Join(home, ".tide", "memory")
}

// ProjectDir 返回指定项目工作区下的项目记忆目录 (<workDir>/.tide/memory)
func ProjectDir(workDir string) string {
	workDir = strings.TrimSpace(workDir)
	if workDir == "" {
		if wd, err := os.Getwd(); err == nil {
			workDir = wd
		} else {
			workDir = "."
		}
	}
	return filepath.Join(workDir, ".tide", "memory")
}

// File 表示单个已读取的记忆文件快照
type File struct {
	Scope    string // "global" 或 "project"
	FileName string // "preferences.md", "project.md", "learnings.md"
	Path     string // 文件所在绝对路径
	Content  string // 文件文本内容
}

// Bundle 汇集全局与项目两层的模块化记忆
type Bundle struct {
	WorkDir      string
	GlobalDir    string
	ProjectDir   string
	GlobalFiles  []File
	ProjectFiles []File
}

// HasContent 检查是否有任何非空的记忆内容
func (b *Bundle) HasContent() bool {
	if b == nil {
		return false
	}
	for _, f := range b.GlobalFiles {
		if strings.TrimSpace(f.Content) != "" {
			return true
		}
	}
	for _, f := range b.ProjectFiles {
		if strings.TrimSpace(f.Content) != "" {
			return true
		}
	}
	return false
}

// FormatForPrompt 将记忆体系格式化为适合注入系统提示词的 Markdown 结构
func (b *Bundle) FormatForPrompt() string {
	if b == nil {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("# Long-Term Memory (长期记忆库)\n")
	sb.WriteString("Tide 具备本地持久化记忆系统，分为两个层级的 Markdown 文件：\n")
	sb.WriteString(fmt.Sprintf("- 全局通用记忆: %s\n", b.GlobalDir))
	sb.WriteString(fmt.Sprintf("- 当前项目记忆: %s\n", b.ProjectDir))
	sb.WriteString("你可以通过内置的 read_file、write_file、edit_file 工具随时读取或沉淀新的关键信息到上述对应目录中。\n")
	sb.WriteString("注意：长期记忆是过往沉淀的背景知识与偏好参考，并非不可更改的硬性指令。若记忆内容与用户当前最新提出的明确要求存在冲突，请始终以用户当前最新要求为准。\n\n")

	if !b.HasContent() {
		sb.WriteString("当前尚未记录长期记忆。在会话过程中，若识别到用户的个人偏好习惯、关键任务决策或核心经验沉淀，请及时记录。\n")
		return sb.String()
	}

	sb.WriteString("## 当前生效的长效记忆内容：\n")

	// 1. 全局记忆展示
	for _, f := range b.GlobalFiles {
		content := strings.TrimSpace(f.Content)
		if content != "" {
			sb.WriteString(fmt.Sprintf("\n### [全局记忆] %s (%s)\n", f.FileName, f.Path))
			sb.WriteString(content + "\n")
		}
	}

	// 2. 项目记忆展示
	for _, f := range b.ProjectFiles {
		content := strings.TrimSpace(f.Content)
		if content != "" {
			sb.WriteString(fmt.Sprintf("\n### [项目记忆] %s (%s)\n", f.FileName, f.Path))
			sb.WriteString(content + "\n")
		}
	}

	return sb.String()
}

// LoadBundle 从磁盘加载指定工作区的全局与项目记忆文件，支持传入可选的 customGlobalDir 用于测试隔离
func LoadBundle(workDir string, customGlobalDir ...string) *Bundle {
	globalDir := GlobalDir()
	if len(customGlobalDir) > 0 && strings.TrimSpace(customGlobalDir[0]) != "" {
		globalDir = strings.TrimSpace(customGlobalDir[0])
	}
	projectDir := ProjectDir(workDir)

	bundle := &Bundle{
		WorkDir:    workDir,
		GlobalDir:  globalDir,
		ProjectDir: projectDir,
	}

	// 读取全局记忆：preferences.md 与 learnings.md
	globalNames := []string{FilePreferences, FileLearnings}
	for _, name := range globalNames {
		p := filepath.Join(globalDir, name)
		if data, err := os.ReadFile(p); err == nil {
			content := string(data)
			if strings.TrimSpace(content) != "" {
				bundle.GlobalFiles = append(bundle.GlobalFiles, File{
					Scope:    "global",
					FileName: name,
					Path:     p,
					Content:  content,
				})
			}
		}
	}

	// 读取项目记忆：project.md、preferences.md 与 learnings.md
	projectNames := []string{FileProject, FilePreferences, FileLearnings}
	for _, name := range projectNames {
		p := filepath.Join(projectDir, name)
		if data, err := os.ReadFile(p); err == nil {
			content := string(data)
			if strings.TrimSpace(content) != "" {
				bundle.ProjectFiles = append(bundle.ProjectFiles, File{
					Scope:    "project",
					FileName: name,
					Path:     p,
					Content:  content,
				})
			}
		}
	}

	return bundle
}

// EnsureDirs 创建全局与项目的记忆文件夹
func EnsureDirs(workDir string, customGlobalDir ...string) error {
	globalDir := GlobalDir()
	if len(customGlobalDir) > 0 && strings.TrimSpace(customGlobalDir[0]) != "" {
		globalDir = strings.TrimSpace(customGlobalDir[0])
	}
	if err := os.MkdirAll(globalDir, 0o755); err != nil {
		return fmt.Errorf("failed to create global memory dir %s: %w", globalDir, err)
	}

	projectDir := ProjectDir(workDir)
	if err := os.MkdirAll(projectDir, 0o755); err != nil {
		return fmt.Errorf("failed to create project memory dir %s: %w", projectDir, err)
	}

	return nil
}

// InitTemplates 初始化记忆模板文件（仅在文件不存在时创建，不覆盖已有内容）
func InitTemplates(workDir string, customGlobalDir ...string) error {
	if err := EnsureDirs(workDir, customGlobalDir...); err != nil {
		return err
	}

	globalDir := GlobalDir()
	if len(customGlobalDir) > 0 && strings.TrimSpace(customGlobalDir[0]) != "" {
		globalDir = strings.TrimSpace(customGlobalDir[0])
	}
	projectDir := ProjectDir(workDir)

	initFileIfNotExists(filepath.Join(globalDir, FilePreferences), `# 个人偏好与习惯 (Global Preferences)
- 交流语言: 优先使用中文交流，逻辑严谨、条理清晰
- 协作风格: 简洁高效、直奔主题，必要时提供结构化分析
`)

	initFileIfNotExists(filepath.Join(projectDir, FileProject), `# 工作区与任务背景 (Workspace Context)
- 目标定位: Tide 智能助手工作区
- 核心要求: 协助用户高效执行任务，在需要时主动通过内置工具探索与操作文件
`)

	return nil
}

func initFileIfNotExists(path, defaultContent string) {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		_ = os.WriteFile(path, []byte(defaultContent), 0o644)
	}
}
