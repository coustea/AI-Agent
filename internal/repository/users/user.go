// Package users 只负责 users 表：模型、字段约束与仓储查询。
//
// 认证逻辑不在这里：JWT 的签发与校验在 service/auth，
// Gin 认证中间件在 middleware，HTTP 入口在 handlers。
package users

import "time"

// User 对应 users 表。ID 由业务层生成 UUID。
type User struct {
	ID           string    `gorm:"column:id;type:varchar(36);primaryKey" json:"id"`
	CreatedAt    time.Time `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime" json:"created_at"`
	UpdatedAt    time.Time `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime" json:"updated_at"`
	Email        string    `gorm:"column:email;type:varchar(191);not null;uniqueIndex:uk_users_email" json:"email"`
	PasswordHash string    `gorm:"column:password_hash;type:varchar(255);not null" json:"-"`
	Username     string    `gorm:"column:username;type:varchar(100);not null;index:idx_users_username" json:"username"`
	Avatar       string    `gorm:"column:avatar;type:varchar(255);not null;default:''" json:"avatar"`
	Status       int8      `gorm:"column:status;type:tinyint;not null;default:1;index:idx_users_status" json:"status"`
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
