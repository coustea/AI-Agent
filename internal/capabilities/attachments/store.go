package attachments

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// ErrNotFound 附件不存在或不属于该用户。
// 两种情况返回同一错误，避免通过状态码差异探测他人附件。
var ErrNotFound = errors.New("attachment not found")

// attachmentRow 对应 attachments 表。
type attachmentRow struct {
	ID             string    `gorm:"column:id;type:varchar(36);primaryKey"`
	UserID         string    `gorm:"column:user_id;type:varchar(36);not null;index:idx_attachments_user,priority:1"`
	ConversationID string    `gorm:"column:conversation_id;type:varchar(36);not null;index:idx_attachments_conversation,priority:1"`
	Filename       string    `gorm:"column:filename;type:varchar(255);not null"`
	Ext            string    `gorm:"column:ext;type:varchar(16);not null"`
	Kind           string    `gorm:"column:kind;type:varchar(16);not null"`
	MIME           string    `gorm:"column:mime;type:varchar(128);not null"`
	Size           int64     `gorm:"column:size;type:bigint;not null;default:0"`
	Stored         string    `gorm:"column:stored;type:varchar(255);not null"`
	Text           string    `gorm:"column:text;type:mediumtext;not null"`
	ExtractError   string    `gorm:"column:extract_error;type:text;not null"`
	Truncated      bool      `gorm:"column:truncated;type:tinyint(1);not null;default:0"`
	CreatedAt      time.Time `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_attachments_user,priority:2"`
}

func (attachmentRow) TableName() string { return "attachments" }

func (r *attachmentRow) toDomain() *Attachment {
	return &Attachment{
		ID:             r.ID,
		UserID:         r.UserID,
		ConversationID: r.ConversationID,
		Filename:       r.Filename,
		Ext:            r.Ext,
		Kind:           r.Kind,
		MIME:           r.MIME,
		Size:           r.Size,
		Stored:         r.Stored,
		Text:           r.Text,
		ExtractError:   r.ExtractError,
		Truncated:      r.Truncated,
		CreatedAt:      r.CreatedAt,
	}
}

// Config 是附件能力配置。
type Config struct {
	// Dir 存储根目录
	Dir string
	// MaxBytes 单文件大小上限
	MaxBytes int64
	// MaxExtractChars 单文件提取文本上限
	MaxExtractChars int
}

// Store 是附件的持久化与文件存储。
type Store struct {
	db  *gorm.DB
	cfg Config
}

// NewStore 构造存储。
func NewStore(db *gorm.DB, cfg Config) (*Store, error) {
	abs, err := filepath.Abs(cfg.Dir)
	if err != nil {
		return nil, fmt.Errorf("解析附件目录失败: %w", err)
	}
	if err := os.MkdirAll(abs, 0o755); err != nil {
		return nil, fmt.Errorf("创建附件目录失败: %w", err)
	}

	if cfg.MaxBytes <= 0 {
		cfg.MaxBytes = 32 << 20
	}
	if cfg.MaxExtractChars <= 0 {
		cfg.MaxExtractChars = 20000
	}
	cfg.Dir = abs

	return &Store{db: db, cfg: cfg}, nil
}

// Schema 声明本包拥有的表。
func (s *Store) Schema() []any { return []any{&attachmentRow{}} }

// Config 返回生效配置，供 Handler 做大小校验。
func (s *Store) Config() Config { return s.cfg }

