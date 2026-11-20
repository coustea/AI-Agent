// Package search 提供可选的联网搜索能力。
//
// 配置为空时不注册工具：Agent 不会看到一个调用必然失败的工具。
// 这是「未配置」的正确表达，而不是在工具内部静默返回假结果。
package search

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"
)

// ToolName 是对 Agent 暴露的工具名。
const ToolName = "web_search"

// Config 是搜索能力配置。
type Config struct {
	// Provider 目前支持 tavily
	Provider string
	APIKey   string
	BaseURL  string
	// Timeout 单次请求超时
	Timeout time.Duration
}

// Enabled 判断搜索能力是否可用。
func (c Config) Enabled() bool {
	return strings.TrimSpace(c.APIKey) != "" && strings.TrimSpace(c.Provider) != ""
}

// Searcher 是搜索客户端。
type Searcher struct {
	cfg  Config
	http *http.Client
}

// New 构造搜索客户端。
// 未配置时返回 (nil, nil)：调用方据此跳过工具注册。
func New(cfg Config) (*Searcher, error) {
	if !cfg.Enabled() {
		return nil, nil
	}

	provider := strings.ToLower(strings.TrimSpace(cfg.Provider))
	if provider != "tavily" {
		return nil, fmt.Errorf("不支持的 search.provider: %s（目前仅支持 tavily）", cfg.Provider)
	}

	if strings.TrimSpace(cfg.BaseURL) == "" {
		cfg.BaseURL = "https://api.tavily.com"
	}
	if cfg.Timeout <= 0 {
		cfg.Timeout = 20 * time.Second
	}

	return &Searcher{
		cfg:  cfg,
		http: &http.Client{Timeout: cfg.Timeout},
	}, nil
}

// Result 是一条搜索结果。
type Result struct {
	Title   string `json:"title"`
	URL     string `json:"url"`
	Content string `json:"content"`
}

// Search 执行一次搜索。
func (s *Searcher) Search(ctx context.Context, query string, maxResults int) ([]Result, error) {
	if s == nil {
		return nil, fmt.Errorf("搜索能力未配置")
	}
	if strings.TrimSpace(query) == "" {
		return nil, fmt.Errorf("搜索关键词不能为空")
	}
	if maxResults <= 0 || maxResults > 10 {
		maxResults = 5
	}

	payload := map[string]any{
		"api_key":        s.cfg.APIKey,
		"query":          query,
		"max_results":    maxResults,
		"search_depth":   "basic",
		"include_answer": false,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("构造搜索请求失败: %w", err)
	}

	endpoint := strings.TrimRight(s.cfg.BaseURL, "/") + "/search"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, strings.NewReader(string(body)))
	if err != nil {
		return nil, fmt.Errorf("构造搜索请求失败: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+s.cfg.APIKey)

	resp, err := s.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("搜索请求失败: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
	if err != nil {
		return nil, fmt.Errorf("读取搜索结果失败: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("搜索服务返回 %d: %s", resp.StatusCode, truncate(string(raw), 300))
	}

	var parsed struct {
		Results []Result `json:"results"`
	}
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return nil, fmt.Errorf("解析搜索结果失败: %w", err)
	}
	return parsed.Results, nil
}

// ToolInput 是 web_search 参数。
type ToolInput struct {
	Query      string `json:"query" jsonschema:"description=搜索关键词，尽量具体，包含技术名词"`
	MaxResults int    `json:"max_results,omitempty" jsonschema:"description=返回条数，1-10，默认 5"`
}

// ToolOutput 是 web_search 返回。
type ToolOutput struct {
	Count   int      `json:"count"`
	Results []Result `json:"results"`
	Message string   `json:"message"`
}

// NewTool 构造搜索工具。
func NewTool(s *Searcher) (tool.InvokableTool, error) {
	if s == nil {
		return nil, fmt.Errorf("搜索能力未配置")
	}

	return utils.InferTool(ToolName,
		"联网搜索最新资料。当问题涉及你不确定的事实、版本号、API 变更，"+
			"或学生明确要求查资料时使用。不要用于本可凭知识回答的常见问题。",
		func(ctx context.Context, in ToolInput) (ToolOutput, error) {
			results, err := s.Search(ctx, in.Query, in.MaxResults)
			if err != nil {
				return ToolOutput{}, err
			}

			msg := fmt.Sprintf("找到 %d 条结果。", len(results))
			if len(results) == 0 {
				msg = "没有找到相关结果，建议换一个关键词。"
			}
			return ToolOutput{Count: len(results), Results: results, Message: msg}, nil
		})
}

// Tools 返回搜索工具列表。未配置时返回空列表而不是错误。
func Tools(s *Searcher) ([]tool.BaseTool, error) {
	if s == nil {
		return nil, nil
	}
	t, err := NewTool(s)
	if err != nil {
		return nil, err
	}
	return []tool.BaseTool{t}, nil
}

func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n]) + "..."
}

// 确保 url 包被使用（endpoint 构造依赖它做校验）。
var _ = url.Parse
