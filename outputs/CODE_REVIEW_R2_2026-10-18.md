# Tide 全仓架构与代码评审 · 第二轮（2026-10-18）

> 评审范围：`cmd/` + `internal/` 全部 48 个 Go 文件（生产约 7.5k 行，测试约 4.8k 行）。
> 验证基线（本轮实跑）：`go build ./...` 通过、`go vet ./...` 零告警、`go test ./...` 9 包全 ok、`gofmt -l` 无输出。
> 本文档为只读评审结论，不含任何代码改动。上一轮结论见 `CODE_REVIEW_2026-10-18.md`，本文只补充「已修复确认」与「新发现问题」。

---

## 一、总体结论

架构分层已经稳定：`LLM → Gateway → Agent → Protocol → TUI`，依赖方向单向、协议层零内部依赖、机制（Registry 钩子）与策略（权限/落盘）分离，这些是全仓最扎实的部分。

本轮真正的风险不在分层，而在**状态机与生命周期**：

1. **中断即污染**：一轮对话在工具执行中途被取消时，记忆里会留下「有 N 个 tool_calls、却只有 M 个 tool 响应」的残缺历史，之后每一轮请求都会被上游 API 以 400 拒绝，直到 `/clear`。这是当前最影响可用性的缺陷。
2. **权限闸门仍是字面量匹配**：实测 `sh -c "rm -rf ~/data"`、`bash -c 'rm -rf /tmp/x'`、`find . -delete`、`xargs rm` 全部不触发任何审批；而 `bash` 工具本身明确「不含策略」，Gate 2 是唯一防线。
3. **全链路没有任何超时与 panic 兜底**：`bash` 一条挂死命令、一次 TLS 握手卡住、一个工具 panic，都能让整轮对话永久挂起或让整个进程崩溃退出。

规模上，TUI 已占生产代码 **39%（2939 行）**，是 Agent 内核（1041 行）的 2.8 倍。前端复杂度仍是仓库最大成本项，且它的正确性依赖「把全局单值 `currentAPIKey` 在 6 处手工清空」这类隐式约定。

---

## 二、分层现状

| 层 | 生产行数 | 实际职责 | 评价 |
|---|---|---|---|
| `cmd/tide` | 75 | 唯一入口，配置损坏双重回退 | 干净 |
| `internal/protocol` | 243 | 纯数据契约 + `Agent` 接口 + Trace DTO | 无内部依赖，跨端可复用，成立 |
| `internal/gateway` | 712 | 单 `Client` 覆盖 4 厂商，SSE 拼装 tool_calls，429/5xx 退避 | 边界清晰；但依赖 `config` 做元数据查询 |
| `internal/agent` | 1041 | ReAct 循环、装配、6 个 Hook、审批桥、大结果落盘 | 职责开始过载（见 P2-7） |
| `internal/config` | 586 | 厂商元数据 + 模型推断 + 环境变量 + 视图映射 + 落盘 | 事实上的「上帝包」 |
| `internal/permission` | 377 | 三道闸门 | 结构对，规则弱 |
| `internal/tool` | 1185 | Registry + 6 内置工具 + SafePath | 工具实现质量不均 |
| `internal/memory` | 339 | 滑动窗口 + 双层 Markdown 记忆 | 轮次原子性正确，但只按条数裁剪 |
| `internal/tui` | 2939 | 7 状态机 + 渲染 | 最大模块，状态重复 |

**值得保留的设计**：`Registry.Execute` 的「钩子 → 校验 → 执行 → 钩子」流水线（`tool.go:98-165`）；`sliding_window.go:76-94` 的轮次原子性回溯；`proc_unix.go` 的 `Setpgid` + 负 PID `SIGKILL` 进程组回收。

---

## 三、问题清单

### P0 — 阻断级

#### P0-1 中断后记忆留下孤立 tool_calls，会话永久不可用

`internal/agent/loop.go:218-271`

