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
var ErrInvalidUpload = errors.New("invalid attachment upload")

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
		cfg.MaxBytes = 5 << 20
	}
	if cfg.MaxExtractChars <= 0 {
		cfg.MaxExtractChars = 12000
	}
	cfg.Dir = abs

	return &Store{db: db, cfg: cfg}, nil
}

// Schema 声明本包拥有的表。
func Schema() []any { return []any{&attachmentRow{}} }

// Config 返回生效配置，供 Handler 做大小校验。
func (s *Store) Config() Config { return s.cfg }

// Save 保存上传的文件并提取文本。
//
// 参数 body 是已通过大小校验的读取器；filename 仅用于推断扩展名与展示，
// 落盘文件名由服务端生成，绝不复用用户输入。
func (s *Store) Save(ctx context.Context, userID, conversationID, filename string, body io.Reader) (*Attachment, error) {
	ext := strings.ToLower(filepath.Ext(filename))
	if !Supported(ext) {
		return nil, fmt.Errorf("%w: 不支持的文件类型 %q，支持: %s", ErrInvalidUpload, ext, strings.Join(SupportedExts(), ", "))
	}

	if strings.TrimSpace(conversationID) == "" {
		return nil, fmt.Errorf("%w: 缺少会话 ID，附件必须归属某个会话", ErrInvalidUpload)
	}

	id := uuid.NewString()
	// 按「用户/会话」分目录，直接落在会话工作区内，Agent 可通过 /workspace/ 引用。
	// 文件名用 id，杜绝路径注入；两段目录名都来自已认证上下文，不接受用户输入。
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
		return nil, fmt.Errorf("%w: 附件超过大小上限 %d MB", ErrInvalidUpload, s.cfg.MaxBytes>>20)
	}
	if written == 0 {
		_ = os.Remove(full)
		return nil, fmt.Errorf("%w: 附件内容为空", ErrInvalidUpload)
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

	// 所有允许上传的附件都提取文本。
	// shortcut: 上传期限制 5MB/12000 字确保一次性直读；后续需支持长教材时再引入分块检索。
	text, extractErr := extract(ctx, ext, data)
	if extractErr != nil {
		// 提取失败要记录原因并如实告知，不能静默当成空附件。
		a.ExtractError = extractErr.Error()
	}
	if runes := []rune(text); len(runes) > s.cfg.MaxExtractChars {
		_ = os.Remove(full)
		return nil, fmt.Errorf("%w: 文档正文共 %d 字，超过上限 %d 字，请拆分或精简后再上传", ErrInvalidUpload, len(runes), s.cfg.MaxExtractChars)
	}
	a.Text = text

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

// GetMany 校验用户与会话归属，按请求顺序返回去重后的附件。
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

// FindMany 按 ID 批量查找附件，按入参顺序返回，跳过不存在的。
//
// 与 GetMany 的区别在容错策略：
//   - GetMany 用于「本轮消息引用了这些附件」——缺失意味着请求非法，必须报错；
//   - FindMany 用于「历史消息里记录过这些附件」——附件记录可能因清理而不在，
//     此时应继续展示其余附件，而不是让整个历史列表查询失败。
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

	var rows []attachmentRow
	if err := s.db.WithContext(ctx).Where("id IN ? AND user_id = ? AND conversation_id = ?", wanted, userID, conversationID).Find(&rows).Error; err != nil {
		return nil, fmt.Errorf("查询附件失败: %w", err)
	}

	byID := make(map[string]*Attachment, len(rows))
	for i := range rows {
		a := rows[i].toDomain()
		byID[a.ID] = a
	}

	out := make([]*Attachment, 0, len(wanted))
	for _, id := range wanted {
		if a, ok := byID[id]; ok {
			out = append(out, a)
		}
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

// attachmentRelDir 生成附件相对存储根的目录：{user_id}/{conversation_id}。
//
// 两段目录名都来自已认证上下文，但这里仍逐段校验：
// 一旦上游把用户输入透传进来，多一层防线就能挡住 ../ 逃逸。
func attachmentRelDir(userID, conversationID string) (string, error) {
	for _, seg := range []struct{ name, value string }{
		{"用户 ID", userID},
		{"会话 ID", conversationID},
	} {
		v := strings.TrimSpace(seg.value)
		if v == "" || v == "." || v == ".." || filepath.Base(v) != v ||
			strings.ContainsAny(v, `/\`) {
			return "", fmt.Errorf("非法的%s: %q", seg.name, seg.value)
		}
	}
	return filepath.Join(userID, conversationID), nil
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

// ReadBytes 读取附件原件。
func ReadBytes(s *Store, a *Attachment) ([]byte, error) {
	p, err := s.Path(a)
	if err != nil {
		return nil, err
	}
	return os.ReadFile(p)
}

// FullText 从原始文件重新提取完整文本，不做 MaxExtractChars 截断。
//
// 入库时保存的 Text 是按 MaxExtractChars 截断后的副本，只够内联进消息。
// 模型要看完整内容时必须回到原始文件重新解析：否则 read_attachment 只会
// 重复返回同一份截断文本，而消息里却写着「完整内容请用 read_attachment 读取」，
// 等于让模型去调用一个必然拿不到完整内容的工具。
func (s *Store) FullText(ctx context.Context, a *Attachment) (string, error) {
	if a == nil {
		return "", fmt.Errorf("附件不存在")
	}

	data, err := ReadBytes(s, a)
	if err != nil {
		return "", fmt.Errorf("读取附件原始文件失败: %w", err)
	}
	text, err := extract(ctx, a.Ext, data)
	if err != nil {
		return "", err
	}
	return text, nil
}

// Status 检查原件可用性，保留元数据以便历史追溯。
func (s *Store) Status(a *Attachment) string {
	if !Supported(a.Ext) {
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
