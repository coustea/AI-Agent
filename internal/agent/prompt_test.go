package agent

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
)

// TestBasePromptNotEmpty 验证静态底座存在且足够精简。
func TestBasePromptNotEmpty(t *testing.T) {
	p := BasePrompt()
	if strings.TrimSpace(p) == "" {
		t.Fatal("tutor.md 不应为空")
	}

	// 计划要求精简底座：不写工具参数说明书（工具用法由 eino Schema 承担）。
	for _, forbidden := range []string{"参数说明", "argumentsInJSON", "JSON Schema"} {
		if strings.Contains(p, forbidden) {
			t.Errorf("静态 Prompt 不应包含工具参数说明：%q", forbidden)
		}
	}

	// 但必须包含导师身份
	if !strings.Contains(p, "辅导员") {
		t.Error("应包含导师身份说明")
	}
}

// TestAssemblePromptZeroEmptyNoise 验证空记忆/空摘要/空工作区都不注入。
func TestAssemblePromptZeroEmptyNoise(t *testing.T) {
	got := AssemblePrompt(PromptInput{
		Base: "底座",
		Now:  "2026-11-20",
		// MemoryDoc / Summary / WorkspaceFiles 全空
	})

	if !strings.Contains(got, "底座") {
		t.Error("应包含底座")
	}
	if !strings.Contains(got, "2026-11-20") {
		t.Error("当前日期应始终注入")
	}

	// 三个可选段落都不应出现
	for _, unwanted := range []string{"关于这位学生", "会话摘要", "工作区文件"} {
		if strings.Contains(got, unwanted) {
			t.Errorf("空内容不应注入 %q 段落", unwanted)
		}
	}
}

// TestAssemblePromptWithContent 验证有内容时对应段落被注入。
func TestAssemblePromptWithContent(t *testing.T) {
	got := AssemblePrompt(PromptInput{
		Base:           "底座",
		Now:            "2026-11-20",
		MemoryDoc:      "## 学习背景\n\n计算机专业",
		Summary:        "已讨论 TCP 三次握手",
		WorkspaceFiles: []string{"notes.md", "demo.go"},
	})

	for _, want := range []string{
		"关于这位学生", "计算机专业",
		"会话摘要", "TCP 三次握手",
		"工作区文件", "/workspace/notes.md", "/workspace/demo.go",
	} {
		if !strings.Contains(got, want) {
			t.Errorf("应包含 %q", want)
		}
	}
}

// fakeAppender 记录 remember 工具写入的内容。
type fakeAppender struct {
	userIDs []string
	notes   []string
	err     error
}

func (f *fakeAppender) AppendPending(_ context.Context, userID, note string) error {
	if f.err != nil {
		return f.err
	}
	f.userIDs = append(f.userIDs, userID)
	f.notes = append(f.notes, note)
	return nil
}

// TestRememberToolRecords 验证工具从 ctx 取 UserID 并写入。
func TestRememberToolRecords(t *testing.T) {
	app := &fakeAppender{}
	tool := NewRememberTool(app)
	if tool == nil {
		t.Fatal("工具不应为 nil")
	}

	ctx := WithScope(context.Background(), Scope{UserID: "user-1", SessionID: "s1"})

	out, err := tool.InvokableRun(ctx, `{"note":"偏好先看代码"}`)
	if err != nil {
		t.Fatalf("InvokableRun: %v", err)
	}
	if !strings.Contains(out, "偏好先看代码") {
		t.Errorf("返回信息应回显内容，实际 %q", out)
	}

	if len(app.userIDs) != 1 || app.userIDs[0] != "user-1" {
		t.Errorf("UserID 应来自 ctx，实际 %v", app.userIDs)
	}
	if len(app.notes) != 1 || app.notes[0] != "偏好先看代码" {
		t.Errorf("note 不符: %v", app.notes)
	}
}

// TestRememberToolRejectsMissingScope 验证缺少用户上下文时拒绝写入。
// 这是权限边界：模型无法通过参数指定他人，也不能在无身份时落库。
func TestRememberToolRejectsMissingScope(t *testing.T) {
	app := &fakeAppender{}
	tool := NewRememberTool(app)

	// 没有 Scope 的 ctx
	if _, err := tool.InvokableRun(context.Background(), `{"note":"x"}`); err == nil {
		t.Fatal("缺少用户上下文时应拒绝写入")
	}
	if len(app.notes) != 0 {
		t.Error("被拒绝时不应发生写入")
	}
}

// TestRememberToolRejectsEmptyNote 验证空 note 被拒绝。
func TestRememberToolRejectsEmptyNote(t *testing.T) {
	app := &fakeAppender{}
	tool := NewRememberTool(app)
	ctx := WithScope(context.Background(), Scope{UserID: "u1"})

	if _, err := tool.InvokableRun(ctx, `{"note":"   "}`); err == nil {
		t.Error("空 note 应被拒绝")
	}
}

// TestRememberToolNilAppender 验证未启用记忆时返回 nil（不被注册）。
func TestRememberToolNilAppender(t *testing.T) {
	if got := NewRememberTool(nil); got != nil {
		t.Error("appender 为 nil 时应返回 nil")
	}
}

// TestRememberToolPropagatesError 验证写入失败向上传递。
func TestRememberToolPropagatesError(t *testing.T) {
	app := &fakeAppender{err: context.DeadlineExceeded}
	tool := NewRememberTool(app)
	ctx := WithScope(context.Background(), Scope{UserID: "u1"})

	if _, err := tool.InvokableRun(ctx, `{"note":"x"}`); err == nil {
		t.Error("写入失败应向上传递")
	}
}

// TestRememberToolInvalidJSON 验证非法参数报错。
func TestRememberToolInvalidJSON(t *testing.T) {
	tool := NewRememberTool(&fakeAppender{})
	ctx := WithScope(context.Background(), Scope{UserID: "u1"})

	if _, err := tool.InvokableRun(ctx, `{bad json`); err == nil {
		t.Error("非法 JSON 应报错")
	}
}

// TestRememberToolInfo 验证工具 Schema 包含必需的 note 参数。
func TestRememberToolInfo(t *testing.T) {
	tool := NewRememberTool(&fakeAppender{})

	info, err := tool.Info(context.Background())
	if err != nil {
		t.Fatalf("Info: %v", err)
	}
	if info.Name != RememberToolName {
		t.Errorf("工具名 = %q, want %q", info.Name, RememberToolName)
	}
	if info.Desc == "" {
		t.Error("应有工具描述")
	}
	if info.ParamsOneOf == nil {
		t.Fatal("应有参数 Schema")
	}

	params, err := info.ParamsOneOf.ToJSONSchema()
	if err != nil {
		t.Fatalf("ToJSONSchema: %v", err)
	}
	raw, err := json.Marshal(params)
	if err != nil {
		t.Fatalf("序列化 Schema: %v", err)
	}
	if !strings.Contains(string(raw), "note") {
		t.Errorf("Schema 应包含 note 参数，实际 %s", raw)
	}
}

// TestScopeRoundTrip 验证 Scope 在 ctx 中的存取。
func TestScopeRoundTrip(t *testing.T) {
	want := Scope{UserID: "u1", SessionID: "s1", Root: "/tmp/ws"}
	ctx := WithScope(context.Background(), want)

	got, ok := ScopeFrom(ctx)
	if !ok {
		t.Fatal("应能取出 Scope")
	}
	if got != want {
		t.Errorf("Scope = %+v, want %+v", got, want)
	}

	// 无 Scope 时应返回 false
	if _, ok := ScopeFrom(context.Background()); ok {
		t.Error("空 ctx 不应有 Scope")
	}
}
