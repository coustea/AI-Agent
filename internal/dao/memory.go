package dao

import (
	"context"
	"errors"
	"time"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	"mentorly/internal/model"
)

// MemoryRepo 长期记忆仓储，一个用户一行。
type MemoryRepo struct {
	db *gorm.DB
}

func NewMemoryRepo(db *gorm.DB) *MemoryRepo {
	return &MemoryRepo{db: db}
}

// Get 读取用户记忆，不存在时返回空内容而非错误。
func (r *MemoryRepo) Get(ctx context.Context, userID string) (*model.UserMemory, error) {
	var m model.UserMemory
	err := r.db.WithContext(ctx).First(&m, "user_id = ?", userID).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return &model.UserMemory{UserID: userID, Content: "", Version: 0}, nil
		}
		return nil, err
	}
	return &m, nil
}

// SaveWithVersion 乐观锁写入：仅当库中 version 等于 baseVersion 时更新。
// 返回 false 表示版本已变（并发写冲突），调用方应基于最新版本重试。
func (r *MemoryRepo) SaveWithVersion(ctx context.Context, userID, content string, baseVersion int) (bool, error) {
	if baseVersion == 0 {
		// 首次写入：用 INSERT ... ON DUPLICATE KEY UPDATE 保证并发下不报唯一键冲突。
		m := &model.UserMemory{
			UserID:    userID,
			Content:   content,
			Version:   1,
			UpdatedAt: time.Now(),
		}
		res := r.db.WithContext(ctx).Clauses(onDuplicateKeyUpdate()).Create(m)
		if res.Error != nil {
			return false, res.Error
		}
		return true, nil
	}

	res := r.db.WithContext(ctx).Model(&model.UserMemory{}).
		Where("user_id = ? AND version = ?", userID, baseVersion).
		Updates(map[string]any{
			"content":    content,
			"version":    baseVersion + 1,
			"updated_at": time.Now(),
		})
	if res.Error != nil {
		return false, res.Error
	}
	return res.RowsAffected > 0, nil
}

// Upsert 直接覆盖写入，用于用户手动编辑与清空（不需要乐观锁语义）。
func (r *MemoryRepo) Upsert(ctx context.Context, userID, content string) error {
	m := &model.UserMemory{
		UserID:    userID,
		Content:   content,
		Version:   1,
		UpdatedAt: time.Now(),
	}
	return r.db.WithContext(ctx).Clauses(onDuplicateKeyUpdate()).Create(m).Error
}

// Delete 清空记忆。
func (r *MemoryRepo) Delete(ctx context.Context, userID string) error {
	return r.db.WithContext(ctx).Where("user_id = ?", userID).Delete(&model.UserMemory{}).Error
}

// onDuplicateKeyUpdate 返回 MySQL 的 ON DUPLICATE KEY UPDATE 子句，
// 让「首次插入」与「并发覆盖」合并成一条语句，避免先查后写在并发下报唯一键冲突。
func onDuplicateKeyUpdate() clause.OnConflict {
	return clause.OnConflict{
		Columns: []clause.Column{{Name: "user_id"}},
		DoUpdates: clause.Assignments(map[string]any{
			"content":    gorm.Expr("VALUES(content)"),
			"version":    gorm.Expr("version + 1"),
			"updated_at": time.Now(),
		}),
	}
}
