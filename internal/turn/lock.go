package turn

import (
	"context"
	"errors"
	"time"

	"mentorly/internal/platform/store"
)

// redisLock 把 store.Lock 适配成编排层需要的 Lock 接口。
//
// 适配放在 turn 包而不是 store 包：store 不知道编排层的抽象，
// 由使用方承担适配职责，依赖方向才保持单向。
type redisLock struct {
	lock *store.Lock
}

// NewRedisLock 构造适配器。
func NewRedisLock(l *store.Lock) Lock {
	if l == nil {
		return nil
	}
	return &redisLock{lock: l}
}

// Acquire 获取锁，把 store 的哨兵错误翻译成编排层的 ErrLockBusy。
func (l *redisLock) Acquire(ctx context.Context, key string, ttl time.Duration) (func(), error) {
	release, err := l.lock.Acquire(ctx, key, ttl)
	if err != nil {
		if errors.Is(err, store.ErrLockBusy) {
			return nil, ErrLockBusy
		}
		return nil, err
	}
	return release, nil
}
