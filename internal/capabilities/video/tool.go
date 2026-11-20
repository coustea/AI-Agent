package video

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/capabilities/artifacts"
	"mentorly/internal/runtime"
)

// ToolName 是对 Agent 暴露的工具名。
const ToolName = "generate_explainer_video"

// ToolInput 是 generate_explainer_video 的参数。
type ToolInput struct {
	Title    string       `json:"title" jsonschema:"description=视频标题，概括讲解主题"`
	Subtitle string       `json:"subtitle,omitempty" jsonschema:"description=副标题，可留空"`
	Scenes   []SceneInput `json:"scenes" jsonschema:"description=分镜列表，2-8 个为宜，按讲解顺序排列"`
}

// SceneInput 是单个分镜参数。
type SceneInput struct {
	Heading   string   `json:"heading" jsonschema:"description=本分镜标题，一句话"`
	Bullets   []string `json:"bullets" jsonschema:"description=本分镜要点，1-5 条，每条不超过 400 字"`
	Narration string   `json:"narration,omitempty" jsonschema:"description=旁白字幕，一两句口语化说明"`
	Seconds   int      `json:"seconds,omitempty" jsonschema:"description=本分镜时长（秒），2-30，默认 6"`
}

// ToolOutput 是 generate_explainer_video 的返回。
type ToolOutput struct {
	ArtifactID  string `json:"artifact_id"`
	Title       string `json:"title"`
	Status      string `json:"status"`
	Scenes      int    `json:"scenes"`
	TotalSecs   int    `json:"total_seconds"`
	DownloadURL string `json:"download_url"`
	StatusURL   string `json:"status_url"`
	Message     string `json:"message"`
}

// NewTool 构造讲解视频生成工具。
//
// 与课件一样走异步：视频渲染需要逐帧绘制并编码，
// 同步等待会阻塞整个 SSE 流。
func NewTool(r *Renderer) (tool.InvokableTool, error) {
	if r == nil {
		return nil, artifacts.ErrUnavailable
	}

	return utils.InferTool(ToolName,
		"生成可播放的讲解动画视频（MP4）。当学生要求「动画讲解」「视频说明」「做个讲解视频」时，"+
			"必须调用本工具真正生成，不能只用文字描述方案。"+
			"先规划分镜：每个分镜一个知识点，配 1-5 条要点和一句旁白。"+
			"本工具会立即返回真实 artifact_id 与状态；在拿到返回值之前，"+
			"不得声称视频已生成或给出任何下载链接。",
		func(ctx context.Context, in ToolInput) (ToolOutput, error) {
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return ToolOutput{}, err
			}

			spec := Spec{Title: in.Title, Subtitle: in.Subtitle}
			total := 0
			for _, sc := range in.Scenes {
				sec := sc.Seconds
				if sec <= 0 {
					sec = 6
				}
				total += sec
				spec.Scenes = append(spec.Scenes, Scene{
					Heading:   sc.Heading,
					Bullets:   sc.Bullets,
					Narration: sc.Narration,
					Seconds:   sec,
				})
			}

			// 校验失败返回具体原因，模型可据此调整分镜后重试。
			if err := spec.Validate(); err != nil {
				return ToolOutput{}, fmt.Errorf("视频分镜不合法: %w", err)
			}

			a, err := r.Generate(ctx, p.UserID, p.ConversationID, spec)
			if err != nil {
				return ToolOutput{}, fmt.Errorf("视频生成失败: %w", err)
			}

			return ToolOutput{
				ArtifactID:  a.ID,
				Title:       a.Title,
				Status:      a.Status,
				Scenes:      len(spec.Scenes),
				TotalSecs:   total,
				DownloadURL: "/api/v1/artifacts/" + a.ID + "/download",
				StatusURL:   "/api/v1/artifacts/" + a.ID,
				Message: fmt.Sprintf(
					"已提交讲解视频《%s》生成任务（%d 个分镜，约 %d 秒），当前状态 %s。渲染完成后可下载。",
					a.Title, len(spec.Scenes), total, a.Status),
			}, nil
		})
}
