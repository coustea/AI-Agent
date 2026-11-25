package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"
)

// SearchConfig 是联网搜索工具的配置参数。
type SearchConfig struct {
	Provider string
	APIKey   string
	BaseURL  string
	Timeout  time.Duration
}

// SearchResult 描述单条联网搜索命中结果。
type SearchResult struct {
	Title   string `json:"title"`
	URL     string `json:"url"`
	Content string `json:"content"`
}

// WebSearchInput 是 web_search 工具的入参。
type WebSearchInput struct {
	Query      string `json:"query" jsonschema:"description=搜索关键词，尽量具体，包含技术名词"`
	MaxResults int    `json:"max_results,omitempty" jsonschema:"description=返回条数，1-10，默认 5"`
}

// WebSearchOutput 是 web_search 工具的返回值。
type WebSearchOutput struct {
	Count   int            `json:"count"`
	Results []SearchResult `json:"results"`
	Message string         `json:"message"`
}

// NewWebSearch 构造联网搜索工具；未配置凭据时返回 (nil, nil)，调用方跳过注册。
func NewWebSearch(cfg SearchConfig) (tool.InvokableTool, error) {
	if strings.TrimSpace(cfg.APIKey) == "" || strings.TrimSpace(cfg.Provider) == "" {
		return nil, nil
	}
	if !strings.EqualFold(strings.TrimSpace(cfg.Provider), "tavily") {
		return nil, fmt.Errorf("不支持的 search.provider: %s（目前仅支持 tavily）", cfg.Provider)
	}
	if strings.TrimSpace(cfg.BaseURL) == "" {
		cfg.BaseURL = "https://api.tavily.com"
	}
	if cfg.Timeout <= 0 {
		cfg.Timeout = 20 * time.Second
	}

	client := &http.Client{Timeout: cfg.Timeout}
	endpoint := strings.TrimRight(cfg.BaseURL, "/")
	if !strings.HasSuffix(endpoint, "/search") {
		endpoint += "/search"
	}

	return utils.InferTool(ToolWebSearch,
		"联网搜索最新资料。当问题涉及你不确定的事实、版本号、API 变更，或学生明确要求查资料时使用。不要用于本可凭知识回答的常见问题。",
		func(ctx context.Context, in WebSearchInput) (WebSearchOutput, error) {
			if strings.TrimSpace(in.Query) == "" {
				return WebSearchOutput{}, fmt.Errorf("搜索关键词不能为空")
			}
			maxRes := in.MaxResults
			if maxRes <= 0 || maxRes > 10 {
				maxRes = 5
			}
			body, err := json.Marshal(map[string]any{
				"query": in.Query, "max_results": maxRes, "search_depth": "basic", "include_answer": false,
			})
			if err != nil {
				return WebSearchOutput{}, fmt.Errorf("构造搜索请求失败: %w", err)
			}
			req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, strings.NewReader(string(body)))
			if err != nil {
				return WebSearchOutput{}, fmt.Errorf("构造搜索请求失败: %w", err)
			}
			req.Header.Set("Content-Type", "application/json")
			req.Header.Set("Authorization", "Bearer "+cfg.APIKey)

			resp, err := client.Do(req)
			if err != nil {
				return WebSearchOutput{}, fmt.Errorf("搜索请求失败: %w", err)
			}
			defer resp.Body.Close()

			raw, err := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
			if err != nil {
				return WebSearchOutput{}, fmt.Errorf("读取搜索结果失败: %w", err)
			}
			if resp.StatusCode != http.StatusOK {
				return WebSearchOutput{}, fmt.Errorf("搜索服务返回 %d: %s", resp.StatusCode, truncate(string(raw), 300))
			}
			var parsed struct {
				Results []SearchResult `json:"results"`
			}
			if err := json.Unmarshal(raw, &parsed); err != nil {
				return WebSearchOutput{}, fmt.Errorf("解析搜索结果失败: %w", err)
			}
			msg := fmt.Sprintf("找到 %d 条结果。", len(parsed.Results))
			if len(parsed.Results) == 0 {
				msg = "没有找到相关结果，建议换一个关键词。"
			}
			return WebSearchOutput{Count: len(parsed.Results), Results: parsed.Results, Message: msg}, nil
		})
}
