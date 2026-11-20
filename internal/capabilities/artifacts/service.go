package artifacts

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"

	"mentorly/internal/runtime"
)

// ErrUnavailable 生成能力未配置（缺少 ffmpeg、字体或渲染引擎）。
var ErrUnavailable = errors.New("产物生成能力未配置")

// ProduceFunc 是同步生成器：把产物写到 workDir 下的 outName，返回 MIME 与展示用 Meta。
//
// 返回值必须真实：写不出文件就必须返回 error，
// 不允许返回占位文件或伪造的成功结果。
type ProduceFunc func(ctx context.Context, req ProduceRequest) (Produced, error)

// ProduceRequest 是生成器收到的入参。
type ProduceRequest struct {
	// WorkDir 生成器可写的临时目录
	WorkDir string
	// OutName 期望的输出文件名（含扩展名）
	OutName string
	// Title 产物标题
	Title string
	// Spec 生成规格，由各 Capability 自行解释
	Spec any
	// Report 进度回调，长任务用它汇报
	Report func(progress int, note string)
}

// Produced 是生成结果。
type Produced struct {
	MIME string
	Meta map[string]any
}

// Service 编排产物的完整生命周期：建记录 → 执行生成 → 更新状态 → 落盘。
//
// 同步与异步两种模式共用同一条落盘与状态更新路径，
// 避免「同步能出文件、异步状态不对」这类分叉缺陷。
type Service struct {
	store *Store
	jobs  *runtime.JobRunner
	log   *zap.Logger
}

// Deps 是 Service 的装配参数。
type Deps struct {
	Store *Store
	Jobs  *runtime.JobRunner
	Log   *zap.Logger
}

// New 构造 Service。
func New(d Deps) *Service {
	log := d.Log
	if log == nil {
		log = zap.NewNop()
	}
	return &Service{store: d.Store, jobs: d.Jobs, log: log}
}

// Store 暴露底层存储，供 Handler 做下载与列表。
func (s *Service) Store() *Store { return s.store }

// CreateSync 创建一条产物记录并同步执行生成。
//
// 适用于图解这类秒级完成的产物：调用方（Tool）直接拿到可用文件，
// 不需要再轮询状态。
func (s *Service) CreateSync(
	ctx context.Context,
	userID, conversationID, kind, title, outName string,
	produce ProduceFunc,
	spec any,
) (*Artifact, error) {
	if produce == nil {
		return nil, fmt.Errorf("生成器不能为空")
	}

	a := &Artifact{
		ID:             uuid.NewString(),
		UserID:         userID,
		ConversationID: conversationID,
		Kind:           kind,
		Title:          title,
		Status:         StatusRunning,
		MIME:           mimeOf(outName),
		Meta:           map[string]any{},
	}
	if err := s.store.Create(ctx, a); err != nil {
		return nil, err
	}

	workDir, err := s.workDir(a.ID)
	if err != nil {
		return nil, err
	}
	defer os.RemoveAll(workDir)

	outName = safeName(outName, a.ID)
	produced, err := produce(ctx, ProduceRequest{
		WorkDir: workDir,
		OutName: outName,
		Title:   title,
		Spec:    spec,
		Report:  func(int, string) {},
	})
	if err != nil {
		s.fail(ctx, a, err)
		return a, err
	}

	if err := s.finalize(ctx, a, workDir, outName, produced); err != nil {
		return a, err
	}
	return a, nil
}

// CreateAsync 创建产物记录并提交后台生成任务。
//
// 适用于 PPT、视频这类可能耗时几十秒到几分钟的产物：
// HTTP 请求立即返回 artifact_id，前端轮询或订阅进度。
func (s *Service) CreateAsync(
	ctx context.Context,
	userID, conversationID, kind, title, outName string,
	produce ProduceFunc,
	spec any,
) (*Artifact, error) {
	if produce == nil {
		return nil, fmt.Errorf("生成器不能为空")
	}
	if s.jobs == nil {
		return nil, fmt.Errorf("异步任务执行器未配置")
	}

	a := &Artifact{
		ID:             uuid.NewString(),
		UserID:         userID,
		ConversationID: conversationID,
		Kind:           kind,
		Title:          title,
		Status:         StatusQueued,
		MIME:           mimeOf(outName),
		Meta:           map[string]any{},
	}
	if err := s.store.Create(ctx, a); err != nil {
		return nil, err
	}

	outName = safeName(outName, a.ID)
	workDir, err := s.workDir(a.ID)
	if err != nil {
		return nil, err
	}

	// 任务在后台运行，不能沿用请求 ctx：请求结束（SSE 关闭）不该杀掉生成。
	// 权限与身份已在上面用请求 ctx 校验并落库，这里只需 userID 字符串。
	if _, err := s.jobs.Submit(kind, a.ID, func(jobCtx context.Context, report func(int, string)) error {
		defer os.RemoveAll(workDir)

		produced, err := produce(jobCtx, ProduceRequest{
			WorkDir: workDir,
			OutName: outName,
			Title:   title,
			Spec:    spec,
			Report:  report,
		})
		if err != nil {
			s.fail(jobCtx, a, err)
			return err
		}
		return s.finalize(jobCtx, a, workDir, outName, produced)
	}); err != nil {
		s.fail(ctx, a, err)
		return a, err
	}

	return a, nil
}

