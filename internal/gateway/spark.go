package gateway

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"

	"my-agent/internal/config"
)

// Spark 通过讯飞星辰 MaaS 平台 API 调用大模型
type Spark struct {
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client

	mu         sync.RWMutex
	totalUsage Usage
}

// NewSpark 创建星辰 MaaS 网关实例
func NewSpark(baseURL, apiKey, model string, client *http.Client) (*Spark, error) {
	baseURL = strings.TrimSpace(baseURL)
	if baseURL == "" {
		baseURL = config.DefaultSparkBaseURL
	}
	apiKey = strings.TrimSpace(apiKey)
	if apiKey == "" {
		return nil, ErrEmptyAPIKey
	}
	if strings.TrimSpace(model) == "" {
		model = config.DefaultSparkModel
	}
	if client == nil {
		client = http.DefaultClient
	}
	return &Spark{
		baseURL:    strings.TrimRight(baseURL, "/"),
		apiKey:     apiKey,
		model:      strings.TrimSpace(model),
		httpClient: client,
	}, nil
}

func (s *Spark) endpoint() string {
	return chatURL(s.baseURL)
}

func (s *Spark) setAuth(req *http.Request) {
	if s.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+s.apiKey)
	}
}

// Chat 执行同步对话调用
func (s *Spark) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	httpReq, err := buildHTTPRequest(ctx, s.endpoint(), s.model, req, false)
	if err != nil {
		return nil, err
	}
	s.setAuth(httpReq)

	resp, err := s.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("spark: http error: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("spark: read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("spark: status %d: %s", resp.StatusCode, string(body))
	}

	content, toolCalls, usage, err := parseResponse(body)
	if err != nil {
		return nil, fmt.Errorf("spark: %w", err)
	}

	s.mu.Lock()
	s.totalUsage.Add(usage)
	s.mu.Unlock()

	return &ChatResponse{Content: content, ToolCalls: toolCalls, Usage: usage}, nil
}

// ChatStream 执行流式调用
func (s *Spark) ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error) {
	httpReq, err := buildHTTPRequest(ctx, s.endpoint(), s.model, req, true)
	if err != nil {
		return nil, err
	}
	s.setAuth(httpReq)

	resp, err := s.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("spark: http stream error: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		return nil, fmt.Errorf("spark: stream status %d: %s", resp.StatusCode, string(body))
	}

	out := make(chan StreamChunk, 32)
	go func() {
		defer resp.Body.Close()
		defer close(out)
		usage := readSSE(ctx, resp.Body, out)
		if usage.TotalTokens > 0 {
			s.mu.Lock()
			s.totalUsage.Add(usage)
			s.mu.Unlock()
		}
	}()

	return out, nil
}

// TotalUsage 获取累计 Token 用量
func (s *Spark) TotalUsage() Usage {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.totalUsage
}
