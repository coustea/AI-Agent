package middleware_test

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"

	"mentorly/internal/config"
	"mentorly/internal/middleware"
	"mentorly/internal/service/auth"
)

func newTestJWT(expire time.Duration) *auth.Jwt {
	return auth.New(config.JWTConfig{Secret: "test-secret-at-least-thirty-two-characters", Issuer: "mentorly-test", Expire: expire})
}

type stubChecker struct {
	err   error
	calls int
}

func (s *stubChecker) VerifyUser(_ context.Context, _ string) error {
	s.calls++
	return s.err
}

func newRouter(j *auth.Jwt, checker middleware.UserChecker) *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	g := r.Group("")
	g.Use(middleware.Auth(j, checker))
	g.GET("/whoami", func(c *gin.Context) {
		id, ok := middleware.CurrentUser(c)
		c.JSON(http.StatusOK, gin.H{
			"ok":       ok,
			"user_id":  id.UserID,
			"username": id.Username,
		})
	})
	return r
}

func doGet(t *testing.T, r *gin.Engine, token string) (int, map[string]any) {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, "/whoami", nil)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	var body map[string]any
	if w.Body.Len() > 0 {
		_ = json.Unmarshal(w.Body.Bytes(), &body)
	}
	return w.Code, body
}

func TestMiddlewareInjectsUserIDAndUsername(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	checker := &stubChecker{}
	code, body := doGet(t, newRouter(j, checker), token)
	if code != http.StatusOK {
		t.Fatalf("status = %d, want 200", code)
	}
	if body["ok"] != true || body["user_id"] != "user-1" || body["username"] != "alice" || checker.calls != 1 {
		t.Fatalf("unexpected identity or calls: body=%v calls=%d", body, checker.calls)
	}
}

func TestMiddlewareRejectsMissingHeader(t *testing.T) {
	j := newTestJWT(time.Hour)
	code, body := doGet(t, newRouter(j, nil), "")
	if code != http.StatusUnauthorized || body["message"] != "缺少 Authorization 请求头" {
		t.Fatalf("status=%d body=%v", code, body)
	}
}

func TestMiddlewareRejectsExpiredToken(t *testing.T) {
	j := newTestJWT(-time.Hour)
	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}
	code, body := doGet(t, newRouter(j, nil), token)
	if code != http.StatusUnauthorized || body["message"] != "登录已过期，请重新登录" {
		t.Fatalf("status=%d body=%v", code, body)
	}
}

func TestMiddlewareRejectsDeletedUser(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, _ := j.GenerateToken("user-1", "alice")
	code, _ := doGet(t, newRouter(j, &stubChecker{err: auth.ErrNotFound}), token)
	if code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", code)
	}
}

func TestMiddlewareRejectsDisabledUser(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, _ := j.GenerateToken("user-1", "alice")
	code, body := doGet(t, newRouter(j, &stubChecker{err: auth.ErrDisabled}), token)
	if code != http.StatusForbidden || body["message"] != "账号已被禁用" {
		t.Fatalf("status=%d body=%v", code, body)
	}
}

func TestMiddlewareFailsClosedOnCheckerError(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, _ := j.GenerateToken("user-1", "alice")
	code, _ := doGet(t, newRouter(j, &stubChecker{err: errors.New("db down")}), token)
	if code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", code)
	}
}

func TestMiddlewareRejectsTamperedSignature(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, _ := j.GenerateToken("user-1", "alice")
	tampered := token[:len(token)-4] + "AAAA"
	if code, _ := doGet(t, newRouter(j, &stubChecker{}), tampered); code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", code)
	}
}

func TestCurrentUserAbsentWithoutMiddleware(t *testing.T) {
	gin.SetMode(gin.TestMode)
	c, _ := gin.CreateTestContext(httptest.NewRecorder())
	if _, ok := middleware.CurrentUser(c); ok {
		t.Fatal("未认证的上下文不应返回身份")
	}
}

func TestMustUserPanicsWithoutMiddleware(t *testing.T) {
	gin.SetMode(gin.TestMode)
	c, _ := gin.CreateTestContext(httptest.NewRecorder())
	defer func() {
		if recover() == nil {
			t.Fatal("缺少身份时 MustUser 应 panic")
		}
	}()
	_ = middleware.MustUser(c)
}

func TestIdentityCarriesBothFields(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, _ := j.GenerateToken("user-9", "bob")
	code, body := doGet(t, newRouter(j, &stubChecker{}), token)
	if code != http.StatusOK || body["user_id"] != "user-9" || body["username"] != "bob" {
		t.Fatalf("status=%d body=%v", code, body)
	}
}
