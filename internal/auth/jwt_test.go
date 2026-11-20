package auth_test

import (
	"errors"
	"testing"
	"time"

	"mentorly/internal/auth"
	"mentorly/internal/config"
)

func newTestJWT(expire time.Duration) *auth.Jwt {
	return auth.New(config.JWTConfig{
		Secret: "mentorly-dev-secret-key-change-in-production",
		Issuer: "Mentorly",
		Expire: expire,
	})
}

func TestGenerateAndParse(t *testing.T) {
	j := newTestJWT(time.Hour)

	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}
	if token == "" {
		t.Fatal("token 为空")
	}

	claims, err := j.ParseToken(token)
	if err != nil {
		t.Fatalf("ParseToken: %v", err)
	}
	if claims.UserID != "user-1" || claims.Username != "alice" {
		t.Errorf("claims = %+v", claims)
	}
}

func TestGenerateTokenRejectsEmptyInput(t *testing.T) {
	j := newTestJWT(time.Hour)

	if _, err := j.GenerateToken("", "alice"); !errors.Is(err, auth.ErrInvalidInput) {
		t.Errorf("空 userID 应返回 ErrInvalidInput，实际 %v", err)
	}
	if _, err := j.GenerateToken("user-1", ""); !errors.Is(err, auth.ErrInvalidInput) {
		t.Errorf("空 username 应返回 ErrInvalidInput，实际 %v", err)
	}
}

func TestExpiredToken(t *testing.T) {
	// 负的有效期让 token 立即过期
	j := newTestJWT(-time.Hour)

	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	if _, err := j.ParseToken(token); !errors.Is(err, auth.ErrExpiredToken) {
		t.Errorf("期望 ErrExpiredToken，实际 %v", err)
	}
}

func TestParseTokenRejectsBadInput(t *testing.T) {
	j := newTestJWT(time.Hour)

	if _, err := j.ParseToken(""); !errors.Is(err, auth.ErrInvalidToken) {
		t.Errorf("空 token 应返回 ErrInvalidToken，实际 %v", err)
	}
	if _, err := j.ParseToken("not-a-jwt"); !errors.Is(err, auth.ErrInvalidToken) {
		t.Errorf("非法 token 应返回 ErrInvalidToken，实际 %v", err)
	}
}

func TestParseTokenRejectsWrongSecret(t *testing.T) {
	issuer := newTestJWT(time.Hour)
	attacker := auth.New(config.JWTConfig{
		Secret: "another-secret-key-that-is-long-enough-32",
		Issuer: "Mentorly",
		Expire: time.Hour,
	})

	token, err := issuer.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	// 用不同密钥校验必须失败，否则任何人都能伪造身份。
	if _, err := attacker.ParseToken(token); err == nil {
		t.Fatal("不同密钥应校验失败")
	}
}

func TestParseTokenRejectsWrongIssuer(t *testing.T) {
	signer := newTestJWT(time.Hour)
	other := auth.New(config.JWTConfig{
		Secret: "mentorly-dev-secret-key-change-in-production",
		Issuer: "SomeoneElse",
		Expire: time.Hour,
	})

	token, err := signer.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	if _, err := other.ParseToken(token); err == nil {
		t.Fatal("issuer 不匹配应校验失败")
	}
}
