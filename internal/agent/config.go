package agent

import (
	"fmt"
	"strings"

	"my-agent/internal/config"
	"my-agent/pkg/llm"
)

// newLLMFromConfig 根据配置初始化 pkg/llm.Client (基于标准统一的 OpenAI 协议)
func newLLMFromConfig(cfg *config.Config) (*llm.Client, error) {
	if cfg == nil {
		return nil, fmt.Errorf("agent: configuration cannot be nil")
	}

	// 远程端点缺少密钥时保留未就绪状态（返回 nil, nil），待向导或配置补齐
	if !config.IsLocalURL(cfg.BaseURL) && strings.TrimSpace(cfg.APIKey) == "" {
		return nil, nil
	}

	return llm.New(llm.Config{
		BaseURL: cfg.BaseURL,
		APIKey:  cfg.APIKey,
		Model:   cfg.ModelName,
	})
}

// UpdateConfig 运行时更新端点地址、API 密钥与模型名称（事务原子性：候选副本校验 -> 构建客户端 -> 持久化落盘 -> 提交生效）
func (a *CoreAgent) UpdateConfig(baseURL, apiKey, model string) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	if a.cfg == nil {
		a.cfg = config.DefaultConfig()
	}

	candidate := a.cfg.Clone()

	// 1. 检查并更新 BaseURL
	if bStr := strings.TrimSpace(baseURL); bStr != "" {
		candidate.BaseURL = bStr
	}

	// 2. 检查并更新 APIKey
	if kStr := strings.TrimSpace(apiKey); kStr != "" {
		candidate.APIKey = kStr
	}

	// 3. 检查并更新 ModelName
	if mStr := strings.TrimSpace(model); mStr != "" {
		candidate.ModelName = mStr
	}

	// 4. 远程端点校验
	if !config.IsLocalURL(candidate.BaseURL) && strings.TrimSpace(candidate.APIKey) == "" {
		return fmt.Errorf("agent: 远程端点需要提供 API Key")
	}

	// 5. 初始化大模型客户端
	llmClient, err := newLLMFromConfig(candidate)
	if err != nil {
		return fmt.Errorf("agent: 初始化大模型客户端失败: %w", err)
	}

	// 6. 持久化落盘配置文件
	cfgPath := a.cfgPath
	if cfgPath == "" {
		cfgPath = config.DefaultConfigPath()
	}
	if err := config.SaveConfig(cfgPath, candidate); err != nil {
		return fmt.Errorf("agent: 保存配置失败: %w", err)
	}

	// 全部校验与构建成功后原子提交
	a.cfg = candidate
	a.cfgPath = cfgPath
	a.llm = llmClient
	return nil
}
