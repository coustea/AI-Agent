# P2 —— bash 工具安全加固设计文档（v3：以可插拔接缝为中心）

> 日期：2026-10-15｜状态：**已实施**（用户批准「不要兼容旧代码，开始实现 P2」）。
> 未回答的 3 个决策点一律采用本文档的推荐项：仅 `PreToolUse` 接缝 / `confirm` 无 UI 时拒绝 / persona 增加约束句。
> 实施结果见文末「8. 实施记录」。
> 取代 `OPTIMIZATION_PLAN.md` 第 3 节（P2 v1）与本文档 v2。
> **v3 的核心修正**：权限是**挂到执行流水线上的可插拔钩子**，既不属于 ReAct 循环，也不属于工具实现。v2 把策略放在 `bash.go` 内部，方向是错的。

---

## 0. 结论摘要

参考实现 `Python/learn-claude-code` 给出的核心范式是：**权限是执行流水线上的一个挂载点，不是循环里的一行 if，也不是工具里的一个检查**。

- s03 把 `check_permission()` 写在循环里 —— 教学过渡态；
- **s04 起把它移出循环，挂到 `PreToolUse` hook 注册表上**，循环只调 `trigger_hooks("PreToolUse", block)`；
- s15 成熟形态沿用该结构，策略逻辑全在 hook 回调里，循环与工具都不感知权限。

本仓当前状态是**两个错误都没有避免**：`bash.go:63-69` 把 5 条黑名单**嵌在工具内部**，而 `tool.Registry.Execute`（`tool.go:71-115`）是一条「校验 → 执行」的直通管线，**没有任何挂载点**。

v3 的设计因此改为两步：

1. **先建接缝**：在 `tool.Registry` 上引入 `PreToolUse` 钩子链（对应参考实现的 `PreToolUse` 事件）。`Registry` 只负责**按序调用**，不感知任何具体策略。
2. **再挂策略**：`bash` 的三档策略（deny/allow/confirm）实现为**一个独立的钩子**，放在 `internal/tool/permission` 包，由 `agent.NewAgent` 在装配期挂上去。

`bash.go` 因此退化为**纯执行器**（零策略代码）；`agent.go` 的 ReAct 循环**一行都不改**（只在装配处多一行挂载）。

---

## 1. 参考实现的权限模型（证据）

### 1.1 三代演进

| 版本 | 形态 | 位置 |
|---|---|---|
| s03 | 三闸门 `deny → 规则 → 审批` | 硬编码在 `agent_loop` 内（`s03_permission/code.py:201-212`） |
| **s04** | 移出循环，挂到 `PreToolUse` | hook 注册表（`s04_hooks/README.zh.md:42`） |
| s15 | 成熟形态，循环与工具均不感知权限 | `s15_integrated_harness/code.py:1797-1830` |

s04 的关键代码（`s04_hooks/README.zh.md:62-78`）：

```python
HOOKS = {"UserPromptSubmit": [], "PreToolUse": [], "PostToolUse": [], "Stop": []}

def register_hook(event, callback):
    HOOKS[event].append(callback)

def trigger_hooks(event, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:   # 返回值非 None → 拦截，短路
            return result
    return None
```

循环侧只留一行（`s04_hooks/README.zh.md:168`）：

```python
blocked = trigger_hooks("PreToolUse", block)
if blocked:
    results.append({... "content": str(blocked)})
    continue
```

**这就是「挂在上去」的确切含义**：循环提供挂载点与调用时机，策略通过注册进入，循环本身不出现任何权限判断。

### 1.2 s15 成熟形态的三处设计

`s15_integrated_harness/code.py:1797-1830`：

1. **deny 优先于一切**：命中硬拒绝表即返回，永不询问；
2. **无法交互 → 拒绝**：非主线程时返回 `interactive approval is unavailable during an asynchronous turn`；
3. **审批默认拒绝**：`[y/N]`，仅 `y`/`yes` 放行。

另有 `mcp_tool_policies` 这种「每工具策略表、未登记默认 confirm」的白名单模型。

### 1.3 参考实现自身的缺陷（v3 予以修正）

| 缺陷 | 证据 | 后果 |
|---|---|---|
| 粗放子串兜底 | `any(kw in cmd for kw in ["rm ", ...])`（`s03_permission/code.py:180-181`） | `echo form data`、`echo firm` 含子串 `"rm "` → 误报 |
| 正则不可移植到 Go | 用了前瞻断言 `(?=\s\|$\|[;&\|()])` | Go 的 `regexp` 是 RE2，**不支持前瞻** |

