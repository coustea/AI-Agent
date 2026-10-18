# Tide 系统加固设计方案（第二轮评审问题修复）

> 基线：HEAD = `b2f5e03`（"系统重构：全面清理规范代码、修复配置分裂与状态中断缺陷并加固安全闸门"）。
> 本文只做设计，不含代码改动。实施分四批，每批独立验收、独立提交。
> 遵循仓库约定：不为旧实现保留兼容层/别名；本地单用户场景不做并发协调设计；全部模型统一 OpenAI Chat Completions 协议。

---

## 〇、现状核对（b2f5e03 已修 / 本方案对准的残余）

| 上轮编号 | 当前状态 | 结论依据（HEAD 实查） |
|---|---|---|
| P0-1 中断补齐 ToolResult | ✅ 已修 | `loop.go:235-310` 三处分支均补齐取消结果 |
| P1-1 Gate 2 引号/xargs/find | ✅ 部分已修 | 正则已支持 `"'\x60` 前缀、`xargs`、`find -delete`；新增 5 条测试 |
| P1-1 解释器/命令替换/mv | ❌ 残余 | `python3 -c "shutil.rmtree(...)"`、`$(rm -rf x)` 仍放行 → 本方案 D3 |
| P1-2 reasoning_content 回灌 | ❌ 未修 | `wire.go:89-105` 仍无条件出站，且 assistant+ToolCalls 时发空串 → D1 |
| P1-3 零超时零 recover | ❌ 未修 | 生产代码 grep 无一处 `WithTimeout`/`recover()` → D2 |
| P1-4 SafePath 软链穿透 | ❌ 未修 | 仍只 `Abs/Clean` → D4 |
| P2-1 装配顺序 | ❌ 未修 | `NewFromConfig` 仍先 `WithDefaultTools()` → D5 |
| P2-2 日志写放大 | ❌ 未修 | `recordEvent` 每事件全量重写 `latest.json`、0644 → D6 |
| P2-3 只按条数裁剪 | ❌ 未修 | 固定 40 条 → D7 |
| P2-4 每 delta 全量重渲染 | ❌ 未修 | `renderChatMessages` 全量重建 → D8 |
| P2-5 currentAPIKey 全局单值 | ❌ 未修 | 6 处手工清空 → D12 |
| P2-6 退出不取消/审批残留 | ❌ 未修 | 但 `cmd.Cancel` 进程组回收已完备，只缺出口接线 → D9 |
| P2-7 落盘策略归属 agent | ❌ 未修 | → D10 |
| P2-8 Router 死路径 | ❌ 未修 | **生产代码零调用方**（实查 grep），可整体删除 → D11 |
| P2-9 llamacpp 恒就绪 | ❌ 未修 | → D11 |
| P3-1 Gate 1 误伤 | ❌ 未修 | `Contains("rm -rf /")` 仍硬拒 `rm -rf /tmp/x` → D3 |

---

## 批次一：可用性（D1 / D2 / D9）

### D1 出站剥离 reasoning_content（P1-2）

**问题**：`toWireMessages`（`wire.go:89-105`）把记忆里的思维链写回请求体；按 DeepSeek 文档输入含 `reasoning_content` 即 400。更糟的是 `:101-105`：assistant 带 ToolCalls 时还会显式发送 `"reasoning_content": ""`。

**方案**：出站一律剥离，字段从 wire 结构体上删除（不留兼容）：

- `wireMsg` 删除 `ReasoningContent` 字段；`toWireMessages` 删除两处赋值逻辑。
- 入站解析链路不动：`wireChunk.Delta.ReasoningContent`、`ChatResponse.ReasoningContent`、记忆层保存、TUI 展示、Trace 记录全部保留。
- 结果：`reasoning_content` 的数据流变为严格单向 —— 上游 → 本地展示/存档，永不出站。

**涉及文件**：`internal/gateway/wire.go`、`internal/gateway/gateway_test.go`。

