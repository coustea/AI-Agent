package harness

import (
	"context"
	"strings"
	"sync"
	"time"

	"go.uber.org/zap"

	"mentorly/internal/dao"
	"mentorly/internal/memory"
)

// TitleGenerator 用固定 worker 池异步生成会话标题。
//
// 这是非关键副作用：标题生成失败只是保持默认标题「新会话」，
// 绝不影响对话本身，也不向用户报错。
type TitleGenerator struct {
	model   memory.ChatModel
	chat    *dao.ChatRepo
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
func NewTitleGenerator(model memory.ChatModel, chat *dao.ChatRepo, workers int, timeout time.Duration, log *zap.Logger) *TitleGenerator {
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
		chat:    chat,
		log:     log,
		timeout: timeout,
		// 队列容量有限：标题是尽力而为的副作用，
		// 队列满了就丢弃，不能阻塞对话主链路。
		queue: make(chan titleJob, workers*4),
	}

	for i := 0; i < workers; i++ {
		g.wg.Add(1)
		go g.worker(i)
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
	g.once.Do(func() {
		close(g.queue)
	})

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
func (g *TitleGenerator) worker(id int) {
	defer g.wg.Done()

	for job := range g.queue {
		g.generate(job)
		_ = id
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

	if err := g.chat.UpdateTitle(ctx, job.sessionID, title); err != nil {
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

	// 只取第一行。
	if i := strings.IndexAny(t, "\r\n"); i >= 0 {
		t = strings.TrimSpace(t[:i])
	}

	// 去掉包裹的引号与书名号。
	t = strings.Trim(t, "\"'`《》「」『』“”‘’")

	// 去掉前缀式回答，如「标题：xxx」。
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
