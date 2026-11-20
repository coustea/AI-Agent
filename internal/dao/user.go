package dao

import (
	"errors"

	"gorm.io/gorm"

	"mentorly/internal/model"
)

// ErrDuplicateUser 表示唯一键冲突，即该邮箱已被注册。
// 把驱动底层错误翻译成哨兵错误，避免上层直接依赖 gorm 或 MySQL 错误码。
var ErrDuplicateUser = errors.New("duplicate user")

// ErrRecordNotFound 资源不存在，屏蔽 gorm 细节。
var ErrRecordNotFound = errors.New("record not found")

// UserRepo 用户仓储
type UserRepo struct {
	db *gorm.DB
}

func NewUserRepo(db *gorm.DB) *UserRepo {
	return &UserRepo{db: db}
}

// Create 创建用户。依赖 InitMySQL 开启的 TranslateError，
// 唯一键冲突会被翻译成 gorm.ErrDuplicatedKey。
func (r *UserRepo) Create(user *model.User) error {
	err := r.db.Create(user).Error
	if errors.Is(err, gorm.ErrDuplicatedKey) {
		return ErrDuplicateUser
	}
	return err
}

// GetByID 按主键查询
func (r *UserRepo) GetByID(id string) (*model.User, error) {
	var user model.User
	if err := r.db.First(&user, "id = ?", id).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrRecordNotFound
		}
		return nil, err
	}
	return &user, nil
}

// GetByEmail 按邮箱查询，登录时使用。
func (r *UserRepo) GetByEmail(email string) (*model.User, error) {
	var user model.User
	if err := r.db.Where("email = ?", email).First(&user).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrRecordNotFound
		}
		return nil, err
	}
	return &user, nil
}

// ExistsByEmail 判断邮箱是否已注册。
func (r *UserRepo) ExistsByEmail(email string) (bool, error) {
	var count int64
	if err := r.db.Model(&model.User{}).Where("email = ?", email).Count(&count).Error; err != nil {
		return false, err
	}
	return count > 0, nil
}
