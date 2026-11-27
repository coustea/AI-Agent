// Package users 负责 users 表模型与仓储查询。
package users

import (
	"context"
	"errors"
	"time"

	"gorm.io/gorm"
)

const (
	UserStateDisabled int8 = 0
	UserStateActive   int8 = 1
)

var (
	ErrDuplicateUser = errors.New("duplicate user")
	ErrUserNotFound  = errors.New("user not found")
)

type User struct {
	ID           string    `gorm:"column:id;type:varchar(36);primaryKey"`
	CreatedAt    time.Time `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime"`
	UpdatedAt    time.Time `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime"`
	Email        string    `gorm:"column:email;type:varchar(191);not null;uniqueIndex:uk_users_email"`
	PasswordHash string    `gorm:"column:password_hash;type:varchar(255);not null"`
	Username     string    `gorm:"column:username;type:varchar(100);not null;index:idx_users_username"`
	Status       int8      `gorm:"column:status;type:tinyint;not null;default:1;index:idx_users_status"`
}

func (User) TableName() string { return "users" }

func (u *User) IsActive() bool { return u.Status == UserStateActive }

type Store struct {
	db *gorm.DB
}

func NewStore(db *gorm.DB) *Store { return &Store{db: db} }

func (s *Store) Create(ctx context.Context, user *User) error {
	err := s.db.WithContext(ctx).Create(user).Error
	if errors.Is(err, gorm.ErrDuplicatedKey) {
		return ErrDuplicateUser
	}
	return err
}

func (s *Store) GetByID(ctx context.Context, id string) (*User, error) {
	var user User
	if err := s.db.WithContext(ctx).First(&user, "id = ?", id).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrUserNotFound
		}
		return nil, err
	}
	return &user, nil
}

func (s *Store) GetByEmail(ctx context.Context, email string) (*User, error) {
	var user User
	if err := s.db.WithContext(ctx).Where("email = ?", email).First(&user).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrUserNotFound
		}
		return nil, err
	}
	return &user, nil
}