```go
_ = a.memory.Append(ctx, protocol.Message{        // ← 先落 assistant(含 N 个 ToolCalls)
    Role: protocol.RoleAssistant, ToolCalls: toolCalls,
})
...
for _, tc := range toolCalls {
    if ctx.Err() != nil { return stepUsage, false, ctx.Err() }   // ← 中途返回
    ...
    _ = a.memory.Append(ctx, protocol.Message{Role: protocol.RoleTool, ToolResult: &res})
}
```

复现路径（100% 命中）：模型一次返回 2 个 tool_calls → 用户按 Ctrl+C / Esc 中断 → `ctx.Err() != nil` 在第 2 个工具前返回 → 记忆里留下 1 个 assistant(tool_calls=2) + 1 个 tool。

下一轮 `BuildContext` 会把这段残缺历史原样发给上游，OpenAI/DeepSeek 一律返回
`An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'`。
用户看到的是「中断一次之后，这个会话就再也问不动了」，只能 `/clear`。

同一分支还覆盖 `sendEvent` 返回 false（`loop.go:241-246`、`260-265`）的情况。

**修复方向**：中断/失败时补齐「未执行工具的合成 ToolResult」（内容为 `canceled by user`），保证 assistant(tool_calls) 与 tool 消息数量严格配对；或把 assistant 消息的落库推迟到工具循环收敛之后。

---

### P1 — 需优先处理

#### P1-1 权限 Gate 2 仍是字面量匹配，包装执行完全绕过

`internal/permission/permission.go:43`（正则）与 `:271`（硬拒绝表）

本轮用同一套正则实测（命令 → 是否触发审批）：

| 命令 | 是否触发 | 说明 |
|---|---|---|
| `rm -rf ./build` | ✅ | 段首命中 |
| `cd / && rm -rf var` | ✅ | `&&` 后命中 |
| `sh -c "rm -rf ~/data"` | ❌ | `rm` 前是双引号 |
| `bash -c 'rm -rf /tmp/x'` | ❌ | `rm` 前是单引号 |
| `find . -name '*.tmp' -delete` | ❌ | `find` 不在规则表 |
| `xargs rm` | ❌ | `rm` 前是空格但非段首 |
| `python3 -c "import shutil; shutil.rmtree('x')"` | ❌ | 解释器执行 |
| `mv ~/x ~/y`、`echo x > important.go` | ❌ | 移动/覆盖不在规则表 |

`bash` 工具（`bash.go:11-14`）明确声明「纯执行器、不含任何安全策略」，`cmd.Dir` 只设初始目录，`cd` 之后不受任何约束。结论：Gate 2 只能拦住「诚实的模型」，拦不住任何包装。

**修复方向**：命令规范化后再匹配（剥离 `sh|bash|zsh -c` 引号层、`eval`、`xargs`），对无法静态判定的包装执行直接升级为「需审批」；`find -delete`、`mv`、解释器 `-c` 一并纳入。

#### P1-2 `reasoning_content` 被无条件回灌上游

`internal/gateway/wire.go:89-92`、`:101-105`

```go
if m.ReasoningContent != "" {
    s := m.ReasoningContent
    msg.ReasoningContent = &s        // 每一轮历史都带上上一轮的思维链
}
```

记忆层把 `ReasoningContent` 完整保存（`loop.go:221`），`toWireMessages` 又把它写回请求体。按 DeepSeek 官方文档，输入消息中出现 `reasoning_content` 会返回 400；Gemini/Spark 的 OpenAI 兼容层对未知字段的处理也不一致。当前 `gateway_test.go` 只断言了**解析**（`reasoning` 累加），从未断言**出站 payload**，所以这条链路完全没有测试覆盖。

**修复方向**：`reasoning_content` 只用于本地展示与 Trace，出站时一律剥离；补一条「构造请求体不得包含该字段」的断言。

#### P1-3 全链路零超时、零 panic 兜底

