package auth

import (
	"errors"

	"gorm.io/gorm"
)

// ErrDuplicateUser 表示唯一键冲突，即该邮箱已被注册。
// 把驱动底层错误翻译成哨兵错误，避免上层直接依赖 gorm 或 MySQL 错误码。
var ErrDuplicateUser = errors.New("duplicate user")

// ErrUserNotFound 用户不存在。
var ErrUserNotFound = errors.New("user not found")

// Store 用户仓储。
type Store struct {
	db *gorm.DB
}

func NewStore(db *gorm.DB) *Store {
	return &Store{db: db}
}

// Create 创建用户。依赖 InitMySQL 开启的 TranslateError，
// 唯一键冲突会被翻译成 gorm.ErrDuplicatedKey。
func (s *Store) Create(user *User) error {
	err := s.db.Create(user).Error
	if errors.Is(err, gorm.ErrDuplicatedKey) {
		return ErrDuplicateUser
	}
	return err
}

// GetByID 按主键查询
func (s *Store) GetByID(id string) (*User, error) {
	var user User
	if err := s.db.First(&user, "id = ?", id).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrUserNotFound
		}
		return nil, err
	}
	return &user, nil
}

// GetByEmail 按邮箱查询，登录时使用。
func (s *Store) GetByEmail(email string) (*User, error) {
	var user User
	if err := s.db.Where("email = ?", email).First(&user).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrUserNotFound
		}
		return nil, err
	}
	return &user, nil
}

// ExistsByEmail 判断邮箱是否已注册。
func (s *Store) ExistsByEmail(email string) (bool, error) {
	var count int64
	if err := s.db.Model(&User{}).Where("email = ?", email).Count(&count).Error; err != nil {
		return false, err
	}
	return count > 0, nil
}
