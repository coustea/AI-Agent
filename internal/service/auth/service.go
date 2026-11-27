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
	ErrEmailTaken         = errors.New("该邮箱已被注册")
	ErrInvalidCredentials = errors.New("邮箱或密码错误")
	ErrNotFound           = errors.New("用户不存在")
	ErrDisabled           = errors.New("账号已被禁用")
)

type Service struct {
	repo *users.Store
	jwt  *Jwt
}

func NewService(repo *users.Store, jwt *Jwt) *Service {
	return &Service{repo: repo, jwt: jwt}
}

type Credential struct {
	Token string
	User  *users.User
}

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
	if err := s.repo.Create(ctx, user); err != nil {
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

func (s *Service) Login(ctx context.Context, email, password string) (*Credential, error) {
	user, err := s.repo.GetByEmail(ctx, email)
	if err != nil {
		if errors.Is(err, users.ErrUserNotFound) {
			return nil, ErrInvalidCredentials
		}
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}
	if bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)) != nil {
		return nil, ErrInvalidCredentials
	}
	if !user.IsActive() {
		return nil, ErrDisabled
	}
	token, err := s.jwt.GenerateToken(user.ID, user.Username)
	if err != nil {
		return nil, err
	}
	return &Credential{Token: token, User: user}, nil
}

// VerifyUser 核对 token 对应的真实账号状态，确保删号与禁用即时生效。
func (s *Service) VerifyUser(ctx context.Context, userID string) error {
	if strings.TrimSpace(userID) == "" {
		return ErrNotFound
	}
	user, err := s.repo.GetByID(ctx, userID)
	if err != nil {
		if errors.Is(err, users.ErrUserNotFound) {
			return ErrNotFound
		}
		return fmt.Errorf("查询用户状态失败: %w", err)
	}
	if !user.IsActive() {
		return ErrDisabled
	}
	return nil
}

func (s *Service) Profile(ctx context.Context, userID string) (*users.User, error) {
	user, err := s.repo.GetByID(ctx, userID)
	if err != nil {
		if errors.Is(err, users.ErrUserNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}
	return user, nil
}
