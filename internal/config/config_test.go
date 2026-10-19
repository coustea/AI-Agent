package config

import (
	"os"
	"path/filepath"
	"testing"

	"my-agent/pkg/llm"
)

func TestConfig_Defaults(t *testing.T) {
	if llm.DefaultModel(llm.ProviderGemini) != llm.DefaultGeminiModel {
		t.Errorf("expected %s, got %s", llm.DefaultGeminiModel, llm.DefaultModel(llm.ProviderGemini))
	}
	if llm.DefaultModel(llm.ProviderDeepSeek) != llm.DefaultDeepSeekModel {
		t.Errorf("expected %s, got %s", llm.DefaultDeepSeekModel, llm.DefaultModel(llm.ProviderDeepSeek))
	}
	if llm.DefaultModel(llm.ProviderLlamaCpp) != llm.DefaultLlamaCppModel {
		t.Errorf("expected %s, got %s", llm.DefaultLlamaCppModel, llm.DefaultModel(llm.ProviderLlamaCpp))
	}

	if llm.DefaultModel(llm.ProviderSpark) != llm.DefaultSparkModel {
		t.Errorf("expected %s, got %s", llm.DefaultSparkModel, llm.DefaultModel(llm.ProviderSpark))
	}

	if llm.DefaultBaseURL(llm.ProviderGemini) != llm.DefaultGeminiBaseURL {
		t.Errorf("expected %s, got %s", llm.DefaultGeminiBaseURL, llm.DefaultBaseURL(llm.ProviderGemini))
	}
	if llm.DefaultBaseURL(llm.ProviderDeepSeek) != llm.DefaultDeepSeekBaseURL {
		t.Errorf("expected %s, got %s", llm.DefaultDeepSeekBaseURL, llm.DefaultBaseURL(llm.ProviderDeepSeek))
	}
	if llm.DefaultBaseURL(llm.ProviderSpark) != llm.DefaultSparkBaseURL {
		t.Errorf("expected %s, got %s", llm.DefaultSparkBaseURL, llm.DefaultBaseURL(llm.ProviderSpark))
	}
	if llm.DefaultBaseURL(llm.ProviderLlamaCpp) != llm.DefaultLlamaCppBaseURL {
		t.Errorf("expected %s, got %s", llm.DefaultLlamaCppBaseURL, llm.DefaultBaseURL(llm.ProviderLlamaCpp))
	}

	if !llm.IsLocalProvider(llm.ProviderLlamaCpp) {
		t.Errorf("expected llamacpp to be local provider")
	}
	if llm.IsLocalProvider(llm.ProviderDeepSeek) {
		t.Errorf("expected deepseek to not be local provider")
	}
	if llm.IsLocalProvider(llm.ProviderGemini) {
		t.Errorf("expected gemini to not be local provider")
	}
	if llm.IsLocalProvider(llm.ProviderSpark) {
		t.Errorf("expected spark to not be local provider")
	}
}

