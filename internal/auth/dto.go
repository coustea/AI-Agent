package auth

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

// toUserResp 转成对外结构，剥离密码哈希等敏感字段。
func toUserResp(u *User) UserResp {
	return UserResp{
		ID:       u.ID,
		Username: u.Username,
		Email:    u.Email,
		Avatar:   u.Avatar,
	}
}

// toCredentialResp 把凭证转成登录响应。
func toCredentialResp(c *Credential) LoginResp {
	return LoginResp{
		Token: c.Token,
		User:  toUserResp(c.User),
	}
}
