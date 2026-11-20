// Package setup_test 验证核心依赖可用，防止 go.mod 被误改后静默降级。
package setup_test

import (
	"strings"
	"testing"
	"time"

	"github.com/cloudwego/eino/schema"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"github.com/spf13/viper"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"

	"mentorly/internal/platform/auth"
	"mentorly/internal/platform/config"
)

// TestGinUsable 确认 gin 引擎可创建并注册路由。
func TestGinUsable(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/ping", func(c *gin.Context) { c.String(200, "pong") })

	if len(r.Routes()) == 0 {
		t.Fatal("gin 未注册任何路由")
	}
}

// TestGormUsable 确认 gorm 能构建 MySQL 方言的语句（不建立真实连接）。
func TestGormUsable(t *testing.T) {
	db, err := gorm.Open(mysql.New(mysql.Config{
		// 指向不可达端口，配合 DisableAutomaticPing 保证不会真的连库。
		DSN:                       "user:pass@tcp(127.0.0.1:1)/db?charset=utf8mb4&parseTime=True",
		SkipInitializeWithVersion: true,
	}), &gorm.Config{
		DryRun:               true,
		DisableAutomaticPing: true,
	})
	if err != nil {
		t.Fatalf("gorm 初始化失败: %v", err)
	}

	stmt := db.Session(&gorm.Session{DryRun: true}).Find(&[]struct{ ID uint }{})
	if stmt.Statement == nil || stmt.Statement.SQL.String() == "" {
		t.Fatal("gorm 未生成 SQL 语句")
	}
}

// TestRedisUsable 确认 go-redis 能构建客户端与命令（不发包）。
func TestRedisUsable(t *testing.T) {
	client := redis.NewClient(&redis.Options{Addr: "127.0.0.1:6379"})
	defer func() { _ = client.Close() }()

	if client.Options().Addr != "127.0.0.1:6379" {
		t.Fatal("redis 客户端配置异常")
	}
}

// TestViperDurationHook 确认 viper 能正确解析带单位的时长，
// 这是 jwt.expire 配置正确性的前提。
func TestViperDurationHook(t *testing.T) {
	v := viper.New()
	v.SetConfigType("yaml")
	if err := v.ReadConfig(strings.NewReader("expire: 168h\n")); err != nil {
		t.Fatalf("读取配置失败: %v", err)
	}

	var out struct {
		Expire time.Duration `mapstructure:"expire"`
	}
	if err := v.Unmarshal(&out); err != nil {
		t.Fatalf("反序列化失败: %v", err)
	}
	if out.Expire != 168*time.Hour {
		t.Errorf("expire = %v, want 168h", out.Expire)
	}
}

// TestEinoSchema 确认 eino 消息构造可用。
func TestEinoSchema(t *testing.T) {
	msg := schema.UserMessage("hello")
	if msg.Role != schema.User {
		t.Fatalf("eino role 异常: %v", msg.Role)
	}
}

// TestJWTUsable 确认 auth 层可签发与解析 token。
func TestJWTUsable(t *testing.T) {
	j := auth.New(config.JWTConfig{
		Secret: "mentorly-dev-secret-key-change-in-production",
		Issuer: "Mentorly",
		Expire: time.Hour,
	})

	token, err := j.GenerateToken("u1", "alice")
	if err != nil {
		t.Fatalf("签发失败: %v", err)
	}
	claims, err := j.ParseToken(token)
	if err != nil {
		t.Fatalf("解析失败: %v", err)
	}
	if claims.UserID != "u1" {
		t.Errorf("userID = %q", claims.UserID)
	}
}
