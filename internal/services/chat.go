package services

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"

	"mentorly/internal/dao"
	"mentorly/internal/dto"
	"mentorly/internal/harness"
	"mentorly/internal/model"
)

// 业务层错误，供 handler 映射状态码。
var (
	// ErrSessionNotFound 会话不存在或无权访问
	ErrSessionNotFound = errors.New("会话不存在")
	// ErrMemoryTooLong 手动编辑的记忆超出上限
	ErrMemoryTooLong = errors.New("记忆内容超出长度上限")
)

// ChatService 负责会话 CRUD、历史分页、记忆管理与调用 Harness。
type ChatService struct {
	chat     *dao.ChatRepo
	mem      *dao.MemoryRepo
	harness  *harness.TutorHarness
	maxChars int
}

// NewChatService 构造服务。
func NewChatService(chat *dao.ChatRepo, mem *dao.MemoryRepo, h *harness.TutorHarness, memoryMaxChars int) *ChatService {
	if memoryMaxChars <= 0 {
		memoryMaxChars = 2000
	}
	return &ChatService{
		chat:     chat,
		mem:      mem,
		harness:  h,
		maxChars: memoryMaxChars,
	}
}

// Available 表示对话能力是否可用（未配置模型时 handler 返回 503）。
func (s *ChatService) Available() bool {
	return s.harness != nil && s.harness.Enabled()
}

// CreateSession 创建会话。
func (s *ChatService) CreateSession(ctx context.Context, userID string, req *dto.CreateSessionReq) (*dto.SessionResp, error) {
	title := strings.TrimSpace(req.Title)
	if title == "" {
		title = "新会话"
	}

	sess := &model.ChatSession{
		ID:     uuid.NewString(),
		UserID: userID,
		Title:  title,
	}

	if err := s.chat.CreateSession(ctx, sess); err != nil {
		return nil, fmt.Errorf("创建会话失败: %w", err)
	}

	resp := toSessionResp(sess)
	return &resp, nil
}

// ListSessions 列出会话。
func (s *ChatService) ListSessions(ctx context.Context, userID string, limit int) ([]dto.SessionResp, error) {
	rows, err := s.chat.ListSessions(ctx, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("查询会话列表失败: %w", err)
	}

	out := make([]dto.SessionResp, 0, len(rows))
	for i := range rows {
		out = append(out, toSessionResp(&rows[i]))
	}
	return out, nil
}

// RenameSession 重命名。
func (s *ChatService) RenameSession(ctx context.Context, userID, sessionID string, req *dto.RenameSessionReq) error {
	err := s.chat.RenameSession(ctx, sessionID, userID, strings.TrimSpace(req.Title))
	if err != nil {
		if errors.Is(err, dao.ErrRecordNotFound) {
			return ErrSessionNotFound
		}
		return fmt.Errorf("重命名会话失败: %w", err)
	}
	return nil
}

// DeleteSession 软删除。
func (s *ChatService) DeleteSession(ctx context.Context, userID, sessionID string) error {
	err := s.chat.DeleteSession(ctx, sessionID, userID)
	if err != nil {
		if errors.Is(err, dao.ErrRecordNotFound) {
			return ErrSessionNotFound
		}
		return fmt.Errorf("删除会话失败: %w", err)
	}
	return nil
}

// ListMessages 游标分页查询历史。
func (s *ChatService) ListMessages(ctx context.Context, userID, sessionID string, beforeID uint64, limit int) ([]dto.MessageResp, error) {
	// 先校验归属，避免越权读取他人消息。
	if _, err := s.chat.GetSessionForUser(ctx, sessionID, userID); err != nil {
		if errors.Is(err, dao.ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	rows, err := s.chat.ListMessagesBefore(ctx, sessionID, beforeID, limit)
	if err != nil {
		return nil, fmt.Errorf("查询消息失败: %w", err)
	}

	out := make([]dto.MessageResp, 0, len(rows))
	for i := range rows {
		out = append(out, toMessageResp(&rows[i]))
	}
	return out, nil
}

// PrepareTurn 调用 Harness 完成阶段 1。
func (s *ChatService) PrepareTurn(ctx context.Context, userID, sessionID, question string) (*harness.PreparedTurn, error) {
	if !s.Available() {
		return nil, ErrChatUnavailable
	}

	turn, err := s.harness.PrepareTurn(ctx, userID, sessionID, question)
	if err != nil {
		if errors.Is(err, harness.ErrSessionNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, err
	}
	return turn, nil
}

// ErrChatUnavailable 对话能力不可用。
var ErrChatUnavailable = errors.New("对话能力未启用")

// GetMemory 读取长期记忆。
func (s *ChatService) GetMemory(ctx context.Context, userID string) (*dto.MemoryResp, error) {
	doc, err := s.mem.Get(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("读取记忆失败: %w", err)
	}
	return &dto.MemoryResp{
		Content:   doc.Content,
		Version:   doc.Version,
		UpdatedAt: doc.UpdatedAt,
	}, nil
}

// UpdateMemory 手动编辑记忆。
// 上限为 memory_max_chars 的 2 倍：手动编辑允许比自动提取稍长，
// 但仍需有边界，避免把整份文档塞进 prompt。
func (s *ChatService) UpdateMemory(ctx context.Context, userID, content string) error {
	if n := len([]rune(content)); n > s.maxChars*2 {
		return fmt.Errorf("%w: 最多 %d 字符，当前 %d", ErrMemoryTooLong, s.maxChars*2, n)
	}

	if err := s.mem.Upsert(ctx, userID, content); err != nil {
		return fmt.Errorf("保存记忆失败: %w", err)
	}
	return nil
}

// ClearMemory 清空记忆。
func (s *ChatService) ClearMemory(ctx context.Context, userID string) error {
	if err := s.mem.Delete(ctx, userID); err != nil {
		return fmt.Errorf("清空记忆失败: %w", err)
	}
	return nil
}

// Harness 暴露底层 Harness，供 handler 在 SSE 流中直接调用 RunTurn。
func (s *ChatService) Harness() *harness.TutorHarness { return s.harness }

// toSessionResp 转成响应结构。
func toSessionResp(s *model.ChatSession) dto.SessionResp {
	return dto.SessionResp{
		ID:           s.ID,
		Title:        s.Title,
		LastActiveAt: s.LastActiveAt,
		CreatedAt:    s.CreatedAt,
	}
}

// toMessageResp 转成响应结构，并把 meta.usage 展开成扁平字段。
func toMessageResp(m *model.ChatMessage) dto.MessageResp {
	resp := dto.MessageResp{
		ID:        m.ID,
		Role:      m.Role,
		Content:   m.Content,
		Status:    m.Status,
		Tokens:    m.Tokens,
		CreatedAt: m.CreatedAt,
	}

	if m.Meta.Usage != nil || m.Meta.ElapsedMS > 0 {
		meta := &dto.MessageMetaDTO{ElapsedMS: m.Meta.ElapsedMS}
		if m.Meta.Usage != nil {
			meta.PromptTokens = m.Meta.Usage.PromptTokens
			meta.CompletionTokens = m.Meta.Usage.CompletionTokens
			meta.TotalTokens = m.Meta.Usage.TotalTokens
		}
		resp.Meta = meta
	}

	return resp
}
