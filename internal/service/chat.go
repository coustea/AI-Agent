package service

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"

	"mentorly/internal/agent"
	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
	"mentorly/internal/utils"
	logutil "mentorly/internal/utils/log"
)

var (
	ErrConversationBusy     = errors.New("会话正在运行，请等待本轮结束")
	ErrEmptyQuestion        = errors.New("问题内容不能为空")
	ErrConversationNotFound = conversations.ErrConversationNotFound
)

type Conversation = conversations.Conversation
type Event = agent.Event

// Chat 负责业务校验、会话互斥、消息持久化和自动标题。
type Chat struct {
	store             *conversations.Store
	attachments       *attachments.Store
	maxAttachmentsMsg int
	log               *zap.Logger
	mu                sync.Mutex
	active            map[string]struct{}
}

func NewChat(store *conversations.Store, attachments *attachments.Store, maxAttachmentsPerMsg int, log *zap.Logger) *Chat {
	if log == nil {
		log = zap.NewNop()
	}
	if maxAttachmentsPerMsg <= 0 {
		maxAttachmentsPerMsg = 3
	}
	return &Chat{store: store, attachments: attachments, maxAttachmentsMsg: maxAttachmentsPerMsg, log: log, active: make(map[string]struct{})}
}

func (s *Chat) CreateConversation(ctx context.Context, userID, title string) (*conversations.Conversation, error) {
	return s.store.CreateConversation(ctx, userID, title)
}

func (s *Chat) ListConversations(ctx context.Context, userID string, limit int) ([]conversations.Conversation, error) {
	return s.store.ListConversations(ctx, userID, limit)
}

func (s *Chat) RenameConversation(ctx context.Context, id, userID, title string) error {
	return s.store.RenameConversation(ctx, id, userID, title)
}

func (s *Chat) DeleteConversation(ctx context.Context, id, userID string) error {
	key := userID + ":" + id
	if !s.acquire(key) {
		return ErrConversationBusy
	}
	defer s.release(key)
	return s.store.DeleteConversation(ctx, id, userID)
}

// MessageView 是一条消息及其按上传顺序排列的附件。
type MessageView struct {
	conversations.Message
	Attachments []*attachments.Attachment
}

func (s *Chat) ListMessages(ctx context.Context, id, userID string, limit int) ([]MessageView, error) {
	if _, err := s.store.GetConversation(ctx, id, userID); err != nil {
		return nil, err
	}
	msgs, err := s.store.ListVisibleMessages(ctx, id, limit)
	if err != nil {
		return nil, err
	}

	allIDs := make([]string, 0, len(msgs))
	seen := make(map[string]struct{}, len(msgs))
	for i := range msgs {
		for _, aid := range msgs[i].AttachmentIDs {
			if _, dup := seen[aid]; !dup {
				seen[aid] = struct{}{}
				allIDs = append(allIDs, aid)
			}
		}
	}

	byID := make(map[string]*attachments.Attachment, len(allIDs))
	if len(allIDs) > 0 {
		rows, err := s.attachments.FindMany(ctx, userID, id, allIDs)
		if err != nil {
			s.log.Warn("加载消息附件失败", zap.Error(err), zap.String("conversation_id", id))
		}
		for _, a := range rows {
			byID[a.ID] = a
		}
	}

	out := make([]MessageView, 0, len(msgs))
	for i := range msgs {
		out = append(out, MessageView{Message: msgs[i], Attachments: orderedAttachments(msgs[i].AttachmentIDs, byID)})
	}
	return out, nil
}

