package config_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"mentorly/internal/config"
)

// setupEnv 为配置测试准备环境变量，避免依赖开发者本地 .env。
func setupEnv(t *testing.T) {
	t.Helper()

	vars := map[string]string{
		"APP_NAME":       "Mentorly",
		"APP_ENV":        "development",
		"APP_HOST":       "0.0.0.0",
		"APP_PORT":       "8080",
		"JWT_SECRET":     "mentorly-dev-secret-key-change-in-production",
		"JWT_ISSUER":     "Mentorly",
		"JWT_EXPIRE":     "168h",
		"LLM_PROVIDER":   "openai",
		"LLM_MODEL":      "deepseek-chat",
		"LLM_BASE_URL":   "https://api.deepseek.com/v1",
		"LLM_API_KEY":    "test-key",
		"MYSQL_USERNAME": "root",
		"MYSQL_PASSWORD": "secret",
		"MYSQL_DATABASE": "mentorly",
		"DB_DSN":         "",
		"REDIS_ADDR":     "127.0.0.1:6379",
		"REDIS_PASSWORD": "",
		"REDIS_DB":       "0",
		// 联网搜索是可选项，显式留空表示禁用。
		"SEARCH_PROVIDER": "",
		"SEARCH_API_KEY":  "",
		"SEARCH_BASE_URL": "",
	}
	for k, v := range vars {
		t.Setenv(k, v)
	}
}

func TestLoad(t *testing.T) {
	setupEnv(t)
	// Load 使用相对路径，测试时切回项目根目录
	t.Chdir("../..")

	cfg, err := config.Load()
	if err != nil {
		t.Fatalf("Load: %v", err)
	}

	if cfg.APP.Name != "Mentorly" {
		t.Errorf("app.name = %q", cfg.APP.Name)
	}
	if cfg.APP.Addr() != "0.0.0.0:8080" {
		t.Errorf("app.Addr() = %q", cfg.APP.Addr())
	}

	// 结构体字段是 []byte 之外的时间类型，viper 的 Duration Hook 应把 "168h" 解析成 time.Duration
	if cfg.JWT.Expire != 168*time.Hour {
		t.Errorf("jwt.expire = %v, want 168h", cfg.JWT.Expire)
	}

	// 未显式配置 DSN 时，应由字段拼装
	want := "root:secret@tcp(127.0.0.1:3306)/mentorly?charset=utf8mb4&parseTime=True&loc=Local"
	if got := cfg.Database.MySQL.BuildDSN(); got != want {
		t.Errorf("BuildDSN() = %q, want %q", got, want)
	}

	// llm 的超时支持 "480s" 这类带单位写法。
	// 该值需明显大于 chat.run_timeout 的一半，否则长回答会被截断。
	if cfg.LLM.Timeout != 480*time.Second {
		t.Errorf("llm.timeout = %v, want 480s", cfg.LLM.Timeout)
	}
	if cfg.LLM.Timeout < cfg.Chat.RunTimeout/2 {
		t.Errorf("llm.timeout(%v) 应 >= run_timeout(%v) 的一半",
			cfg.LLM.Timeout, cfg.Chat.RunTimeout)
	}
	if cfg.LLM.MaxToken != 8192 {
		t.Errorf("llm.max_token = %d, want 8192", cfg.LLM.MaxToken)
	}
	if cfg.LLM.ExtraFields["temperature"] != 0.7 {
		t.Errorf("llm.extra_fields = %v", cfg.LLM.ExtraFields)
	}
}

func TestLoadMissingEnv(t *testing.T) {
	setupEnv(t)
	// 用 t.Setenv 之后再用 os.Unsetenv 才能真正移除，
	// 验证的是「变量完全未定义」而非「显式留空」。
	t.Setenv("JWT_ISSUER", "")
	if err := os.Unsetenv("JWT_ISSUER"); err != nil {
		t.Fatalf("Unsetenv: %v", err)
	}
	t.Chdir("../..")

	_, err := config.Load()
	if err == nil {
		t.Fatal("期望因缺失环境变量而报错，实际成功")
	}
	if !strings.Contains(err.Error(), "JWT_ISSUER") {
		t.Errorf("错误信息应包含变量名 JWT_ISSUER，实际: %v", err)
	}
}

func TestLoadRejectsShortJWTSecret(t *testing.T) {
	setupEnv(t)
	t.Setenv("JWT_SECRET", "too-short")
	t.Chdir("../..")

	_, err := config.Load()
	if err == nil {
		t.Fatal("期望因 jwt.secret 过短而报错，实际成功")
	}
}

func TestBuildDSNPrefersExplicitDSN(t *testing.T) {
	m := config.MySQLConfig{DSN: "explicit-dsn"}
	if got := m.BuildDSN(); got != "explicit-dsn" {
		t.Errorf("显式 DSN 应优先，实际 %q", got)
	}
}

// TestTimeoutConsistency 验证单次模型调用超时与整轮超时的关系校验。
//
// 这是一个真实踩过的坑：llm.timeout=120s 而 chat.run_timeout=600s 时，
// 「详细讲解」这类长回答会在流式传输中途被 HTTP 客户端掐断，
// 表现为整轮 cancelled 且 prompt_tokens 为空，排查成本很高。
func TestTimeoutConsistency(t *testing.T) {
	setupEnv(t)
	t.Chdir("../..")

	// 当前配置应通过校验
	cfg, err := config.Load()
	if err != nil {
		t.Fatalf("默认配置应合法: %v", err)
	}
	if cfg.LLM.Timeout < cfg.Chat.RunTimeout/2 {
		t.Errorf("llm.timeout(%v) 应 >= run_timeout(%v) 的一半",
			cfg.LLM.Timeout, cfg.Chat.RunTimeout)
	}
}

// TestShortLLMTimeoutRejected 验证过小的 llm.timeout 会被拦下。
func TestShortLLMTimeoutRejected(t *testing.T) {
	setupEnv(t)

	// 用一个临时配置文件，把 llm.timeout 改小
	dir := t.TempDir()
	orig, err := os.ReadFile("internal/config/config.yaml")
	if err != nil {
		t.Skipf("读取原始配置失败: %v", err)
	}
	broken := strings.Replace(string(orig), "timeout: 480s", "timeout: 10s", 1)
	path := filepath.Join(dir, "config.yaml")
	if err := os.WriteFile(path, []byte(broken), 0o644); err != nil {
		t.Fatalf("写入临时配置: %v", err)
	}

	t.Setenv("APP_CONFIG_PATH", path)

	_, err = config.Load()
	if err == nil {
		t.Fatal("llm.timeout 过小时应启动失败")
	}
	if !strings.Contains(err.Error(), "llm.timeout") {
		t.Errorf("错误信息应点明 llm.timeout，实际: %v", err)
	}
}
