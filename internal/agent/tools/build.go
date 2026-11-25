// Package tools 独立实现 TutorAgent 的全部外部业务工具，并统一装配为 []tool.BaseTool。
//
// 工具分层（内置工具由 Eino deep.New 与官方 skill 中间件自动注入，本包不重复实现）：
//   - [内置] write_todos / ls / read_file / write_file / edit_file / glob / grep / task / skill
//   - [外部] execute          — 跨平台通用命令执行工具（shell.go；违规拦截由 ToolGuard 中间件负责）
//   - [外部] list_attachments — 按消息顺序列出当前会话实际引用的历史附件索引（list_attachments.go）
//   - [外部] read_attachment  — 校验用户与会话归属后按字符分页读取附件正文（read_attachment.go）
//   - [外部] web_search       — 可选联网搜索（Tavily），未配置凭据时跳过注册（web_search.go）
package tools

import (
	"context"
	"strings"

	"github.com/cloudwego/eino/components/tool"

	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
)

// 外部业务工具名称常量。
const (
	ToolExecute         = "execute"
	ToolReadAttachment  = "read_attachment"
	ToolListAttachments = "list_attachments"
	ToolWebSearch       = "web_search"

	defaultMountWorkspace = "/workspace"
)

// PrincipalFunc 从运行期 context 提取当前已认证的 (userID, conversationID)。
type PrincipalFunc func(ctx context.Context) (userID, conversationID string, err error)

// Config 是统一装配 TutorAgent 全部外部业务工具所需的依赖与配置。
type Config struct {
	Attachments    *attachments.Store
	Conversations  *conversations.Store
	MountWorkspace string
	Principal      PrincipalFunc
	Shell          ShellConfig
	Search         SearchConfig
}

// Build 按顺序装配全部已启用的外部业务工具，并报告可选联网搜索是否已启用。
func Build(cfg Config) (list []tool.BaseTool, searchEnabled bool, err error) {
	readAtt, err := NewReadAttachment(cfg.Attachments, cfg.Principal, cfg.MountWorkspace)
	if err != nil {
		return nil, false, err
	}
	listAtt, err := NewListAttachments(cfg.Attachments, cfg.Conversations, cfg.Principal, cfg.MountWorkspace)
	if err != nil {
		return nil, false, err
	}
	list = []tool.BaseTool{readAtt, listAtt}

	if cfg.Shell.WorkspaceOf != nil {
		sh, err := NewShell(cfg.Shell)
		if err != nil {
			return nil, false, err
		}
		list = append(list, sh)
	}

	searchTool, err := NewWebSearch(cfg.Search)
	if err != nil {
		return nil, false, err
	}
	if searchTool != nil {
		list = append(list, searchTool)
		searchEnabled = true
	}
	return list, searchEnabled, nil
}

// attachmentVirtualPath 返回附件在 Agent 虚拟文件系统中的路径（<mount>/<id><ext>）。
func attachmentVirtualPath(mountWorkspace string, a *attachments.Attachment) string {
	mount := strings.TrimRight(strings.TrimSpace(mountWorkspace), "/")
	if mount == "" {
		mount = defaultMountWorkspace
	}
	return mount + "/" + a.ID + a.Ext
}

// truncate 按 Unicode 字符数截断字符串，避免截断多字节中文字符。
func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n]) + "…"
}