**验收**：
- 新增测试 `TestBuildRequestPayload_StripsReasoningContent`：构造含 `ReasoningContent` 的 assistant 历史 + 带 ToolCalls 的 assistant 消息，`buildRequestPayload` 后 unmarshal 到 `[]map[string]any`，断言任何 message 都不存在 `reasoning_content` 键（覆盖"空串也被发送"的场景）。
- 现有 4 厂商流式解析测试全绿。

**风险**：无。个别厂商兼容层可能接受该字段回传，删除后行为只会更符合规范。

---

### D2 全链路超时与 panic 兜底（P1-3）

**问题**：一条 `sleep 100000`、一次 TLS 握手挂死、一个工具 panic，分别导致整轮永久挂起 / 整个 TUI 进程崩溃。

**方案**：四个独立点位，各自小而闭环：

1. **bash 默认超时**（`bash.go`）
   - `BashInput` 增加 `timeout_ms *int64`（可选）；Schema 同步声明（"optional, default 120000, max 600000"）。
   - `Execute` 内：`timeoutMs` 缺省 120000，夹取到 `[1000, 600000]`；`ctx, cancel := context.WithTimeout(ctx, d)` 后传入 `createShellCmd`。
   - 超时触发时 `exec.CommandContext` 走已配置的 `cmd.Cancel`（负 PID SIGKILL 杀进程组），错误文案明确标注 `bash: command timed out after Xms`。
   - 注意区分：`ctx.Err() == context.DeadlineExceeded`（自身超时）返回超时错误；`ctx.Err() == context.Canceled`（用户中断）沿用现有 `return ctx.Err()`。

2. **HTTP 传输超时**（`gateway.go`）
   - 弃用 `http.DefaultClient`，构造带 `Transport` 的 client：`net.Dialer{Timeout: 10s}` 的 `DialContext`、`TLSHandshakeTimeout: 10s`、`ResponseHeaderTimeout: 120s`。
   - SSE 整体兜底：`ChatStream` 内 `ctx, cancel := context.WithTimeout(ctx, 10*time.Minute)` + `defer cancel()`。不做流内逐 chunk 空闲超时——本地单用户，粗粒度兜底足够，细粒度需侵入连接层，收益不成比例（明确取舍）。

3. **agentLoop goroutine recover**（`loop.go` `Run` 的派生 goroutine）
   - 顶部 `defer func() { if r := recover(); r != nil { turnErr 置为 panic 错误; sendEvent(EventError) } }()`，保证 `outCh` 必然走既有 `defer close` 正常关闭、`running` 标志复位。

4. **工具级 recover**（`tool.go` `Registry.Execute`）
   - `t.Execute` 外包 `defer recover()`，panic 转为 `IsError=true` 的 ToolResult（内容 `tool panicked: <v>`），单工具崩溃不再击穿整轮。

**涉及文件**：`bash.go`、`proc_unix.go`（不动，仅依赖）、`gateway.go`、`loop.go`、`tool/tool.go` 及对应测试。

**验收**：
- `TestBashTool_Timeout`：`sleep 5` + `timeout_ms=300`，断言 1s 内返回且错误含 `timed out`。
- `TestRegistryExecute_PanicRecovery`：注册 panic 工具，断言得到 IsError 结果而非崩溃。
- `TestAgentRun_PanicInLoop`：注入 panic hook，断言收到 `EventError` 且通道关闭、可再次 `Run`。
- `TestBashTool_Timeout_KillsProcessGroup`（可选，Unix）：超时后 `pgrep` 验证无残留子进程。

**风险**：10 分钟流式上限对超长生成（大仓库分析）可能偏紧——上限值实施时提为常量便于调整；默认 120s bash 超时对 `go build` 大仓可能偏紧——文档与 Schema 中写明可由模型按需传参覆盖。

---

### D9 退出清理与审批残留（P2-6）

**问题**：`/exit`、`Ctrl+D`、`tea.Quit` 出口不调 `m.cancel()`；正在跑的 bash（已 `Setpgid` 脱离父进程组）在主进程退出后继续运行；中断路径只调 cancel 不清 `pendingPerm`，残留审批态吞按键。

**前提**（已实查）：`cmd.Cancel` 负 PID SIGKILL 已完备——只要 cancel 被调用，进程组就会被收割。问题纯粹是"没人调用"。

