package agent

import (
	"fmt"
	"strings"

	"my-agent/internal/config"
	"my-agent/internal/gateway"
)

// UpdateConfig 运行时更新模型提供商、密钥与模型名称（具备事务原子性：先在候选副本上校验、初始化网关并落盘，全部成功后原子生效）
func (a *CoreAgent) UpdateConfig(provider, apiKey, model string) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	if a.cfg == nil {
		a.cfg = config.DefaultConfig()
	}

	candidate := a.cfg.Clone()

	// 1. 若未显式传入 provider，尝试从 model 名称智能识别所属厂商或保持当前激活厂商
	pStr := strings.TrimSpace(provider)
	mStr := strings.TrimSpace(model)
	if pStr == "" && mStr != "" {
		if inferred := config.InferProviderFromModel(mStr); inferred != "" {
			pStr = string(inferred)
		}
	}
	if pStr == "" {
		pStr = string(candidate.Provider)
	}

	newProvider := config.Provider(pStr)
	// 切换厂商（自动载入该厂商已保存的配置历史）
	candidate.SwitchProvider(newProvider)

	// 2. 检查并更新 APIKey（若传入非空，则更新并覆盖；若传入空，则沿用该厂商已保存的密钥）
	if strings.TrimSpace(apiKey) != "" {
		candidate.APIKey = strings.TrimSpace(apiKey)
	}

	// 3. 检查并更新 ModelName
	if mStr != "" {
		candidate.ModelName = config.NormalizeModelName(newProvider, mStr)
	} else if candidate.ModelName == "" {
		candidate.ModelName = config.DefaultModel(newProvider)
	} else {
		candidate.ModelName = config.NormalizeModelName(newProvider, candidate.ModelName)
	}

	// 4. 远程厂商必须具备有效 APIKey
	if !config.IsLocalProvider(newProvider) && strings.TrimSpace(candidate.APIKey) == "" {
		return fmt.Errorf("agent: provider %q requires an API key", newProvider)
	}

	// 5. 初始化新网关
	gw, err := gateway.NewGatewayFromConfig(candidate)
	if err != nil {
		return fmt.Errorf("agent: initialize gateway failed: %w", err)
	}

	// 6. 持久化落盘配置文件
	cfgPath := a.cfgPath
	if cfgPath == "" {
		cfgPath = config.DefaultConfigPath()
	}
	if err := config.SaveConfig(cfgPath, candidate); err != nil {
		return fmt.Errorf("agent: save config failed: %w", err)
	}

	// 全部校验与构建成功后原子提交
	a.cfg = candidate
	a.cfgPath = cfgPath
	a.gw = gw
	return nil
}
