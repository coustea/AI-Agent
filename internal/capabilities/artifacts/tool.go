package artifacts

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/runtime"
)

// StatusToolName 是查询产物状态的工具名。
const StatusToolName = "get_artifact_status"

// StatusInput 是 get_artifact_status 参数。
type StatusInput struct {
	ArtifactID string `json:"artifact_id" jsonschema:"description=产物 ID，由生成工具返回"`
}

// StatusOutput 是 get_artifact_status 返回。
type StatusOutput struct {
	ArtifactID  string `json:"artifact_id"`
	Kind        string `json:"kind"`
	Title       string `json:"title"`
	Status      string `json:"status"`
	Progress    int    `json:"progress"`
	Size        int64  `json:"size,omitempty"`
	Error       string `json:"error,omitempty"`
	DownloadURL string `json:"download_url,omitempty"`
	Message     string `json:"message"`
}

// NewStatusTool 构造产物状态查询工具。
//
// 返回的状态与进度全部来自数据库与任务执行器的真实值，
// 不返回虚构的进度或伪造的完成状态。
func NewStatusTool(svc *Service) (tool.InvokableTool, error) {
	if svc == nil {
		return nil, ErrUnavailable
	}

	return utils.InferTool(StatusToolName,
		"查询课件或视频的生成进度。生成类工具返回 artifact_id 后，"+
			"当学生询问「好了吗」「进度如何」时用本工具查询真实状态。",
		func(ctx context.Context, in StatusInput) (StatusOutput, error) {
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return StatusOutput{}, err
			}

			a, err := svc.Store().GetForUser(ctx, in.ArtifactID, p.UserID)
			if err != nil {
				if err == ErrNotFound {
					return StatusOutput{}, fmt.Errorf("未找到该产物，或它不属于当前用户")
				}
				return StatusOutput{}, err
			}

			// 把任务执行器的内存状态同步到记录，保证返回的是最新真实状态。
			if err := svc.SyncStatus(ctx, a); err != nil {
				return StatusOutput{}, err
			}

			out := StatusOutput{
				ArtifactID: a.ID,
				Kind:       a.Kind,
				Title:      a.Title,
				Status:     a.Status,
				Progress:   a.Progress,
				Size:       a.Size,
				Error:      a.Error,
			}
			if a.Done() {
				out.DownloadURL = "/api/v1/artifacts/" + a.ID + "/download"
			}

			switch a.Status {
			case StatusCompleted:
				out.Message = fmt.Sprintf("《%s》已生成完成，可以下载。", a.Title)
			case StatusFailed:
				out.Message = fmt.Sprintf("《%s》生成失败：%s", a.Title, a.Error)
			case StatusCanceled:
				out.Message = fmt.Sprintf("《%s》生成已取消。", a.Title)
			default:
				out.Message = fmt.Sprintf("《%s》正在生成中，进度 %d%%。", a.Title, a.Progress)
			}
			return out, nil
		})
}

// Tools 返回产物相关的工具。
func Tools(svc *Service) ([]tool.BaseTool, error) {
	st, err := NewStatusTool(svc)
	if err != nil {
		return nil, err
	}
	return []tool.BaseTool{st}, nil
}
