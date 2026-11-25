package middlewares

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap"

	logutil "mentorly/internal/utils/log"
)

// ErrToolDenied 在工具调用触发高危命令拦截规则时返回。
var ErrToolDenied = errors.New("工具调用被拒绝")

// destructivePatterns 在工具执行前统一拦截跨平台高危命令，给出明确拒绝理由。
var destructivePatterns = []struct{ pattern, reason string }{
	{"rm -rf /", "拒绝执行删除根目录的命令"},
	{"rm -rf ~", "拒绝执行删除用户目录的命令"},
	{"rm -rf /*", "拒绝执行删除根目录的命令"},
	{"sudo", "拒绝执行提权命令"},
	{"mkfs", "拒绝执行格式化文件系统"},
	{"dd if=", "拒绝执行裸设备写入"},
	{"shutdown", "拒绝执行关机命令"},
	{"reboot", "拒绝执行重启命令"},
	{":(){", "拒绝执行 fork 炸弹"},
	{"chmod -r 777 /", "拒绝执行破坏系统权限的命令"},
	{"format ", "拒绝执行格式化磁盘命令"},
	{"rd /s /q c:\\", "拒绝执行删除系统盘目录的命令"},
	{"rmdir /s /q c:\\", "拒绝执行删除系统盘目录的命令"},
	{"del /f /s /q c:\\", "拒绝执行批量删除系统盘文件的命令"},
	{"remove-item -recurse -force c:\\", "拒绝执行删除系统盘目录的命令"},
	{"stop-computer", "拒绝执行关机命令"},
	{"restart-computer", "拒绝执行重启命令"},
	{"diskpart", "拒绝执行磁盘分区命令"},
}

// ToolGuardConfig 是自定义 ToolGuard 中间件的构造参数。
type ToolGuardConfig struct {
	SkillsRoot     string
	MountSkills    string
	MountWorkspace string
	WorkspaceOf    func(context.Context) string
	FatalErrors    []error
	FormatError    func(error) (string, bool)
}

// ToolGuard 按 Eino 官方 ChatModelAgentMiddleware 规范实现的自定义中间件：
// 嵌入 *adk.BaseChatModelAgentMiddleware 继承其余 5 个钩子的默认空实现，
// 仅覆盖全部 4 个 Wrap*ToolCall 钩子：执行前拦截破坏性命令，执行后把可恢复工具错误转为脱敏文本反馈。
type ToolGuard struct {
	*adk.BaseChatModelAgentMiddleware
	skillsRoot     string
	mountSkills    string
	mountWorkspace string
	workspaceOf    func(context.Context) string
	fatalErrors    []error
	formatError    func(error) (string, bool)
}

// 编译期断言：确保 ToolGuard 完整满足 Eino 官方 ChatModelAgentMiddleware 接口。
var _ adk.ChatModelAgentMiddleware = (*ToolGuard)(nil)

// NewToolGuard 构造工具保护中间件，并将 SkillsRoot 规范为绝对路径用于错误脱敏。
func NewToolGuard(cfg ToolGuardConfig) *ToolGuard {
	absSkills := ""
	if strings.TrimSpace(cfg.SkillsRoot) != "" {
		absSkills, _ = filepath.Abs(cfg.SkillsRoot)
	}
	return &ToolGuard{
		BaseChatModelAgentMiddleware: &adk.BaseChatModelAgentMiddleware{},
		skillsRoot:                   absSkills,
		mountSkills:                  cfg.MountSkills,
		mountWorkspace:               cfg.MountWorkspace,
		workspaceOf:                  cfg.WorkspaceOf,
		fatalErrors:                  cfg.FatalErrors,
		formatError:                  cfg.FormatError,
	}
}

