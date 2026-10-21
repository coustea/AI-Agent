package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestConfig_Defaults(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.BaseURL != "https://api.openai.com/v1" {
		t.Errorf("默认 BaseURL 期望 https://api.openai.com/v1，实际 %s", cfg.BaseURL)
	}
	if cfg.ModelName != "gpt-4o" {
		t.Errorf("默认模型期望 gpt-4o，实际 %s", cfg.ModelName)
	}
}

func TestConfig_AutoDiscovery_Env(t *testing.T) {
	origURL := os.Getenv("OPENAI_BASE_URL")
	origKey := os.Getenv("OPENAI_API_KEY")
	origModel := os.Getenv("OPENAI_MODEL")
	defer func() {
		_ = os.Setenv("OPENAI_BASE_URL", origURL)
		_ = os.Setenv("OPENAI_API_KEY", origKey)
		_ = os.Setenv("OPENAI_MODEL", origModel)
	}()

	_ = os.Setenv("OPENAI_BASE_URL", "https://custom.api.com/v1")
	_ = os.Setenv("OPENAI_API_KEY", "sk-custom-secret")
	_ = os.Setenv("OPENAI_MODEL", "custom-model")

	cfg := DefaultConfig()
	if cfg.BaseURL != "https://custom.api.com/v1" {
		t.Errorf("期望读取环境变量 BaseURL，实际 %s", cfg.BaseURL)
	}
	if cfg.APIKey != "sk-custom-secret" {
		t.Errorf("期望读取环境变量 APIKey，实际 %s", cfg.APIKey)
	}
	if cfg.ModelName != "custom-model" {
		t.Errorf("期望读取环境变量 ModelName，实际 %s", cfg.ModelName)
	}
}

func TestConfig_SaveAndLoad(t *testing.T) {
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "test_config.json")

	initial := &Config{
		BaseURL:   "https://api.deepseek.com/v1",
		APIKey:    "sk-ds-key",
		ModelName: "deepseek-chat",
	}

	if err := SaveConfig(cfgPath, initial); err != nil {
		t.Fatalf("SaveConfig 失败: %v", err)
	}

	loaded, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("LoadConfig 失败: %v", err)
	}

	if loaded.BaseURL != initial.BaseURL || loaded.APIKey != initial.APIKey || loaded.ModelName != initial.ModelName {
		t.Errorf("配置持久化后不一致: loaded=%+v, initial=%+v", loaded, initial)
	}
}

func TestConfig_IsLocalURL(t *testing.T) {
	cases := []struct {
		url  string
		want bool
	}{
		{"http://127.0.0.1:8080", true},
		{"http://localhost:11434/v1", true},
		{"http://[::1]:8080", true},
		{"https://api.openai.com/v1", false},
		{"https://api.deepseek.com", false},
	}

	for _, tc := range cases {
		if got := IsLocalURL(tc.url); got != tc.want {
			t.Errorf("IsLocalURL(%q) = %v, want %v", tc.url, got, tc.want)
		}
	}
}

func TestConfig_ToView(t *testing.T) {
	remote := &Config{
		BaseURL:   "https://api.openai.com/v1",
		APIKey:    "sk-xxx",
		ModelName: "gpt-4o",
	}
	v1 := remote.ToView()
	if !v1.HasAPIKey {
		t.Errorf("远程且具备 Key 应为 HasAPIKey=true")
	}

	local := &Config{
		BaseURL:   "http://127.0.0.1:11434",
		ModelName: "qwen2.5",
	}
	v2 := local.ToView()
	if !v2.HasAPIKey {
		t.Errorf("本地免密端点应自动判定为 HasAPIKey=true")
	}
}
