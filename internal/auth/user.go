// Package auth 是用户身份与认证的限界上下文：注册、登录、资料、账号状态，
// 以及 JWT 的签发、校验与 Gin 认证中间件。
//
// 传输结构（dto）与 HTTP handler 也在本包内，但领域类型不携带 JSON tag，
// 由 dto 层负责转换，避免领域模型被 HTTP 契约绑住。
package auth

// User 对应 users 表。ID 由业务层生成 UUID。
type User struct {
	Base
	Email        string `gorm:"column:email;type:varchar(191);not null;uniqueIndex:uk_users_email" json:"email"`
	PasswordHash string `gorm:"column:password_hash;type:varchar(255);not null" json:"-"`
	Username     string `gorm:"column:username;type:varchar(100);not null;index:idx_users_username" json:"username"`
	Avatar       string `gorm:"column:avatar;type:varchar(255);not null;default:''" json:"avatar"`
	Status       int8   `gorm:"column:status;type:tinyint;not null;default:1;index:idx_users_status" json:"status"`
}

// TableName 固定表名，避免命名策略变更导致漂移。
func (User) TableName() string { return "users" }

// 用户状态取值。存入 users.status。
const (
	// UserStateDisabled 账号已被禁用，登录与鉴权都应拒绝
	UserStateDisabled int8 = 0
	// UserStateActive 账号正常可用
	UserStateActive int8 = 1
)

// IsActive 判断账号是否处于可正常使用的状态。
func (u *User) IsActive() bool { return u.Status == UserStateActive }