- 超时：生产代码中 `context.WithTimeout/WithDeadline` **一次都没有**（只在测试里出现）。TUI 用 `context.WithCancel(context.Background())`（`chat.go:209`），没有 deadline。`bash` 没有 timeout 参数，`sleep 100000` 或交互式命令会永久挂住整轮；`http.DefaultClient`（`gateway.go:74`）也没有 dial/握手/空闲读超时，SSE 半开连接同样永久挂住。
- panic：全仓无 `recover()`。`Registry.Execute` 直接调用 `t.Execute`（`tool.go:141`），工具一旦 panic，panic 发生在 `Run` 派生出的 goroutine 里（`loop.go:41`），**整个 TUI 进程崩溃**，且 `outCh` 永不关闭。

**修复方向**：`agentLoop` 顶部 `defer recover()` 转成 `EventError`；`Registry.Execute` 单工具级 recover；`bash` 增加默认超时（如 120s，可由参数覆盖）；HTTP client 配置 `DialContext` 超时与 `ResponseHeaderTimeout`，SSE 增加空闲读超时。

#### P1-4 `SafePath` 不解析符号链接，沙箱可被穿透

`internal/tool/builtin/safe_path.go:36-39` 只用 `filepath.Abs`/`Clean`，没有 `filepath.EvalSymlinks`。

工作区内若存在指向 `/etc` 或 `~` 的符号链接（`git clone` 的仓库、用户自己建的软链都很常见），`read_file` 会读到工作区外，`write_file` 会写到工作区外，且 Gate 2 的路径判定（`permission.go:314-344`）同样只看字面路径，不会拦截。这是「沙箱」承诺的实际漏洞。

**修复方向**：`SafePath` 对已存在的路径做 `EvalSymlinks`，对不存在的目标做「父目录 EvalSymlinks + 拼接」，再判前缀。

---

### P2 — 一致性与性能

**P2-1 装配顺序缺陷：`WithDefaultTools` 与 `WithWorkDir` 相互覆盖**

`internal/agent/builder.go:187-192`

```go
defaultOpts := []Option{ WithDefaultTools(), WithConfig(...) }   // 此刻 a.workDir = os.Getwd()
defaultOpts = append(defaultOpts, opts...)                        // 若 opts 含 WithWorkDir，只改 a.workDir
```

工具在 `WithDefaultTools` 执行时就把 `workDir` 固化进 6 个工具实例，之后 `WithWorkDir` 只更新 `a.workDir` 与 `permission.workDir`。结果：**工具沙箱指向 A 目录，权限判定指向 B 目录**。当前 `main.go` 不传 `WithWorkDir`，属潜伏缺陷；`WithDefaultTools(workDir...)` 这个可选参数本身就是为绕开它而加的补丁。

**P2-2 日志中间件每个事件全量重写 `latest.json`**

`internal/agent/logger.go:57-63`、`:77-84`

`recordEvent` 每次都对**全部已累积事件**做 `MarshalIndent` 并整文件覆盖，再追加一行 JSONL。一轮 10 步、每步 4 个事件的对话，`latest.json` 会被重写约 40 次，体积随轮次线性增长，写入成本随事件数平方增长，而且这些 I/O 全部发生在**流式回调路径上**，直接拖慢首 token 与增量渲染。

同时 `latest.json` 以 `0644` 落盘（`logger.go:61`），内容包含完整系统提示词、长期记忆、全部对话与工具输出；而配置文件是 `0600`。权限口径不一致。

**P2-3 上下文只按条数裁剪，不按 token 预算**

`internal/memory/sliding_window.go:70-72` 固定 40 条。单条工具结果上限 8000 字符（`interceptor.go:106`），40 条最坏约 32 万字符 ≈ 10 万 token，足以超出多数模型上下文。缺少「按 token 预算裁剪 + 超限摘要」策略，长任务下会以「上游 400 context length」的形式暴露。

**P2-4 TUI 每 token 全量重渲染**

`internal/tui/chat.go:386-498`

渲染器初始化已缓存（`markdown.go:15-38`，上一轮 P2-2 已修），但 `renderChatMessages` 仍在**每个 delta 上重建全部历史消息的字符串**，历史 `BlockText` 每次都重新走一遍 glamour `Render`。复杂度仍是 O(轮次长度²)。10 轮对话后每个 token 触发数十次 Markdown 解析。

