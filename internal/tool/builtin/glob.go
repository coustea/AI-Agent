package builtin

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// skippedDirs 是检索类工具（glob/grep）统一跳过的目录集合：
// 版本控制、本地状态、缓存与依赖目录，避免无意义遍历与噪声命中。
var skippedDirs = map[string]bool{
	".git":         true,
	".tide":        true,
	".agents":      true,
	"node_modules": true,
	"vendor":       true,
}

// GlobTool 基于模式匹配查找工作区内的文件，学习自 learn-claude-code 中的 run_glob
type GlobTool struct {
	workDir *WorkDirRef
}

func NewGlobTool(workDir *WorkDirRef) *GlobTool {
	return &GlobTool{workDir: workDir}
}

func (t *GlobTool) Name() string {
	return "glob"
}

func (t *GlobTool) Description() string {
	return "Find files matching a glob pattern across the workspace (supports recursive **). Use this to explore repository structure or locate files when exact paths are unknown."
}

func (t *GlobTool) Schema() json.RawMessage {
	return json.RawMessage(`{
		"type": "object",
		"properties": {
			"pattern": {
				"type": "string",
				"description": "Glob pattern to match files against, e.g. **/*.go, internal/**/*.go, or *.md"
			}
		},
		"required": ["pattern"]
	}`)
}

type GlobInput struct {
	Pattern string `json:"pattern"`
}

func (t *GlobTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	var input GlobInput
	if err := json.Unmarshal(args, &input); err != nil {
		return "", fmt.Errorf("failed to parse glob arguments: %w", err)
	}

	pattern := strings.TrimSpace(input.Pattern)
	if pattern == "" {
		return "", fmt.Errorf("pattern cannot be empty")
	}

	workDirAbs, err := filepath.Abs(t.workDir.Get())
	if err != nil {
		return "", fmt.Errorf("failed to get absolute workdir: %w", err)
	}

	re, err := globToRegexp(pattern)
	if err != nil {
		return "", fmt.Errorf("invalid glob pattern: %w", err)
	}

	var matches []string
	matchSet := make(map[string]struct{})

	err = filepath.WalkDir(workDirAbs, func(path string, d fs.DirEntry, err error) error {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		if err != nil {
			// 条目不可访问（权限、悬空链接等）：跳过该子树而非中断整次遍历，
			// 也不能静默 return nil——SkipDir 让语义显式化。
			return filepath.SkipDir
		}

		rel, relErr := filepath.Rel(workDirAbs, path)
		if relErr != nil {
			return filepath.SkipDir
		}
		if rel == "." {
			return nil
		}
		relSlash := filepath.ToSlash(rel)

		// 统一跳过版本控制、缓存与依赖目录
		if d.IsDir() && skippedDirs[d.Name()] {
			return filepath.SkipDir
		}

		if re.MatchString(relSlash) {
			if _, exists := matchSet[relSlash]; !exists {
				matchSet[relSlash] = struct{}{}
				matches = append(matches, relSlash)
			}
		}

		return nil
	})

	if err != nil {
		return "", err
	}

	sort.Strings(matches)

	if len(matches) == 0 {
		return "(no matches)", nil
	}

	const maxMatches = 200
	shown := matches
	var omitted bool
	if len(matches) > maxMatches {
		shown = matches[:maxMatches]
		omitted = true
	}

	var result strings.Builder
	for i, m := range shown {
		if i > 0 {
			result.WriteString("\n")
		}
		result.WriteString(m)
	}

	if omitted {
		result.WriteString("\n... (more matches omitted; narrow the pattern)")
	}

	return result.String(), nil
}

// globToRegexp 将包含 *、?、** 的 glob 通配符表达式编译为高效的正则表达式
func globToRegexp(pattern string) (*regexp.Regexp, error) {
	pattern = filepath.ToSlash(strings.TrimPrefix(pattern, "./"))
	var sb strings.Builder
	sb.WriteString("^")

	i := 0
	n := len(pattern)
	for i < n {
		switch {
		case i+1 < n && pattern[i:i+2] == "**":
			i += 2
			if i < n && pattern[i] == '/' {
				i++
				sb.WriteString("(.*/)?")
			} else {
				sb.WriteString(".*")
			}
		case pattern[i] == '*':
			sb.WriteString("[^/]*")
			i++
		case pattern[i] == '?':
			sb.WriteString("[^/]")
			i++
		case strings.ContainsRune(".+^$()|{}[]\\", rune(pattern[i])):
			sb.WriteString("\\")
			sb.WriteByte(pattern[i])
			i++
		default:
			sb.WriteByte(pattern[i])
			i++
		}
	}

	sb.WriteString("$")
	return regexp.Compile(sb.String())
}
