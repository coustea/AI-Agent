package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestConfig_Defaults(t *testing.T) {
	if DefaultModel(ProviderGemini) != DefaultGeminiModel {
		t.Errorf("expected %s, got %s", DefaultGeminiModel, DefaultModel(ProviderGemini))
	}
	if DefaultModel(ProviderDeepSeek) != DefaultDeepSeekModel {
		t.Errorf("expected %s, got %s", DefaultDeepSeekModel, DefaultModel(ProviderDeepSeek))
	}
	if DefaultModel(ProviderLlamaCpp) != DefaultLlamaCppModel {
		t.Errorf("expected %s, got %s", DefaultLlamaCppModel, DefaultModel(ProviderLlamaCpp))
	}

	if DefaultModel(ProviderSpark) != DefaultSparkModel {
		t.Errorf("expected %s, got %s", DefaultSparkModel, DefaultModel(ProviderSpark))
	}

	if DefaultBaseURL(ProviderGemini) != GeminiBaseURL {
		t.Errorf("expected %s, got %s", GeminiBaseURL, DefaultBaseURL(ProviderGemini))
	}
	if DefaultBaseURL(ProviderDeepSeek) != DeepSeekBaseURL {
		t.Errorf("expected %s, got %s", DeepSeekBaseURL, DefaultBaseURL(ProviderDeepSeek))
	}
	if DefaultBaseURL(ProviderSpark) != DefaultSparkBaseURL {
		t.Errorf("expected %s, got %s", DefaultSparkBaseURL, DefaultBaseURL(ProviderSpark))
	}
	if DefaultBaseURL(ProviderLlamaCpp) != DefaultLlamaCppBaseURL {
		t.Errorf("expected %s, got %s", DefaultLlamaCppBaseURL, DefaultBaseURL(ProviderLlamaCpp))
	}

	if !IsLocalProvider(ProviderLlamaCpp) {
		t.Errorf("expected llamacpp to be local provider")
	}
	if IsLocalProvider(ProviderDeepSeek) {
		t.Errorf("expected deepseek to not be local provider")
	}
	if IsLocalProvider(ProviderGemini) {
		t.Errorf("expected gemini to not be local provider")
	}
	if IsLocalProvider(ProviderSpark) {
		t.Errorf("expected spark to not be local provider")
	}
}

func TestConfig_SaveAndLoad(t *testing.T) {
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "config.json")

	cfg := &Config{
		Provider:  ProviderGemini,
		BaseURL:   GeminiBaseURL,
		ModelName: DefaultGeminiModel,
		APIKey:    "test-gemini-key",
	}

	if err := SaveConfig(cfgPath, cfg); err != nil {
		t.Fatalf("failed to save config: %v", err)
	}

	loaded, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("failed to load config: %v", err)
	}

	if loaded.Provider != ProviderGemini {
		t.Errorf("expected provider %s, got %s", ProviderGemini, loaded.Provider)
	}
	if loaded.APIKey != "test-gemini-key" {
		t.Errorf("expected api key test-gemini-key, got %s", loaded.APIKey)
	}
	if loaded.ModelName != DefaultGeminiModel {
		t.Errorf("expected model %s, got %s", DefaultGeminiModel, loaded.ModelName)
	}
}

