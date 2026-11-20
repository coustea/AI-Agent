package diagram

import (
	"context"
	"fmt"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/capabilities/artifacts"
	"mentorly/internal/runtime"
)

// ToolName 是对 Agent 暴露的工具名。
const ToolName = "generate_diagram"

// ToolInput 是 generate_diagram 的参数。
type ToolInput struct {
	// Title 图解标题
	Title string `json:"title" jsonschema:"description=图解标题，简洁描述这张图要表达什么，如「HTTP 请求处理流程」"`
	// Mermaid Mermaid 源码，包含图类型声明
	Mermaid string `json:"mermaid" jsonschema:"description=Mermaid 源码，第一行必须是图类型声明，如 flowchart TB 或 sequenceDiagram。节点标签用中文"`
	// Kind 图类型，仅用于元信息展示
	Kind string `json:"kind,omitempty" jsonschema:"description=图类型，可选 flow/sequence/state，默认 flow"`
}

// ToolOutput 是 generate_diagram 的返回。
type ToolOutput struct {
	ArtifactID string `json:"artifact_id"`
	Title      string `json:"title"`
	MIME       string `json:"mime"`
	Size       int64  `json:"size"`
	Nodes      int    `json:"nodes"`
	Edges      int    `json:"edges"`
	// DownloadURL 是前端可直接下载的相对路径
	DownloadURL string `json:"download_url"`
	// Message 给模型看的简短结果说明
	Message string `json:"message"`
}

// NewTool 构造图解生成工具。
//
// 工具只做三件事：校验入参、调用渲染器、返回真实产物引用。
// 不返回任何虚构的下载链接——URL 由产物 ID 拼出，下载时仍要过权限校验。
func NewTool(r *Renderer) (tool.InvokableTool, error) {
	if r == nil {
		return nil, artifacts.ErrUnavailable
	}

	return utils.InferTool(ToolName,
		"把教学主题画成结构清晰的图解（SVG）。当学生需要理解流程、架构、时序或状态流转时使用。"+
			"必须调用本工具真正生成，不能只给 Mermaid 源码让用户自己渲染。"+
			"本工具会立即返回真实 artifact_id 与下载链接；在拿到返回值之前不得编造。",
		func(ctx context.Context, in ToolInput) (ToolOutput, error) {
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return ToolOutput{}, err
			}

			if in.Title == "" {
				in.Title = "图解"
			}

			a, err := r.Generate(ctx, p.UserID, p.ConversationID, Spec{
				Title:   in.Title,
				Kind:    in.Kind,
				Mermaid: in.Mermaid,
			})
			if err != nil {
				return ToolOutput{}, fmt.Errorf("图解生成失败: %w", err)
			}

			return ToolOutput{
				ArtifactID:  a.ID,
				Title:       a.Title,
				MIME:        a.MIME,
				Size:        a.Size,
				Nodes:       intOf(a.Meta["nodes"]),
				Edges:       intOf(a.Meta["edges"]),
				DownloadURL: "/api/v1/artifacts/" + a.ID + "/download",
				Message:     fmt.Sprintf("已生成图解《%s》，包含 %d 个节点、%d 条连线。", a.Title, intOf(a.Meta["nodes"]), intOf(a.Meta["edges"])),
			}, nil
		})
}

func intOf(v any) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	return 0
}
