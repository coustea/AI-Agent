package auth

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"

	"mentorly/internal/repository/users"
)

type User = users.User

var (
	// ErrEmailTaken 邮箱已被注册
	ErrEmailTaken = errors.New("该邮箱已被注册")
	// ErrInvalidCredentials 邮箱或密码错误（统一提示，避免泄露账号是否存在）
	ErrInvalidCredentials = errors.New("邮箱或密码错误")
	// ErrNotFound 用户不存在
	ErrNotFound = errors.New("用户不存在")
	// ErrDisabled 账号已被禁用
	ErrDisabled = errors.New("账号已被禁用")
)

// UserStatus 描述 JWT 所指用户在数据库中的实际状态。
type UserStatus int

const (
	UserStatusUnknown UserStatus = iota
	UserStatusActive
	UserStatusMissing
	UserStatusDisabled
)

// Service 是用户身份业务逻辑。
type Service struct {
	repo *users.Store
	jwt  *Jwt
}

// NewService 构造身份服务。
func NewService(repo *users.Store, jwt *Jwt) *Service {
	return &Service{repo: repo, jwt: jwt}
}

// Credential 是登录/注册成功后的凭证与用户信息。
type Credential struct {
	Token string
	User  *users.User
}

// Register 注册新用户，返回用户信息与登录 token。
func (s *Service) Register(ctx context.Context, username, email, password string) (*Credential, error) {
	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return nil, err
	}

	user := &users.User{
		ID:           uuid.NewString(),
		Username:     username,
		Email:        email,
		PasswordHash: string(hash),
		Status:       users.UserStateActive,
	}

	if err := s.repo.Create(user); err != nil {
		if errors.Is(err, users.ErrDuplicateUser) {
			return nil, ErrEmailTaken
		}
		return nil, fmt.Errorf("创建用户失败: %w", err)
	}

	token, err := s.jwt.GenerateToken(user.ID, user.Username)
	if err != nil {
		return nil, err
	}
	return &Credential{Token: token, User: user}, nil
}

// Login 校验邮箱密码并签发 token。
func (s *Service) Login(ctx context.Context, email, password string) (*Credential, error) {
	user, err := s.repo.GetByEmail(email)
	if err != nil {
		if errors.Is(err, users.ErrUserNotFound) {
			// 邮箱不存在与密码错误返回同一提示，避免被用来枚举已注册邮箱。
			return nil, ErrInvalidCredentials
		}
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}

	if bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)) != nil {
		return nil, ErrInvalidCredentials
	}

	// 密码正确也要拦住已禁用的账号，否则停用形同虚设：
	// 被停用者重新登录即可拿到新 token。
	if !user.IsActive() {
		return nil, ErrDisabled
	}

	token, err := s.jwt.GenerateToken(user.ID, user.Username)
	if err != nil {
		return nil, err
	}
	return &Credential{Token: token, User: user}, nil
}

// CheckUserStatus 实现 UserChecker：把 token 里的 user_id 映射为真实账号状态。
//
// 这是「JWT 只验签名」的补强。用户被删除或 status 置 0 后，
// 旧 token 在有效期（默认 168h）内仍然签名合法，若只验签名，
// 停用和删号都无法即时生效。
func (s *Service) CheckUserStatus(ctx context.Context, userID string) (UserStatus, error) {
	if strings.TrimSpace(userID) == "" {
		return UserStatusMissing, nil
	}

	user, err := s.repo.GetByID(userID)
	if err != nil {
		if errors.Is(err, users.ErrUserNotFound) {
			return UserStatusMissing, nil
		}
		// 数据库故障与「用户不存在」必须区分：前者不能当成删号，
		// 也绝不能放行，交给中间件返回 500。
		return UserStatusUnknown, fmt.Errorf("查询用户状态失败: %w", err)
	}

	if !user.IsActive() {
		return UserStatusDisabled, nil
	}
	return UserStatusActive, nil
}

// Profile 查询用户资料。
func (s *Service) Profile(ctx context.Context, userID string) (*users.User, error) {
	user, err := s.repo.GetByID(userID)
	if err != nil {
		if errors.Is(err, users.ErrUserNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}
	return user, nil
}
