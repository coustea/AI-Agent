package middlewares

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/adk/middlewares/reduction"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
)

func TestClearWriteToolArg(t *testing.T) {
	small := &reduction.ToolDetail{
		ToolArgument: &schema.ToolArgument{Text: `{"file_path":"/workspace/a.txt","content":"hi"}`},
		ToolResult:   &schema.ToolResult{Parts: []schema.ToolOutputPart{{Type: schema.ToolPartTypeText, Text: "ok"}}},
	}
	if res, err := clearWriteToolArg(t.Context(), small); err != nil || res.NeedClear {
		t.Fatalf("小入参不应被清理: res=%+v err=%v", res, err)
	}

	large := &reduction.ToolDetail{
		ToolArgument: &schema.ToolArgument{Text: `{"file_path":"/workspace/big.py","content":"` + strings.Repeat("x", 1024) + `"}`},
		ToolResult:   &schema.ToolResult{Parts: []schema.ToolOutputPart{{Type: schema.ToolPartTypeText, Text: "ok"}}},
	}
	res, err := clearWriteToolArg(t.Context(), large)
	if err != nil || !res.NeedClear {
		t.Fatalf("大入参应被清理: res=%+v err=%v", res, err)
	}
	if !strings.Contains(res.ToolArgument.Text, `"/workspace/big.py"`) || !strings.Contains(res.ToolArgument.Text, `"cleared":true`) || len(res.ToolArgument.Text) > 100 {
		t.Fatalf("清理后的入参不符合预期: %s", res.ToolArgument.Text)
	}
}

func TestToolGuardCheckSanitizeAndFatalPassthrough(t *testing.T) {
	ws, skills := t.TempDir(), t.TempDir()
	errFatal := errors.New("missing principal")
	g := NewToolGuard(ToolGuardConfig{
		SkillsRoot:     skills,
		MountSkills:    "/skills",
		MountWorkspace: "/workspace",
		WorkspaceOf:    func(context.Context) string { return ws },
		FatalErrors:    []error{errFatal},
	})

	if err := g.Check("read_file", `{}`); err != nil {
		t.Fatalf("只读工具不应被拦截: %v", err)
	}
	for _, bad := range []string{
		`{"command":"rm -rf /"}`,
		`{"command":"sudo apt update"}`,
		`{"command":"echo x > /dev/sda"}`,
		`{"command":"rd /s /q C:\\Windows"}`,
		`{"command":"touch \"$SKILLS_DIR/docx/bad.txt\""}`,
		`{"command":"echo bad >> \"$SKILLS_DIR/docx/SKILL.md\""}`,
		fmt.Sprintf(`{"command":"rm -f %q"}`, skills+"/a.md"),
	} {
		if err := g.Check("execute", bad); !errors.Is(err, ErrToolDenied) {
			t.Fatalf("高危或写技能命令应返回 ErrToolDenied (%s): got %v", bad, err)
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

	ep, err := g.WrapInvokableToolCall(t.Context(), func(context.Context, string, ...tool.Option) (string, error) {
		return "", fmt.Errorf("failed in %s and %s", ws, skills)
	}, &adk.ToolContext{Name: "grep"})
	if err != nil {
		t.Fatal(err)
	}
	out, err := ep(t.Context(), "{}")
	if err != nil || strings.Contains(out, ws) || strings.Contains(out, skills) || !strings.Contains(out, "/workspace") || !strings.Contains(out, "/skills") {
		t.Fatalf("路径脱敏异常: out=%q err=%v", out, err)
	}

	fatalEP, err := g.WrapInvokableToolCall(t.Context(), func(context.Context, string, ...tool.Option) (string, error) {
		return "", errFatal
	}, &adk.ToolContext{Name: "grep"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := fatalEP(t.Context(), "{}"); !errors.Is(err, errFatal) {
		t.Fatalf("致命错误应原样透传: got %v", err)
	}
}