**方案**：
- `app.go` 新增 `func (m *TideApp) shutdown()`：① `m.cancel()`；② 遍历 `m.pendingPerm` 向每个 chan 发 `DecisionDeny` 并清空 map（审批 UI 若在等待，立即以"会话结束"收敛）。
- 所有退出出口（`/exit` 命令、`Ctrl+D`、`Esc` 确认退出、`tea.Quit` 返回前）统一先执行 `m.shutdown()`，再 `tea.Quit`。
- 中断路径（`Ctrl+C` 中断当前轮）同样改为调用一个 `interruptTurn()`：cancel + 清 pendingPerm（与 shutdown 共用清理逻辑，只是不退出）。

**涉及文件**：`internal/tui/app.go`、`chat.go`、`command.go`。

**验收**：
- 手工用例：启动长 `sleep` 工具调用 → `/exit` → `ps` 确认无残留 bash/sleep 进程。
- 审批卡片弹出时 `/exit`：审批卡消失、进程退出、无 goroutine 泄漏报错。
- 单测：模拟 pendingPerm 有挂起项时 shutdown，断言全部收到 Deny。

---

## 批次二：安全（D3 / D4）

### D3 权限闸门：命令规范化 + Gate 1 正则化（P1-1 残余 + P3-1）

**问题**：
- Gate 2 是字面正则表，`python3 -c "import shutil; shutil.rmtree('x')"`、`$(rm -rf x)` 命令替换、`eval` 包装全部绕过。
- Gate 1 用 `Contains("rm -rf /")`，把 `rm -rf /tmp/x` 硬拒绝且不可审批（误伤）。

**设计原则**：Gate 2 的职责不是"精确判定危险"，而是**"宁可多审批"**——无法静态判定的命令一律升级为审批；配合既有会话级信任（AllowSession）把打扰控制在一次。本地单用户场景下，误报成本 = 按一次"允许"，漏报成本 = 数据损失，不对称明显。

**方案分两层**：

**A. Gate 1 硬拒绝表正则化**（替换 `Contains` 字符串表）：

