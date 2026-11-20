package memory

import (
	"context"
	"fmt"
	"strings"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"

	"mentorly/internal/runtime"
)

// 工具名。与 Skills 中引用的名称保持一致。
const (
	SearchToolName = "memory_search"
	SaveToolName   = "memory_save"
	DeleteToolName = "memory_delete"
)

// ---------- memory_search ----------

// SearchInput 是 memory_search 参数。
type SearchInput struct {
	Query string `json:"query,omitempty" jsonschema:"description=检索关键词，多个词用空格分隔。留空则返回最近记录的记忆"`
	Limit int    `json:"limit,omitempty" jsonschema:"description=返回条数，1-20，默认 10"`
}

// MemoryItem 是返回给模型的记忆条目。
type MemoryItem struct {
	ID      string `json:"id"`
	Kind    string `json:"kind"`
	Content string `json:"content"`
}

// SearchOutput 是 memory_search 返回。
type SearchOutput struct {
	Count   int          `json:"count"`
	Items   []MemoryItem `json:"items"`
	Message string       `json:"message"`
}

// NewSearchTool 构造记忆检索工具。
func NewSearchTool(s *Store) (tool.InvokableTool, error) {
	if s == nil {
		return nil, fmt.Errorf("记忆存储未配置")
	}

	return utils.InferTool(SearchToolName,
		"检索这位学生的长期记忆（跨会话有效）。在需要了解学生的背景、偏好、目标或薄弱点，"+
			"或学生提到「之前说过」时使用。留空 query 可获取最近的记忆概览。",
		func(ctx context.Context, in SearchInput) (SearchOutput, error) {
			// 用户身份只来自运行上下文，绝不接受模型传入的 user_id。
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return SearchOutput{}, err
			}

			rows, err := s.Search(ctx, p.UserID, in.Query, in.Limit)
			if err != nil {
				return SearchOutput{}, err
			}

			items := make([]MemoryItem, 0, len(rows))
			for _, m := range rows {
				items = append(items, MemoryItem{ID: m.ID, Kind: m.Kind, Content: m.Content})
			}

			msg := fmt.Sprintf("找到 %d 条相关记忆。", len(items))
			if len(items) == 0 {
				msg = "暂无相关记忆。"
			}

			return SearchOutput{Count: len(items), Items: items, Message: msg}, nil
		})
}

// ---------- memory_save ----------

// SaveInput 是 memory_save 参数。
type SaveInput struct {
	Content string `json:"content" jsonschema:"description=记忆内容，一句话说清一件事，不超过 500 字"`
	Kind    string `json:"kind,omitempty" jsonschema:"description=类别：fact（客观事实）/ preference（偏好）/ weakness（薄弱点）/ goal（目标）"`
}

// SaveOutput 是 memory_save 返回。
type SaveOutput struct {
	ID      string `json:"id"`
	Saved   bool   `json:"saved"`
	Message string `json:"message"`
}

// NewSaveTool 构造记忆写入工具。
//
// 只在学生明确要求记住，或明确同意记录时使用——
// 这条约束写在工具描述与 Prompt 两处，因为记忆属于用户隐私边界。
func NewSaveTool(s *Store) (tool.InvokableTool, error) {
	if s == nil {
		return nil, fmt.Errorf("记忆存储未配置")
	}

	return utils.InferTool(SaveToolName,
		"把一条值得长期记住的信息写入学生档案，跨会话生效。"+
			"仅当学生明确要求记住，或明确同意记录时调用。"+
			"不要记录一次性的问答内容，也不要把整段对话搬进来。",
		func(ctx context.Context, in SaveInput) (SaveOutput, error) {
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return SaveOutput{}, err
			}

			content := strings.TrimSpace(in.Content)
			if content == "" {
				return SaveOutput{}, fmt.Errorf("记忆内容不能为空")
			}

			m := &Memory{
				UserID:         p.UserID,
				Kind:           in.Kind,
				Content:        content,
				Source:         "explicit",
				ConversationID: p.ConversationID,
			}
			if err := s.Save(ctx, m); err != nil {
				return SaveOutput{}, err
			}

			return SaveOutput{
				ID:      m.ID,
				Saved:   true,
				Message: "已记住：" + m.Content,
			}, nil
		})
}

// ---------- memory_delete ----------

// DeleteInput 是 memory_delete 参数。
type DeleteInput struct {
	ID string `json:"id" jsonschema:"description=要删除的记忆 ID，先用 memory_search 获取"`
}

// DeleteOutput 是 memory_delete 返回。
type DeleteOutput struct {
	Deleted bool   `json:"deleted"`
	Message string `json:"message"`
}

// NewDeleteTool 构造记忆删除工具。
func NewDeleteTool(s *Store) (tool.InvokableTool, error) {
	if s == nil {
		return nil, fmt.Errorf("记忆存储未配置")
	}

	return utils.InferTool(DeleteToolName,
		"删除一条长期记忆。当学生要求「忘掉」「不要记这个」时使用。"+
			"需要先通过 memory_search 拿到记忆 ID。",
		func(ctx context.Context, in DeleteInput) (DeleteOutput, error) {
			p, err := runtime.MustPrincipal(ctx)
			if err != nil {
				return DeleteOutput{}, err
			}

			if strings.TrimSpace(in.ID) == "" {
				return DeleteOutput{}, fmt.Errorf("记忆 ID 不能为空")
			}

			if err := s.DeleteForUser(ctx, in.ID, p.UserID); err != nil {
				if err == ErrNotFound {
					return DeleteOutput{}, fmt.Errorf("未找到该记忆，或它不属于当前用户")
				}
				return DeleteOutput{}, err
			}

			return DeleteOutput{Deleted: true, Message: "已删除该条记忆。"}, nil
		})
}

// Tools 返回全部记忆工具。
func Tools(s *Store) ([]tool.BaseTool, error) {
	search, err := NewSearchTool(s)
	if err != nil {
		return nil, err
	}
	save, err := NewSaveTool(s)
	if err != nil {
		return nil, err
	}
	del, err := NewDeleteTool(s)
	if err != nil {
		return nil, err
	}
	return []tool.BaseTool{search, save, del}, nil
}
