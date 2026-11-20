package store

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// ErrLockBusy 表示锁已被占用，即同一会话正在生成中。
var ErrLockBusy = errors.New("session is busy")

// releaseScript 只释放自己持有的锁，避免误删其他请求刚获取的锁。
var releaseScript = redis.NewScript(`
if redis.call("GET", KEYS[1]) == ARGV[1] then
	return redis.call("DEL", KEYS[1])
end
return 0
`)

// Lock 基于 Redis 的分布式锁，用于禁止同一会话并发生成。
type Lock struct {
	client *redis.Client
}

func NewLock(client *redis.Client) *Lock {
	return &Lock{client: client}
}

// Acquire 尝试获取锁，成功返回释放函数。
// 使用 SET NX EX 保证原子性：拿不到就立即返回 ErrLockBusy（单飞语义，不阻塞等待）。
func (r *Lock) Acquire(ctx context.Context, key string, ttl time.Duration) (release func(), err error) {
	token := randomToken()

	ok, err := r.client.SetNX(ctx, key, token, ttl).Result()
	if err != nil {
		return nil, fmt.Errorf("获取会话锁失败: %w", err)
	}
	if !ok {
		return nil, ErrLockBusy
	}

	release = func() {
		// 释放用独立 context：请求 ctx 此时可能已取消，
		// 若复用会导致锁无法释放、会话被永久锁死。
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		_ = releaseScript.Run(ctx, r.client, []string{key}, token).Err()
	}

	return release, nil
}

// randomToken 生成锁持有者标识。
func randomToken() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		// crypto/rand 失败极罕见，退化到时间戳保证仍能区分持有者。
		return fmt.Sprintf("%d", time.Now().UnixNano())
	}
	return hex.EncodeToString(b)
}
