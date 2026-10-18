package agent

import (
	"fmt"
	"strings"

	"my-agent/internal/config"
	"my-agent/internal/gateway"
)

// UpdateConfig 运行时更新模型提供商、密钥与模型名称（由内核自动负责校验、落盘 config.json 与热切网关）
func (a *CoreAgent) UpdateConfig(provider, apiKey, model string) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	if a.cfg == nil {
		a.cfg = &config.Config{
			Provider:  config.ProviderLlamaCpp,
			ModelName: config.DefaultLlamaCppModel,
			BaseURL:   config.DefaultLlamaCppBaseURL,
		}
	}

	// 1. 若未显式传入 provider，尝试从 model 名称智能识别所属厂商或保持当前激活厂商
	pStr := strings.TrimSpace(provider)
	mStr := strings.TrimSpace(model)
	if pStr == "" && mStr != "" {
		if inferred := config.InferProviderFromModel(mStr); inferred != "" {
			pStr = string(inferred)
		}
	}
	if pStr == "" {
		pStr = string(a.cfg.Provider)
	}

	newProvider := config.Provider(pStr)
	// 切换厂商（自动载入该厂商已保存的配置历史）
	a.cfg.SwitchProvider(newProvider)

	// 2. 检查并更新 APIKey（若传入非空，则更新并覆盖；若传入空，则沿用该厂商已保存的密钥）
	if strings.TrimSpace(apiKey) != "" {
		a.cfg.APIKey = strings.TrimSpace(apiKey)
	}

	// 3. 检查并更新 ModelName
	if mStr != "" {
		a.cfg.ModelName = config.NormalizeModelName(newProvider, mStr)
	} else if a.cfg.ModelName == "" {
		a.cfg.ModelName = config.DefaultModel(newProvider)
	} else {
		a.cfg.ModelName = config.NormalizeModelName(newProvider, a.cfg.ModelName)
	}

	// 4. 远程厂商必须具备有效 APIKey
	if !config.IsLocalProvider(newProvider) && strings.TrimSpace(a.cfg.APIKey) == "" {
		return fmt.Errorf("agent: provider %q requires an API key", newProvider)
	}

	if a.cfgPath == "" {
		a.cfgPath = config.DefaultConfigPath()
	}
	if err := config.SaveConfig(a.cfgPath, a.cfg); err != nil {
		return fmt.Errorf("agent: save config failed: %w", err)
	}

	gw, err := gateway.NewGatewayFromConfig(a.cfg)
	if err != nil {
		return fmt.Errorf("agent: initialize gateway failed: %w", err)
	}
	a.gw = gw
	return nil
}

// SetGateway 支持运行时热切换大模型网关
func (a *CoreAgent) SetGateway(gw gateway.Gateway) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if gw != nil {
		a.gw = gw
	}
}
