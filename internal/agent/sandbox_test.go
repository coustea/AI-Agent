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
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"
)

func TestWorkspaceMountRouting(t *testing.T) {
	ws, skills := t.TempDir(), t.TempDir()
	w := &workspace{skillsRoot: skills}
	ctx := withPrincipal(t.Context(), Principal{UserID: "u", Workspace: ws})
	cases := []struct {
		path  string
		write bool
		want  string
		err   error
	}{
		{path: "", want: ws},
		{path: "   ", want: ws},
		{path: "/workspace", want: ws},
		{path: "notes/a.md", write: true, want: filepath.Join(ws, "notes", "a.md")},
		{path: `/workspace/notes\a.md`, want: filepath.Join(ws, "notes", "a.md")},
		{path: "/skills", want: skills},
		{path: "/skills/docx/SKILL.md", want: filepath.Join(skills, "docx", "SKILL.md")},
		{path: "/skills/docx/SKILL.md", write: true, err: ErrReadOnly},
		{path: "/workspace/../skills/a.md", write: true, err: ErrReadOnly},
		{path: "/workspace-other/a.md", err: ErrPathDenied},
		{path: "/skills-other/a.md", err: ErrPathDenied},
		{path: "/outside/a.md", err: ErrPathDenied},
		{path: "../outside/a.md", err: ErrPathDenied},
	}
	for _, tc := range cases {
		t.Run(fmt.Sprintf("%s/write=%t", tc.path, tc.write), func(t *testing.T) {
			got, err := w.mapPath(ctx, tc.path, tc.write)
			if got != tc.want || !errors.Is(err, tc.err) {
				t.Fatalf("mapPath = %q, %v; want %q, %v", got, err, tc.want, tc.err)
			}
		})
	}
	ctx = withPrincipal(t.Context(), Principal{UserID: "u"})
	if _, err := w.mapPath(ctx, "/workspace/a.md", false); !errors.Is(err, ErrPathDenied) {
		t.Fatalf("missing workspace must be denied: %v", err)
	}
}

func TestOfficialBackendIsolation(t *testing.T) {
	ws, skills := t.TempDir(), t.TempDir()
	b, err := newWorkspace(ws, skills)
	if err != nil {
		t.Fatal(err)
	}
	ctx := withPrincipal(t.Context(), Principal{UserID: "u", ConversationID: "c", Workspace: ws})
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
		Handlers: []adk.ChatModelAgentMiddleware{newToolGuard(skills, 0)},
	})
	if err != nil {
		t.Fatal(err)
	}
	a := &Agent{agent: native, log: zap.NewNop()}
	res := a.Run(ctx, &RunContext{
		principal: Principal{UserID: "u", ConversationID: "c", Workspace: ws},
		Messages:  []*schema.Message{schema.UserMessage("查找课件材料")},
	}, nil)
	if res.Status != StatusCompleted || res.Message.Content != "找到文件" {
		t.Fatalf("agent failed to recover: status=%s content=%q err=%v", res.Status, res.Message.Content, res.runErr)
	}
}

