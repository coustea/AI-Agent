package presentation

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/capabilities/artifacts"
	"mentorly/internal/runtime"
)

// ToolName 是对 Agent 暴露的工具名。
const ToolName = "generate_presentation"

// ToolInput 是 generate_presentation 的参数。
type ToolInput struct {
	Title    string       `json:"title" jsonschema:"description=课件标题，概括主题，如「Go 并发模型入门」"`
	Subtitle string       `json:"subtitle,omitempty" jsonschema:"description=副标题，可留空"`
	Slides   []SlideInput `json:"slides" jsonschema:"description=幻灯片列表，每页包含标题与要点"`
}

// SlideInput 是单页幻灯片参数。
type SlideInput struct {
	Title   string   `json:"title" jsonschema:"description=本页标题，一句话"`
	Bullets []string `json:"bullets" jsonschema:"description=本页要点，3-6 条，每条不超过 160 字"`
	Note    string   `json:"note,omitempty" jsonschema:"description=讲稿备注，可留空"`
}

// ToolOutput 是 generate_presentation 的返回。
type ToolOutput struct {
	ArtifactID  string `json:"artifact_id"`
	Title       string `json:"title"`
	Status      string `json:"status"`
	Slides      int    `json:"slides"`
	DownloadURL string `json:"download_url"`
	StatusURL   string `json:"status_url"`
	Message     string `json:"message"`
}

// NewTool 构造课件生成工具。
//
// 返回的 artifact_id 与 status 都是真实值：文件此时可能仍在生成中，
// 因此必须如实返回 queued/running，由前端轮询 status_url。
func NewTool(r *Renderer) (tool.InvokableTool, error) {
	if r == nil {
		return nil, artifacts.ErrUnavailable
	}

	return utils.InferTool(ToolName,
		"生成可下载的 PowerPoint 教学课件（.pptx）。当学生要求「做一份课件/PPT/幻灯片」时，"+
			"必须调用本工具真正生成，不能只用文字描述大纲。"+
			"先规划大纲：每页一个主题，3-6 条要点，要点简洁。"+
			"本工具会立即返回真实 artifact_id 与状态；在拿到返回值之前，"+
			"不得声称课件已生成或给出任何下载链接。",
		func(ctx context.Context, in ToolInput) (ToolOutput, error) {
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return ToolOutput{}, err
			}

			spec := Spec{Title: in.Title, Subtitle: in.Subtitle}
			for _, s := range in.Slides {
				spec.Slides = append(spec.Slides, Slide{
					Title:   s.Title,
					Bullets: s.Bullets,
					Note:    s.Note,
				})
			}

			// 校验失败直接返回具体原因，让模型有机会自行修正重试。
			if err := spec.Validate(); err != nil {
				return ToolOutput{}, fmt.Errorf("课件规格不合法: %w", err)
			}

			a, err := r.Generate(ctx, p.UserID, p.ConversationID, spec)
			if err != nil {
				return ToolOutput{}, fmt.Errorf("课件生成失败: %w", err)
			}

			return ToolOutput{
				ArtifactID:  a.ID,
				Title:       a.Title,
				Status:      a.Status,
				Slides:      len(spec.Slides) + 1,
				DownloadURL: "/api/v1/artifacts/" + a.ID + "/download",
				StatusURL:   "/api/v1/artifacts/" + a.ID,
				Message: fmt.Sprintf(
					"已提交课件《%s》生成任务（共 %d 页），当前状态 %s。生成完成后可下载。",
					a.Title, len(spec.Slides)+1, a.Status),
			}, nil
		})
}
