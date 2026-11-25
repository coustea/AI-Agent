// Package response 定义全站统一响应体，避免各 handler 各写一套 JSON 结构。
package response

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// Body 是全站统一响应结构。
// Code 为业务码：0 表示成功，非 0 表示具体错误。
type Body struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

// 常用业务错误码
const (
	CodeOK           = 0
	CodeBadRequest   = 40000
	CodeUnauthorized = 40100
	CodeForbidden    = 40300
	CodeNotFound     = 40400
	CodeConflict     = 40900
	CodeServerError  = 50000
	CodeUnavailable  = 50300
)

// OK 返回成功响应
func OK(c *gin.Context, data any) {
	c.JSON(http.StatusOK, Body{Code: CodeOK, Message: "ok", Data: data})
}

// Fail 返回指定 HTTP 状态码与业务码的错误响应
func Fail(c *gin.Context, status, code int, message string) {
	c.JSON(status, Body{Code: code, Message: message})
}

// BadRequest 参数错误
func BadRequest(c *gin.Context, message string) {
	Fail(c, http.StatusBadRequest, CodeBadRequest, message)
}

// Unauthorized 未认证
func Unauthorized(c *gin.Context, message string) {
	Fail(c, http.StatusUnauthorized, CodeUnauthorized, message)
}

// Forbidden 无权限
func Forbidden(c *gin.Context, message string) {
	Fail(c, http.StatusForbidden, CodeForbidden, message)
}

// NotFound 资源不存在
func NotFound(c *gin.Context, message string) {
	Fail(c, http.StatusNotFound, CodeNotFound, message)
}

// Conflict 资源冲突
func Conflict(c *gin.Context, message string) {
	Fail(c, http.StatusConflict, CodeConflict, message)
}

// ServerError 服务端错误
func ServerError(c *gin.Context, message string) {
	Fail(c, http.StatusInternalServerError, CodeServerError, message)
}

// Unavailable 依赖不可用
func Unavailable(c *gin.Context, message string) {
	Fail(c, http.StatusServiceUnavailable, CodeUnavailable, message)
}
