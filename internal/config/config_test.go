package config

import (
	"os"
	"path/filepath"
	"testing"

	"my-agent/pkg/llm"
)

// 厂商默认值是对外契约：这里用字面量钉住，任何默认端点/模型漂移都会被发现。
func TestConfig_Defaults(t *testing.T) {
	cases := []struct {
		provider llm.Provider
		baseURL  string
		model    string
		local    bool
	}{
		{llm.ProviderLlamaCpp, "http://127.0.0.1:8080", "local-model", true},
		{llm.ProviderDeepSeek, "https://api.deepseek.com", "deepseek-flash", false},
		{llm.ProviderGemini, "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash", false},
		{llm.ProviderSpark, "https://maas-api.cn-huabei-1.xf-yun.com/v2", "spark-x2.5-4b", false},
	}

	for _, tc := range cases {
		spec := ProviderSpec(tc.provider)
		if spec.BaseURL != tc.baseURL {
			t.Errorf("%s: 默认端点期望 %s，实际 %s", tc.provider, tc.baseURL, spec.BaseURL)
		}
		if spec.DefaultModel != tc.model {
			t.Errorf("%s: 默认模型期望 %s，实际 %s", tc.provider, tc.model, spec.DefaultModel)
		}
		if spec.Local != tc.local {
			t.Errorf("%s: Local 期望 %v，实际 %v", tc.provider, tc.local, spec.Local)
		}
		if got := NormalizeModelName(tc.provider, ""); got != tc.model {
			t.Errorf("%s: 空模型名应归一化为 %s，实际 %s", tc.provider, tc.model, got)
		}
	}
}

// 模型名 → 厂商推断与别名解析（元数据已下沉到 pkg/llm.Spec，此处只验证配置层视图）
func TestConfig_ProviderMetadata(t *testing.T) {
	if got := InferProviderFromModel("deepseek-chat"); got != llm.ProviderDeepSeek {
		t.Errorf("期望 deepseek，实际 %s", got)
	}
	if got := InferProviderFromModel("gemini-2.5-pro"); got != llm.ProviderGemini {
		t.Errorf("期望 gemini，实际 %s", got)
	}
	if got := InferProviderFromModel("spark-x2.5"); got != llm.ProviderSpark {
		t.Errorf("期望 spark，实际 %s", got)
	}
	if got := InferProviderFromModel("qwen2.5-coder-7b"); got != llm.ProviderLlamaCpp {
		t.Errorf("期望 llamacpp，实际 %s", got)
	}
	if got := InferProviderFromModel("unknown-model"); got != "" {
		t.Errorf("未知模型应返回空串，实际 %s", got)
	}

	// 别名与未知厂商：一律规范化到规范 ID，未知回落 llamacpp
	if got := ProviderSpec(llm.Provider("ds")).ID; got != llm.ProviderDeepSeek {
		t.Errorf("别名 ds 应解析为 deepseek，实际 %s", got)
	}
	if got := ProviderSpec(llm.Provider("不存在的厂商")).ID; got != llm.ProviderLlamaCpp {
		t.Errorf("未知厂商应回落 llamacpp，实际 %s", got)
	}

	// 星火模型名笔误自动修正
	if got := NormalizeModelName(llm.ProviderSpark, "spark-2.5"); got != sparkX25Model {
		t.Errorf("期望 %s，实际 %s", sparkX25Model, got)
	}
	if got := NormalizeModelName(llm.ProviderSpark, "4b"); got != sparkX254BModel {
		t.Errorf("期望 %s，实际 %s", sparkX254BModel, got)
	}
}

func TestConfig_SaveAndLoad(t *testing.T) {
	tmpDir := t.TempDir()
	cfgPath := filepath.Join(tmpDir, "config.json")

	cfg := &Config{
		Provider:  llm.ProviderGemini,
		BaseURL:   ProviderSpec(llm.ProviderGemini).BaseURL,
		ModelName: ProviderSpec(llm.ProviderGemini).DefaultModel,
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
	if loaded.ModelName != ProviderSpec(llm.ProviderGemini).DefaultModel {
		t.Errorf("expected model %s, got %s", ProviderSpec(llm.ProviderGemini).DefaultModel, loaded.ModelName)
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
	if cfg.Provider != llm.ProviderSpark || cfg.ModelName != ProviderSpec(llm.ProviderSpark).DefaultModel {
		t.Errorf("expected default to spark (%s), got provider: %s, model: %s", ProviderSpec(llm.ProviderSpark).DefaultModel, cfg.Provider, cfg.ModelName)
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
		BaseURL:   ProviderSpec(llm.ProviderDeepSeek).BaseURL,
		ModelName: ProviderSpec(llm.ProviderDeepSeek).DefaultModel,
		APIKey:    "sk-deepseek-initial",
	}

	// 1. 保存 DeepSeek 配置
	if err := SaveConfig(cfgPath, cfg); err != nil {
		t.Fatalf("failed to save config: %v", err)
	}

	// 2. 切换到 Gemini 并配置保存
	cfg.SwitchProvider(llm.ProviderGemini)
	cfg.APIKey = "sk-gemini-initial"
	cfg.ModelName = ProviderSpec(llm.ProviderGemini).DefaultModel
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
	if dsSaved.APIKey != "sk-deepseek-initial" || dsSaved.ModelName != ProviderSpec(llm.ProviderDeepSeek).DefaultModel {
		t.Errorf("expected preserved deepseek config, got %+v", dsSaved)
	}

	// 4. 切回 DeepSeek，无需重复输入 APIKey
	loaded.SwitchProvider(llm.ProviderDeepSeek)
	if loaded.APIKey != "sk-deepseek-initial" {
		t.Errorf("expected switched api key to be sk-deepseek-initial, got %s", loaded.APIKey)
	}
	if loaded.ModelName != ProviderSpec(llm.ProviderDeepSeek).DefaultModel {
		t.Errorf("expected switched model name to be %s, got %s", ProviderSpec(llm.ProviderDeepSeek).DefaultModel, loaded.ModelName)
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
	if cfg.ModelName != ProviderSpec(llm.ProviderSpark).DefaultModel {
		t.Fatalf("expected default model %s, got %s", ProviderSpec(llm.ProviderSpark).DefaultModel, cfg.ModelName)
	}
}