// Check 校验 execute 工具命令是否命中跨平台高危模式或尝试修改只读技能目录。
func (g *ToolGuard) Check(name, args string) error {
	if name != "execute" {
		return nil
	}
	cmd := extractCommand(args)
	lower := strings.ToLower(cmd)
	for _, d := range destructivePatterns {
		if strings.Contains(lower, d.pattern) {
			return fmt.Errorf("%w: %s", ErrToolDenied, d.reason)
		}
	}
	// 拦截向 /dev/ 块设备或系统设备写入（放行 >/dev/null）。
	scrubbedDev := strings.NewReplacer("> /dev/null", "", ">/dev/null", "").Replace(lower)
	if strings.Contains(scrubbedDev, "> /dev/") || strings.Contains(scrubbedDev, ">/dev/") {
		return fmt.Errorf("%w: 拒绝直接写入设备文件", ErrToolDenied)
	}
	if g.isSkillsWrite(lower) {
		return fmt.Errorf("%w: 技能目录严格只读，禁止写入或删除", ErrToolDenied)
	}
	return nil
}

// extractCommand 从 execute JSON 参数中提取 command 原文（解决 Windows 反斜杠转义问题），失败时回退原串。
func extractCommand(args string) string {
	var in struct {
		Command string `json:"command"`
	}
	if err := json.Unmarshal([]byte(args), &in); err == nil && in.Command != "" {
		return in.Command
	}
	return args
}

// isSkillsWrite 拦截直接改写/删除技能目录的命令，放行读取与调用技能脚本。
func (g *ToolGuard) isSkillsWrite(lowerCmd string) bool {
	targets := []string{"$skills_dir", "${skills_dir}", "$env:skills_dir", "%skills_dir%", "/skills/"}
	if g.skillsRoot != "" {
		targets = append(targets, strings.ToLower(g.skillsRoot))
		if real, err := filepath.EvalSymlinks(g.skillsRoot); err == nil && real != "" && real != g.skillsRoot {
			targets = append(targets, strings.ToLower(real))
		}
	}
	hitTarget := false
	for _, t := range targets {
		if strings.Contains(lowerCmd, t) {
			hitTarget = true
			break
		}
	}
	if !hitTarget {
		return false
	}
	// 忽略无害的标准错误/黑洞重定向，避免误伤 `python3 "$SKILLS_DIR/..." 2>&1` 等只读执行。
	cleaned := strings.NewReplacer("2>&1", "", ">/dev/null", "", "> /dev/null", "", ">nul", "").Replace(lowerCmd)
	for _, op := range []string{
		">", "rm ", "mv ", "touch ", "tee ", "sed -i", "chmod ", "chown ",
		"del ", "erase ", "rd ", "rmdir ", "remove-item", "set-content", "add-content", "out-file",
	} {
		if strings.Contains(cleaned, op) {
			return true
		}
	}
	return false
}

// recoverError 将可恢复工具错误转为模型反馈；取消、超时、致命错误与中断信号原样透传。
func (g *ToolGuard) recoverError(ctx context.Context, name string, err error) (string, bool) {
	if err == nil || ctx.Err() != nil ||
		errors.Is(err, context.Canceled) ||
		errors.Is(err, context.DeadlineExceeded) {
		return "", false
	}
	for _, fatal := range g.fatalErrors {
		if errors.Is(err, fatal) {
			return "", false
		}
	}
	if _, interrupted := compose.IsInterruptRerunError(err); interrupted {
		return "", false
	}
	if g.formatError != nil {
		if msg, ok := g.formatError(err); ok {
			return msg, true
		}
	}

	sanitized := g.sanitizePaths(ctx, err.Error())
	logutil.FromContext(ctx, nil).Warn("[工具错误已转反馈]", zap.String("tool", name), logutil.Content("错误", sanitized))
	return fmt.Sprintf("工具 %s 执行失败：%s。请检查参数或换用其他方式后继续。", name, sanitized), true
}

// sanitizePaths 将错误文本中的宿主机目录（含软链接真实路径）替换为虚拟挂载点，防止目录结构泄漏给模型。
func (g *ToolGuard) sanitizePaths(ctx context.Context, msg string) string {
	mask := func(s, root, virtual string) string {
		if root == "" || virtual == "" {
			return s
		}
		s = strings.ReplaceAll(s, root, virtual)
		if real, err := filepath.EvalSymlinks(root); err == nil && real != "" && real != root {
			s = strings.ReplaceAll(s, real, virtual)
		}
		return s
	}
	if g.workspaceOf != nil {
		msg = mask(msg, g.workspaceOf(ctx), g.mountWorkspace)
	}
	return mask(msg, g.skillsRoot, g.mountSkills)
}