func TestConfig_AutoDiscovery_Env(t *testing.T) {
	tmpDir := t.TempDir()
	missingPath := filepath.Join(tmpDir, "non_existent.json")

	// 清理当前环境可能存在的真实密钥以确保测试隔离
	t.Setenv("DEEPSEEK_API_KEY", "")
	t.Setenv("GEMINI_API_KEY", "")
	t.Setenv("GOOGLE_API_KEY", "")
	t.Setenv("SPARK_API_KEY", "")
	t.Setenv("MAAS_API_KEY", "")

	// 1. 无环境变量时默认激活官方免费模型 Spark (spark-2.5)
	cfg, err := LoadConfig(missingPath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.Provider != ProviderSpark || cfg.ModelName != DefaultSparkModel {
		t.Errorf("expected default to spark (%s), got provider: %s, model: %s", DefaultSparkModel, cfg.Provider, cfg.ModelName)
	}

	// 2. 设置 SPARK_API_KEY
	t.Setenv("SPARK_API_KEY", "env-spark-key")
	cfgSpark, err := LoadConfig(missingPath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgSpark.Provider != ProviderSpark || cfgSpark.APIKey != "env-spark-key" {
		t.Errorf("expected spark env discovery, got %+v", cfgSpark)
	}

	// 3. 设置 GEMINI_API_KEY (优先级高于 Spark)
	t.Setenv("GEMINI_API_KEY", "env-gemini-key")
	cfgGemini, err := LoadConfig(missingPath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgGemini.Provider != ProviderGemini || cfgGemini.APIKey != "env-gemini-key" {
		t.Errorf("expected gemini env discovery, got %+v", cfgGemini)
	}

	// 4. 设置 DEEPSEEK_API_KEY (优先级最高)
	t.Setenv("DEEPSEEK_API_KEY", "env-deepseek-key")
	cfgDS, err := LoadConfig(missingPath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgDS.Provider != ProviderDeepSeek || cfgDS.APIKey != "env-deepseek-key" {
		t.Errorf("expected deepseek env discovery, got %+v", cfgDS)
	}
}

func TestConfig_ProviderSwitchingAndPersistence(t *testing.T) {
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "coustea_config.json")

	cfg := &Config{
		Provider:  ProviderDeepSeek,
		BaseURL:   DeepSeekBaseURL,
		ModelName: DefaultDeepSeekModel,
		APIKey:    "sk-deepseek-initial",
	}

	// 1. 保存 DeepSeek 配置
	if err := SaveConfig(cfgPath, cfg); err != nil {
		t.Fatalf("failed to save config: %v", err)
	}

	// 2. 切换到 Gemini 并配置保存
	cfg.SwitchProvider(ProviderGemini)
	cfg.APIKey = "sk-gemini-initial"
	cfg.ModelName = DefaultGeminiModel
	if err := SaveConfig(cfgPath, cfg); err != nil {
		t.Fatalf("failed to save gemini config: %v", err)
	}

	// 3. 重新加载，验证 Gemini 为当前激活，且 DeepSeek 的配置历史被妥善保留在 Providers 中
	loaded, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("failed to reload config: %v", err)
	}
	if loaded.Provider != ProviderGemini || loaded.APIKey != "sk-gemini-initial" {
		t.Errorf("expected current provider to be gemini, got %+v", loaded)
	}

	dsSaved := loaded.ProviderFor(ProviderDeepSeek)
	if dsSaved.APIKey != "sk-deepseek-initial" || dsSaved.ModelName != DefaultDeepSeekModel {
		t.Errorf("expected preserved deepseek config, got %+v", dsSaved)
	}

	// 4. 切回 DeepSeek，无需重复输入 APIKey
	loaded.SwitchProvider(ProviderDeepSeek)
	if loaded.APIKey != "sk-deepseek-initial" {
		t.Errorf("expected switched api key to be sk-deepseek-initial, got %s", loaded.APIKey)
	}
	if loaded.ModelName != DefaultDeepSeekModel {
		t.Errorf("expected switched model name to be %s, got %s", DefaultDeepSeekModel, loaded.ModelName)
	}
}

func TestConfig_ResolveConfigPath(t *testing.T) {
	explicit := "/custom/path/config.json"
	if ResolveConfigPath(explicit) != explicit {
		t.Errorf("expected %s, got %s", explicit, ResolveConfigPath(explicit))
	}

	globalPath := GlobalConfigPath()
	if !filepath.IsAbs(globalPath) {
		t.Errorf("expected global path to be absolute, got %s", globalPath)
	}
}

// 测试远程厂商缺密钥的配置文件按未就绪状态加载而非报错（就绪判定交由上层视图表达）
func TestConfig_Load_RemoteWithoutKey_Unready(t *testing.T) {
	t.Setenv("DEEPSEEK_API_KEY", "")
	t.Setenv("GEMINI_API_KEY", "")
	t.Setenv("GOOGLE_API_KEY", "")
	t.Setenv("SPARK_API_KEY", "")
	t.Setenv("MAAS_API_KEY", "")

	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "unready.json")
	raw := `{"provider":"deepseek","model_name":"deepseek-flash","base_url":"https://api.deepseek.com"}`
	if err := os.WriteFile(cfgPath, []byte(raw), 0o600); err != nil {
		t.Fatalf("failed to write fixture config: %v", err)
	}

	cfg, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("expected remote config without key to load, got: %v", err)
	}
	if cfg.Provider != ProviderDeepSeek || cfg.APIKey != "" {
		t.Fatalf("unexpected cfg: provider=%s apiKey=%q", cfg.Provider, cfg.APIKey)
	}
}
