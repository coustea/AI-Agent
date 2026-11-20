package runtime

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"go.uber.org/zap"
)

// 任务终态与中间态。与 artifacts.Artifact.Status 取值保持一致。
const (
	JobQueued    = "queued"
	JobRunning   = "running"
	JobCompleted = "completed"
	JobFailed    = "failed"
	JobCanceled  = "canceled"
)

// ErrJobNotFound 任务不存在。
var ErrJobNotFound = errors.New("runtime: 任务不存在")

// Job 是一次异步生成任务的可观察状态。
//
// 只保存「调度需要的最小信息」：任务本身的内容（输入参数、产物路径）
// 由使用它的 Capability 自己持久化，避免这里长成一个通用任务框架。
type Job struct {
	ID     string
	Kind   string
	Status string
	Error  string
	// Progress 0-100，由执行体主动上报；未上报时为 0。
	Progress int
	// Note 是最近一次进度说明，供前端展示。
	Note      string
	CreatedAt time.Time
	StartedAt time.Time
	EndedAt   time.Time
}

// JobFunc 是任务的实际执行体。
// ctx 会在 Cancel 或超时时取消；返回 error 即任务失败。
type JobFunc func(ctx context.Context, report func(progress int, note string)) error

// JobRunner 是进程内的有界异步任务执行器。
//
// 设计边界：
//   - 只有排队、并发上限、超时、取消四件事；
//   - 不提供依赖编排、重试策略、优先级队列；
//   - 任务状态的真实来源在数据库（artifacts 表），这里只是内存中的执行视图。
//
// 这样 PPT/视频这类长任务不会阻塞 HTTP 请求，同时不会长成一个自研调度平台。
type JobRunner struct {
	mu      sync.Mutex
	jobs    map[string]*jobEntry
	queue   chan *jobEntry
	wg      sync.WaitGroup
	closed  bool
	timeout time.Duration
	log     *zap.Logger
}

type jobEntry struct {
	job    Job
	fn     JobFunc
	cancel context.CancelFunc
	// done 在任务进入终态时关闭，供等待方阻塞。
	done chan struct{}
	// progress 是最近一次上报的进度，供状态查询使用。
	progress int
	note     string
}

// NewJobRunner 创建执行器并启动 workers 个 worker。
// workers <= 0 时取 2；timeout <= 0 时取 10 分钟。
func NewJobRunner(workers int, timeout time.Duration, log *zap.Logger) *JobRunner {
	if workers <= 0 {
		workers = 2
	}
	if timeout <= 0 {
		timeout = 10 * time.Minute
	}
	if log == nil {
		log = zap.NewNop()
	}

	r := &JobRunner{
		jobs:    make(map[string]*jobEntry),
		queue:   make(chan *jobEntry, 64),
		timeout: timeout,
		log:     log,
	}
	r.wg.Add(workers)
	for i := 0; i < workers; i++ {
		go r.worker()
	}
	return r
}

// Submit 提交任务。返回的任务状态为 queued。
// 执行体在 worker 中运行，不阻塞调用方。
func (r *JobRunner) Submit(kind, id string, fn JobFunc) (Job, error) {
	if fn == nil {
		return Job{}, fmt.Errorf("任务执行体不能为空")
	}

	r.mu.Lock()
	if r.closed {
		r.mu.Unlock()
		return Job{}, fmt.Errorf("任务执行器已关闭")
	}
	if _, exists := r.jobs[id]; exists {
		r.mu.Unlock()
		return Job{}, fmt.Errorf("任务已存在: %s", id)
	}
	e := &jobEntry{
		job: Job{
			ID:        id,
			Kind:      kind,
			Status:    JobQueued,
			CreatedAt: time.Now(),
		},
		fn:   fn,
		done: make(chan struct{}),
	}
	r.jobs[id] = e
	// 必须在锁内拷贝：worker 会在任务开始后并发修改 e.job，
	// 直接把 e.job 返回给调用方会造成数据竞争。
	snapshot := e.job
	r.mu.Unlock()

	select {
	case r.queue <- e:
		return snapshot, nil
	default:
		// 队列满：立即失败，不静默丢任务。
		r.finish(e, JobFailed, "任务队列已满", nil)
		return Job{}, fmt.Errorf("任务队列已满，请稍后重试")
	}
}

