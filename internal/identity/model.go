package identity

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
	// UserStatusDisabled 账号已被禁用，登录与鉴权都应拒绝
	UserStatusDisabled int8 = 0
	// UserStatusActive 账号正常可用
	UserStatusActive int8 = 1
)

// IsActive 判断账号是否处于可正常使用的状态。
func (u *User) IsActive() bool { return u.Status == UserStatusActive }
