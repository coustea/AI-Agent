package auth

import "time"

// Base 是所有业务表的公共字段。
// ID 由业务层生成 UUID（见 services 层），不依赖数据库自增，
// 便于分库分表与跨服务传递。
type Base struct {
	ID        string    `gorm:"column:id;type:varchar(36);primaryKey" json:"id"`
	CreatedAt time.Time `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime" json:"created_at"`
	UpdatedAt time.Time `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime" json:"updated_at"`
}
