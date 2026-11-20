// Package identity 是用户身份与认证的领域包：注册、登录、资料与账号状态。
//
// 传输结构（dto）不在这里：本包只返回领域类型，
// 由 httpapi 负责把它转成 JSON，避免领域层被 HTTP 契约绑住。
package identity

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"

	"mentorly/internal/auth"
)

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

// Service 是用户身份业务逻辑。
type Service struct {
	repo *Repo
	jwt  *auth.Jwt
}

// NewService 构造身份服务。
func NewService(repo *Repo, jwt *auth.Jwt) *Service {
	return &Service{repo: repo, jwt: jwt}
}

// Credential 是登录/注册成功后的凭证与用户信息。
type Credential struct {
	Token string
	User  *User
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
func (s *Service) Register(ctx context.Context, username, email, password string) (*Credential, error) {
	hash, err := HashPassword(password)
	if err != nil {
		return nil, err
	}

	user := &User{
		Base:         Base{ID: uuid.NewString()},
		Username:     username,
		Email:        email,
		PasswordHash: hash,
		Status:       UserStatusActive,
	}

	if err := s.repo.Create(user); err != nil {
		if errors.Is(err, ErrDuplicateUser) {
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
		if errors.Is(err, ErrUserNotFound) {
			// 邮箱不存在与密码错误返回同一提示，避免被用来枚举已注册邮箱。
			return nil, ErrInvalidCredentials
		}
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}

	if !CheckPassword(user.PasswordHash, password) {
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

// CheckStatus 实现 auth.UserChecker：把 token 里的 user_id 映射为真实账号状态。
//
// 这是「JWT 只验签名」的补强。用户被删除或 status 置 0 后，
// 旧 token 在有效期（默认 168h）内仍然签名合法，若只验签名，
// 停用和删号都无法即时生效。
func (s *Service) CheckStatus(ctx context.Context, userID string) (auth.UserStatus, error) {
	if strings.TrimSpace(userID) == "" {
		return auth.UserStatusMissing, nil
	}

	user, err := s.repo.GetByID(userID)
	if err != nil {
		if errors.Is(err, ErrUserNotFound) {
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

// CheckUserStatus 是 CheckStatus 的方法名别名，满足 auth.UserChecker 接口。
func (s *Service) CheckUserStatus(ctx context.Context, userID string) (auth.UserStatus, error) {
	return s.CheckStatus(ctx, userID)
}

// Profile 查询用户资料。
func (s *Service) Profile(ctx context.Context, userID string) (*User, error) {
	user, err := s.repo.GetByID(userID)
	if err != nil {
		if errors.Is(err, ErrUserNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}
	return user, nil
}
