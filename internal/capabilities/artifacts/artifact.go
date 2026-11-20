// Package artifacts 管理 Agent 生成的产物：图解、PPT、讲解视频。
//
// 职责边界：
//   - 产物的元数据持久化（artifacts 表）与文件落盘；
//   - 异步生成任务的状态记录；
//   - 对 Agent 暴露查询工具，对 HTTP 暴露下载与查询接口。
//
// 本包不包含任何渲染逻辑：具体怎么画图、怎么生成 PPTX、怎么编码视频，
// 分别属于 diagram / presentation / video 三个 Capability。
// 这样渲染方案可以独立替换，而产物存储与权限校验只有一份实现。
package artifacts

import "time"

// 产物类型。
const (
	KindDiagram      = "diagram"
	KindPresentation = "presentation"
	KindVideo        = "video"
)

// 产物状态。与 runtime 的任务状态一一对应，保证前端只需理解一套状态机。
const (
	StatusQueued    = "queued"
	StatusRunning   = "running"
	StatusCompleted = "completed"
	StatusFailed    = "failed"
	StatusCanceled  = "canceled"
)

// IsTerminal 判断是否已进入终态。
func IsTerminal(status string) bool {
	switch status {
	case StatusCompleted, StatusFailed, StatusCanceled:
		return true
	}
	return false
}

// Artifact 是一次生成的产物。
//
// File 是相对存储根的路径，不对外暴露宿主机绝对路径：
// 下载必须经过 Handler 的权限校验，不能靠路径拼接绕过。
type Artifact struct {
	ID             string
	UserID         string
	ConversationID string
	Kind           string
	Title          string
	Status         string
	// Progress 0-100，异步任务用
	Progress int
	// File 相对产物根目录的文件名（如 {id}.pptx），完成前为空
	File string
	// MIME 产物 MIME 类型，用于下载响应
	MIME string
	// Size 产物字节数
	Size int64
	// Error 失败原因，成功时为空
	Error string
	// Meta 结构化补充信息（如视频时长、幻灯片页数）
	Meta map[string]any
	// CreatedAt / UpdatedAt 用于列表排序与并发控制
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Done 判断是否完成且文件可用。
func (a *Artifact) Done() bool {
	return a.Status == StatusCompleted && a.File != ""
}