// finalize 把生成的文件落盘并更新记录为完成。
func (s *Service) finalize(ctx context.Context, a *Artifact, workDir, outName string, produced Produced) error {
	src := filepath.Join(workDir, outName)
	if _, err := os.Stat(src); err != nil {
		err = fmt.Errorf("生成器未产出文件 %s: %w", outName, err)
		s.fail(ctx, a, err)
		return err
	}

	// 产物文件按 id 命名，避免不同产物的文件名互相覆盖。
	stored := a.ID + filepath.Ext(outName)
	if err := s.store.SaveFile(a, src, stored); err != nil {
		s.fail(ctx, a, err)
		return err
	}

	a.Status = StatusCompleted
	a.Progress = 100
	a.Error = ""
	if produced.MIME != "" {
		a.MIME = produced.MIME
	}
	if produced.Meta != nil {
		a.Meta = produced.Meta
	}

	// 更新失败要让调用方知道：否则会出现「文件在但记录仍是 running」的不一致。
	if err := s.store.Update(ctx, a); err != nil {
		return fmt.Errorf("更新产物状态失败: %w", err)
	}

	s.log.Info("产物生成完成",
		zap.String("artifact_id", a.ID),
		zap.String("kind", a.Kind),
		zap.Int64("size", a.Size),
	)
	return nil
}

// fail 记录失败状态。使用独立的短超时 context，
// 因为调用它的 ctx 可能已被取消（任务超时/客户端断开）。
func (s *Service) fail(ctx context.Context, a *Artifact, cause error) {
	a.Status = StatusFailed
	a.Error = cause.Error()

	saveCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 5*time.Second)
	defer cancel()

	if err := s.store.Update(saveCtx, a); err != nil {
		s.log.Error("记录产物失败状态出错",
			zap.String("artifact_id", a.ID),
			zap.Error(err),
		)
	}
	s.log.Warn("产物生成失败",
		zap.String("artifact_id", a.ID),
		zap.String("kind", a.Kind),
		zap.Error(cause),
	)
}

// workDir 为产物创建独立临时目录。
func (s *Service) workDir(id string) (string, error) {
	dir := filepath.Join(os.TempDir(), "mentorly-artifacts", id)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", fmt.Errorf("创建临时目录失败: %w", err)
	}
	return dir, nil
}

// SyncStatus 把 runtime 的任务状态同步到产物记录。
// 供 Handler 在查询时保证两者一致（任务可能已被取消）。
func (s *Service) SyncStatus(ctx context.Context, a *Artifact) error {
	if s.jobs == nil || IsTerminal(a.Status) {
		return nil
	}
	job, ok := s.jobs.Get(a.ID)
	if !ok {
		return nil
	}

	changed := false
	if a.Status != job.Status {
		a.Status = job.Status
		changed = true
	}
	if job.Progress > a.Progress {
		a.Progress = job.Progress
		changed = true
	}
	if job.Error != "" && a.Error == "" {
		a.Error = job.Error
		changed = true
	}
	if !changed {
		return nil
	}
	return s.store.Update(ctx, a)
}

// Cancel 取消异步生成任务。
func (s *Service) Cancel(ctx context.Context, id, userID string) (*Artifact, error) {
	a, err := s.store.GetForUser(ctx, id, userID)
	if err != nil {
		return nil, err
	}
	if IsTerminal(a.Status) {
		return a, nil
	}
	if s.jobs != nil {
		s.jobs.Cancel(a.ID)
	}
	return a, nil
}

// mimeOf 按扩展名推断 MIME。
func mimeOf(name string) string {
	switch strings.ToLower(filepath.Ext(name)) {
	case ".pptx":
		return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
	case ".mp4":
		return "video/mp4"
	case ".svg":
		return "image/svg+xml"
	case ".png":
		return "image/png"
	case ".md":
		return "text/markdown; charset=utf-8"
	case ".json":
		return "application/json"
	default:
		return "application/octet-stream"
	}
}

// safeName 保证输出文件名只含安全字符，且带正确扩展名。
func safeName(name, id string) string {
	name = filepath.Base(strings.TrimSpace(name))
	if name == "" || name == "." || name == ".." {
		return id
	}
	return name
}