// precheck 提取工具名并在执行前做高危命令拦截；返回非空 denied 时短路工具调用。
func (g *ToolGuard) precheck(tc *adk.ToolContext, args string) (name, denied string) {
	if tc != nil {
		name = tc.Name
	}
	if err := g.Check(name, args); err != nil {
		denied = "操作被拒绝：" + strings.TrimPrefix(err.Error(), ErrToolDenied.Error()+": ")
	}
	return name, denied
}

// toolTextResult 构造增强型工具的单文本输出结构。
func toolTextResult(text string) *schema.ToolResult {
	return &schema.ToolResult{Parts: []schema.ToolOutputPart{{Type: schema.ToolPartTypeText, Text: text}}}
}

// WrapInvokableToolCall 拦截普通同步工具（InvokableTool）的执行与错误恢复。
func (g *ToolGuard) WrapInvokableToolCall(_ context.Context, next adk.InvokableToolCallEndpoint, tc *adk.ToolContext) (adk.InvokableToolCallEndpoint, error) {
	return func(ctx context.Context, args string, opts ...tool.Option) (string, error) {
		name, denied := g.precheck(tc, args)
		if denied != "" {
			return denied, nil
		}
		res, err := next(ctx, args, opts...)
		if fb, ok := g.recoverError(ctx, name, err); ok {
			return fb, nil
		}
		return res, err
	}, nil
}

// WrapStreamableToolCall 拦截普通流式工具（StreamableTool）的执行与错误恢复。
func (g *ToolGuard) WrapStreamableToolCall(_ context.Context, next adk.StreamableToolCallEndpoint, tc *adk.ToolContext) (adk.StreamableToolCallEndpoint, error) {
	return func(ctx context.Context, args string, opts ...tool.Option) (*schema.StreamReader[string], error) {
		name, denied := g.precheck(tc, args)
		if denied != "" {
			return schema.StreamReaderFromArray([]string{denied}), nil
		}
		sr, err := next(ctx, args, opts...)
		if fb, ok := g.recoverError(ctx, name, err); ok {
			return schema.StreamReaderFromArray([]string{fb}), nil
		}
		return sr, err
	}, nil
}

// WrapEnhancedInvokableToolCall 拦截增强同步工具（EnhancedInvokableTool）的执行与错误恢复。
func (g *ToolGuard) WrapEnhancedInvokableToolCall(_ context.Context, next adk.EnhancedInvokableToolCallEndpoint, tc *adk.ToolContext) (adk.EnhancedInvokableToolCallEndpoint, error) {
	return func(ctx context.Context, args *schema.ToolArgument, opts ...tool.Option) (*schema.ToolResult, error) {
		raw := ""
		if args != nil {
			raw = args.Text
		}
		name, denied := g.precheck(tc, raw)
		if denied != "" {
			return toolTextResult(denied), nil
		}
		res, err := next(ctx, args, opts...)
		if fb, ok := g.recoverError(ctx, name, err); ok {
			return toolTextResult(fb), nil
		}
		return res, err
	}, nil
}

// WrapEnhancedStreamableToolCall 拦截增强流式工具（EnhancedStreamableTool）的执行与错误恢复。
func (g *ToolGuard) WrapEnhancedStreamableToolCall(_ context.Context, next adk.EnhancedStreamableToolCallEndpoint, tc *adk.ToolContext) (adk.EnhancedStreamableToolCallEndpoint, error) {
	return func(ctx context.Context, args *schema.ToolArgument, opts ...tool.Option) (*schema.StreamReader[*schema.ToolResult], error) {
		raw := ""
		if args != nil {
			raw = args.Text
		}
		name, denied := g.precheck(tc, raw)
		if denied != "" {
			return schema.StreamReaderFromArray([]*schema.ToolResult{toolTextResult(denied)}), nil
		}
		sr, err := next(ctx, args, opts...)
		if fb, ok := g.recoverError(ctx, name, err); ok {
			return schema.StreamReaderFromArray([]*schema.ToolResult{toolTextResult(fb)}), nil
		}
		return sr, err
	}, nil
}
