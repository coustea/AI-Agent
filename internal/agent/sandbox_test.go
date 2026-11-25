package agent

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/cloudwego/eino/adk"
	adkfs "github.com/cloudwego/eino/adk/filesystem"
	"github.com/cloudwego/eino/adk/prebuilt/deep"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"

	"mentorly/internal/agent/middlewares"
	"mentorly/internal/agent/tools"
)

func TestOfficialBackendIsolation(t *testing.T) {
	ws, skills := t.TempDir(), t.TempDir()
	b, err := newWorkspace(ws, skills)
	if err != nil {
		t.Fatal(err)
	}
	ctx := withPrincipal(t.Context(), &runPrincipal{UserID: "u", ConversationID: "c", Workspace: ws})
	if err := b.Write(ctx, &adkfs.WriteRequest{FilePath: "/workspace/a.md", Content: "before"}); err != nil {
		t.Fatal(err)
	}
	if err := b.Edit(ctx, &adkfs.EditRequest{FilePath: "/workspace/a.md", OldString: "before", NewString: "after"}); err != nil {
		t.Fatal(err)
	}
	content, err := b.Read(ctx, &adkfs.ReadRequest{FilePath: "/workspace/a.md"})
	if err != nil || !strings.Contains(content.Content, "after") {
		t.Fatalf("read: %+v %v", content, err)
	}
	rows, err := b.GlobInfo(ctx, &adkfs.GlobInfoRequest{Path: "/workspace", Pattern: "/workspace/*.md"})
	if err != nil || len(rows) != 1 || rows[0].Path != "/workspace/a.md" {
		t.Fatalf("glob paths: %+v %v", rows, err)
	}
	matches, err := b.GrepRaw(ctx, &adkfs.GrepRequest{Path: "/workspace", Pattern: "after"})
	if err != nil || len(matches) != 1 || matches[0].Path != "/workspace/a.md" {
		t.Fatalf("grep paths: %+v %v", matches, err)
	}
	if err := b.Write(ctx, &adkfs.WriteRequest{FilePath: "/skills/a.md", Content: "bad"}); !errors.Is(err, ErrReadOnly) {
		t.Fatalf("readonly: %v", err)
	}
	if err := b.Write(t.Context(), &adkfs.WriteRequest{FilePath: "/workspace/a.md"}); !errors.Is(err, errNoPrincipal) {
		t.Fatalf("missing identity: %v", err)
	}
	foreign := t.TempDir()
	if err := os.WriteFile(filepath.Join(foreign, "secret.md"), []byte("foreign-secret"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(foreign, filepath.Join(ws, "foreign")); err != nil {
		t.Fatal(err)
	}
	content, err = b.Read(ctx, &adkfs.ReadRequest{FilePath: "/workspace/foreign/secret.md"})
	if !errors.Is(err, ErrPathDenied) || content != nil {
		t.Fatalf("symlink escape: %+v %v", content, err)
	}
	if err := b.Write(ctx, &adkfs.WriteRequest{FilePath: "/workspace/foreign/new.md"}); !errors.Is(err, ErrPathDenied) {
		t.Fatalf("symlink write: %v", err)
	}
	missing := filepath.Join(foreign, "missing.md")
	if err := os.Symlink(missing, filepath.Join(ws, "dangling.md")); err != nil {
		t.Fatal(err)
	}
	if err := b.Write(ctx, &adkfs.WriteRequest{FilePath: "/workspace/dangling.md", Content: "bad"}); !errors.Is(err, fs.ErrNotExist) {
		t.Fatalf("dangling symlink write: %v", err)
	}
	if _, err := os.Stat(missing); !errors.Is(err, fs.ErrNotExist) {
		t.Fatalf("write touched target outside workspace: %v", err)
	}
}

func TestFilesystemPathErrorsThroughRunner(t *testing.T) {
	ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
	defer cancel()
	ws, skills := t.TempDir(), t.TempDir()
	b, err := newWorkspace(ws, skills)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(ws, "notes.md"), []byte("placeholder"), 0600); err != nil {
		t.Fatal(err)
	}
	calls := []schema.ToolCall{
		{ID: "grep-path", Type: "function", Function: schema.FunctionCall{Name: "grep", Arguments: `{"pattern":"placeholder","path":"/skills/pptx/node_modules/pptxgenjs"}`}},
		{ID: "grep-denied", Type: "function", Function: schema.FunctionCall{Name: "grep", Arguments: `{"pattern":"placeholder","path":"/outside","output_mode":"count"}`}},
		{ID: "ls", Type: "function", Function: schema.FunctionCall{Name: "ls", Arguments: `{"path":"/workspace/missing"}`}},
		{ID: "glob", Type: "function", Function: schema.FunctionCall{Name: "glob", Arguments: `{"pattern":"*.md","path":"/workspace/missing"}`}},
		{ID: "read", Type: "function", Function: schema.FunctionCall{Name: "read_file", Arguments: `{"file_path":"/workspace/missing"}`}},
		{ID: "write", Type: "function", Function: schema.FunctionCall{Name: "write_file", Arguments: `{"file_path":"/skills/no-write.md","content":"bad"}`}},
		{ID: "edit-miss", Type: "function", Function: schema.FunctionCall{Name: "edit_file", Arguments: `{"file_path":"/workspace/notes.md","old_string":"not-present","new_string":"x"}`}},
		{ID: "bad-json", Type: "function", Function: schema.FunctionCall{Name: "read_file", Arguments: `{"file_path":`}},
	}
	want := map[string]string{
		"grep-path":   "/skills/pptx/node_modules/pptxgenjs",
		"grep-denied": "路径不可访问",
		"ls":          "/workspace/missing",
		"glob":        "/workspace/missing",
		"read":        "/workspace/missing",
		"write":       "目录只读",
		"edit-miss":   "edit_file",
		"bad-json":    "read_file",
	}
	m := &retryTestModel{stream: func(_ context.Context, input []*schema.Message) (*schema.StreamReader[*schema.Message], error) {
		results := make(map[string]string)
		for _, msg := range input {
			if msg.Role == schema.Tool {
				results[msg.ToolCallID] = msg.Content
			}
		}
		if len(results) == 0 {
			return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("", calls)}), nil
		}
		for id, fragment := range want {
			result := results[id]
			if !strings.Contains(result, fragment) || !strings.Contains(result, "请") || strings.Contains(result, ws) || strings.Contains(result, skills) {
				return nil, fmt.Errorf("unexpected tool result for %s: %q", id, result)
			}
		}
		if result, ok := results["retry-grep"]; ok {
			if !strings.HasSuffix(result, "\n/workspace/notes.md") {
				return nil, fmt.Errorf("unexpected result for corrected grep: %q", result)
			}
			return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("找到文件", nil)}), nil
		}
		return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("", []schema.ToolCall{{ID: "retry-grep", Type: "function", Function: schema.FunctionCall{Name: "grep", Arguments: `{"pattern":"placeholder","path":"/workspace"}`}}})}), nil
	}}
	native, err := deep.New(ctx, &deep.Config{
		Name: "test", ChatModel: m, Backend: b, MaxIteration: 5,
		Handlers: []adk.ChatModelAgentMiddleware{middlewares.NewToolGuard(toolGuardConfig(skills))},
	})
	if err != nil {
		t.Fatal(err)
	}
	a := &Agent{agent: native, log: zap.NewNop()}
	res := a.Run(ctx, &RunContext{
		principal: &runPrincipal{UserID: "u", ConversationID: "c", Workspace: ws},
		Messages:  []*schema.Message{schema.UserMessage("查找课件材料")},
	}, nil)
	if res.Status != StatusCompleted || res.Message.Content != "找到文件" {
		t.Fatalf("agent failed to recover: status=%s content=%q err=%v", res.Status, res.Message.Content, res.runErr)
	}
	recorded := make(map[string]string)
	for _, msg := range res.Transcript {
		if msg.Role == schema.Tool {
			recorded[msg.ToolCallID] = msg.Content
		}
	}
	if len(recorded) != len(calls)+1 || !strings.HasSuffix(recorded["retry-grep"], "\n/workspace/notes.md") {
		t.Fatalf("missing tool results in transcript: %v", recorded)
	}
	for id, fragment := range want {
		if !strings.Contains(recorded[id], fragment) {
			t.Errorf("tool result %s not recorded: %q", id, recorded[id])
		}
	}
}

