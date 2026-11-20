package artifacts

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"gorm.io/gorm"
)

// ErrNotFound 产物不存在或不属于该用户。
// 两种情况返回同一错误，避免通过状态码差异探测他人产物是否存在。
var ErrNotFound = errors.New("artifact not found")

// artifactRow 对应 artifacts 表。
//
// Meta 用 JSON 列存结构化补充信息，避免为「视频时长」「幻灯片页数」
// 这类展示性字段反复加列。这些字段不参与查询条件，因此不需要范式化。
type artifactRow struct {
	ID             string         `gorm:"column:id;type:varchar(36);primaryKey"`
	UserID         string         `gorm:"column:user_id;type:varchar(36);not null;index:idx_artifacts_user,priority:1"`
	ConversationID string         `gorm:"column:conversation_id;type:varchar(36);not null;index:idx_artifacts_conversation,priority:1"`
	Kind           string         `gorm:"column:kind;type:varchar(32);not null"`
	Title          string         `gorm:"column:title;type:varchar(200);not null"`
	Status         string         `gorm:"column:status;type:varchar(16);not null;index:idx_artifacts_user,priority:2"`
	Progress       int            `gorm:"column:progress;type:int;not null;default:0"`
	File           string         `gorm:"column:file;type:varchar(255);not null"`
	MIME           string         `gorm:"column:mime;type:varchar(128);not null"`
	Size           int64          `gorm:"column:size;type:bigint;not null;default:0"`
	Error          string         `gorm:"column:error;type:text;not null"`
	Meta           map[string]any `gorm:"column:meta;type:json;serializer:json"`
	CreatedAt      time.Time      `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_artifacts_user,priority:3"`
	UpdatedAt      time.Time      `gorm:"column:updated_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoUpdateTime"`
}

func (artifactRow) TableName() string { return "artifacts" }

func (r *artifactRow) toDomain() *Artifact {
	return &Artifact{
		ID:             r.ID,
		UserID:         r.UserID,
		ConversationID: r.ConversationID,
		Kind:           r.Kind,
		Title:          r.Title,
		Status:         r.Status,
		Progress:       r.Progress,
		File:           r.File,
		MIME:           r.MIME,
		Size:           r.Size,
		Error:          r.Error,
		Meta:           r.Meta,
		CreatedAt:      r.CreatedAt,
		UpdatedAt:      r.UpdatedAt,
	}
}

// Store 是产物的持久化与文件存储。
//
// 元数据在 MySQL，文件在本地目录：产物动辄几 MB，
// 放数据库会让备份与迁移变得笨重。
type Store struct {
	db  *gorm.DB
	dir string
}

// NewStore 创建存储。dir 为产物根目录，不存在时创建。
func NewStore(db *gorm.DB, dir string) (*Store, error) {
	abs, err := filepath.Abs(dir)
	if err != nil {
		return nil, fmt.Errorf("解析产物目录失败: %w", err)
	}
	if err := os.MkdirAll(abs, 0o755); err != nil {
		return nil, fmt.Errorf("创建产物目录失败: %w", err)
	}
	return &Store{db: db, dir: abs}, nil
}

// Schema 声明本包拥有的表，供启动期统一 AutoMigrate。
func (s *Store) Schema() []any { return []any{&artifactRow{}} }

// Create 落库一条产物记录，状态为 queued。
func (s *Store) Create(ctx context.Context, a *Artifact) error {
	if strings.TrimSpace(a.ID) == "" {
		return fmt.Errorf("产物 ID 不能为空")
	}
	now := time.Now()
	row := &artifactRow{
		ID:             a.ID,
		UserID:         a.UserID,
		ConversationID: a.ConversationID,
		Kind:           a.Kind,
		Title:          a.Title,
		Status:         a.Status,
		Progress:       a.Progress,
		File:           a.File,
		MIME:           a.MIME,
		Size:           a.Size,
		Error:          a.Error,
		Meta:           a.Meta,
		CreatedAt:      now,
		UpdatedAt:      now,
	}
	if err := s.db.WithContext(ctx).Create(row).Error; err != nil {
		return fmt.Errorf("保存产物记录失败: %w", err)
	}
	a.CreatedAt, a.UpdatedAt = now, now
	return nil
}