// Get 查询任务状态。
func (r *JobRunner) Get(id string) (Job, bool) {
	r.mu.Lock()
	defer r.mu.Unlock()
	e, ok := r.jobs[id]
	if !ok {
		return Job{}, false
	}
	// 在锁内拷贝，调用方拿到的是独立快照。
	j := e.job
	j.Progress = e.progress
	j.Note = e.note
	return j, true
}

// Cancel 取消任务。已完成的任务返回 false。
func (r *JobRunner) Cancel(id string) bool {
	r.mu.Lock()
	e, ok := r.jobs[id]
	if !ok || e.cancel == nil {
		r.mu.Unlock()
		return false
	}
	cancel := e.cancel
	r.mu.Unlock()

	cancel()
	return true
}

// Wait 阻塞等待任务结束或 ctx 取消。
func (r *JobRunner) Wait(ctx context.Context, id string) (Job, error) {
	r.mu.Lock()
	e, ok := r.jobs[id]
	r.mu.Unlock()
	if !ok {
		return Job{}, ErrJobNotFound
	}

	select {
	case <-e.done:
		j, _ := r.Get(id)
		return j, nil
	case <-ctx.Done():
		return Job{}, ctx.Err()
	}
}

// Close 停止接受新任务并等待在途任务结束。
func (r *JobRunner) Close(timeout time.Duration) {
	r.mu.Lock()
	if r.closed {
		r.mu.Unlock()
		return
	}
	r.closed = true
	// 取消所有在途任务，避免退出时卡住。
	for _, e := range r.jobs {
		if e.cancel != nil {
			e.cancel()
		}
	}
	r.mu.Unlock()

	close(r.queue)

	done := make(chan struct{})
	go func() {
		r.wg.Wait()
		close(done)
	}()

	if timeout <= 0 {
		timeout = 10 * time.Second
	}
	select {
	case <-done:
	case <-time.After(timeout):
		r.log.Warn("任务执行器关闭超时，仍有任务在运行")
	}
}

func (r *JobRunner) worker() {
	defer r.wg.Done()
	for e := range r.queue {
		r.run(e)
	}
}

func (r *JobRunner) run(e *jobEntry) {
	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	r.mu.Lock()
	if e.job.Status != JobQueued {
		r.mu.Unlock()
		return
	}
	e.job.Status = JobRunning
	e.job.StartedAt = time.Now()
	e.cancel = cancel
	r.mu.Unlock()

	report := func(progress int, note string) {
		r.mu.Lock()
		e.progress = progress
		e.note = note
		r.mu.Unlock()
	}

	// 防止执行体 panic 拖垮整个 worker。
	var runErr error
	func() {
		defer func() {
			if rec := recover(); rec != nil {
				runErr = fmt.Errorf("任务执行 panic: %v", rec)
			}
		}()
		runErr = e.fn(ctx, report)
	}()

	switch {
	case runErr == nil:
		r.finish(e, JobCompleted, "", nil)
	case errors.Is(runErr, context.Canceled), errors.Is(ctx.Err(), context.Canceled):
		r.finish(e, JobCanceled, "任务已取消", nil)
	case errors.Is(runErr, context.DeadlineExceeded), errors.Is(ctx.Err(), context.DeadlineExceeded):
		r.finish(e, JobFailed, "任务执行超时", nil)
	default:
		r.finish(e, JobFailed, runErr.Error(), runErr)
	}
}

func (r *JobRunner) finish(e *jobEntry, status, errMsg string, cause error) {
	r.mu.Lock()
	already := e.job.Status == JobCompleted || e.job.Status == JobFailed || e.job.Status == JobCanceled
	e.job.Status = status
	e.job.Error = errMsg
	e.job.EndedAt = time.Now()
	e.cancel = nil
	r.mu.Unlock()

	if !already {
		close(e.done)
	}
	if cause != nil {
		r.log.Warn("异步任务失败",
			zap.String("job_id", e.job.ID),
			zap.String("kind", e.job.Kind),
			zap.Error(cause),
		)
	}
}
