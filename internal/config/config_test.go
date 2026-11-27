package config_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"mentorly/internal/config"
)

func setupEnv(t *testing.T) {
	t.Helper()
	vars := map[string]string{
		"APP_NAME":        "Mentorly",
		"APP_ENV":         "development",
		"APP_HOST":        "0.0.0.0",
		"APP_PORT":        "8080",
		"JWT_SECRET":      "mentorly-dev-secret-key-change-in-production",
		"JWT_ISSUER":      "Mentorly",
		"JWT_EXPIRE":      "168h",
		"LLM_PROVIDER":    "openai",
		"LLM_MODEL":       "deepseek-chat",
		"LLM_BASE_URL":    "https://api.deepseek.com/v1",
		"LLM_API_KEY":     "test-key",
		"MYSQL_USERNAME":  "root",
		"MYSQL_PASSWORD":  "secret",
		"MYSQL_DATABASE":  "mentorly",
		"DB_DSN":          "",
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
	if cfg.JWT.Expire != 168*time.Hour {
		t.Errorf("jwt.expire = %v, want 168h", cfg.JWT.Expire)
	}

	want := "root:secret@tcp(127.0.0.1:3306)/mentorly?charset=utf8mb4&parseTime=True&loc=Local"
	if got := cfg.Database.MySQL.BuildDSN(); got != want {
		t.Errorf("BuildDSN() = %q, want %q", got, want)
	}
	if cfg.LLM.Timeout != 60*time.Second {
		t.Errorf("llm.timeout = %v, want 60s", cfg.LLM.Timeout)
	}
	if cfg.LLM.ContextWindow != 1000000 {
		t.Errorf("context_window = %d", cfg.LLM.ContextWindow)
	}
	if cfg.LLM.MaxToken != 131072 {
		t.Errorf("llm.max_token = %d, want 131072", cfg.LLM.MaxToken)
	}
	if cfg.LLM.ThinkingMode != "first_call_only" {
		t.Errorf("llm.thinking_mode = %q, want first_call_only", cfg.LLM.ThinkingMode)
	}
	if cfg.LLM.ExtraFields["temperature"] != 0.7 {
		t.Errorf("llm.extra_fields = %v", cfg.LLM.ExtraFields)
	}
}

func TestLoadMissingEnv(t *testing.T) {
	setupEnv(t)
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

	if _, err := config.Load(); err == nil {
		t.Fatal("期望因 jwt.secret 过短而报错，实际成功")
	}
}

func TestBuildDSNPrefersExplicitDSN(t *testing.T) {
	m := config.MySQLConfig{DSN: "explicit-dsn"}
	if got := m.BuildDSN(); got != "explicit-dsn" {
		t.Errorf("显式 DSN 应优先，实际 %q", got)
	}
}

func TestInvalidTokenCapacityRejected(t *testing.T) {
	setupEnv(t)
	t.Chdir("../..")
	orig, err := os.ReadFile("internal/config/config.yaml")
	if err != nil {
		t.Fatal(err)
	}
	for _, key := range []string{"context_window: 1000000", "max_token: 131072"} {
		broken := strings.Replace(string(orig), key, strings.Split(key, ":")[0]+": -1", 1)
		path := filepath.Join(t.TempDir(), "config.yaml")
		if err := os.WriteFile(path, []byte(broken), 0600); err != nil {
			t.Fatal(err)
		}
		t.Setenv("APP_CONFIG_PATH", path)
		if _, err := config.Load(); err == nil || !strings.Contains(err.Error(), "llm.") {
			t.Fatalf("容量参数应拒绝负数: %v", err)
		}
	}
}

func TestInvalidThinkingModeRejected(t *testing.T) {
	setupEnv(t)
	t.Chdir("../..")
	orig, err := os.ReadFile("internal/config/config.yaml")
	if err != nil {
		t.Skipf("读取原始配置失败: %v", err)
	}
	broken := strings.Replace(string(orig), "thinking_mode: first_call_only", "thinking_mode: unknown", 1)
	path := filepath.Join(t.TempDir(), "config.yaml")
	if err := os.WriteFile(path, []byte(broken), 0o644); err != nil {
		t.Fatalf("写入临时配置: %v", err)
	}
	t.Setenv("APP_CONFIG_PATH", path)

	if _, err := config.Load(); err == nil {
		t.Fatal("非法 thinking_mode 应启动失败")
	} else if !strings.Contains(err.Error(), "thinking_mode") {
		t.Errorf("错误信息应点明 thinking_mode, 实际: %v", err)
	}
}
