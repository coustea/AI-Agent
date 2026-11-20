package tutor

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"

	"mentorly/internal/capabilities/attachments"
	"mentorly/internal/runtime"
)

// ErrUnavailable 对话能力未启用（未配置模型）。
var ErrUnavailable = errors.New("对话能力未启用")

// ErrConversationNotFound 会话不存在或不属于该用户。
var ErrConversationNotFound = errors.New("会话不存在")

// Conversation 是一次会话。
type Conversation struct {
	ID        string
	UserID    string
	Title     string
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Message 是一条已持久化的消息。
//
// 与 Eino schema.Message 的区别：这是存储视图，只保留对话内容；
// 转换为 schema.Message 是 Harness 的职责。
type Message struct {
	ID        uint64
	Role      string
	Content   string
	Status    string
	Tokens    int
	CreatedAt time.Time
	// AttachmentIDs 该条消息关联的附件
	AttachmentIDs []string
}

// 消息角色与状态。
const (
	RoleUser      = "user"
	RoleAssistant = "assistant"

	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCancelled = "cancelled"
	StatusRunning   = "running"
)

// Harness 是运行上下文管理层。
//
// 它只负责「把一次请求变成一个可执行的运行环境」：
//
//	加载历史 → 校验附件 → 创建工作区 → 组装消息 → 注入身份
//
// 它不参与 Agent 推理：不决定是否调用工具、不选择生成哪种产物、
// 不管理 ReAct 状态。这些全部由 TutorAgent 自主决定。
type Harness struct {
	store       ConversationStore
	attachments *attachments.Store
	cfg         Config
	// dirs 是工作目录配置
	workspaceDir string
	offloadDir   string
	log          *zap.Logger
}

// ConversationStore 是 Harness 与 Runtime 需要的持久化能力。
//
// 用窄接口而不是具体类型：这里只需要会话与消息的几个操作，
// 收窄依赖后可以脱离数据库单测。
type ConversationStore interface {
	GetConversation(ctx context.Context, id, userID string) (*Conversation, error)
	ListMessages(ctx context.Context, conversationID string, limit int) ([]Message, error)
	CreateMessage(ctx context.Context, conversationID string, m *Message) error
	TouchConversation(ctx context.Context, id string) error
	UpdateTitle(ctx context.Context, id, title string) error
	CountMessages(ctx context.Context, conversationID string) (int64, error)
}

// HarnessDeps 是 Harness 的装配参数。
type HarnessDeps struct {
	Store        ConversationStore
	Attachments  *attachments.Store
	Config       Config
	WorkspaceDir string
	OffloadDir   string
	Log          *zap.Logger
}

// NewHarness 构造 Harness。
func NewHarness(d HarnessDeps) *Harness {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	return &Harness{
		store:        d.Store,
		attachments:  d.Attachments,
		cfg:          d.Config,
		workspaceDir: d.WorkspaceDir,
		offloadDir:   d.OffloadDir,
		log:          log,
	}
}

// RunContext 是一次运行的完整上下文。
//
// 由 Harness 创建，交给 Runtime 使用；Runtime 不再回查数据库。
type RunContext struct {
	// Principal 身份与目录边界
	Principal *runtime.Principal
	// Sandbox 文件系统边界
	Sandbox *Sandbox
	// Instruction 已组装的 System Prompt
	Instruction string
	// Messages 已转换为 Eino 消息格式的完整历史（含本轮用户消息）
	Messages []*schema.Message
	// UserMessage 本轮用户消息落库后的 ID
	UserMessageID uint64
	// IsFirstTurn 是否会话首轮，用于异步生成标题
	IsFirstTurn bool
	// Question 本轮原始问题文本
	Question string
}

// Prepare 把一次请求准备成可执行的运行上下文。
//
// 参数 attachmentIDs 是前端声明的附件 ID 列表：Harness 会逐个校验归属，
// 无效或不属于该用户的附件会被明确提示，而不是静默丢弃。
func (h *Harness) Prepare(ctx context.Context, userID, conversationID, question string, attachmentIDs []string) (*RunContext, error) {
	question = strings.TrimSpace(question)
	if question == "" {
		return nil, ErrEmptyQuestion
	}

	// 1. 会话归属校验：任何读写前都必须确认这是该用户的会话。
	if _, err := h.store.GetConversation(ctx, conversationID, userID); err != nil {
		if errors.Is(err, ErrConversationNotFound) {
			return nil, ErrConversationNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	// 2. 是否首轮（在写入本轮消息之前统计）
	count, err := h.store.CountMessages(ctx, conversationID)
	if err != nil {
		return nil, fmt.Errorf("统计消息失败: %w", err)
	}

	// 3. 准备目录与沙箱
	workspace := filepath.Join(h.workspaceDir, userID, conversationID)
	offload := filepath.Join(h.offloadDir, userID, conversationID)
	sandbox, err := NewSandbox(workspace, offload, h.cfg.SkillsDir)
	if err != nil {
		return nil, fmt.Errorf("创建工作区失败: %w", err)
	}

	// 4. 构造运行身份
	principal := &runtime.Principal{
		UserID:         userID,
		ConversationID: conversationID,
		Workspace:      workspace,
		Offload:        offload,
		Vision:         h.cfg.Vision,
	}

	// 5. 加载历史消息
	history, err := h.store.ListMessages(ctx, conversationID, 0)
	if err != nil {
		return nil, fmt.Errorf("加载历史消息失败: %w", err)
	}

	// 6. 落库本轮用户消息（必须在打开 SSE 之前完成，
	//    否则一旦写出响应头就无法再返回 400/404）
	userMsg := &Message{
		Role:          RoleUser,
		Content:       question,
		Status:        StatusCompleted,
		AttachmentIDs: attachmentIDs,
	}
	if err := h.store.CreateMessage(ctx, conversationID, userMsg); err != nil {
		return nil, fmt.Errorf("保存消息失败: %w", err)
	}

	// 7. 构造消息列表
	msgs, err := h.buildMessages(ctx, userID, history, question, attachmentIDs)
	if err != nil {
		return nil, err
	}

	// 8. 组装 System Prompt
	instruction := AssemblePrompt(PromptInput{
		Now:       time.Now().Format("2006-01-02"),
		Workspace: listWorkspaceFiles(workspace),
		Vision:    h.cfg.Vision,
	})

	// 更新活跃时间（失败不影响本轮）
	_ = h.store.TouchConversation(ctx, conversationID)

	return &RunContext{
		Principal:     principal,
		Sandbox:       sandbox,
		Instruction:   instruction,
		Messages:      msgs,
		UserMessageID: userMsg.ID,
		IsFirstTurn:   count == 0,
		Question:      question,
	}, nil
}

// buildMessages 把历史消息与附件转换成 Eino 消息。
//
// 关键点：
//   - 空的失败消息会被跳过：它们对模型没有信息量，
//     还会破坏 user/assistant 交替结构；
//   - 历史消息里的附件只保留「曾上传过什么」的说明，
//     不重新内联二进制，避免每轮都重复传输大文件；
//   - 本轮用户消息通过 attachments.BuildUserMessage 构造，可携带图片多模态。
func (h *Harness) buildMessages(
	ctx context.Context,
	userID string,
	history []Message,
	question string,
	attachmentIDs []string,
) ([]*schema.Message, error) {
	out := make([]*schema.Message, 0, len(history)+1)

	for _, m := range history {
		if m.Status == StatusFailed && strings.TrimSpace(m.Content) == "" {
			continue
		}
		if strings.TrimSpace(m.Content) == "" {
			continue
		}

		role := schema.User
		if m.Role == RoleAssistant {
			role = schema.Assistant
		}
		out = append(out, &schema.Message{Role: role, Content: m.Content})
	}

	// 本轮用户消息：需要携带附件
	if h.attachments != nil {
		msg, err := attachments.BuildUserMessage(ctx, h.attachments, userID, question, attachmentIDs)
		if err != nil {
			return nil, fmt.Errorf("构造附件消息失败: %w", err)
		}
		out = append(out, msg)
		return out, nil
	}

	out = append(out, schema.UserMessage(question))
	return out, nil
}

// ErrEmptyQuestion 问题为空。
var ErrEmptyQuestion = errors.New("问题内容不能为空")

// listWorkspaceFiles 列出工作区文件，注入 Prompt 让模型知道有什么可读。
//
// 只列一层目录：深层递归在文件多时会让 Prompt 膨胀，
// 而且模型本来就可以用 glob/grep 自行探索。
func listWorkspaceFiles(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}

	out := make([]string, 0, len(entries))
	for _, e := range entries {
		if e.IsDir() {
			out = append(out, e.Name()+"/")
			continue
		}
		out = append(out, e.Name())
	}
	// 控制注入规模，避免 Prompt 被文件列表占满。
	if len(out) > 40 {
		out = out[:40]
	}
	return out
}
