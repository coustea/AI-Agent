// Package agent 的工具安全守卫与局部错误自愈中间件（toolGuard）。
//
// 职责：
//   - 执行前预检（Check）：拦截 execute 中的高危破坏性命令与对只读技能目录的写入/删除；
//   - 子任务预算控制：为 task 工具施加独立子超时（min(taskTimeout, 整轮剩余-30s)），
//     防止子代理耗尽主代理收尾交付时间；
//   - 执行后自愈（recoverError）：将可由模型修正的普通工具错误、文件沙箱错误与工具局部超时
//     翻译为脱敏文本反馈给模型；仅父上下文取消/超时、身份缺失（errNoPrincipal）与 Eino 中断控制流向上传播。
//
// 并发安全：toolGuard 仅持有不可变的 skillsDir 与 taskTimeout，可跨主代理、子代理与并发会话共享。
package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	"strings"
	"time"

	"github.com/cloudwego/eino/adk"
	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
	"go.uber.org/zap"

	logutil "mentorly/internal/utils/log"
)

const (
	// parentFinishReserve 为主代理留出收尾汇总窗口；剩余时间低于此值时拒绝新启子代理。
	parentFinishReserve = 30 * time.Second
	minSubTaskBudget    = 5 * time.Second
)

// 高危命令黑名单：用于尽早拦截常见破坏性操作（注意：字符串预检并非 OS 级进程沙箱）。
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

type toolGuard struct {
	*adk.BaseChatModelAgentMiddleware
	skillsDir   string
	taskTimeout time.Duration
}

var _ adk.ChatModelAgentMiddleware = (*toolGuard)(nil)

// newToolGuard 构造共享守卫；skillsDir 归一化为绝对路径供命令预检与错误路径脱敏复用。
func newToolGuard(skillsDir string, taskTimeout time.Duration) *toolGuard {
	absSkills, _ := filepath.Abs(skillsDir)
	return &toolGuard{
		BaseChatModelAgentMiddleware: &adk.BaseChatModelAgentMiddleware{},
		skillsDir:                    absSkills,
		taskTimeout:                  taskTimeout,
	}
}

// Check 预检 execute 命令；普通文件工具的路径与只读权限由 workspace.mapPath 负责。
func (g *toolGuard) Check(name, args string) error {
	if name != "execute" {
		return nil
	}
	var in struct {
		Command string `json:"command"`
	}
	cmd := args
	if err := json.Unmarshal([]byte(args), &in); err == nil && in.Command != "" {
		cmd = in.Command
	}
	lower := strings.ToLower(cmd)
	for _, d := range destructivePatterns {
		if strings.Contains(lower, d.pattern) {
			return fmt.Errorf("%w: %s", errToolDenied, d.reason)
		}
	}
	// 放行常规丢弃输出到 /dev/null，拦截向其他设备文件的直接写入。
	scrubbedDev := strings.NewReplacer("> /dev/null", "", ">/dev/null", "").Replace(lower)
	if strings.Contains(scrubbedDev, "> /dev/") || strings.Contains(scrubbedDev, ">/dev/") {
		return fmt.Errorf("%w: 拒绝直接写入设备文件", errToolDenied)
	}
	if g.isSkillsWrite(lower) {
		return fmt.Errorf("%w: 技能目录严格只读，禁止写入或删除", errToolDenied)
	}
	return nil
}

// isSkillsWrite 识别同时提及技能目录（环境变量/虚拟路径/物理路径及其真实软链路径）与写操作符号的命令。
func (g *toolGuard) isSkillsWrite(lowerCmd string) bool {
	targets := []string{"$skills_dir", "${skills_dir}", "$env:skills_dir", "%skills_dir%", MountSkills + "/"}
	if g.skillsDir != "" {
		targets = append(targets, strings.ToLower(g.skillsDir))
		if real, err := filepath.EvalSymlinks(g.skillsDir); err == nil && real != "" && real != g.skillsDir {
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

// recoverError 将可修正错误转成模型反馈。
// 关键不变量：只检查父上下文 ctx.Err() != nil，而非 errors.Is(err, context.DeadlineExceeded)，
// 从而允许工具内部局部超时（如 web_search、task、SSE 空闲超时）自愈，同时保证整轮超时或用户取消仍立即中止。
func (g *toolGuard) recoverError(ctx context.Context, name string, err error) (string, bool) {
	if err == nil || ctx.Err() != nil || errors.Is(err, errNoPrincipal) {
		return "", false
	}
	if _, interrupted := compose.IsInterruptRerunError(err); interrupted {
		// 保留 Eino 中断控制流语义，不能将其吞掉变成普通工具成功输出。
		return "", false
	}
	if msg, ok := formatWorkspaceError(err); ok {
		return msg, true
	}
	sanitized := g.sanitizePaths(ctx, err.Error())
	logutil.FromContext(ctx, nil).Warn("[工具错误已转反馈]", zap.String("tool", name), logutil.Content("错误", sanitized))
	return fmt.Sprintf("工具 %s 执行失败：%s。请检查参数或换用其他方式后继续。", name, sanitized), true
}

// sanitizePaths 将错误文本中的物理工作区与技能目录替换为虚拟路径，防止泄露宿主机目录结构。
func (g *toolGuard) sanitizePaths(ctx context.Context, msg string) string {
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
	if p, err := PrincipalFrom(ctx); err == nil {
		msg = mask(msg, p.Workspace, MountWorkspace)
	}
	return mask(msg, g.skillsDir, MountSkills)
}

// WrapInvokableToolCall 在每次工具调用外层依次执行：命令预检 -> task 子超时预算 -> 执行 -> 错误自愈。
func (g *toolGuard) WrapInvokableToolCall(_ context.Context, next adk.InvokableToolCallEndpoint, tc *adk.ToolContext) (adk.InvokableToolCallEndpoint, error) {
	return func(ctx context.Context, args string, opts ...tool.Option) (string, error) {
		var name string
		if tc != nil {
			name = tc.Name
		}
		if err := g.Check(name, args); err != nil {
			return "操作被拒绝：" + strings.TrimPrefix(err.Error(), errToolDenied.Error()+": "), nil
		}

		callCtx := ctx
		var cancel context.CancelFunc
		if name == "task" && g.taskTimeout > 0 {
			budget := g.taskTimeout
			if dl, ok := ctx.Deadline(); ok {
				remaining := time.Until(dl) - parentFinishReserve
				if remaining < minSubTaskBudget {
					return "当前整轮剩余时间不足以启动子代理，请直接基于已有信息完成汇总交付。", nil
				}
				budget = min(budget, remaining)
			}
			callCtx, cancel = context.WithTimeout(ctx, budget)
			defer cancel()
		}

		res, err := next(callCtx, args, opts...)
		if err != nil && name == "task" && ctx.Err() == nil && cancel != nil && errors.Is(callCtx.Err(), context.DeadlineExceeded) {
			logutil.FromContext(ctx, nil).Warn("[子代理超时已转反馈]", zap.Duration("timeout", g.taskTimeout))
			return "子代理执行超时，已中止该子任务。请直接基于当前已有信息继续完成交付，勿重复委派相同宽泛任务。", nil
		}
		if fb, ok := g.recoverError(ctx, name, err); ok {
			return fb, nil
		}
		return res, err
	}, nil
}
