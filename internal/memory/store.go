package memory

import (
	"strings"
)

// 长期记忆文档的固定二级标题，顺序与 prompts/consolidate.md 保持一致。
var MemorySections = []string{
	"学习背景",
	"长期目标",
	"学习偏好",
	"薄弱知识点",
	"交互约定",
}

// PendingSection 是「待整合」小节的标题。
// remember 工具把模型主动记录的事项追加到这里，下一次整合时并入正式章节。
const PendingSection = "待整合"

// EmptyMemoryDoc 返回一份含全部固定标题的空模板。
func EmptyMemoryDoc() string {
	var b strings.Builder
	for _, s := range MemorySections {
		b.WriteString("## ")
		b.WriteString(s)
		b.WriteString("\n\n")
	}
	return b.String()
}

// StripCodeFence 去掉模型输出可能带的外层代码围栏。
// 模型经常把整段 Markdown 包在 ```markdown ... ``` 里，直接入库会污染渲染。
func StripCodeFence(s string) string {
	t := strings.TrimSpace(s)
	if !strings.HasPrefix(t, "```") {
		return t
	}

	// 去掉起始围栏行（可能带语言标记，如 ```markdown）
	if i := strings.IndexByte(t, '\n'); i >= 0 {
		t = t[i+1:]
	} else {
		// 只有一行 ```xxx，视为空
		return ""
	}

	// 去掉结束围栏
	if idx := strings.LastIndex(t, "```"); idx >= 0 {
		t = t[:idx]
	}

	return strings.TrimSpace(t)
}

// ValidateMemoryDoc 校验整合结果是否可作为记忆文档写入。
//
// 保护策略：模型可能返回空内容或只讲一句话，直接覆盖会丢掉已有记忆。
// 因此要求：非空，且至少包含固定章节中的一个标题。
func ValidateMemoryDoc(content string) bool {
	t := strings.TrimSpace(content)
	if t == "" {
		return false
	}
	for _, sec := range MemorySections {
		if strings.Contains(t, "## "+sec) {
			return true
		}
	}
	return false
}

// TrimToMaxChars 把文档截断到 maxChars 以内，尽量截在行边界，避免切坏 Markdown。
func TrimToMaxChars(content string, maxChars int) string {
	if maxChars <= 0 {
		return content
	}
	runes := []rune(content)
	if len(runes) <= maxChars {
		return content
	}

	cut := string(runes[:maxChars])
	if i := strings.LastIndexByte(cut, '\n'); i > maxChars/2 {
		return strings.TrimSpace(cut[:i])
	}
	return strings.TrimSpace(cut)
}

// PruneEmptySections 剔除空的二级小节，避免空模板白白占用 token。
//
// 规则：若某个 "## 标题" 之后直到下一个 "## " 之前没有任何非空文本，
// 则整节删除（含标题行）。
func PruneEmptySections(content string) string {
	lines := strings.Split(content, "\n")

	type section struct {
		header string
		body   []string
	}

	var (
		sections []section
		preamble []string
		cur      *section
	)

	for _, line := range lines {
		if strings.HasPrefix(strings.TrimSpace(line), "## ") {
			if cur != nil {
				sections = append(sections, *cur)
			}
			cur = &section{header: line}
			continue
		}
		if cur == nil {
			preamble = append(preamble, line)
			continue
		}
		cur.body = append(cur.body, line)
	}
	if cur != nil {
		sections = append(sections, *cur)
	}

	var out []string
	// 保留开头非空内容
	if p := strings.TrimSpace(strings.Join(preamble, "\n")); p != "" {
		out = append(out, p)
	}

	for _, s := range sections {
		if strings.TrimSpace(strings.Join(s.body, "\n")) == "" {
			continue // 空小节整节丢弃
		}
		out = append(out, strings.TrimSpace(s.header))
		out = append(out, strings.TrimSpace(strings.Join(s.body, "\n")))
	}

	return strings.TrimSpace(strings.Join(out, "\n\n"))
}

// HasPending 判断文档的「待整合」小节是否有实际条目。
func HasPending(content string) bool {
	return strings.TrimSpace(PendingContent(content)) != ""
}

// PendingContent 取出「待整合」小节的正文。
func PendingContent(content string) string {
	lines := strings.Split(content, "\n")

	var (
		inPending bool
		buf       []string
	)

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		if strings.HasPrefix(trimmed, "## ") {
			title := strings.TrimSpace(strings.TrimPrefix(trimmed, "## "))
			if title == PendingSection {
				inPending = true
				continue
			}
			if inPending {
				break // 进入下一节，结束收集
			}
			continue
		}

		if inPending {
			buf = append(buf, line)
		}
	}

	return strings.TrimSpace(strings.Join(buf, "\n"))
}

// AppendPending 在「待整合」小节追加一条条目，不存在该小节则创建。
// remember 工具与直接调用都走这里，保证文档结构一致。
func AppendPending(content, note, date string) string {
	entry := "- " + strings.TrimSpace(note)
	if date != "" {
		entry += "（" + date + "）"
	}

	if strings.TrimSpace(content) == "" {
		content = EmptyMemoryDoc()
	}

	lines := strings.Split(content, "\n")

	// 已有「待整合」小节：在该小节末尾插入。
	pendingIdx := -1
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "## ") &&
			strings.TrimSpace(strings.TrimPrefix(trimmed, "## ")) == PendingSection {
			pendingIdx = i
			break
		}
	}

	if pendingIdx >= 0 {
		// 找到该小节结束位置（下一个 "## " 或文件末尾）
		end := len(lines)
		for i := pendingIdx + 1; i < len(lines); i++ {
			if strings.HasPrefix(strings.TrimSpace(lines[i]), "## ") {
				end = i
				break
			}
		}

		// 去掉小节末尾的空行，再追加条目
		insertAt := end
		for insertAt > pendingIdx+1 && strings.TrimSpace(lines[insertAt-1]) == "" {
			insertAt--
		}

		out := make([]string, 0, len(lines)+2)
		out = append(out, lines[:insertAt]...)
		out = append(out, entry, "")
		out = append(out, lines[insertAt:]...)
		return strings.Join(out, "\n")
	}

	// 没有该小节：追加到文档末尾
	base := strings.TrimRight(content, "\n")
	return base + "\n\n## " + PendingSection + "\n" + entry + "\n"
}

// ClearPending 清空「待整合」小节（保留标题），整合成功后调用。
func ClearPending(content string) string {
	lines := strings.Split(content, "\n")

	var (
		out       []string
		inPending bool
	)

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		if strings.HasPrefix(trimmed, "## ") {
			title := strings.TrimSpace(strings.TrimPrefix(trimmed, "## "))
			if title == PendingSection {
				inPending = true
				out = append(out, line)
				continue
			}
			inPending = false
			out = append(out, line)
			continue
		}

		if inPending {
			continue // 丢弃待整合小节内的内容
		}
		out = append(out, line)
	}

	return strings.TrimSpace(strings.Join(out, "\n"))
}