参考实现自己也声明「这张表使用简单字符串匹配来说明权限闸门的位置，**不能视为完整的安全边界**」（`s03_permission/README.zh.md:42`）。

---

## 2. 本仓的接缝应当落在哪里

现有调用链（`agent.go:375` → `tool.go:71`）：

```
CoreAgent.StreamRun 的 ReAct 循环
        │  tools.Execute(ctx, tc)          ← agent.go:375
        ▼
tool.Registry.Execute(ctx, call)            ← tool.go:71
        │  ① 查表 → ② ValidateArguments → ③ t.Execute
        ▼
builtin.BashTool.Execute                    ← bash.go:52
        │  ✗ 5 条黑名单硬编码在此（bash.go:63-69）
        ▼
exec.CommandContext("bash", "-c", command)
```

**结论**：接缝必须在 `tool.Registry.Execute`。理由：

- 它是**唯一**的工具调度汇聚点，所有工具（含未来新增）都经过它 → 一次挂载，全局生效；
- 它已在 `internal/tool` 包内，`gateway.ToolCall` / `gateway.ToolResult` 就是它的输入输出类型，**无需新增类型依赖**；
- `agent.go` 的循环只调用 `Execute`，因此接缝对循环**完全透明**——这正是不改循环就能加权限的原因。

---

## 3. 设计

### 3.1 接缝：`tool.PreToolUse` + `Registry` 挂载点

新增 `internal/tool/hook.go`：

```go
package tool

// PreToolUse 在工具执行前介入（对应 learn-claude-code 的 PreToolUse hook）。
// 返回非 nil 错误表示阻止本次执行；错误内容将作为观察结果回灌给模型。
type PreToolUse func(ctx context.Context, call gateway.ToolCall) error
```

`Registry` 增加钩子链（`tool.go:21-24`）：

```go
type Registry struct {
	mu       sync.RWMutex
	tools    map[string]Tool
	preHooks []PreToolUse
}

// UsePreToolUse 挂载一个执行前钩子。钩子按挂载顺序依次执行，任一返回错误即短路。
// Registry 只负责按序调用，不感知任何具体策略。
func (r *Registry) UsePreToolUse(h PreToolUse) {
	if h == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.preHooks = append(r.preHooks, h)
}
```

`Execute` 插入调用点（`tool.go:71`）：

```go
func (r *Registry) Execute(ctx context.Context, call gateway.ToolCall) (gateway.ToolResult, error) {
	r.mu.RLock()
	t, ok := r.tools[call.Name]
	hooks := r.preHooks          // 快照后立即释放锁，钩子代码不在锁内执行
	r.mu.RUnlock()

	if !ok { /* 原逻辑不变 */ }

	// ① 执行前钩子链：权限等策略在此挂载；Registry 自身不含任何规则
	for _, h := range hooks {
		if err := h(ctx, call); err != nil {
			return gateway.ToolResult{
				ToolCallID: call.ID,
				Name:       call.Name,
				Content:    err.Error(),
				IsError:    true,
			}, err
		}
	}

	// ② 参数校验（原逻辑）
	// ③ t.Execute（原逻辑）
}
```

**顺序说明（钩子先于参数校验）**：与参考实现一致——钩子看到的是**原始调用**，权限处于最外层。钩子若遇到无法解析的参数应返回 `nil` 放行，交由参数校验拒绝，因此**安全等价且不重复报错**。

**并发说明**：钩子切片受既有 `sync.RWMutex` 保护；`Execute` 在 `RLock` 下**只取快照**，调用发生在锁外，避免在持锁期间执行任意用户代码。

### 3.2 策略：`internal/tool/permission` 包（新增）

策略是**一个独立的钩子**，与 `tool` 包单向依赖（`permission → tool`，无环）：

```go
package permission

// New 返回一个实施 bash 权限策略的执行前钩子。
func New() tool.PreToolUse {
	return func(ctx context.Context, call gateway.ToolCall) error {
		if call.Name != "bash" {
			return nil
		}
		var in builtin.BashInput
		if err := json.Unmarshal(call.Arguments, &in); err != nil {
			return nil // 参数非法，交由 Registry 的参数校验拒绝
		}
		decision, reason := classify(in.Command)
		switch decision {
		case DecisionDeny:
			return fmt.Errorf("command blocked by policy: %s", reason)
		case DecisionConfirm:
			return fmt.Errorf("command requires manual approval: %s "+
				"(no interactive approver is configured)", reason)
		}
		return nil
	}
}
```

