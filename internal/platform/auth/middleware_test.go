package auth_test

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"

	"mentorly/internal/platform/auth"
)

// stubChecker 用固定返回值模拟用户状态回查。
type stubChecker struct {
	status auth.UserStatus
	err    error
	calls  int
}

func (s *stubChecker) CheckUserStatus(_ context.Context, _ string) (auth.UserStatus, error) {
	s.calls++
	return s.status, s.err
}

// newRouter 构建一个只挂了认证中间件的最小路由，
// /whoami 返回中间件写入上下文的身份，用于确认放行时上下文确实被填充。
func newRouter(j *auth.Jwt, checker auth.UserChecker) *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	g := r.Group("")
	g.Use(auth.Middleware(j, checker))
	g.GET("/whoami", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"user_id":  auth.CurrentUserID(c),
			"username": auth.CurrentUsername(c),
		})
	})
	return r
}

// doGet 发起一次带 Bearer token 的请求，返回状态码与响应体。
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

	checker := &stubChecker{status: auth.UserStatusActive}
	code, body := doGet(t, newRouter(j, checker), token)
	if code != http.StatusOK {
		t.Fatalf("status = %d, want 200", code)
	}

	// user_id 与 username 必须都能从上下文取到，这是 handler 依赖的契约。
	if body["user_id"] != "user-1" {
		t.Errorf("user_id = %v, want user-1", body["user_id"])
	}
	if body["username"] != "alice" {
		t.Errorf("username = %v, want alice", body["username"])
	}
	if checker.calls != 1 {
		t.Errorf("用户状态应被回查一次，实际 %d 次", checker.calls)
	}
}

func TestMiddlewareRejectsMissingHeader(t *testing.T) {
	j := newTestJWT(time.Hour)
	code, body := doGet(t, newRouter(j, nil), "")
	if code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", code)
	}
	if body["message"] != "缺少 Authorization 请求头" {
		t.Errorf("message = %v", body["message"])
	}
}

func TestMiddlewareRejectsExpiredToken(t *testing.T) {
	j := newTestJWT(-time.Hour)
	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	// 过期与非法要给出不同提示，前端据此决定是否跳登录页。
	code, body := doGet(t, newRouter(j, nil), token)
	if code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", code)
	}
	if body["message"] != "登录已过期，请重新登录" {
		t.Errorf("message = %v", body["message"])
	}
}

func TestMiddlewareRejectsDeletedUser(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	// 签名有效但账号已删除：必须拒绝，否则删号在 token 过期前无效。
	checker := &stubChecker{status: auth.UserStatusMissing}
	code, _ := doGet(t, newRouter(j, checker), token)
	if code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", code)
	}
}

func TestMiddlewareRejectsDisabledUser(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	// 被禁用是「已认证但无权限」，用 403 与「未认证」区分。
	checker := &stubChecker{status: auth.UserStatusDisabled}
	code, body := doGet(t, newRouter(j, checker), token)
	if code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", code)
	}
	if body["message"] != "账号已被禁用" {
		t.Errorf("message = %v", body["message"])
	}
}

func TestMiddlewareFailsClosedOnCheckerError(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	// 数据库故障时绝不能放行，否则一次故障就等于认证失效。
	checker := &stubChecker{status: auth.UserStatusUnknown, err: errors.New("db down")}
	code, _ := doGet(t, newRouter(j, checker), token)
	if code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", code)
	}
}

func TestMiddlewareRejectsTamperedSignature(t *testing.T) {
	j := newTestJWT(time.Hour)
	token, err := j.GenerateToken("user-1", "alice")
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	// 改动签名末位，模拟伪造 token。
	tampered := token[:len(token)-4] + "AAAA"
	if code, _ := doGet(t, newRouter(j, &stubChecker{status: auth.UserStatusActive}), tampered); code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", code)
	}
}