func TestGuardRecoversToolErrorsAndPreservesFatalErrors(t *testing.T) {
	ws, skills := t.TempDir(), t.TempDir()
	g := middlewares.NewToolGuard(toolGuardConfig(skills))
	if err := g.Check("read_file", `{}`); err != nil {
		t.Fatalf("只读工具不应被拦截: %v", err)
	}
	if err := g.Check("execute", `{"command":"rm -rf /"}`); err == nil {
		t.Fatal("破坏性命令应被拦截")
	}

	ctx := withPrincipal(t.Context(), &runPrincipal{UserID: "u", ConversationID: "c", Workspace: ws})

	// 1. 可恢复工具错误（含非路径错与 JSON 解析错）应转为脱敏文本反馈，不泄露宿主机路径。
	recoverable := []struct {
		tool string
		err  error
	}{
		{"grep", fmt.Errorf("ripgrep failed with exit code 2: rg: %s/bad: No such file", skills)},
		{"edit_file", fmt.Errorf("old_string not found in %s/a.js", ws)},
		{"skill", errors.New("failed to get skill: skill not found: diagram")},
		{"write_file", errors.New("failed to unmarshal arguments in json: unexpected EOF")},
	}
	for _, tc := range recoverable {
		ep, err := g.WrapInvokableToolCall(ctx, func(context.Context, string, ...tool.Option) (string, error) {
			return "", tc.err
		}, &adk.ToolContext{Name: tc.tool})
		if err != nil {
			t.Fatal(err)
		}
		out, err := ep(ctx, "{}")
		if err != nil {
			t.Fatalf("%s 可恢复错误不应中断运行: %v", tc.tool, err)
		}
		if !strings.Contains(out, tc.tool) || strings.Contains(out, ws) || strings.Contains(out, skills) {
			t.Fatalf("%s 反馈异常或泄露宿主机路径: %q", tc.tool, out)
		}
	}

	// Streamable 与 EnhancedInvokable 钩子同样能将可恢复错误转为文本反馈。
	streamEP, err := g.WrapStreamableToolCall(ctx, func(context.Context, string, ...tool.Option) (*schema.StreamReader[string], error) {
		return nil, errors.New("stream tool boom")
	}, &adk.ToolContext{Name: "execute"})
	if err != nil {
		t.Fatal(err)
	}
	sr, err := streamEP(ctx, "{}")
	if err != nil {
		t.Fatalf("streamable 可恢复错误不应中断运行: %v", err)
	}
	chunk, _ := sr.Recv()
	sr.Close()
	if !strings.Contains(chunk, "stream tool boom") {
		t.Fatalf("streamable 反馈内容不符: %q", chunk)
	}

	enhEP, err := g.WrapEnhancedInvokableToolCall(ctx, func(context.Context, *schema.ToolArgument, ...tool.Option) (*schema.ToolResult, error) {
		return nil, errors.New("enhanced boom")
	}, &adk.ToolContext{Name: "read_file"})
	if err != nil {
		t.Fatal(err)
	}
	res, err := enhEP(ctx, &schema.ToolArgument{Text: "{}"})
	if err != nil || res == nil || len(res.Parts) == 0 || !strings.Contains(res.Parts[0].Text, "enhanced boom") {
		t.Fatalf("enhanced 反馈异常: res=%+v err=%v", res, err)
	}

	// 2. 致命错误（取消、超时、身份缺失）必须原样透传，绝不能吞掉。
	for _, want := range []error{
		context.Canceled,
		context.DeadlineExceeded,
		errNoPrincipal,
		errors.Join(context.Canceled, &workspacePathError{"/workspace/notes.md", fs.ErrNotExist}),
	} {
		ep, err := g.WrapInvokableToolCall(ctx, func(context.Context, string, ...tool.Option) (string, error) {
			return "", want
		}, &adk.ToolContext{Name: "grep"})
		if err != nil {
			t.Fatal(err)
		}
		if _, err := ep(ctx, "{}"); !errors.Is(err, want) {
			t.Fatalf("致命错误不应被吞掉: got %v, want %v", err, want)
		}
	}
}