```go
var hardDenyPatterns = []*regexp.Regexp{
    // rm 任何形式作用于根或根下通配（放行 rm -rf /tmp/x —— 它会落到 Gate 2 走审批）
    `(?i)(?:^|[;&|()\n"'\x60])\s*rm\s+(?:-{1,2}[a-zA-Z]+\s+)*+(?:/(?:\s|\*|$)|/\*)`,
    `(?i)(?:^|[;&|()\n"'\x60])\s*(?:sudo|shutdown|reboot|mkfs)\b`,
    `(?i)(?:^|[;&|()\n"'\x60])\s*dd\s+[^|]*\bif=`,
    `(?:>|>>)\s*/dev/(?:sd|disk|nvme)`,
    `:\(\)\s*\{\s*:\|:&\s*\}\s*;:`,
}
```

`WithHardDenyList` 选项语义随之变更为"追加正则"；默认表内置不可清空。

**B. Gate 2 命令规范化管线**（`permission` 包新增 `normalize.go`）：

```
输入原始 command：
1. 引号感知切分：按 ; && || | 换行 切段（不进入引号内部），得到候选段列表
2. 每段：剥离前导环境变量赋值（FOO=bar）与前导包装动词白名单（env、nohup、timeout N、nice、command）
3. 若首 token ∈ {sh,bash,zsh,dash,ksh} 且带 -c：提取引号内整段内容 → 递归回步骤 1
4. 若首 token == eval：取剩余参数拼接 → 递归回步骤 1
5. 命令替换检测：段内出现 $(...) 或反引号，且替换体内含危险动词集合
   {rm, rmdir, unlink, shred, dd, mkfs, shutdown, reboot, kill, chmod, chown, mv, curl, wget, python*, perl, ruby, node}
   任意一个 → 判定"无法静态判定"，needsApproval
6. 解释器内联执行：首 token ∈ {python*, perl, ruby, node, php} 且参数含 -c/-e → needsApproval
7. 每个叶子段跑现有正则规则表（destructiveWord / findDelete / gitDangerous / ... 不变）
8. 覆盖重定向：解析 `> path` / `>> path` 目标（非 /dev/* 设备），stat 目标存在且位于工作区内 → needsApproval
   （覆盖已有文件才是破坏；新建文件与 write_file 工具行为等价，放行）
```

实现为一个纯函数 `analyzeCommand(cmd string) (leafSegments []string, undecidable bool, redirectedTargets []string)`，与决策逻辑解耦，全部规则表驱动、可单测。

**明确不纳入**（取舍说明）：`mv` 单独出现不触发审批——mv 是可恢复操作且日常高频，纳入会造成持续打扰；其风险面（配合 `>` 覆盖、配合软链逃逸）已分别被规则 8 和 D4 覆盖。

**涉及文件**：`internal/permission/permission.go`（重写 Gate 1/调用点）、新增 `normalize.go`、`permission_test.go` 大幅扩充。

**验收**（表驱动用例，全部进测试）：

| 命令 | 期望 |
|---|---|
| `python3 -c "import shutil; shutil.rmtree('x')"` | 审批 |
| `echo $(rm -rf ~/data)` | 审批（命令替换含危险动词） |
| `eval "git reset --hard"` | 审批 |
| `nohup rm -rf ./build &` | 审批（剥离 nohup 后命中 rm） |
| `rm -rf /tmp/x` | **审批**（原为硬拒绝误伤） |
| `rm -rf /`、`rm -rf /*` | 硬拒绝（正则命中根） |
| `go build ./... > build.log 2>&1`（build.log 不存在） | 放行 |
| `echo x > main.go`（main.go 存在） | 审批 |
| `go test ./... > /dev/null` | 放行 |
| 现有全部用例（含 b2f5e03 新增 5 条） | 不回归 |

**风险**：规范化切分器是新的代码面（约 100~150 行），引号嵌套的极端 case 可能漏判——用规则 5 的"无法判定即审批"兜底；测试用例覆盖嵌套引号、转义引号。

---

### D4 SafePath 符号链接解析 + 路径判定统一（P1-4 + P3-2）

**问题**：`SafePath` 只 `Abs/Clean`，工作区内一条指向 `~` 的软链即可越界读写；且工作区判定逻辑在 5 处重复实现（`permission.go`、`safe_path.go`、`memory.ProjectDir`、各工具构造器、`prompt.go`），规则易漂移。

**方案**：

1. **新建 `internal/fsutil` 包**，提供唯一实现：

```go
// ResolveInWorkspace 判定 target 是否位于 workDir 或 ~/.tide 之内。
// 解析链：Abs → 对"最近存在的祖先目录"做 EvalSymlinks → 拼回不存在尾部 → 前缀判定。
// workDir 自身也先 EvalSymlinks（macOS /tmp → /private/tmp 经典陷阱）。
func ResolveInWorkspace(workDir, target string) (abs string, inside bool)
```

   - 已存在路径：直接 `EvalSymlinks`。
   - 不存在路径（write_file 新建场景）：沿父目录链向上找到最近存在的祖先，`EvalSymlinks` 后拼回剩余尾部。
   - `~/.tide` 白名单与现状保持一致。

2. **改造调用方，删除重复实现**：
   - `builtin.SafePath` → 薄封装 `fsutil.ResolveInWorkspace`（保留函数名与错误语义，内部一行转发）。
   - `permission.isPathEscapingWorkspace` → 同样改为转发，删除约 30 行重复逻辑。
   - `memory.ProjectDir` / `prompt.go` 的路径拼接属"目录构造"而非"边界判定"，保持现状（不属于同一职责），但在 D5 的 WorkDirRef 统一取值。

3. **TOCTOU 说明**：EvalSymlinks 与实际 open 之间存在竞态窗口，本地单用户、非对抗场景下接受（与 Gate 2 同一威胁模型）。

**涉及文件**：新增 `internal/fsutil/fsutil.go` + 测试；`safe_path.go`、`permission.go`、相应测试。

**验收**：
- `ln -s ~/.ssh ./evil` 后 `read_file ./evil/id_rsa` 拒绝；`write_file ./evil/pwn` 拒绝。
- 不存在路径 `write_file ./normal/new.go`（./normal 为普通目录）放行。
- 父目录软链：`ln -s /etc ./etc-link` 后 `write_file ./etc-link/x` 拒绝（祖先 EvalSymlinks 生效）。
- macOS 临时目录：workDir 为 `/tmp/xxx` 软链形态时正常工作。

---

## 批次三：结构与性能（D5 / D6 / D7 / D8 / D10 / D11）

### D5 装配顺序：WorkDir 共享引用（P2-1）

**问题**：`WithDefaultTools` 在构造时把 workDir 固化进 6 个工具实例，之后 `WithWorkDir` 只改 `a.workDir` 与 `permission.workDir`，导致工具沙箱与权限判定指向不同目录（当前只是潜伏）。`WithDefaultTools(workDir...)` 可选参数本身是绕行补丁。

**方案**：工具不再持有 workDir 值，持有共享引用：

```go
// internal/tool/builtin/workdir.go
type WorkDirRef struct { mu sync.RWMutex; dir string }
func NewWorkDirRef(dir string) *WorkDirRef
func (r *WorkDirRef) Get() string   // 空 dir 时回退 os.Getwd()
func (r *WorkDirRef) Set(dir string)
```

- `NewAgent` 创建 `ref := NewWorkDirRef(wd)`，存入 CoreAgent。
- 6 个工具构造函数签名统一改为接收 `*WorkDirRef`；`Execute` 时 `ref.Get()` 取当前值。
- `WithWorkDir` 改为 `ref.Set + permission.SetWorkDir + persona/memory 更新`（现逻辑不变，只多 Set）。
- **删除 `WithDefaultTools` 的可选 workDir 参数**（不留兼容），装配顺序从此无关。

**涉及文件**：`builtin/workdir.go`（新增）、6 个工具文件构造与 Execute、`builder.go`、相关测试。

**验收**：`NewAgent(gw, WithDefaultTools(), WithWorkDir(B))` 后执行 `read_file B/../escape`，断言沙箱以 B 为根；`/model` 与向导流程回归。

---

### D6 日志中间件：轮末快照 + 权限收敛（P2-2）

**问题**：每事件对全部累积事件 `MarshalIndent` + 整文件覆盖（写放大随事件数平方增长），且发生在流式回调路径上拖慢首 token；`latest.json` 0644 落盘完整对话与系统提示词，与配置文件 0600 口径不一致。

**方案**：
- `recordEvent` 拆分：**内存 append + JSONL 追加**保留（JSONL 是 O(1) 追加，且是逐事件审计通道，保留实时性）；**删除其中的 `writeLatestJSONLocked` 调用**。
- `latest.json` 语义变更为**轮末快照**：仅在 `OnTurnEnd` 写一次（崩溃时轮内数据仍完整保留在 agent.jsonl）。
- 落盘权限统一 `0600`（latest.json 与 agent.jsonl 同步改）。
- `OnTurnStart` 的 `events = make(...)` 重置逻辑不变，`Traces()` 不变（`/log` 面板读内存，不受影响）。

**涉及文件**：`internal/agent/logger.go`。

**验收**：单测断言 `OnTurnStart→OnLLMRequest` 序列后 `latest.json` 未被写入，`OnTurnEnd` 后写入且为全量；`stat` 断言 0600；现有日志面板功能回归。

---

### D7 上下文按字符预算裁剪（P2-3）

**问题**：滑动窗口固定 40 条，单条工具结果上限 8000 字符，最坏 ~32 万字符远超模型上下文，长任务以"上游 400 context length"暴露。

**方案**：`NewSlidingWindowMemory` 签名变更为 `(maxMessages int, maxContextBytes int)`（不留兼容，同步改全部 5 处调用；`builder.go` 默认 `40, 160_000`）：
- `BuildContext` 裁剪时在现有"条数 + 轮次原子性回溯"之上，叠加**从最新向前累计 Content+ToolCalls 字节数**，超预算即截止。
- 字符近似 token（≈4:1），不引入 tokenizer 依赖；预算值取保守档，留出系统提示词 + 工具 Schema 的余量。
- 最早被裁掉的用户消息无法恢复——可接受（与现有 40 条裁剪同语义，只是更早触发）。

**涉及文件**：`internal/memory/sliding_window.go`、`memory_test.go`、`agent/builder.go`、`agent_test.go`。

**验收**：构造超预算历史，断言 BuildContext 输出总字节 ≤ 预算，且任意 assistant(tool_calls) 与其 tool 结果不拆对；现有轮次原子性测试不回归。

---

### D8 TUI 渲染：块级结果缓存（P2-4）

**问题**：每个 delta 触发全部历史消息重建 + 历史块重新 glamour Render，复杂度 O(轮次²)。

**方案**：
- 渲染缓存：`map[uint64]string`，key = FNV64(块内容 + 终端宽度 + glamour 样式)。
- `renderChatMessages` 中**已完成的历史块**先查缓存，miss 才 Render 并回填；**流式中的当前块**不缓存（内容每帧变化）。
- 缓存挂在渲染器结构（`markdown.go` 已有宽度缓存先例），容量不设上限（本地单用户，会话内块数有限）。
- 顺带解决 P3-9 的一半：`ChatMessage.Content` 与 `Blocks` 双份状态暂不拆（结构改动波及 TUI 状态机，收益已被缓存抵消，标记为非目标）。

**涉及文件**：`internal/tui/markdown.go`、`chat.go`。

**验收**：基准对比（10 轮对话下渲染耗时下降一个数量级）；长会话滚动/增量流式无视觉回归。

---

### D10 大结果落盘迁移出 agent 包（P2-7）

**问题**：`interceptor.go` 的大结果落盘（8000/2000 阈值、`.tide/tool-results` 目录、文件名去重）是存储策略，却写死在 Agent 内核；换宿主必须改内核包。

**方案**：新建 `internal/middleware` 包：
- `LargeResultSpill(threshold, headroom, dir)` 作为标准 `PostToolUse` 钩子迁入，逻辑原样搬移。
- `LoggingMiddleware` 同步迁入该包（同样属于可替换策略，`agent` 包只留接口与挂载机制）。
- `agent` 包删除 `interceptor.go` 与 `logger.go`；`builder.go` 的 `WithLoggingMiddleware` 改为转发构造（或直接删除该 Option，`main.go` 用 `WithHook(middleware.NewLoggingMiddleware(wd))` 显式装配——**选后者**，装配更显式且少一层转发）。
- `Traces()` 的类型断言问题（P3-10）一并消除：`main.go` 创建 middleware 实例后同时传给 TUI `/log` 面板持有，`CoreAgent.Traces()` 删除。

**涉及文件**：新增 `internal/middleware/`（spill.go、logging.go + 测试）；删除 `agent/interceptor.go`、`agent/logger.go`；`builder.go`、`agent.go`、`main.go`、TUI `/log` 面板接线。

**验收**：`go test ./...` 全绿；大结果落盘行为与现状逐字节一致（用现有 interceptor 测试迁移断言）；`/log` 面板正常；`agent` 包对外 API 中不再出现落盘路径常量。

---

### D11 死代码清理 + llamacpp 就绪探测（P2-8 + P2-9 + P3-11）

**问题**：`Router` 按 `req.Model` 路由为死路径（生产零调用，实查确认）；map 兜底遍历顺序随机；`llamacpp` 恒就绪，本地服务未启动时用户首次提问才拿到连接错误；4 个死 API 仅测试引用。

**方案**：
- **删除 `internal/gateway/router.go` 及其测试**（实际路由已由 `UpdateConfig` 热装网关完成，职责单一且可复现）。
- **删除死 API**：`CoreAgent.TotalUsage`、`CoreAgent.SetGateway`、`TraceEvent.PrettyJSON`、`Client.CheckHealth`（引用它们的测试改为针对真实 API 断言或删除）。
- **llamacpp 就绪探测**：`config_wizard` 在用户选择/确认 llamacpp 后、写配置前，对 `{baseURL}/v1/models` 发一次 `GET`（2s 超时）：失败时在向导界面提示"本地服务未就绪（连接失败），已保留配置，可稍后启动服务"——**不阻断**（服务可能稍后启动），只消除"首问才发现"的困惑。

**涉及文件**：删除 `router.go`；`agent.go`、`config.go`、`protocol.go`、`gateway.go` 删方法；`config_wizard.go` 加探测。

**验收**：`go build ./... && go vet ./... && go test ./...` 全绿；`grep -r "Router\|TotalUsage\|SetGateway\|PrettyJSON" internal cmd` 零生产命中；llamacpp 未启动时走完向导出现提示文案。

---

## 批次四：整洁度小修（D12 + D13）

### D12 currentAPIKey 状态收敛（P2-5）

**方案**：把 API key 输入态从 `TideApp.currentAPIKey` 全局字段**移入 wizardModel 局部字段**：输入过程只在向导模型内部流转；确认时随 `UpdateConfig` 一次性提交；取消/退出向导时状态随模型自然销毁。6 处手工清空点全部删除。不变量从"每个入口记得清"变为"状态根本不泄漏到全局"。

**涉及文件**：`app.go`（删字段）、`config_wizard.go`、`command.go`、`tui_test.go`（删"预置残留 key"用例，改为显式构造）。

**验收**：向导 A 厂商输错 key → 取消 → 重进选择 B 厂商 → B 的请求绝不携带 A 的 key（补一条集成测试）。

### D13 工具细节批量修复（P3-3~P3-8）

| 编号 | 修复 |
|---|---|
| P3-3 | `read_file`：`bufio.Scanner` 换 `bufio.Reader.ReadString('\n')` 循环（无行长上限）；`limit` 改为逐行累计读入，超限即停（不再全量读入后截断） |
| P3-4 | `edit_file`：`old_text` 命中多于 1 处时报错 `old_text matches N locations, provide more context`（对齐 Claude Code 行为） |
| P3-5 | `write_file`：写临时文件（同目录 `.tmp-` 前缀）+ `os.Rename` 原子落盘，失败清理临时文件 |
| P3-6 | `glob` 跳过目录集合与 `grep` 统一：`.git`、`.agents`、`node_modules`、`vendor`（抽成共享变量） |
| P3-7 | 字节截断改安全截断：新增共享 helper `truncateUTF8(s string, n int) string`（截断后回退到 UTF-8 边界 + `ToValidUTF8` 兜底），`bash.go`、`chat.go` 两处调用点替换 |
| P3-8 | `glamour.WithStandardStyle("dark")` 改 `glamour.WithAutoStyle()`（随终端背景自适应），渲染缓存 key 纳入 style（与 D8 联动） |

**验收**：每项一条针对性单测（大单行文件读取、多处 edit 报错、截断含中文/emoji 字符串断言合法 UTF-8 等）；`go vet` / `gofmt` 干净。

---

## 总体验收与实施顺序

1. **每批一个独立提交**，提交信息标注本方案编号（如 `D1`、`D3-A/D3-B`）。
2. 每批完成门槛：`go build ./... && go vet ./... && go test ./... ./cmd/...` 全绿 + `gofmt -l` 无输出 + 本方案该节验收项逐条通过。
3. 批次间允许独立回滚（无跨批文件耦合；D4 与 D5 同触碰 `builtin` 包但改动正交，仍分两提交）。
4. 批次二（D3/D4）与批次三的 D10 属结构性变更——本设计文档即为约定要求的前置评审物，**通过后方可动代码**。

## 明确的非目标

- 不做流式 SSE 逐 chunk 空闲超时（粗粒度整体超时已够，见 D2）。
- 不拆 `ChatMessage.Content/Blocks` 双份状态（P3-9，渲染缓存已抵消其成本）。
- 不重构 `config` 上帝包（P3-12）——待后续按宿主形态（CLI/Desktop）统一重新设计，避免本轮扩散。
- 不做多用户/并发锁设计（本地单用户约定）。
- `mv`、`chmod` 等可恢复/低危操作不单独纳入审批（见 D3 取舍）。
