// Package memory 的对外服务面：记忆的读取、手动编辑与清空，
// 以及会话标题的异步生成（标题也只是一条会话字段，不参与轮次编排）。
package memory

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"

	"go.uber.org/zap"
)

// ErrTooLong 手动编辑的记忆超出上限。
var ErrTooLong = errors.New("记忆内容超出长度上限")

// Service 是长期记忆的管理面。
type Service struct {
	store    *Repo
	maxChars int
}

// NewService 构造记忆管理服务。
func NewService(store *Repo, maxChars int) *Service {
	if maxChars <= 0 {
		maxChars = 2000
	}
	return &Service{store: store, maxChars: maxChars}
}

// Get 读取长期记忆。
func (s *Service) Get(ctx context.Context, userID string) (*Doc, error) {
	doc, err := s.store.Get(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("读取记忆失败: %w", err)
	}
	return &Doc{UserID: doc.UserID, Content: doc.Content, Version: doc.Version}, nil
}

// Update 手动编辑记忆。
// 上限为 maxChars 的 2 倍：手动编辑允许比自动提取稍长，
// 但仍需有边界，避免把整份文档塞进 prompt。
func (s *Service) Update(ctx context.Context, userID, content string) error {
	if n := len([]rune(content)); n > s.maxChars*2 {
		return fmt.Errorf("%w: 最多 %d 字符，当前 %d", ErrTooLong, s.maxChars*2, n)
	}
	if err := s.store.Upsert(ctx, userID, content); err != nil {
		return fmt.Errorf("保存记忆失败: %w", err)
	}
	return nil
}

// Clear 清空记忆。
func (s *Service) Clear(ctx context.Context, userID string) error {
	if err := s.store.Delete(ctx, userID); err != nil {
		return fmt.Errorf("清空记忆失败: %w", err)
	}
	return nil
}

// TitleStore 是标题生成需要的写回能力。
type TitleStore interface {
	UpdateTitle(ctx context.Context, sessionID, title string) error
}

// TitleGenerator 用固定 worker 池异步生成会话标题。
//
// 这是非关键副作用：标题生成失败只是保持默认标题「新会话」，
// 绝不影响对话本身，也不向用户报错。
type TitleGenerator struct {
	model   ChatModel
	store   TitleStore
	log     *zap.Logger
	timeout time.Duration

	queue chan titleJob
	wg    sync.WaitGroup
	once  sync.Once
}

type titleJob struct {
	sessionID string
	question  string
	answer    string
}

// NewTitleGenerator 创建并启动 worker 池。
func NewTitleGenerator(model ChatModel, store TitleStore, workers int, timeout time.Duration, log *zap.Logger) *TitleGenerator {
	if log == nil {
		log = zap.NewNop()
	}
	if workers <= 0 {
		workers = 4
	}
	if timeout <= 0 {
		timeout = 30 * time.Second
	}

	g := &TitleGenerator{
		model:   model,
		store:   store,
		log:     log,
		timeout: timeout,
		// 队列容量有限：标题是尽力而为的副作用，
		// 队列满了就丢弃，不能阻塞对话主链路。
		queue: make(chan titleJob, workers*4),
	}

	for i := 0; i < workers; i++ {
		g.wg.Add(1)
		go g.worker()
	}
	return g
}

// Enqueue 投递标题生成任务。非阻塞：队列满时直接丢弃。
func (g *TitleGenerator) Enqueue(sessionID, question, answer string) {
	if g == nil || g.model == nil {
		return
	}
	select {
	case g.queue <- titleJob{sessionID: sessionID, question: question, answer: answer}:
	default:
		g.log.Debug("标题队列已满，跳过本轮标题生成", zap.String("session_id", sessionID))
	}
}

// Close 关闭队列并等待在途任务，最多等待 timeout。
func (g *TitleGenerator) Close(timeout time.Duration) {
	if g == nil {
		return
	}
	g.once.Do(func() { close(g.queue) })

	done := make(chan struct{})
	go func() {
		g.wg.Wait()
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(timeout):
		g.log.Warn("等待标题生成任务超时，强制退出")
	}
}

// worker 消费队列。
func (g *TitleGenerator) worker() {
	defer g.wg.Done()
	for job := range g.queue {
		g.generate(job)
	}
}

// generate 生成并写回标题。
func (g *TitleGenerator) generate(job titleJob) {
	ctx, cancel := context.WithTimeout(context.Background(), g.timeout)
	defer cancel()

	// 截断输入，避免把整轮对话都塞进标题提示词。
	prompt := "学生问题：" + truncateRunes(job.question, 500) +
		"\n\n辅导员回答开头：" + truncateRunes(job.answer, 800) +
		"\n\n请为这段对话起一个不超过 20 字的标题，只输出标题本身，不要标点包裹、不要引号、不要解释。"

	title, err := g.model.Complete(ctx, titleSystemPrompt, prompt)
	if err != nil {
		g.log.Warn("生成会话标题失败", zap.Error(err), zap.String("session_id", job.sessionID))
		return
	}

	title = sanitizeTitle(title)
	if title == "" {
		return
	}

	if err := g.store.UpdateTitle(ctx, job.sessionID, title); err != nil {
		g.log.Warn("写回会话标题失败", zap.Error(err), zap.String("session_id", job.sessionID))
		return
	}
	g.log.Info("会话标题已生成", zap.String("session_id", job.sessionID), zap.String("title", title))
}

const titleSystemPrompt = `你是对话标题生成器。根据学生的问题与辅导员回答的开头，生成一个简洁的会话标题。
要求：
1. 不超过 20 个汉字。
2. 直接输出标题文本，不要引号、书名号、句号或任何解释。
3. 概括主题，不要照抄问题原句。`

// sanitizeTitle 清理模型输出：去掉换行、引号与常见前后缀。
func sanitizeTitle(s string) string {
	t := strings.TrimSpace(s)

	if i := strings.IndexAny(t, "\r\n"); i >= 0 {
		t = strings.TrimSpace(t[:i])
	}
	t = strings.Trim(t, "\"'`《》「」『』“”‘’")
	for _, prefix := range []string{"标题：", "标题:", "会话标题：", "会话标题:"} {
		t = strings.TrimPrefix(t, prefix)
	}
	t = strings.TrimSpace(t)
	// 兜底长度限制，防止模型不遵守约束。
	return truncateRunes(t, 40)
}

// truncateRunes 按字符（而非字节）截断，避免切坏中文。
func truncateRunes(s string, n int) string {
	r := []rune(strings.TrimSpace(s))
	if len(r) <= n {
		return string(r)
	}
	return string(r[:n])
}
