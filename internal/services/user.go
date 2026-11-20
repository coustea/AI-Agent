// Package services 是业务逻辑层，介于 handler 与 dao 之间。
package services

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"

	"mentorly/internal/auth"
	"mentorly/internal/dao"
	"mentorly/internal/dto"
	"mentorly/internal/model"
)

var (
	// ErrEmailTaken 邮箱已被注册
	ErrEmailTaken = errors.New("该邮箱已被注册")
	// ErrInvalidCredentials 邮箱或密码错误（统一提示，避免泄露账号是否存在）
	ErrInvalidCredentials = errors.New("邮箱或密码错误")
	// ErrUserNotFound 用户不存在
	ErrUserNotFound = errors.New("用户不存在")
	// ErrUserDisabled 账号已被禁用
	ErrUserDisabled = errors.New("账号已被禁用")
)

// UserService 用户业务逻辑
type UserService struct {
	repo *dao.UserRepo
	jwt  *auth.Jwt
}

func NewUserService(repo *dao.UserRepo, jwt *auth.Jwt) *UserService {
	return &UserService{repo: repo, jwt: jwt}
}

// HashPassword 生成 bcrypt 密码哈希。
func HashPassword(password string) (string, error) {
	hashed, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return "", fmt.Errorf("生成密码哈希失败: %w", err)
	}
	return string(hashed), nil
}

// CheckPassword 校验密码是否匹配。
func CheckPassword(hashedPassword, plainPassword string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(plainPassword)) == nil
}

// Register 注册新用户，返回用户信息与登录 token。
func (s *UserService) Register(req *dto.RegisterReq) (*dto.LoginResp, error) {
	hash, err := HashPassword(req.Password)
	if err != nil {
		return nil, err
	}

	user := &model.User{
		Base:         model.Base{ID: uuid.NewString()},
		Username:     req.Username,
		Email:        req.Email,
		PasswordHash: hash,
		Status:       1,
	}

	if err := s.repo.Create(user); err != nil {
		if errors.Is(err, dao.ErrDuplicateUser) {
			return nil, ErrEmailTaken
		}
		return nil, fmt.Errorf("创建用户失败: %w", err)
	}

	token, err := s.jwt.GenerateToken(user.ID, user.Username)
	if err != nil {
		return nil, err
	}

	return &dto.LoginResp{Token: token, User: toUserResp(user)}, nil
}

// Login 校验邮箱密码并签发 token。
func (s *UserService) Login(req *dto.LoginReq) (*dto.LoginResp, error) {
	user, err := s.repo.GetByEmail(req.Email)
	if err != nil {
		if errors.Is(err, dao.ErrRecordNotFound) {
			// 邮箱不存在与密码错误返回同一提示，避免被用来枚举已注册邮箱。
			return nil, ErrInvalidCredentials
		}
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}

	if !CheckPassword(user.PasswordHash, req.Password) {
		return nil, ErrInvalidCredentials
	}

	// 密码正确也要拦住已禁用的账号，否则停用形同虚设：
	// 被停用者重新登录即可拿到新 token。
	if !user.IsActive() {
		return nil, ErrUserDisabled
	}

	token, err := s.jwt.GenerateToken(user.ID, user.Username)
	if err != nil {
		return nil, err
	}

	return &dto.LoginResp{Token: token, User: toUserResp(user)}, nil
}

// CheckUserStatus 实现 auth.UserChecker：把 token 里的 user_id 映射为真实账号状态。
//
// 这是「JWT 只验签名」的补强。用户被删除或 status 置 0 后，
// 旧 token 在有效期（默认 168h）内仍然签名合法，若只验签名，
// 停用和删号都无法即时生效。
func (s *UserService) CheckUserStatus(ctx context.Context, userID string) (auth.UserStatus, error) {
	if strings.TrimSpace(userID) == "" {
		return auth.UserStatusMissing, nil
	}

	user, err := s.repo.GetByID(userID)
	if err != nil {
		if errors.Is(err, dao.ErrRecordNotFound) {
			return auth.UserStatusMissing, nil
		}
		// 数据库故障与「用户不存在」必须区分：前者不能当成删号，
		// 也绝不能放行，交给中间件返回 500。
		return auth.UserStatusUnknown, fmt.Errorf("查询用户状态失败: %w", err)
	}

	if !user.IsActive() {
		return auth.UserStatusDisabled, nil
	}
	return auth.UserStatusActive, nil
}

// GetProfile 查询用户资料。
func (s *UserService) GetProfile(userID string) (*dto.UserResp, error) {
	user, err := s.repo.GetByID(userID)
	if err != nil {
		if errors.Is(err, dao.ErrRecordNotFound) {
			return nil, ErrUserNotFound
		}
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}

	resp := toUserResp(user)
	return &resp, nil
}

// toUserResp 转成对外结构，剥离密码哈希等敏感字段。
func toUserResp(u *model.User) dto.UserResp {
	return dto.UserResp{
		ID:       u.ID,
		Username: u.Username,
		Email:    u.Email,
		Avatar:   u.Avatar,
	}
}