同包内 `policy.go` 实现分类（v2 的算法保持不变）：

```go
type Decision int

const (
	DecisionAllow   Decision = iota // 直接执行
	DecisionConfirm                 // 需人工确认；当前阶段无审批 UI → 拒绝
	DecisionDeny                    // 硬拒绝
)

// classify 归一化后依次判定 deny → allow → confirm。
func classify(command string) (Decision, string)
```

三档判定（顺序固定 `deny → allow → confirm`）：

| 档 | 判定依据 | 结果 |
|---|---|---|
| **deny** | 硬拒绝模式：`rm -rf /`、`rm -rf ~`、`mkfs`、`dd if=`、`dd of=/dev/`、`> /dev/sd*`、`sudo`、`shutdown`/`reboot`/`halt`、fork bomb、`chmod -R 777 /` 等（包级 `regexp.MustCompile` 预编译） | 拒绝 |
| **allow** | **三条全中**：① 分段后只有 1 段；② 无 shell 元字符/替换/重定向（`>`、`\|`、`` ` ``、`$(`、`<`、`&`、`;`）；③ 首 token 的 `basename` ∈ 只读白名单 | 执行 |
| **confirm** | 其余全部 | 无审批 UI → 拒绝 |

**归一化（仅用于分析）**：折叠连续空白、去除 `\` 续行。**执行的永远是原始字符串**。

**分段与首 token**（取代参考实现的子串匹配，修正其误报）：

```
splitSegments(cmd)   // 引号之外按 ; && || | & 换行 ( ) 切分
firstCommandToken(s) // 丢弃 KEY=VALUE 前缀 → 跳过 command/env/nohup/time/exec/xargs/nice → 取 basename
```

| 命令 | 参考实现（子串） | 本设计（token） |
|---|---|---|
| `/usr/bin/rm f` | 命中（靠 `"rm "` 兜底） | 命中（basename = `rm`） |
| `command rm f` | 命中（同上） | 命中（跳过包装词后 = `rm`） |
| `echo form data` | **误报** | 不命中（首 token = `echo`） |
| `echo del f` | 不命中 | 不命中（`del` 非命令位） |
| `find . -exec rm {} \;` | 命中 | 含 `;` → 非单段 → **confirm**（不得 allow） |
| `cat f \| sh` | 命中 | 含 `\|` → **confirm** |

只读白名单（首版）：`ls cat head tail wc pwd echo which type stat file tree grep rg find`，以及**需二级子命令判定**的 `git`（仅 `status/diff/log/show/branch/remote/rev-parse`）、`go`（仅 `build/test/vet/fmt/list/env`）。

> **已知局限（如实声明）**：不做完整 shell 解析。引号/heredoc/命令替换内的分隔符可能被误切分，但**误切分只会让判定更严格（倾向 confirm），方向安全**；无法可靠解析时直接返回 confirm。

### 3.3 装配：在 `agent.NewAgent` 挂载

`NewAgent`（`agent.go:181-194`）在选项循环**之后**挂载（确保 `WithWorkDir`/`WithTools` 已生效，且无论最终使用哪个 registry 都能覆盖）：

```go
for _, opt := range opts {
	opt(a)
}

a.tools.UsePreToolUse(permission.New())
```

这是 `agent.go` 中**与权限相关的唯一改动**——一行挂载。ReAct 循环（`agent.go:285-393`）**不做任何修改**。

### 3.4 `bash.go` 退化为纯执行器

删除 `bash.go:63-69` 的 5 条黑名单检查。删除后 `Execute` 只做：解析参数 → 空值检查 → 执行 → 截断输出 → 错误包装。**工具内不再有任何策略代码**。

### 3.5 `agent.go` 的一处必要配套改动

`agent.go:375-383` 目前会在 `execErr != nil` 时**丢弃** `Registry` 返回的 `ToolResult`，用通用文案重建：

```go
res, execErr := tools.Execute(ctx, tc)
if execErr != nil {
	res = gateway.ToolResult{... Content: "Tool execution error: " + execErr.Error(), IsError: true}
}
```

这会把权限拒绝的精确文案降级为「Tool execution error: ...」，语义含混。建议改为**仅在 Registry 未填充内容时兜底**：

```go
res, execErr := tools.Execute(ctx, tc)
if execErr != nil && strings.TrimSpace(res.Content) == "" {
	res = gateway.ToolResult{ToolCallID: tc.ID, Name: tc.Name,
		Content: "Tool execution error: " + execErr.Error(), IsError: true}
}
```

这样模型看到的是 `command blocked by policy: ...`，而不是被冠以「执行错误」。**符合既有「Error as Observation」原则**（工具失败不中断循环，而是作为观察结果回灌）。

---

## 4. 代码落点

| 文件 | 动作 |
|---|---|
| `internal/tool/hook.go` | **新增**：`PreToolUse` 类型定义与文档 |
| `internal/tool/tool.go` | **修改**：`Registry` 增加 `preHooks` 字段 + `UsePreToolUse`；`Execute` 插入钩子调用（`tool.go:71`） |
| `internal/tool/permission/permission.go` | **新增**：`New()` 返回 `tool.PreToolUse` |
| `internal/tool/permission/policy.go` | **新增**：`Decision`、`classify`、归一化、分段、首 token、deny 正则、只读白名单 |
| `internal/tool/permission/policy_test.go` | **新增**：表驱动用例 |
| `internal/tool/builtin/bash.go` | **修改**：删除 `:63-69` 黑名单，退化为纯执行器 |
| `internal/tool/builtin/builtin_test.go` | **修改**：`TestBashTool:255-260` 的「危险命令被拒」用例移除（职责已移交 `permission`），改为验证纯执行语义 |
| `internal/tool/tool_test.go` | **修改/新增**：验证钩子按序执行、返回错误即短路、拒绝时 `ToolResult.IsError == true` |
| `internal/agent/agent.go` | **修改**：装配处挂载钩子（§3.3）；工具错误处理改为不覆盖已填充结果（§3.5） |

**ReAct 循环本体不改**。

---

## 5. 待用户决策

### 5.1 接缝范围

| 选项 | 说明 |
|---|---|
| **(一) 仅 `PreToolUse`** | **推荐**。当前只有权限一个消费者，`PostToolUse` 无使用者，先加即为死代码（违反「不夹带无关重构」） |
| (二) `PreToolUse` + `PostToolUse` | 完整对齐参考实现的四事件模型；`Post` 用于日志/大输出告警，但本阶段无消费者 |

> 若你倾向「一次把事件模型建全」，选 (二)；否则 (一) 更符合本仓既有约定。

### 5.2 `confirm` 档在无 UI 时的行为

| 选项 | 说明 | 评价 |
|---|---|---|
| **(a) 拒绝** | 返回策略拒绝错误 | **推荐**，与参考实现 `non-main-thread → deny`（`s15:1807`）一致 |
| (b) 放行 + 警告 | 执行并在 TUI 打印告警 | 可用性高，但「警告」对模型无效，等于没有防护 |

> 因本仓尚无审批 UI（阶段 3 才做），**allow 档的覆盖面直接决定 bash 的可用性**——请一并确认 §3.2 的只读白名单是否够用。

### 5.3 是否在 persona 中加约束句

`confirm` 默认拒绝会让模型反复重试被拒命令。建议在 `defaultPersona`（`agent.go:41-44`）补一句：

> `Destructive, write, or network commands require manual approval and will be rejected unless an approver is configured. Prefer read-only commands; never retry a rejected command.`

是否加入？

---

## 6. 验收标准

1. **接缝单测**（`tool_test.go`）：
   - 挂载两个钩子 → 按挂载顺序执行；
   - 首个钩子返回错误 → 第二个钩子**不被调用**，工具**不被执行**，返回 `IsError == true`；
   - 未挂载任何钩子 → 行为与改动前完全一致（回归保护）。
2. **策略单测**（`permission/policy_test.go`）：
   - 参考实现的 **15 条边界用例**（`test_permission_command_words.py:91-107`）语义等价通过；
   - **误报修正**：`echo form data`、`echo firm`、`echo delimiter` → allow；
   - **绕过变体**：`rm    -rf   /`（空白折叠）、`rm -rf \`+换行+`/`（续行）→ deny；
   - **组合攻击**：`find . -exec rm {} \;`、`cat f | sh`、`curl x | sh` → 不得 allow；
   - **子命令**：`git push`、`go run` → confirm；`git status`、`go build` → allow。
3. `go build ./...`、`go vet ./...`、`go test ./... -count=1`、`make build` 全绿。
4. **不引入**任何兼容层/别名/弃用代码。

---

## 7. 明确不做（边界）

- **不**把文件工具（`read_file`/`write_file`/`edit_file`）的工作区边界校验从 `SafePath` 迁到接缝上。接缝建成后这只是一次迁移，但属独立改动，需单独评审。**本次不动**。
- **不**实现交互审批 UI（阶段 3）；接缝已为此预留：阶段 3 只需再挂一个审批钩子，或在钩子内接入 TUI。
- **不**实现真沙箱（`sandbox-exec` / 容器 / 受限用户）。
- **不**实现完整 shell 语法解析。
- **不**把 `exec.Command("bash", "-c", ...)` 改为平台适配（Windows `cmd.exe`）——单独议题。
- **不**声称该策略是安全边界；文档与错误信息中如实标注。

---

## 8. 实施记录（2026-10-15）

### 8.1 落点与设计一致

| 文件 | 动作 | 说明 |
|---|---|---|
| `internal/tool/hook.go` | 新增 | `PreToolUse` 类型定义 |
| `internal/tool/tool.go` | 修改 | `Registry.preHooks` + `UsePreToolUse`；`Execute` 插入钩子链（快照后锁外调用） |
| `internal/tool/permission/permission.go` | 新增 | `New()` 返回 `tool.PreToolUse`，仅拦 `bash` |
| `internal/tool/permission/policy.go` | 新增 | `Decision`、`classify`、归一化、分段、首 token、deny 规则、只读白名单 |
| `internal/tool/permission/policy_test.go` | 新增 | 策略表驱动用例 |
| `internal/tool/permission/permission_test.go` | 新增 | 钩子行为用例 |
| `internal/tool/builtin/bash.go` | 修改 | 删除 5 条黑名单，退化为纯执行器 |
| `internal/tool/builtin/builtin_test.go` | 修改 | 「危险命令被拒」改为验证纯执行语义 |
| `internal/tool/tool_test.go` | 修改 | 4 个接缝用例：顺序+短路、放行后执行、先于参数校验看到原始调用、无钩子回归 |
| `internal/agent/agent.go` | 修改 | 装配处挂载钩子；工具错误处理仅在 `res.Content` 为空时兜底；persona 增约束句 |
| `internal/agent/agent_test.go` | 修改 | 新增 `TestCoreAgent_PermissionHook_Mounted` |

**ReAct 循环本体未改**。

### 8.2 实施中的两处补充（设计时未写明，实现时发现必需）

1. **`find` 的危险选项需显式禁止**。§3.2 只写了「`find . -exec rm {} \;` 含 `;` → 非单段 → confirm」，但 `find . -exec rm {} +` 不含任何 shell 元字符，仅靠首 token 白名单会被**误放行**。故新增 `readOnlyForbiddenFlags`，把 `find` 的 `-exec/-execdir/-ok/-okdir/-delete/-fprint/-fprint0/-fprintf/-fls` 一并降级为 confirm。
2. **归一化必须保留换行**。换行是 shell 的命令分隔符；若在归一化阶段一并折叠空白，`echo a<换行>rm -rf /` 会被压成单段并以 `echo` 命中白名单而被放行。故 `normalize` 只折叠**段内**空白，换行原样保留参与分段。

另：`parseCommand` 对命令 basename 做**小写归一**，以对齐参考实现「命令词大小写不敏感」的语义（`RM -RF /` 同样命中 deny）。

### 8.3 验证结果

```
gofmt -l internal/ cmd/ main.go   → 无输出
go build ./...                    → 通过
go vet ./...                      → 通过
go test ./... -count=1            → 全部 ok（含新增 permission 包）
make build                        → 产出 coustea 二进制
```

### 8.4 已知局限（如实声明，与 §3.2 一致）

- 不做完整 shell 解析；引号/heredoc/命令替换内的分隔符可能被误切分，但误切分只会让判定更严格（倾向 confirm）。
- `go test` / `go build` 属白名单，理论上可执行仓库内的任意测试代码；这是白名单设计的既有取舍，非本次引入。
- 该策略**不是安全边界**，只是「避免模型无意间执行破坏性命令」的护栏。

