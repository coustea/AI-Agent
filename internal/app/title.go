package app

import (
	"context"
	"strings"
	"sync"
	"time"

	"github.com/cloudwego/eino/components/model"
	"go.uber.org/zap"

	"mentorly/internal/runtime"
)

// TitleStore 是标题生成需要的持久化能力。
type TitleStore interface {
	UpdateTitle(ctx context.Context, id, title string) error
}

// TitleDeps 是标题生成器的装配参数。
type TitleDeps struct {
	Model   model.ToolCallingChatModel
	Store   TitleStore
	Workers int
	Timeout time.Duration
	Log     *zap.Logger
}

// TitleWorker 异步生成会话标题。
//
// 为什么放在 app 而不是 tutor 包：
// 标题是会话的业务属性，与 Agent 推理无关；
// 而且它需要模型补全能力，属于「组合根可以同时看到两侧」的职责。
type TitleWorker struct {
	cm      model.ToolCallingChatModel
	store   TitleStore
	jobs    chan titleJob
	timeout time.Duration
	log     *zap.Logger
	wg      sync.WaitGroup
	once    sync.Once
}

type titleJob struct {
	conversationID string
	question       string
	answer         string
}

// NewTitleWorker 构造并启动 worker。
func NewTitleWorker(d TitleDeps) *TitleWorker {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}

	w := &TitleWorker{
		cm:      d.Model,
		store:   d.Store,
		timeout: d.Timeout,
		log:     log,
	}
	if w.timeout <= 0 {
		w.timeout = 120 * time.Second
	}

	workers := d.Workers
	if workers <= 0 {
		workers = 2
	}

	// 模型未配置时 worker 依然创建，但 Enqueue 直接返回：
	// 这样调用方不必到处判空。
	w.jobs = make(chan titleJob, 128)
	w.wg.Add(workers)
	for i := 0; i < workers; i++ {
		go w.worker()
	}

	return w
}

// Enqueue 提交一个标题生成任务。队列满时丢弃（标题不是关键路径）。
func (w *TitleWorker) Enqueue(conversationID, question, answer string) {
	if w == nil || w.cm == nil {
		return
	}
	w.log.Info("提交标题生成任务", zap.String("conversation_id", conversationID))
	select {
	case w.jobs <- titleJob{conversationID: conversationID, question: question, answer: answer}:
	default:
		w.log.Debug("标题生成队列已满，跳过", zap.String("conversation_id", conversationID))
	}
}

// Close 停止接受新任务并等待在途任务结束。
func (w *TitleWorker) Close(timeout time.Duration) {
	if w == nil {
		return
	}
	w.once.Do(func() {
		close(w.jobs)
	})

	done := make(chan struct{})
	go func() {
		w.wg.Wait()
		close(done)
	}()

	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	select {
	case <-done:
	case <-time.After(timeout):
		w.log.Warn("标题生成器关闭超时")
	}
}

func (w *TitleWorker) worker() {
	defer w.wg.Done()
	for job := range w.jobs {
		w.generate(job)
	}
}

// generate 生成并写入标题。
func (w *TitleWorker) generate(job titleJob) {
	ctx, cancel := context.WithTimeout(context.Background(), w.timeout)
	defer cancel()

	// 只取问题与回答的开头：标题只需要主题，不需要完整内容。
	user := "用户问题：\n" + truncateRunes(job.question, 500) + "\n\n助手回答开头：\n" + truncateRunes(job.answer, 800)

	title, err := runtime.Complete(ctx, w.cm, titleSystemPrompt, user)
	if err != nil {
		w.log.Warn("生成会话标题失败", zap.Error(err), zap.String("conversation_id", job.conversationID))
		return
	}

	title = sanitizeTitle(title)
	if title == "" {
		return
	}

	if err := w.store.UpdateTitle(ctx, job.conversationID, title); err != nil {
		w.log.Warn("写入会话标题失败", zap.Error(err))
		return
	}
	w.log.Info("会话标题已生成",
		zap.String("conversation_id", job.conversationID),
		zap.String("title", title),
	)
}

const titleSystemPrompt = `你为学习对话生成简短标题。
要求：
- 只输出标题本身，不要任何前缀、引号或解释
- 8-20 个汉字，概括这次对话的核心主题
- 使用名词短语，不要用完整句子
- 不要出现「对话」「提问」「关于」这类空词`

// sanitizeTitle 清理模型输出：去掉引号、前缀与多余空白。
func sanitizeTitle(s string) string {
	s = strings.TrimSpace(s)

	// 去掉常见的模型前缀
	for _, prefix := range []string{"标题：", "标题:", "Title:", "title:"} {
		s = strings.TrimPrefix(s, prefix)
	}

	// 去掉包裹的引号
	s = strings.Trim(s, `"'“”‘’`+"`")
	s = strings.TrimSpace(s)

	// 只取第一行
	if idx := strings.IndexByte(s, '\n'); idx >= 0 {
		s = strings.TrimSpace(s[:idx])
	}

	return truncateRunes(s, 100)
}

// truncateRunes 按字符截断。
func truncateRunes(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}
