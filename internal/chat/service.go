package chat

import (
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"

	"mentorly/internal/infra"
)

// ErrSessionNotFound 会话不存在或无权访问。
var ErrSessionNotFound = errors.New("会话不存在")

// ErrTooLong 手动编辑内容超出上限。
var ErrTooLong = errors.New("内容超出长度上限")

// Config 是本模块的业务参数。
//
// 刻意不引用 internal/config：模块只接收拍平后的业务参数，
// 对配置文件的形状零知识，也不知道数据库连哪。
type Config struct {
	// WorkspaceDir 会话工作目录根路径，实际为 {WorkspaceDir}/{userID}/{sessionID}
	WorkspaceDir string
	// OffloadDir 工具结果卸载根目录，与工作目录分开以保持会话目录干净
	OffloadDir string
	// SkillsDir 技能目录，只读挂载为 Agent 的 /skills
	SkillsDir string
	// MaxSteps Agent 单轮最大迭代步数
	MaxSteps int
	// RunTimeout 单轮生成总超时
	RunTimeout time.Duration
	// HistoryMaxMessages 历史消息条数上限
	HistoryMaxMessages int
	// HistoryBudgetTokens 历史 token 预算
	HistoryBudgetTokens int
	// CompressTriggerTokens 触发压缩的 token 阈值
	CompressTriggerTokens int
	// CompressTriggerMessages 触发压缩的消息条数阈值
	CompressTriggerMessages int
	// CompressSourceMaxChars 单次送入压缩的原文最大字符数
	CompressSourceMaxChars int
	// KeepRecentTurns 压缩时保留原文的最近轮数
	KeepRecentTurns int
	// TitleWorkers 异步生成标题的 worker 数
	TitleWorkers int
	// TitleTimeout 单次标题生成超时
	TitleTimeout time.Duration
}

// Service 是 chat 模块的业务面。
//
// 会话管理（建/列/改名/删/历史）与一轮对话的完整生命周期都在这里：
// 它们是同一个模块的两面，按生命周期阶段拆成多个文件只会增加跳转成本。
type Service struct {
	store   *Store
	lock    *infra.Lock
	agent   *AgentRunner
	title   *titleWorker
	counter Counter
	cfg     Config
	log     *zap.Logger
}

// Deps 是模块的外部依赖，由 api 层装配。
type Deps struct {
	Store *Store
	Lock  *infra.Lock
	Agent *AgentRunner
	Log   *zap.Logger
	Cfg   Config
}

// New 构造 chat 业务。
func New(d Deps) *Service {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	s := &Service{
		store:   d.Store,
		lock:    d.Lock,
		agent:   d.Agent,
		counter: Counter{},
		cfg:     d.Cfg,
		log:     log,
	}
	if d.Agent != nil {
		s.title = newTitleWorker(d.Agent, d.Store, d.Cfg.TitleWorkers, d.Cfg.TitleTimeout, log)
	}
	return s
}

// Enabled 表示对话能力是否可用（未配置模型时返回 false，接口应返回 503）。
func (s *Service) Enabled() bool {
	return s != nil && s.agent != nil && s.store != nil
}

// Close 关闭后台 worker，用于进程优雅退出。
func (s *Service) Close(timeout time.Duration) {
	if s == nil || s.title == nil {
		return
	}
	s.title.Close(timeout)
}

// ---------- 会话管理 ----------

// CreateSession 创建会话。标题留空时用默认标题，首轮回答后异步生成真实标题。
func (s *Service) CreateSession(ctx context.Context, userID, title string) (*Session, error) {
	title = strings.TrimSpace(title)
	if title == "" {
		title = "新会话"
	}

	sess := &Session{
		ID:     uuid.NewString(),
		UserID: userID,
		Title:  title,
	}
	if err := s.store.CreateSession(ctx, sess); err != nil {
		return nil, fmt.Errorf("创建会话失败: %w", err)
	}
	return sess, nil
}

// ListSessions 列出用户的会话。
func (s *Service) ListSessions(ctx context.Context, userID string, limit int) ([]Session, error) {
	rows, err := s.store.ListSessions(ctx, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("查询会话列表失败: %w", err)
	}
	return rows, nil
}

// RenameSession 重命名会话。
func (s *Service) RenameSession(ctx context.Context, userID, sessionID, title string) error {
	err := s.store.RenameSession(ctx, sessionID, userID, strings.TrimSpace(title))
	if err != nil {
		if errors.Is(err, ErrRecordNotFound) {
			return ErrSessionNotFound
		}
		return fmt.Errorf("重命名会话失败: %w", err)
	}
	return nil
}