**修复方向**：按「块内容 hash + 宽度」缓存渲染结果，只重渲染变化块。

**P2-5 `currentAPIKey` 全局单值，不变量靠 6 处手工清空维持**

字段在 `app.go:59`，清空点散落于 `config_wizard.go:82 / 136 / 156 / 238 / 347` 与 `command.go:45`。上一轮的「跨厂商密钥污染」主路径已修（进入未配置厂商分支时先清空），但正确性依赖「每个入口都记得清」这一约定——新增一个入口就会重新引入污染。`tui_test.go:519` 甚至直接用「预置一个残留 key」来构造用例，说明这个状态本身就是模糊的。

**修复方向**：改为 `pendingKeys map[string]string`（按厂商存放），或在 `syncActiveProvider` 内统一清理。

**P2-6 退出与中断不取消 context，`bash` 子进程可能残留**

`main.go:70-74` 直接 `p.Run()`，没有退出钩子；`/exit`、`Ctrl+D` 走 `tea.Quit`，`m.cancel` 不会被调用。正在执行的 `bash` 因 `Setpgid` 已脱离父进程组，主进程退出后它继续运行（典型场景：模型执行了 `go test ./...` 或 `npm run dev`）。`Ctrl+C` 中断路径只调用了 `m.cancel()`，但 `m.pendingPerm` 未清理（`app.go:216-237`），残留的审批态会吞掉后续所有按键，直到用户再按一次 Esc。

**P2-7 `agent` 包职责过载，横切策略写死在包内**

`interceptor.go` 的大结果落盘（8000/2000 字符阈值、`.tide/tool-results` 目录、文件名去重）是**存储策略**，却定义在 Agent 内核里；`permissionPreHook` 把权限判定也挂进了内核。装配期挂钩子的形式是对的，但钩子实现归属错位——换一个宿主（Desktop/Wails）想改落盘策略，必须改 Agent 包。

**P2-8 `Router` 的模型路由是死路径，回退不确定**

`router.go:58-64` 按 `req.Model` 推断厂商，但 `loop.go:160-163` 构造 `ChatRequest` 时从不设置 `Model`，第 1 步永不命中；实际路由发生在 `UpdateConfig`。`router.go:72-74` 的兜底遍历 map，顺序随机，多厂商注册时结果不可复现。

**P2-9 `llamacpp` 恒就绪，启动不做健康检查**

`gateway.go:136` 的 `CheckHealth` 仅测试使用；`config.go` 把本地厂商标为「恒就绪」，`ConfigView.HasAPIKey` 对本地厂商直接为 true。127.0.0.1:8080 未启动时，用户在首次提问才拿到连接错误，而 `bash` 侧完全可以直接探测。

---

### P3 — 整洁度与体验

