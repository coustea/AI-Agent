package gateway

import (
	"context"
	"fmt"
	"strings"
	"sync"

	"my-agent/internal/config"
)

// Router 作为统一网关，负责根据请求的模型名称或配置进行模型路由与分配
type Router struct {
	mu        sync.RWMutex
	active    string             // 当前默认激活的提供商名称
	providers map[string]Gateway // 注册的各厂商网关实例 ("gemini", "deepseek", "llamacpp")
}

// NewRouter 创建一个支持多厂商模型动态分配的网关路由实例
func NewRouter(defaultProvider string) *Router {
	return &Router{
		active:    strings.ToLower(strings.TrimSpace(defaultProvider)),
		providers: make(map[string]Gateway),
	}
}

// Register 注册指定厂商的模型网关实例
func (r *Router) Register(name string, gw Gateway) {
	r.mu.Lock()
	defer r.mu.Unlock()
	key := strings.ToLower(strings.TrimSpace(name))
	if key != "" && gw != nil {
		r.providers[key] = gw
		if r.active == "" {
			r.active = key
		}
	}
}

// SetActive 切换当前默认分配的模型厂商
func (r *Router) SetActive(name string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.active = strings.ToLower(strings.TrimSpace(name))
}

// Route 根据请求参数智能分配具体的模型网关
func (r *Router) Route(req *ChatRequest) (Gateway, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	if len(r.providers) == 0 {
		return nil, fmt.Errorf("gateway router: no providers registered")
	}

	// 1. 若请求明确指定了模型，优先根据模型名称前缀智能分配
	if req != nil && strings.TrimSpace(req.Model) != "" {
		m := strings.ToLower(strings.TrimSpace(req.Model))
		if strings.HasPrefix(m, "gemini") {
			if gw, ok := r.providers["gemini"]; ok {
				return gw, nil
			}
		}
		if strings.HasPrefix(m, "deepseek") {
			if gw, ok := r.providers["deepseek"]; ok {
				return gw, nil
			}
		}
		if strings.Contains(m, "llama") || strings.Contains(m, "local") {
			if gw, ok := r.providers["llamacpp"]; ok {
				return gw, nil
			}
		}
	}

	// 2. 匹配当前激活的默认厂商
	if gw, ok := r.providers[r.active]; ok {
		return gw, nil
	}

	// 3. 回退策略：选取已注册的任意可用厂商
	for _, gw := range r.providers {
		return gw, nil
	}

	return nil, fmt.Errorf("gateway router: active provider %q not found", r.active)
}

// Chat 经过网关进行模型分配后执行同步对话
func (r *Router) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	gw, err := r.Route(req)
	if err != nil {
		return nil, err
	}
	return gw.Chat(ctx, req)
}

// ChatStream 经过网关进行模型分配后执行流式对话
func (r *Router) ChatStream(ctx context.Context, req *ChatRequest) (<-chan StreamChunk, error) {
	gw, err := r.Route(req)
	if err != nil {
		return nil, err
	}
	return gw.ChatStream(ctx, req)
}

// TotalUsage 统计所有已注册厂商消耗的累计总 Token 用量
func (r *Router) TotalUsage() Usage {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var total Usage
	for _, gw := range r.providers {
		total.Add(gw.TotalUsage())
	}
	return total
}

// NewGatewayFromConfig 根据配置构建支持模型分配的网关实例
func NewGatewayFromConfig(cfg *config.Config) (Gateway, error) {
	if cfg == nil {
		return nil, fmt.Errorf("gateway: configuration cannot be nil")
	}

	activeName := strings.ToLower(string(cfg.Provider))
	router := NewRouter(activeName)

	// 1. 若配置中保存了各厂商独立配置，初始化已配置的提供商
	if cfg.Providers != nil {
		for pName, pcfg := range cfg.Providers {
			gw, err := initProviderGateway(config.Provider(pName), pcfg.BaseURL, pcfg.APIKey, pcfg.ModelName)
			if err == nil {
				router.Register(pName, gw)
			}
		}
	}

	// 2. 确保当前激活的提供商一定初始化并注册
	activeGW, err := initProviderGateway(cfg.Provider, cfg.BaseURL, cfg.APIKey, cfg.ModelName)
	if err != nil {
		return nil, err
	}
	router.Register(activeName, activeGW)

	return router, nil
}

func initProviderGateway(p config.Provider, baseURL, apiKey, model string) (Gateway, error) {
	pName := strings.ToLower(string(p))
	switch pName {
	case "gemini", "google":
		return NewGemini(baseURL, apiKey, model, nil)
	case "deepseek", "ds":
		return NewDeepSeek(baseURL, apiKey, model, nil)
	case "llamacpp", "llama", "local", "":
		return NewLlamaCpp(baseURL, apiKey, model, nil)
	default:
		return nil, fmt.Errorf("unsupported provider %q", p)
	}
}