// DeleteSession 软删除会话。
func (s *Service) DeleteSession(ctx context.Context, userID, sessionID string) error {
	if err := s.store.DeleteSession(ctx, sessionID, userID); err != nil {
		if errors.Is(err, ErrRecordNotFound) {
			return ErrSessionNotFound
		}
		return fmt.Errorf("删除会话失败: %w", err)
	}
	return nil
}

// Messages 游标分页查询历史（含 tokens 与 meta 的完整视图）。
func (s *Service) Messages(ctx context.Context, userID, sessionID string, beforeID uint64, limit int) ([]MessageView, error) {
	// 先校验归属，避免越权读取他人消息。
	if _, err := s.store.GetSessionForUser(ctx, sessionID, userID); err != nil {
		if errors.Is(err, ErrRecordNotFound) {
			return nil, ErrSessionNotFound
		}
		return nil, fmt.Errorf("查询会话失败: %w", err)
	}

	rows, err := s.store.ListMessageViews(ctx, sessionID, beforeID, limit)
	if err != nil {
		return nil, fmt.Errorf("查询消息失败: %w", err)
	}
	return rows, nil
}

// ---------- 异步标题 ----------

// titleWorker 用固定 worker 池异步生成会话标题。
//
// 这是非关键副作用：标题生成失败只是保持默认标题「新会话」，
// 绝不影响对话本身，也不向用户报错。
//
// 放在本包而非独立模块：标题是 chat_sessions 的一列，
// 它的产物就是会话的一个字段，属于会话生命周期。
type titleWorker struct {
	runner  *AgentRunner
	store   *Store
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

// newTitleWorker 创建并启动 worker 池。
func newTitleWorker(runner *AgentRunner, store *Store, workers int, timeout time.Duration, log *zap.Logger) *titleWorker {
	if workers <= 0 {
		workers = 4
	}
	if timeout <= 0 {
		timeout = 120 * time.Second
	}

	w := &titleWorker{
		runner:  runner,
		store:   store,
		log:     log,
		timeout: timeout,
		// 队列容量有限：标题是尽力而为的副作用，
		// 队列满了就丢弃，不能阻塞对话主链路。
		queue: make(chan titleJob, workers*4),
	}

	for i := 0; i < workers; i++ {
		w.wg.Add(1)
		go w.worker()
	}
	return w
}

// Enqueue 投递标题生成任务。非阻塞：队列满时直接丢弃。
func (w *titleWorker) Enqueue(sessionID, question, answer string) {
	if w == nil || w.runner == nil {
		return
	}
	select {
	case w.queue <- titleJob{sessionID: sessionID, question: question, answer: answer}:
	default:
		w.log.Debug("标题队列已满，跳过本轮标题生成", zap.String("session_id", sessionID))
	}
}

// Close 关闭队列并等待在途任务，最多等待 timeout。
func (w *titleWorker) Close(timeout time.Duration) {
	if w == nil {
		return
	}
	w.once.Do(func() { close(w.queue) })

	done := make(chan struct{})
	go func() {
		w.wg.Wait()
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(timeout):
		w.log.Warn("等待标题生成任务超时，强制退出")
	}
}

// worker 消费队列。
func (w *titleWorker) worker() {
	defer w.wg.Done()
	for job := range w.queue {
		w.generate(job)
	}
}

// generate 生成并写回标题。
func (w *titleWorker) generate(job titleJob) {
	ctx, cancel := context.WithTimeout(context.Background(), w.timeout)
	defer cancel()

	// 截断输入，避免把整轮对话都塞进标题提示词。
	prompt := "学生问题：" + truncateRunes(job.question, 500) +
		"\n\n辅导员回答开头：" + truncateRunes(job.answer, 800) +
		"\n\n请为这段对话起一个不超过 20 字的标题，只输出标题本身，不要标点包裹、不要引号、不要解释。"

	title, err := w.runner.Complete(ctx, titleSystemPrompt, prompt)
	if err != nil {
		w.log.Warn("生成会话标题失败", zap.Error(err), zap.String("session_id", job.sessionID))
		return
	}

	title = sanitizeTitle(title)
	if title == "" {
		return
	}

	if err := w.store.UpdateTitle(ctx, job.sessionID, title); err != nil {
		w.log.Warn("写回会话标题失败", zap.Error(err), zap.String("session_id", job.sessionID))
		return
	}
	w.log.Info("会话标题已生成", zap.String("session_id", job.sessionID), zap.String("title", title))
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

// workspace 返回会话工作目录。
func (s *Service) workspace(userID, sessionID string) string {
	return filepath.Join(s.cfg.WorkspaceDir, userID, sessionID)
}

// offload 返回工具结果卸载目录。
func (s *Service) offload(userID, sessionID string) string {
	return filepath.Join(s.cfg.OffloadDir, userID, sessionID)
}