// Save 保存上传的文件并提取文本。
//
// 参数 body 是已通过大小校验的读取器；filename 仅用于推断扩展名与展示，
// 落盘文件名由服务端生成，绝不复用用户输入。
func (s *Store) Save(ctx context.Context, userID, conversationID, filename string, body io.Reader) (*Attachment, error) {
	ext := strings.ToLower(filepath.Ext(filename))
	if !Supported(ext) {
		return nil, fmt.Errorf("不支持的文件类型 %q，支持: %s", ext, strings.Join(SupportedExts(), ", "))
	}

	id := uuid.NewString()
	// 按用户分目录，便于整用户清理；文件名用 id，杜绝路径注入。
	relDir := userID
	dir := filepath.Join(s.cfg.Dir, relDir)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("创建用户附件目录失败: %w", err)
	}

	stored := id + ext
	full := filepath.Join(dir, stored)

	f, err := os.Create(full)
	if err != nil {
		return nil, fmt.Errorf("创建附件文件失败: %w", err)
	}

	// 多读 1 字节用于判断是否超限，避免把超大文件整个写入磁盘。
	written, copyErr := io.Copy(f, io.LimitReader(body, s.cfg.MaxBytes+1))
	closeErr := f.Close()

	if copyErr != nil {
		_ = os.Remove(full)
		return nil, fmt.Errorf("写入附件失败: %w", copyErr)
	}
	if closeErr != nil {
		_ = os.Remove(full)
		return nil, fmt.Errorf("保存附件失败: %w", closeErr)
	}
	if written > s.cfg.MaxBytes {
		_ = os.Remove(full)
		return nil, fmt.Errorf("附件超过大小上限 %d MB", s.cfg.MaxBytes>>20)
	}
	if written == 0 {
		_ = os.Remove(full)
		return nil, fmt.Errorf("附件内容为空")
	}

	// 重新读取文件内容用于文本提取（避免把整个文件留在内存）。
	data, err := os.ReadFile(full)
	if err != nil {
		_ = os.Remove(full)
		return nil, fmt.Errorf("读取附件失败: %w", err)
	}

	a := &Attachment{
		ID:             id,
		UserID:         userID,
		ConversationID: conversationID,
		Filename:       sanitizeFilename(filename),
		Ext:            ext,
		Kind:           kindOf(ext),
		MIME:           mimeOf(ext),
		Size:           written,
		Stored:         filepath.Join(relDir, stored),
	}

	// 图片走多模态直传，不需要文本；其余类型提取文本。
	if !a.NativeImage() {
		text, extractErr := extract(ext, data)
		if extractErr != nil {
			// 提取失败要记录原因并如实告知，不能静默当成空附件。
			a.ExtractError = extractErr.Error()
		}
		if runes := []rune(text); len(runes) > s.cfg.MaxExtractChars {
			a.Text = string(runes[:s.cfg.MaxExtractChars])
			a.Truncated = true
		} else {
			a.Text = text
		}
	}

	row := &attachmentRow{
		ID:             a.ID,
		UserID:         a.UserID,
		ConversationID: a.ConversationID,
		Filename:       a.Filename,
		Ext:            a.Ext,
		Kind:           a.Kind,
		MIME:           a.MIME,
		Size:           a.Size,
		Stored:         a.Stored,
		Text:           a.Text,
		ExtractError:   a.ExtractError,
		Truncated:      a.Truncated,
		CreatedAt:      time.Now(),
	}
	if err := s.db.WithContext(ctx).Create(row).Error; err != nil {
		_ = os.Remove(full)
		return nil, fmt.Errorf("保存附件记录失败: %w", err)
	}

	return a, nil
}

// GetForUser 按 ID 取附件并校验归属。
// 这是唯一的读取入口，任何访问都必须经过它。
func (s *Store) GetForUser(ctx context.Context, id, userID string) (*Attachment, error) {
	var row attachmentRow
	err := s.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).First(&row).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("查询附件失败: %w", err)
	}
	return row.toDomain(), nil
}

// ListForConversation 列出某会话的附件。
func (s *Store) ListForConversation(ctx context.Context, userID, conversationID string) ([]Attachment, error) {
	var rows []attachmentRow
	err := s.db.WithContext(ctx).
		Where("user_id = ? AND conversation_id = ?", userID, conversationID).
		Order("created_at ASC").
		Find(&rows).Error
	if err != nil {
		return nil, fmt.Errorf("查询会话附件失败: %w", err)
	}

	out := make([]Attachment, 0, len(rows))
	for i := range rows {
		out = append(out, *rows[i].toDomain())
	}
	return out, nil
}

// Path 返回附件文件的宿主机路径。
func (s *Store) Path(a *Attachment) (string, error) {
	if a == nil || strings.TrimSpace(a.Stored) == "" {
		return "", fmt.Errorf("附件文件不存在")
	}
	clean := filepath.Clean(a.Stored)
	if strings.Contains(clean, "..") || filepath.IsAbs(clean) {
		return "", fmt.Errorf("附件路径非法")
	}
	return filepath.Join(s.cfg.Dir, clean), nil
}

// Open 打开附件文件供下载或读取。
func (s *Store) Open(a *Attachment) (*os.File, error) {
	p, err := s.Path(a)
	if err != nil {
		return nil, err
	}
	f, err := os.Open(p)
	if err != nil {
		return nil, fmt.Errorf("打开附件失败: %w", err)
	}
	return f, nil
}

// extract 按类型提取文本。
func extract(ext string, data []byte) (string, error) {
	switch kindOf(ext) {
	case KindPDF:
		return extractPDF(data)
	case KindDocx:
		return extractDocx(data)
	case KindPPTX:
		return extractPPTX(data)
	case KindText:
		return string(data), nil
	case KindImage:
		return "", nil
	default:
		return "", fmt.Errorf("暂不支持解析 %s 文件", ext)
	}
}

// sanitizeFilename 清理用户提供的文件名，只保留可展示的部分。
func sanitizeFilename(name string) string {
	name = filepath.Base(strings.TrimSpace(name))
	name = strings.ReplaceAll(name, "\x00", "")
	if name == "" || name == "." || name == ".." {
		return "attachment"
	}
	if runes := []rune(name); len(runes) > 120 {
		return string(runes[:120])
	}
	return name
}