func TestExecuteToolThroughRunnerWithToolGuard(t *testing.T) {
	ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
	defer cancel()

	ws, skills := t.TempDir(), t.TempDir()
	b, err := newWorkspace(ws, skills)
	if err != nil {
		t.Fatal(err)
	}
	sh, err := tools.NewShell(tools.ShellConfig{SkillsDir: skills, WorkspaceOf: WorkspaceDir})
	if err != nil {
		t.Fatal(err)
	}

	calls := []schema.ToolCall{
		{ID: "ok-1", Type: "function", Function: schema.FunctionCall{Name: tools.ToolExecute, Arguments: `{"command":"echo hello-mentorly"}`}},
		{ID: "bad-1", Type: "function", Function: schema.FunctionCall{Name: tools.ToolExecute, Arguments: `{"command":"sudo whoami"}`}},
		{ID: "bad-2", Type: "function", Function: schema.FunctionCall{Name: tools.ToolExecute, Arguments: `{"command":"touch \"$SKILLS_DIR/bad.txt\""}`}},
	}
	m := &retryTestModel{stream: func(_ context.Context, input []*schema.Message) (*schema.StreamReader[*schema.Message], error) {
		results := make(map[string]string)
		for _, msg := range input {
			if msg.Role == schema.Tool {
				results[msg.ToolCallID] = msg.Content
			}
		}
		if len(results) == 0 {
			return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("", calls)}), nil
		}
		if !strings.Contains(results["ok-1"], "hello-mentorly") {
			return nil, fmt.Errorf("正常命令输出异常: %q", results["ok-1"])
		}
		if !strings.Contains(results["bad-1"], "操作被拒绝") || !strings.Contains(results["bad-2"], "操作被拒绝") {
			return nil, fmt.Errorf("高危或写技能命令未被 ToolGuard 拦截: bad-1=%q bad-2=%q", results["bad-1"], results["bad-2"])
		}
		return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("已执行并完成校验", nil)}), nil
	}}

	native, err := deep.New(ctx, &deep.Config{
		Name:      "test",
		ChatModel: m,
		Backend:   b,
		ToolsConfig: adk.ToolsConfig{
			ToolsNodeConfig: compose.ToolsNodeConfig{Tools: []tool.BaseTool{sh}},
		},
		MaxIteration: 5,
		Handlers:     []adk.ChatModelAgentMiddleware{middlewares.NewToolGuard(toolGuardConfig(skills))},
	})
	if err != nil {
		t.Fatal(err)
	}
	a := &Agent{agent: native, log: zap.NewNop()}
	res := a.Run(ctx, &RunContext{
		principal: &runPrincipal{UserID: "u", ConversationID: "c", Workspace: ws},
		Messages:  []*schema.Message{schema.UserMessage("测试自研 execute 工具")},
	}, nil)
	if res.Status != StatusCompleted || res.Message.Content != "已执行并完成校验" {
		t.Fatalf("端到端执行失败: status=%s content=%q err=%v", res.Status, res.Message.Content, res.runErr)
	}
	if _, err := os.Stat(filepath.Join(skills, "bad.txt")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("技能目录被意外写入: %v", err)
	}
}
