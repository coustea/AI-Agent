package auth

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"mentorly/internal/config"
)

var (
	ErrInvalidInput = errors.New("user_id and username are required")
	ErrInvalidToken = errors.New("invalid token")
	ErrExpiredToken = errors.New("token has expired")
)

// Claims 定义 JWT 携带的用户身份载荷。
type Claims struct {
	UserID   string `json:"user_id"`
	Username string `json:"username"`
	jwt.RegisteredClaims
}

// Jwt 提供 HS256 的签发与解析能力，参数来自配置文件而非硬编码。
type Jwt struct {
	secret []byte
	issuer string
	expire time.Duration
}

// New 从配置构建 Jwt 实例。
func New(cfg config.JWTConfig) *Jwt {
	return &Jwt{
		secret: []byte(cfg.Secret),
		issuer: cfg.Issuer,
		expire: cfg.Expire,
	}
}

// GenerateToken 为指定用户签发 JWT 字符串。
func (j *Jwt) GenerateToken(userID, username string) (string, error) {
	if strings.TrimSpace(userID) == "" || strings.TrimSpace(username) == "" {
		return "", ErrInvalidInput
	}

	now := time.Now()
	claims := Claims{
		UserID:   userID,
		Username: username,
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    j.issuer,
			Subject:   userID,
			IssuedAt:  jwt.NewNumericDate(now),
			NotBefore: jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(j.expire)),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString(j.secret)
	if err != nil {
		return "", fmt.Errorf("sign jwt token: %w", err)
	}
	return signed, nil
}

// ParseToken 解析并校验 JWT 字符串，返回强类型 Claims。
func (j *Jwt) ParseToken(tokenStr string) (*Claims, error) {
	if strings.TrimSpace(tokenStr) == "" {
		return nil, ErrInvalidToken
	}

	claims := &Claims{}
	token, err := jwt.ParseWithClaims(
		tokenStr,
		claims,
		func(_ *jwt.Token) (any, error) { return j.secret, nil },
		jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}),
		jwt.WithIssuer(j.issuer),
		jwt.WithExpirationRequired(),
	)
	if err != nil {
		if errors.Is(err, jwt.ErrTokenExpired) {
			return nil, ErrExpiredToken
		}
		return nil, fmt.Errorf("%w: %v", ErrInvalidToken, err)
	}
	if !token.Valid || strings.TrimSpace(claims.UserID) == "" || strings.TrimSpace(claims.Username) == "" {
		return nil, ErrInvalidToken
	}

	return claims, nil
}
