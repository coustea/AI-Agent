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

	"mentorly/internal/utils"
)

const (
	KindDoc     = "doc"
	KindPDF     = "pdf"
	KindDocx    = "docx"
	KindText    = "text"
	KindUnknown = "unknown"
)

var (
	ErrNotFound      = errors.New("attachment not found")
	ErrInvalidUpload = errors.New("invalid attachment upload")
)

// Attachment 对应 attachments 表。
type Attachment struct {
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
	CreatedAt      time.Time `gorm:"column:created_at;type:datetime(3);not null;default:CURRENT_TIMESTAMP(3);autoCreateTime;index:idx_attachments_user,priority:2"`
}

func (Attachment) TableName() string { return "attachments" }

func kindOf(ext string) string {
	switch strings.ToLower(ext) {
	case ".doc":
		return KindDoc
	case ".docx":
		return KindDocx
	case ".pdf":
		return KindPDF
	case ".md":
		return KindText
	default:
		return KindUnknown
	}
}

func mimeOf(ext string) string {
	switch strings.ToLower(ext) {
	case ".doc":
		return "application/msword"
	case ".docx":
		return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
	case ".pdf":
		return "application/pdf"
	case ".md":
		return "text/markdown; charset=utf-8"
	default:
		return "application/octet-stream"
	}
}

func Supported(ext string) bool { return kindOf(ext) != KindUnknown }
func SupportedExts() []string   { return []string{".doc", ".docx", ".pdf", ".md"} }

type Config struct {
	Dir             string
	MaxBytes        int64
	MaxExtractChars int
}

type Store struct {
	db  *gorm.DB
	cfg Config
}

func NewStore(db *gorm.DB, cfg Config) (*Store, error) {
	abs, err := filepath.Abs(cfg.Dir)
	if err != nil {
		return nil, fmt.Errorf("解析附件目录失败: %w", err)
	}
	if err := os.MkdirAll(abs, 0o755); err != nil {
		return nil, fmt.Errorf("创建附件目录失败: %w", err)
	}
	if cfg.MaxBytes <= 0 {
		cfg.MaxBytes = 5 << 20
	}
	if cfg.MaxExtractChars <= 0 {
		cfg.MaxExtractChars = 12000
	}
	cfg.Dir = abs
	return &Store{db: db, cfg: cfg}, nil
}

func Schema() []any { return []any{&Attachment{}} }

func (s *Store) Config() Config { return s.cfg }

// Save 保存上传的文件并提取完整文本。
func (s *Store) Save(ctx context.Context, userID, conversationID, filename string, body io.Reader) (*Attachment, error) {
	ext := strings.ToLower(filepath.Ext(filename))
	if !Supported(ext) {
		return nil, fmt.Errorf("%w: 不支持的文件类型 %q，支持: %s", ErrInvalidUpload, ext, strings.Join(SupportedExts(), ", "))
	}
	if strings.TrimSpace(conversationID) == "" {
		return nil, fmt.Errorf("%w: 缺少会话 ID，附件必须归属某个会话", ErrInvalidUpload)
	}

	id := uuid.NewString()
	relDir, err := attachmentRelDir(userID, conversationID)
	if err != nil {
		return nil, err
	}
	dir := filepath.Join(s.cfg.Dir, relDir)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("创建会话附件目录失败: %w", err)
	}

	stored := id + ext
	full := filepath.Join(dir, stored)
	f, err := os.Create(full)
	if err != nil {
		return nil, fmt.Errorf("创建附件文件失败: %w", err)
	}

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
		return nil, fmt.Errorf("%w: 附件超过大小上限 %d MB", ErrInvalidUpload, s.cfg.MaxBytes>>20)
	}
	if written == 0 {
		_ = os.Remove(full)
		return nil, fmt.Errorf("%w: 附件内容为空", ErrInvalidUpload)
	}

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
		CreatedAt:      time.Now(),
	}

	// shortcut: 上传期限制 5MB/12000 字确保一次性直读；后续需支持长教材时再引入分块检索。
	text, extractErr := extract(ctx, ext, data)
	if extractErr != nil {
		a.ExtractError = extractErr.Error()
	}
	if runes := []rune(text); len(runes) > s.cfg.MaxExtractChars {
		_ = os.Remove(full)
		return nil, fmt.Errorf("%w: 文档正文共 %d 字，超过上限 %d 字，请拆分或精简后再上传", ErrInvalidUpload, len(runes), s.cfg.MaxExtractChars)
	}
	a.Text = text

	if err := s.db.WithContext(ctx).Create(a).Error; err != nil {
		_ = os.Remove(full)
		return nil, fmt.Errorf("保存附件记录失败: %w", err)
	}
	return a, nil
}