func TestGuardRecoversToolErrorsAndPreservesFatalErrors(t *testing.T) {
	ws, skills := t.TempDir(), t.TempDir()
	g := newToolGuard(skills, 60*time.Millisecond)
	if err := g.Check("read_file", `{}`); err != nil {
		t.Fatalf("只读工具不应被拦截: %v", err)
	}
	for _, bad := range []string{
		`rm -rf /`,
		`{"command":"", "note":"sudo"}`,
		`{"command":"sudo`,
		`{"command":"rm -rf /"}`,
		`{"command":"sudo apt update"}`,
		`{"command":"echo x > /dev/sda"}`,
		`{"command":"rd /s /q C:\\Windows"}`,
		`{"command":"touch \"$SKILLS_DIR/docx/bad.txt\""}`,
		fmt.Sprintf(`{"command":"rm -f %q"}`, skills+"/a.md"),
	} {
		if err := g.Check("execute", bad); !errors.Is(err, errToolDenied) {
			t.Fatalf("高危或写技能命令应返回 errToolDenied (%s): got %v", bad, err)
		}
	}
	for _, okCmd := range []string{
		`{"command":"python3 \"$SKILLS_DIR/docx/scripts/run.py\" >/dev/null 2>&1"}`,
		`{"command":"cat \"$SKILLS_DIR/docx/SKILL.md\""}`,
	} {
		if err := g.Check("execute", okCmd); err != nil {
			t.Fatalf("只读技能命令不应被误拦 (%s): got %v", okCmd, err)
		}
	}

	ctx := withPrincipal(t.Context(), Principal{UserID: "u", ConversationID: "c", Workspace: ws})
	recoverable := []struct {
		tool string
		err  error
	}{
		{"grep", fmt.Errorf("ripgrep failed with exit code 2: rg: %s/bad: No such file", skills)},
		{"edit_file", fmt.Errorf("old_string not found in %s/a.js", ws)},
		{"skill", errors.New("failed to get skill: skill not found: diagram")},
		{"write_file", errors.New("failed to unmarshal arguments in json: unexpected EOF")},
		{"web_search", fmt.Errorf("搜索请求失败: %w", context.DeadlineExceeded)},
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

	// 验证 task 子代理独立超时：父 ctx 存活时中止子任务并转为可恢复文本反馈。
	taskEP, err := g.WrapInvokableToolCall(ctx, func(callCtx context.Context, _ string, _ ...tool.Option) (string, error) {
		<-callCtx.Done()
		return "", callCtx.Err()
	}, &adk.ToolContext{Name: "task"})
	if err != nil {
		t.Fatal(err)
	}
	taskOut, err := taskEP(ctx, `{}`)
	if err != nil || !strings.Contains(taskOut, "子代理执行超时") {
		t.Fatalf("task 局部超时未自愈恢复: out=%q err=%v", taskOut, err)
	}

	// 验证父 ctx 剩余预算不足时跳过启动子代理，预留主代理收尾时间。
	tightParent, tightCancel := context.WithTimeout(ctx, 10*time.Second)
	defer tightCancel()
	tightOut, err := taskEP(tightParent, `{}`)
	if err != nil || !strings.Contains(tightOut, "剩余时间不足") {
		t.Fatalf("紧预算未拦截 task 启动: out=%q err=%v", tightOut, err)
	}

	// 验证缺少身份及父上下文已取消/超时仍原样向上传递。
	epNoPrincipal, err := g.WrapInvokableToolCall(ctx, func(context.Context, string, ...tool.Option) (string, error) {
		return "", errNoPrincipal
	}, &adk.ToolContext{Name: "grep"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := epNoPrincipal(ctx, "{}"); !errors.Is(err, errNoPrincipal) {
		t.Fatalf("身份缺失错误不应被吞掉: got %v", err)
	}

	canceledCtx, cancel := context.WithCancel(ctx)
	cancel()
	expiredCtx, expireCancel := context.WithDeadline(ctx, time.Now().Add(-time.Millisecond))
	defer expireCancel()
	for _, tc := range []struct {
		pctx context.Context
		want error
	}{
		{canceledCtx, context.Canceled},
		{expiredCtx, context.DeadlineExceeded},
		{canceledCtx, errors.Join(context.Canceled, &workspacePathError{"/workspace/notes.md", fs.ErrNotExist})},
	} {
		ep, err := g.WrapInvokableToolCall(tc.pctx, func(context.Context, string, ...tool.Option) (string, error) {
			return "", tc.want
		}, &adk.ToolContext{Name: "grep"})
		if err != nil {
			t.Fatal(err)
		}
		if _, err := ep(tc.pctx, "{}"); !errors.Is(err, tc.want) {
			t.Fatalf("父上下文终止错误不应被吞掉: got %v, want %v", err, tc.want)
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
	sh := newShell(0, skills)

	calls := []schema.ToolCall{
		{ID: "ok-1", Type: "function", Function: schema.FunctionCall{Name: "execute", Arguments: `{"command":"echo hello-mentorly"}`}},
		{ID: "bad-1", Type: "function", Function: schema.FunctionCall{Name: "execute", Arguments: `{"command":"sudo whoami"}`}},
		{ID: "bad-2", Type: "function", Function: schema.FunctionCall{Name: "execute", Arguments: `{"command":"touch \"$SKILLS_DIR/bad.txt\""}`}},
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
		Name:         "test",
		ChatModel:    m,
		Backend:      b,
		Shell:        sh,
		MaxIteration: 5,
		Handlers:     []adk.ChatModelAgentMiddleware{newToolGuard(skills, 0)},
	})
	if err != nil {
		t.Fatal(err)
	}
	a := &Agent{agent: native, log: zap.NewNop()}
	res := a.Run(ctx, &RunContext{
		principal: Principal{UserID: "u", ConversationID: "c", Workspace: ws},
		Messages:  []*schema.Message{schema.UserMessage("测试 execute 工具")},
	}, nil)
	if res.Status != StatusCompleted || res.Message.Content != "已执行并完成校验" {
		t.Fatalf("端到端执行失败: status=%s content=%q err=%v", res.Status, res.Message.Content, res.runErr)
	}
	if _, err := os.Stat(filepath.Join(skills, "bad.txt")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("技能目录被意外写入: %v", err)
	}
}

func TestWorkspaceBoundedReadAndWrite(t *testing.T) {
	ws, skills := t.TempDir(), t.TempDir()
	b, err := newWorkspace(ws, skills)
	if err != nil {
		t.Fatal(err)
	}
	ctx := withPrincipal(t.Context(), Principal{UserID: "u", ConversationID: "c", Workspace: ws})

	var lines []string
	for i := 1; i <= 260; i++ {
		lines = append(lines, fmt.Sprintf("line-%d", i))
	}
	if err := os.WriteFile(filepath.Join(ws, "big.txt"), []byte(strings.Join(lines, "\n")), 0o600); err != nil {
		t.Fatal(err)
	}
	got, err := b.Read(ctx, &adkfs.ReadRequest{FilePath: "/workspace/big.txt", Offset: 1, Limit: 2000})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(got.Content, "line-201") || !strings.Contains(got.Content, "line-200") {
		t.Fatalf("Read 未钳制到 %d 行", maxReadLines)
	}

	tooManyLines := strings.Repeat("x\n", maxWriteLines+5)
	err = b.Write(ctx, &adkfs.WriteRequest{FilePath: "/workspace/huge.js", Content: tooManyLines})
	if !errors.Is(err, ErrWriteTooLarge) {
		t.Fatalf("超行数写入应返回 ErrWriteTooLarge: %v", err)
	}
	if msg, ok := formatWorkspaceError(err); !ok || !strings.Contains(msg, "edit_file") {
		t.Fatalf("formatWorkspaceError 缺少自愈建议: ok=%v msg=%q", ok, msg)
	}
}

func TestSubAgentIsolationAndTranscriptCleanliness(t *testing.T) {
	// task 需为主代理预留 30s 收尾，父预算须大于该余量才会启动子代理。
	ctx, cancel := context.WithTimeout(t.Context(), 60*time.Second)
	defer cancel()
	ws, skills := t.TempDir(), t.TempDir()
	if err := os.WriteFile(filepath.Join(ws, "notes.md"), []byte("SECRET_NOTE_CONTENT"), 0o600); err != nil {
		t.Fatal(err)
	}

	m := &retryTestModel{stream: func(_ context.Context, input []*schema.Message) (*schema.StreamReader[*schema.Message], error) {
		sys := ""
		if len(input) > 0 && input[0].Role == schema.System {
			sys = input[0].Content
		}
		last := input[len(input)-1]

		if strings.Contains(sys, "只读资料与工作区检索子代理") {
			if last.Role == schema.Tool {
				if !strings.Contains(last.Content, "SECRET_NOTE_CONTENT") {
					return nil, fmt.Errorf("explorer 未读到工作区文件: %q", last.Content)
				}
				return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("摘要：notes.md 包含目标笔记", nil)}), nil
			}
			return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("", []schema.ToolCall{{
				ID: "sub-read-1", Type: "function", Function: schema.FunctionCall{Name: "read_file", Arguments: `{"file_path":"/workspace/notes.md"}`},
			}})}), nil
		}

		if last.Role == schema.Tool && last.ToolCallID == "task-1" {
			if !strings.Contains(last.Content, "摘要：notes.md") {
				return nil, fmt.Errorf("主代理未收到子代理摘要: %q", last.Content)
			}
			return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("已通过子代理核实笔记内容", nil)}), nil
		}
		return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("", []schema.ToolCall{{
			ID: "task-1", Type: "function", Function: schema.FunctionCall{Name: "task", Arguments: `{"subagent_type":"explorer","description":"读取 /workspace/notes.md 并返回摘要"}`},
		}})}), nil
	}}

	a, err := New(ctx, AgentDeps{
		Model: m,
		Config: Config{
			WorkspaceDir: ws,
			SkillsDir:    skills,
			ThinkingMode: thinkingOff,
		},
		Log: zap.NewNop(),
	})
	if err != nil {
		t.Fatal(err)
	}

	res := a.Run(ctx, &RunContext{
		principal: Principal{UserID: "u", ConversationID: "c", Workspace: ws},
		Messages:  []*schema.Message{schema.UserMessage("帮我查一下 notes.md")},
	}, nil)
	if res.Status != StatusCompleted || res.Message.Content != "已通过子代理核实笔记内容" {
		t.Fatalf("子代理委派失败: status=%s content=%q err=%v", res.Status, res.Message.Content, res.runErr)
	}
	if len(res.ToolCalls) != 1 || res.ToolCalls[0] != "task" {
		t.Fatalf("主代理 ToolCalls 被子代理污染: %v", res.ToolCalls)
	}
	for _, msg := range res.Transcript {
		if msg.Role == schema.Tool && msg.ToolCallID == "sub-read-1" {
			t.Fatalf("子代理内部工具输出泄漏到了主代理 Transcript: %+v", res.Transcript)
		}
	}
}