// Update 更新产物的可变字段。只允许更新状态、进度、文件与错误。
//
// Meta 必须手动序列化成 JSON 字符串：gorm 的 Updates(map) 走的是原生
// 参数绑定，不会应用 serializer:json，直接传 map 会报
// "unsupported type map[string]interface{}"。
func (s *Store) Update(ctx context.Context, a *Artifact) error {
	metaJSON, err := json.Marshal(a.Meta)
	if err != nil {
		return fmt.Errorf("序列化产物元信息失败: %w", err)
	}

	updates := map[string]any{
		"status":     a.Status,
		"progress":   a.Progress,
		"file":       a.File,
		"mime":       a.MIME,
		"size":       a.Size,
		"error":      a.Error,
		"meta":       string(metaJSON),
		"updated_at": time.Now(),
	}
	res := s.db.WithContext(ctx).Model(&artifactRow{}).Where("id = ?", a.ID).Updates(updates)
	if res.Error != nil {
		return fmt.Errorf("更新产物记录失败: %w", res.Error)
	}
	if res.RowsAffected == 0 {
		return ErrNotFound
	}
	return nil
}

// GetForUser 按 ID 取产物并校验归属。
// 这是唯一的读取入口：任何下载/查询都必须经过它，避免出现绕过归属校验的路径。
func (s *Store) GetForUser(ctx context.Context, id, userID string) (*Artifact, error) {
	var row artifactRow
	err := s.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).First(&row).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("查询产物失败: %w", err)
	}
	return row.toDomain(), nil
}

// List 列出某会话（conversationID 非空）或某用户的全部产物。
func (s *Store) List(ctx context.Context, userID, conversationID string, limit int) ([]Artifact, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}

	q := s.db.WithContext(ctx).Where("user_id = ?", userID)
	if strings.TrimSpace(conversationID) != "" {
		q = q.Where("conversation_id = ?", conversationID)
	}

	var rows []artifactRow
	if err := q.Order("created_at DESC").Limit(limit).Find(&rows).Error; err != nil {
		return nil, fmt.Errorf("查询产物列表失败: %w", err)
	}

	out := make([]Artifact, 0, len(rows))
	for i := range rows {
		out = append(out, *rows[i].toDomain())
	}
	return out, nil
}

// Path 返回产物文件的宿主机绝对路径。
// 只接受已通过 GetForUser 校验的记录，文件名由服务端生成。
func (s *Store) Path(a *Artifact) (string, error) {
	if a == nil || strings.TrimSpace(a.File) == "" {
		return "", fmt.Errorf("产物文件不存在")
	}
	// 双重保险：即使 File 被异常写入，也不允许逃出根目录。
	clean := filepath.Clean(a.File)
	if strings.Contains(clean, "..") || filepath.IsAbs(clean) {
		return "", fmt.Errorf("产物文件名非法: %s", a.File)
	}
	return filepath.Join(s.dir, clean), nil
}

// Dir 返回产物根目录，供生成器写入文件。
func (s *Store) Dir() string { return s.dir }

// Open 打开产物文件供下载。
func (s *Store) Open(a *Artifact) (*os.File, error) {
	p, err := s.Path(a)
	if err != nil {
		return nil, err
	}
	f, err := os.Open(p)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("产物文件已丢失: %w", err)
		}
		return nil, fmt.Errorf("打开产物文件失败: %w", err)
	}
	return f, nil
}

// SaveFile 把生成的临时文件移动到产物目录，并回填 Size 与 File。
// 使用重命名而不是复制：生成器写入的就是最终文件。
func (s *Store) SaveFile(a *Artifact, srcPath, name string) error {
	dst := filepath.Join(s.dir, name)
	if err := os.Rename(srcPath, dst); err != nil {
		// 跨设备时 rename 会失败，退回复制。
		if linkErr := copyFile(srcPath, dst); linkErr != nil {
			return fmt.Errorf("保存产物文件失败: %w", err)
		}
		_ = os.Remove(srcPath)
	}

	st, err := os.Stat(dst)
	if err != nil {
		return fmt.Errorf("读取产物文件信息失败: %w", err)
	}
	a.File = name
	a.Size = st.Size()
	return nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	if _, err := out.ReadFrom(in); err != nil {
		return err
	}
	return out.Sync()
}

// DeleteForUser 删除产物记录与文件。
func (s *Store) DeleteForUser(ctx context.Context, id, userID string) error {
	a, err := s.GetForUser(ctx, id, userID)
	if err != nil {
		return err
	}

	res := s.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).Delete(&artifactRow{})
	if res.Error != nil {
		return fmt.Errorf("删除产物记录失败: %w", res.Error)
	}

	// 文件删除失败不影响记录删除：残留文件可后续清理，
	// 但让用户看到「删不掉」是更糟的体验。
	if p, pathErr := s.Path(a); pathErr == nil {
		_ = os.Remove(p)
	}
	return nil
}