func attachmentIDsOf(items []*attachments.Attachment) []string {
	if len(items) == 0 {
		return nil
	}
	out := make([]string, 0, len(items))
	for _, a := range items {
		if a != nil && strings.TrimSpace(a.ID) != "" {
			out = append(out, a.ID)
		}
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func orderedAttachments(ids []string, byID map[string]*attachments.Attachment) []*attachments.Attachment {
	if len(ids) == 0 {
		return nil
	}
	out := make([]*attachments.Attachment, 0, len(ids))
	for _, id := range ids {
		if a, ok := byID[id]; ok {
			out = append(out, a)
		}
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

type PreparedRun struct {
	Attachments    []*attachments.Attachment
	ConversationID string
	Question       string
	UserMessageID  uint64
	service        *Chat
	key            string
	once           sync.Once
}

func (p *PreparedRun) Close() {
	if p != nil {
		p.once.Do(func() { p.service.release(p.key) })
	}
}

func (s *Chat) Prepare(ctx context.Context, userID, conversationID, question string, attachmentIDs []string) (_ *PreparedRun, err error) {
	if strings.TrimSpace(question) == "" {
		return nil, ErrEmptyQuestion
	}
	if s.maxAttachmentsMsg > 0 && countUniqueAttachmentIDs(attachmentIDs) > s.maxAttachmentsMsg {
		return nil, fmt.Errorf("%w: 单条消息最多附带 %d 个附件", ErrInvalidUpload, s.maxAttachmentsMsg)
	}
	key := userID + ":" + conversationID
	if !s.acquire(key) {
		return nil, ErrConversationBusy
	}
	defer func() {
		if err != nil {
			s.release(key)
		}
	}()
	if _, err = s.store.GetConversation(ctx, conversationID, userID); err != nil {
		return nil, err
	}
	items, err := s.attachments.GetMany(ctx, userID, conversationID, attachmentIDs)
	if err != nil {
		return nil, err
	}
	return &PreparedRun{Attachments: items, ConversationID: conversationID, Question: question, service: s, key: key}, nil
}

func countUniqueAttachmentIDs(ids []string) int {
	seen := make(map[string]struct{}, len(ids))
	for _, id := range ids {
		if id = strings.TrimSpace(id); id != "" {
			seen[id] = struct{}{}
		}
	}
	return len(seen)
}

// SaveUser 必须在 Harness 读取历史之后调用。
func (s *Chat) SaveUser(ctx context.Context, p *PreparedRun, firstTurn bool) error {
	msg := &conversations.Message{
		Visible:       true,
		Role:          conversations.RoleUser,
		Content:       p.Question,
		Status:        conversations.StatusCompleted,
		AttachmentIDs: attachmentIDsOf(p.Attachments),
	}
	if err := s.store.CreateMessage(ctx, p.ConversationID, msg); err != nil {
		return fmt.Errorf("保存用户消息失败: %w", err)
	}
	p.UserMessageID = msg.ID
	logger := logutil.FromContext(ctx, s.log)
	logger.Info("[用户消息已保存]")

	if firstTurn {
		title := utils.ClipRunes(strings.Join(strings.Fields(p.Question), " "), 20)
		if title != "" {
			if err := s.store.UpdateTitle(ctx, p.ConversationID, title); err != nil {
				logger.Warn("更新会话标题失败", zap.Error(err))
			}
			return nil
		}
	}
	if err := s.store.TouchConversation(ctx, p.ConversationID); err != nil {
		logger.Warn("更新会话时间失败", zap.Error(err))
	}
	return nil
}

// SaveResult 保存运行结果后发送 done。
func (s *Chat) SaveResult(ctx context.Context, p *PreparedRun, res agent.Result, sink agent.Emitter) agent.Result {
	saveCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 10*time.Second)
	defer cancel()
	msg := conversations.FromModel(res.Message, res.Status, true)

	covered := 0
	if res.Compaction != nil {
		covered = res.Compaction.CoveredTranscriptCount
	}
	paired, mappedCovered, coveredValid := completedToolPairs(res.Transcript, covered)
	transcript := make([]conversations.Message, 0, len(paired))
	for _, m := range paired {
		transcript = append(transcript, conversations.FromModel(m, conversations.StatusCompleted, false))
	}

	var compaction *conversations.CompactionUpdate
	if res.Compaction != nil && len(res.Compaction.Messages) > 0 && coveredValid && (mappedCovered > 0 || p.UserMessageID > 0) {
		compaction = &conversations.CompactionUpdate{
			Messages:               res.Compaction.Messages,
			UserMessageID:          p.UserMessageID,
			CoveredTranscriptCount: mappedCovered,
		}
	}

	logger := logutil.FromContext(ctx, s.log)
	if err := s.store.SaveRun(saveCtx, p.ConversationID, transcript, &msg, compaction); err != nil {
		logger.Error("[保存结果失败]", logutil.Content("错误", err.Error()))
		res.Status = conversations.StatusFailed
		if sink != nil {
			_ = sink(agent.Event{Type: agent.EventError, Data: agent.ErrorData{Message: "保存对话结果失败"}})
		}
	} else {
		res.MessageID = msg.ID
		logger.Info("[结果已保存]")
	}
	if sink != nil {
		if err := sink(agent.Event{Type: agent.EventDone, Data: agent.DoneData{MessageID: res.MessageID, Status: res.Status, ElapsedMS: res.Elapsed.Milliseconds(), ToolCalls: res.ToolCalls}}); err == nil {
			logger.Info("[结束事件已发送]")
		}
	}
	return res
}

// completedToolPairs 过滤不完整工具对，并把压缩边界映射到过滤后的切片位置。
func completedToolPairs(transcript []*schema.Message, coveredCount int) (out []*schema.Message, mappedCovered int, boundaryValid bool) {
	if coveredCount == 0 {
		boundaryValid = true
	}
	for i := 0; i < len(transcript); {
		call := transcript[i]
		if call == nil || call.Role != schema.Assistant || len(call.ToolCalls) == 0 {
			i++
			continue
		}
		expected := make(map[string]bool, len(call.ToolCalls))
		valid := true
		for _, tc := range call.ToolCalls {
			if tc.ID == "" || tc.Function.Name == "" {
				valid = false
			}
			expected[tc.ID] = false
		}
		if len(expected) != len(call.ToolCalls) {
			valid = false
		}
		j := i + 1
		group := []*schema.Message{call}
		for j < len(transcript) && transcript[j] != nil && transcript[j].Role == schema.Tool {
			result := transcript[j]
			seen, ok := expected[result.ToolCallID]
			if !ok || seen {
				valid = false
			} else {
				expected[result.ToolCallID] = true
				group = append(group, result)
			}
			j++
		}
		for _, seen := range expected {
			if !seen {
				valid = false
			}
		}
		if valid {
			out = append(out, group...)
			if coveredCount > 0 && j == coveredCount {
				mappedCovered = len(out)
				boundaryValid = true
			}
		}
		i = j
	}
	return out, mappedCovered, boundaryValid
}

func (s *Chat) acquire(key string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.active[key]; exists {
		return false
	}
	s.active[key] = struct{}{}
	return true
}

func (s *Chat) release(key string) {
	s.mu.Lock()
	delete(s.active, key)
	s.mu.Unlock()
}