| 编号 | 位置 | 问题 |
|---|---|---|
| P3-1 | `permission.go:31` + `:271` | Gate 1 用 `Contains("rm -rf /")`，导致 `rm -rf /tmp/x` 被**硬拒绝且不可审批**（误伤） |
| P3-2 | 5 处 | 工作区路径判定重复实现：`permission.go:314`、`safe_path.go:11`、`memory.ProjectDir`、各工具构造器、`prompt.go:16`，规则易漂移 |
| P3-3 | `read_file.go:72-82` | `bufio.Scanner` 默认 64KB 行上限，压缩/单行大文件直接报 `token too long`；且 `limit` 是先全量读入再截断，大文件内存翻倍 |
| P3-4 | `edit_file.go:82-87` | `old_text` 出现多次时静默替换第一处，无「多处匹配」报错 |
| P3-5 | `write_file.go:76` | 非原子写（无 temp+rename），写入中断会留下半截文件 |
| P3-6 | `glob.go:103` | 只跳过 `.git`/`.agents`，不跳过 `node_modules`/`vendor`（`grep.go:157` 跳过），JS 仓库下 glob 明显变慢 |
| P3-7 | `bash.go:80`、`chat.go:571` | 用字节下标截断（`output[:50000]`、`snippet[:300]`），中文/emoji 会被切成非法 UTF-8 |
| P3-8 | `markdown.go:30` | 硬编码 `glamour.WithStandardStyle("dark")`，浅色终端下对比度差 |
| P3-9 | `chat.go:46-49` | `ChatMessage` 同时维护 `Content` 与 `Blocks` 两份等价状态，长会话双倍内存；`protocol.Event` 无 turn/message ID，TUI 靠 `messages[lastIdx]` 定位当前轮次 |
| P3-10 | `agent.go:70-79` | `Traces()` 遍历 hooks 做 `*LoggingMiddleware` 类型断言；未装配该中间件时 `/log` 面板恒空 |
| P3-11 | 4 处 | 死 API：`CoreAgent.TotalUsage`（`agent.go:82`）、`CoreAgent.SetGateway`（`config.go:80`）、`TraceEvent.PrettyJSON`（`protocol.go:163`）、`Client.CheckHealth`（`gateway.go:136`）——生产代码零调用方，仅测试引用 |
| P3-12 | `config` 包 | 元数据、推断、环境变量、视图映射、持久化五职责合一；`gateway`（传输层）反向依赖 `config` 查端点/模型，边界不够干净 |

---

## 四、上一轮问题的修复确认

| 上轮编号 | 结论 | 依据 |
|---|---|---|
| P1-2 跨厂商 Key 污染 | **主路径已修**，遗留 P2-5 的隐式不变量 | `config_wizard.go:82/136/156/238` 均先清空 |
| P1-3 `UpdateConfig` 状态分裂 | **已修** | `agent/config.go:20-76` 改为 candidate 副本 → 校验 → 建网关 → 落盘 → 一次性提交 |
| P2-1 每帧 5 次磁盘读 | **已修** | `cachedMemCount`（`app.go:103`、`chat.go:246`），在 Done/Error 时刷新 |
| P2-2 glamour 每帧重建 | **部分修复** | 渲染器按宽度缓存；但全量重渲染仍在（P2-4） |
| P2-4 权限与沙箱判定矛盾 | **未修** | 越界路径仍「先要求审批、再被 `SafePath` 拒绝」 |
| P2-5 Router 死路径 | **未修** | 仍存在（P2-8） |
| P2-7 Done 不释放 context | **已修** | `app.go:336-340` 已调用 `m.cancel()` |
| P2-8 取消后继续执行工具 | **部分修复** | 工具循环前有 `ctx.Err()` 检查（`loop.go:235`），但 delta/reasoning 发送仍忽略返回值（`:187`、`:194`） |
| P3-2 TUI 依赖 config 包 | **已修** | `config_wizard.go` 改为按 `ProviderInfo.Aliases` 匹配 |

---

## 五、建议处理顺序

**第一批（可用性，建议立即修）**
1. P0-1 中断补齐合成 ToolResult —— 影响每一次 Ctrl+C，代价最小。
2. P1-3 超时与 panic 兜底 —— `bash` 默认超时 + `agentLoop` recover。
3. P1-2 出站剥离 `reasoning_content` + 补出站 payload 断言。

**第二批（安全，需先出设计文档）**
4. P1-1 Gate 2 命令规范化（含包装解析与「无法判定即审批」策略）。
5. P1-4 `SafePath` 符号链接解析；顺带合并 P3-2 的 5 处重复路径判定为单一实现。

**第三批（性能与结构）**
6. P2-2 日志改为「轮末一次性写 `latest.json`」+ 权限收敛到 `0600`。
7. P2-4 渲染结果按块缓存。
8. P2-3 上下文按 token 预算裁剪。
9. P2-7 把大结果落盘从 `agent` 包迁到独立的 middleware/tool 层。

**第四批（整洁度）**
10. P3-11 清理死 API；P2-8 删除 Router 死路径或补齐 `Model` 传递；P3-1 修正 Gate 1 误伤。

> 按仓库约定，以上第 4~9 项属结构性变更，需先提交设计文档并通过评审后再改代码。