func TestConfig_SaveAndLoad(t *testing.T) {
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "config.json")

	cfg := &Config{
		Provider:  llm.ProviderGemini,
		BaseURL:   llm.DefaultGeminiBaseURL,
		ModelName: llm.DefaultGeminiModel,
		APIKey:    "test-gemini-key",
	}

	if err := SaveConfig(cfgPath, cfg); err != nil {
		t.Fatalf("failed to save config: %v", err)
	}

	loaded, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("failed to load config: %v", err)
	}

	if loaded.Provider != llm.ProviderGemini {
		t.Errorf("expected provider %s, got %s", llm.ProviderGemini, loaded.Provider)
	}
	if loaded.APIKey != "test-gemini-key" {
		t.Errorf("expected api key test-gemini-key, got %s", loaded.APIKey)
	}
	if loaded.ModelName != llm.DefaultGeminiModel {
		t.Errorf("expected model %s, got %s", llm.DefaultGeminiModel, loaded.ModelName)
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

	// 1. 无环境变量时默认激活官方免费模型 Spark (spark-x2.5-4b)
	cfg, err := LoadConfig(missingPath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.Provider != llm.ProviderSpark || cfg.ModelName != llm.DefaultSparkModel {
		t.Errorf("expected default to spark (%s), got provider: %s, model: %s", llm.DefaultSparkModel, cfg.Provider, cfg.ModelName)
	}

	// 2. 设置 SPARK_API_KEY
	t.Setenv("SPARK_API_KEY", "env-spark-key")
	cfgSpark, err := LoadConfig(missingPath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgSpark.Provider != llm.ProviderSpark || cfgSpark.APIKey != "env-spark-key" {
		t.Errorf("expected spark env discovery, got %+v", cfgSpark)
	}

	// 3. 设置 GEMINI_API_KEY (优先级高于 Spark)
	t.Setenv("GEMINI_API_KEY", "env-gemini-key")
	cfgGemini, err := LoadConfig(missingPath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgGemini.Provider != llm.ProviderGemini || cfgGemini.APIKey != "env-gemini-key" {
		t.Errorf("expected gemini env discovery, got %+v", cfgGemini)
	}

	// 4. 设置 DEEPSEEK_API_KEY (优先级最高)
	t.Setenv("DEEPSEEK_API_KEY", "env-deepseek-key")
	cfgDS, err := LoadConfig(missingPath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgDS.Provider != llm.ProviderDeepSeek || cfgDS.APIKey != "env-deepseek-key" {
		t.Errorf("expected deepseek env discovery, got %+v", cfgDS)
	}
}

func TestConfig_ProviderSwitchingAndPersistence(t *testing.T) {
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "coustea_config.json")

	cfg := &Config{
		Provider:  llm.ProviderDeepSeek,
		BaseURL:   llm.DefaultDeepSeekBaseURL,
		ModelName: llm.DefaultDeepSeekModel,
		APIKey:    "sk-deepseek-initial",
	}

	// 1. 保存 DeepSeek 配置
	if err := SaveConfig(cfgPath, cfg); err != nil {
		t.Fatalf("failed to save config: %v", err)
	}

	// 2. 切换到 Gemini 并配置保存
	cfg.SwitchProvider(llm.ProviderGemini)
	cfg.APIKey = "sk-gemini-initial"
	cfg.ModelName = llm.DefaultGeminiModel
	if err := SaveConfig(cfgPath, cfg); err != nil {
		t.Fatalf("failed to save gemini config: %v", err)
	}

	// 3. 重新加载，验证 Gemini 为当前激活，且 DeepSeek 的配置历史被妥善保留在 Providers 中
	loaded, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("failed to reload config: %v", err)
	}
	if loaded.Provider != llm.ProviderGemini || loaded.APIKey != "sk-gemini-initial" {
		t.Errorf("expected current provider to be gemini, got %+v", loaded)
	}

	dsSaved := loaded.ProviderFor(llm.ProviderDeepSeek)
	if dsSaved.APIKey != "sk-deepseek-initial" || dsSaved.ModelName != llm.DefaultDeepSeekModel {
		t.Errorf("expected preserved deepseek config, got %+v", dsSaved)
	}

	// 4. 切回 DeepSeek，无需重复输入 APIKey
	loaded.SwitchProvider(llm.ProviderDeepSeek)
	if loaded.APIKey != "sk-deepseek-initial" {
		t.Errorf("expected switched api key to be sk-deepseek-initial, got %s", loaded.APIKey)
	}
	if loaded.ModelName != llm.DefaultDeepSeekModel {
		t.Errorf("expected switched model name to be %s, got %s", llm.DefaultDeepSeekModel, loaded.ModelName)
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
	if cfg.Provider != llm.ProviderDeepSeek || cfg.APIKey != "" {
		t.Fatalf("unexpected cfg: provider=%s apiKey=%q", cfg.Provider, cfg.APIKey)
	}
}

// 验证 DefaultSparkAPIKey 在环境变量缺失时作为保底密钥自动生效于 DefaultConfig 和 LoadConfig
func TestConfig_DefaultSparkAPIKey_Fallback(t *testing.T) {
	orig := DefaultSparkAPIKey
	DefaultSparkAPIKey = "builtin-spark-test-key"
	defer func() { DefaultSparkAPIKey = orig }()

	t.Setenv("SPARK_API_KEY", "")
	t.Setenv("MAAS_API_KEY", "")
	t.Setenv("DEEPSEEK_API_KEY", "")
	t.Setenv("GEMINI_API_KEY", "")
	t.Setenv("GOOGLE_API_KEY", "")

	// 1. DefaultConfig 应自动注入
	cfg := DefaultConfig()
	if cfg.ProviderFor(llm.ProviderSpark).APIKey != "builtin-spark-test-key" {
		t.Errorf("expected builtin key in DefaultConfig, got %q", cfg.ProviderFor(llm.ProviderSpark).APIKey)
	}

	// 2. LoadConfig 在已有配置文件但缺 API Key 时同样回退注入
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "spark_empty.json")
	if err := os.WriteFile(cfgPath, []byte(`{"provider":"spark","model_name":"spark-x2.5"}`), 0o600); err != nil {
		t.Fatalf("failed to write fixture: %v", err)
	}
	loaded, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("LoadConfig failed: %v", err)
	}
	if loaded.APIKey != "builtin-spark-test-key" {
		t.Errorf("expected builtin key in LoadConfig, got %q", loaded.APIKey)
	}
}

// 验收：确保所有用户安装后无需任何配置即可开箱即用 Spark 免费模型
func TestConfig_BuiltinSparkReadyOutOfBox(t *testing.T) {
	t.Setenv("SPARK_API_KEY", "")
	t.Setenv("MAAS_API_KEY", "")
	t.Setenv("DEEPSEEK_API_KEY", "")
	t.Setenv("GEMINI_API_KEY", "")

	cfg := DefaultConfig()
	if cfg.Provider != llm.ProviderSpark {
		t.Fatalf("expected default provider to be spark, got %s", cfg.Provider)
	}
	if cfg.APIKey == "" {
		t.Fatalf("expected default spark APIKey to be non-empty out of the box")
	}
	if cfg.ModelName != llm.DefaultSparkModel {
		t.Fatalf("expected default model %s, got %s", llm.DefaultSparkModel, cfg.ModelName)
	}
}