func (s *Store) GetForUser(ctx context.Context, id, userID string) (*Attachment, error) {
	var a Attachment
	err := s.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).First(&a).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("查询附件失败: %w", err)
	}
	return &a, nil
}

func (s *Store) GetMany(ctx context.Context, userID, conversationID string, ids []string) ([]*Attachment, error) {
	rows, err := s.FindMany(ctx, userID, conversationID, ids)
	if err != nil {
		return nil, err
	}
	found := make(map[string]bool, len(rows))
	for _, a := range rows {
		if !Supported(a.Ext) {
			return nil, fmt.Errorf("%w: 仅支持 doc、docx、pdf、md 附件", ErrInvalidUpload)
		}
		found[a.ID] = true
	}
	for _, id := range ids {
		if id = strings.TrimSpace(id); id != "" && !found[id] {
			return nil, ErrNotFound
		}
	}
	return rows, nil
}

func (s *Store) FindMany(ctx context.Context, userID, conversationID string, ids []string) ([]*Attachment, error) {
	wanted := make([]string, 0, len(ids))
	seen := make(map[string]struct{}, len(ids))
	for _, id := range ids {
		id = strings.TrimSpace(id)
		if id == "" {
			continue
		}
		if _, dup := seen[id]; dup {
			continue
		}
		seen[id] = struct{}{}
		wanted = append(wanted, id)
	}
	if len(wanted) == 0 {
		return nil, nil
	}

	var rows []Attachment
	if err := s.db.WithContext(ctx).Where("id IN ? AND user_id = ? AND conversation_id = ?", wanted, userID, conversationID).Find(&rows).Error; err != nil {
		return nil, fmt.Errorf("查询附件失败: %w", err)
	}

	byID := make(map[string]*Attachment, len(rows))
	for i := range rows {
		byID[rows[i].ID] = &rows[i]
	}

	out := make([]*Attachment, 0, len(wanted))
	for _, id := range wanted {
		if a, ok := byID[id]; ok {
			out = append(out, a)
		}
	}
	return out, nil
}

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

func attachmentRelDir(userID, conversationID string) (string, error) {
	for _, seg := range []struct{ name, value string }{
		{"用户 ID", userID},
		{"会话 ID", conversationID},
	} {
		v := strings.TrimSpace(seg.value)
		if v == "" || v == "." || v == ".." || filepath.Base(v) != v || strings.ContainsAny(v, `/\`) {
			return "", fmt.Errorf("非法的%s: %q", seg.name, seg.value)
		}
	}
	return filepath.Join(userID, conversationID), nil
}

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

func sanitizeFilename(name string) string {
	name = filepath.Base(strings.TrimSpace(name))
	name = strings.ReplaceAll(name, "\x00", "")
	if name == "" || name == "." || name == ".." {
		return "attachment"
	}
	return utils.ClipRunes(name, 120)
}

func (s *Store) Status(a *Attachment) string {
	if a == nil || !Supported(a.Ext) {
		return "unsupported"
	}
	p, err := s.Path(a)
	if err != nil {
		return "read_failed"
	}
	info, err := os.Stat(p)
	if errors.Is(err, os.ErrNotExist) {
		return "original_missing"
	}
	if err != nil || !info.Mode().IsRegular() {
		return "read_failed"
	}
	if a.ExtractError != "" {
		return "extraction_failed"
	}
	return "available"
}
