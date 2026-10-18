package builtin

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// GrepTool 在工作区内按正则表达式搜索代码与文件内容，学习自 learn-claude-code 中的 run_grep
type GrepTool struct {
	workDir *WorkDirRef
}

func NewGrepTool(workDir *WorkDirRef) *GrepTool {
	return &GrepTool{workDir: workDir}
}

func (t *GrepTool) Name() string {
	return "grep"
}

func (t *GrepTool) Description() string {
	return "Search for regular expression patterns across files in the workspace. Returns matching file paths, line numbers, and content. Useful for locating function/variable definitions, configurations, or references."
}

func (t *GrepTool) Schema() json.RawMessage {
	return json.RawMessage(`{
		"type": "object",
		"properties": {
			"pattern": {
				"type": "string",
				"description": "The regular expression pattern to search for"
			},
			"path": {
				"type": "string",
				"description": "Optional subdirectory or file path to search within (defaults to workspace root)"
			},
			"include": {
				"type": "string",
				"description": "Optional glob pattern to filter files by name, e.g. '*.go', '*.ts', '*.json'"
			},
			"max_results": {
				"type": "integer",
				"description": "Optional maximum number of matching lines to return (defaults to 100)"
			}
		},
		"required": ["pattern"]
	}`)
}

type GrepInput struct {
	Pattern    string `json:"pattern"`
	Path       string `json:"path,omitempty"`
	Include    string `json:"include,omitempty"`
	MaxResults int    `json:"max_results,omitempty"`
}

// 常见二进制与打包文件扩展名黑名单
var binaryExtensions = map[string]bool{
	".exe": true, ".dll": true, ".so": true, ".dylib": true, ".bin": true,
	".png": true, ".jpg": true, ".jpeg": true, ".gif": true, ".ico": true,
	".zip": true, ".tar": true, ".gz": true, ".tgz": true, ".bz2": true,
	".pdf": true, ".woff": true, ".woff2": true, ".ttf": true, ".eot": true,
	".mp3": true, ".mp4": true, ".wav": true, ".mov": true, ".avi": true,
}

func (t *GrepTool) Execute(ctx context.Context, args json.RawMessage) (string, error) {
	var input GrepInput
	if err := json.Unmarshal(args, &input); err != nil {
		return "", fmt.Errorf("failed to parse grep arguments: %w", err)
	}

	pattern := strings.TrimSpace(input.Pattern)
	if pattern == "" {
		return "", fmt.Errorf("pattern cannot be empty")
	}

	re, err := regexp.Compile(pattern)
	if err != nil {
		return "", fmt.Errorf("invalid regular expression: %w", err)
	}

	searchPath := input.Path
	if strings.TrimSpace(searchPath) == "" {
		searchPath = "."
	}

	targetPath, err := SafePath(t.workDir.Get(), searchPath)
	if err != nil {
		return "", err
	}

	workDirAbs := t.workDir.Get()
	if abs, err := filepath.Abs(workDirAbs); err == nil {
		workDirAbs = abs
	}

	maxResults := input.MaxResults
	if maxResults <= 0 {
		maxResults = 100
	}

	var includeRe *regexp.Regexp
	if strings.TrimSpace(input.Include) != "" {
		includeRe, err = globToRegexp(input.Include)
		if err != nil {
			return "", fmt.Errorf("invalid include pattern: %w", err)
		}
	}

	info, err := os.Stat(targetPath)
	if err != nil {
		return "", fmt.Errorf("failed to access %s: %w", searchPath, err)
	}

	var results []string
	var matchCount int
	var truncated bool

	if !info.IsDir() {
		// 单文件检索
		results, truncated = grepFile(ctx, targetPath, workDirAbs, re, maxResults)
	} else {
		// 目录递归遍历检索
		err = filepath.WalkDir(targetPath, func(path string, d fs.DirEntry, walkErr error) error {
			select {
			case <-ctx.Done():
				return ctx.Err()
			default:
			}

			if walkErr != nil {
				return nil
			}

			// 跳过版本控制与缓存目录
			if d.IsDir() {
				name := d.Name()
				if name == ".git" || name == ".tide" || name == "node_modules" || name == "vendor" {
					return filepath.SkipDir
				}
				return nil
			}

			// 扩展名过滤
			ext := strings.ToLower(filepath.Ext(d.Name()))
			if binaryExtensions[ext] {
				return nil
			}

			// 文件通配名过滤
			if includeRe != nil && !includeRe.MatchString(d.Name()) {
				return nil
			}

			remaining := maxResults - matchCount
			if remaining <= 0 {
				truncated = true
				return fs.SkipAll
			}

			fileMatches, fileTrunc := grepFile(ctx, path, workDirAbs, re, remaining)
			results = append(results, fileMatches...)
			matchCount += len(fileMatches)
			if fileTrunc || matchCount >= maxResults {
				truncated = true
				return fs.SkipAll
			}

			return nil
		})
		if err != nil && err != fs.SkipAll {
			return "", err
		}
	}

	if len(results) == 0 {
		return "(no matches)", nil
	}

	out := strings.Join(results, "\n")
	if truncated {
		out += fmt.Sprintf("\n... (more matches omitted; limit of %d results reached)", maxResults)
	}

	return out, nil
}

// grepFile 扫描单个文本文件，返回匹配项列表
func grepFile(ctx context.Context, fullPath, workDirAbs string, re *regexp.Regexp, budget int) (matches []string, truncated bool) {
	file, err := os.Open(fullPath)
	if err != nil {
		return nil, false
	}
	defer file.Close()

	// 嗅探前 512 字节以快速阻断二进制文件
	header := make([]byte, 512)
	n, _ := file.Read(header)
	if n > 0 && bytes.Contains(header[:n], []byte{0}) {
		return nil, false
	}
	_, _ = file.Seek(0, 0)

	relPath, err := filepath.Rel(workDirAbs, fullPath)
	if err != nil {
		relPath = fullPath
	}
	relSlash := filepath.ToSlash(relPath)

	scanner := bufio.NewScanner(file)
	lineNum := 0

	for scanner.Scan() {
		select {
		case <-ctx.Done():
			return matches, false
		default:
		}

		lineNum++
		line := scanner.Text()
		if re.MatchString(line) {
			matches = append(matches, fmt.Sprintf("%s:%d: %s", relSlash, lineNum, strings.TrimRight(line, "\r\n")))
			if len(matches) >= budget {
				return matches, true
			}
		}
	}

	return matches, false
}
