// Package dto 存放跨层传输对象：请求体与响应体。
// 与 model 分离，避免直接把数据库结构暴露给外部。
package dto

// RegisterReq 注册请求
type RegisterReq struct {
	Username string `json:"username" binding:"required,min=2,max=50"`
	Password string `json:"password" binding:"required,min=6,max=80"`
	Email    string `json:"email" binding:"required,email,max=100"`
}

// LoginReq 登录请求
type LoginReq struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

// UserResp 用户信息响应，不含密码等敏感字段。
type UserResp struct {
	ID       string `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email"`
	Avatar   string `json:"avatar"`
}

// LoginResp 登录响应
type LoginResp struct {
	Token string   `json:"token"`
	User  UserResp `json:"user"`
}
