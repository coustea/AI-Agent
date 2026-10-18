# Tide 全仓代码评审（2026-10-18）

> 评审范围：`cmd/` + `internal/` 全部 48 个 Go 文件。生产代码约 7.6k 行，测试约 4.8k 行（测试/生产 ≈ 0.64）。
> 验证基线：`go build ./...` 通过、`go vet ./...` 无告警、`go test ./...` 9 个包全部 ok。
> 本文档为只读评审结论，不含任何代码改动。

---

## 一、总体结论

分层架构已按 `LLM → Gateway → Agent → Protocol → TUI` 落地，边界清晰，测试基线扎实，无编译/静态检查问题。

主要风险集中在三处：**权限闸门的正则可绕过**、**TUI 配置向导的跨厂商密钥污染**、**运行时配置热切失败后的状态不一致**。性能瓶颈集中在 **TUI 每帧重复磁盘 I/O 与 Markdown 全量重渲染**，与内核无关。

架构层面出现一个新的结构性事实：**TUI 已成为最大模块（2882 行，占生产代码 38%）**，超过 Agent 内核（1281 行）与 Gateway（710 行）之和。前端复杂度已成为仓库主成本，后续演进应优先考虑 UI 层的状态机收敛与渲染缓存。

---

## 二、分层实现要点

| 层 | 文件规模 | 职责与实现特征 |
|---|---|---|
| `cmd/tide` | 40 | 唯一入口；配置损坏时双重回退到 `DefaultConfig()`，保证前端始终拿到非 nil 内核 |
| `internal/protocol` | 242 | 零内部依赖的纯契约层；`Agent` 接口、`Event`/`TraceEvent` DTO 均在此，支持跨端序列化 |
| `internal/gateway` | 710 | 单 `Client` 覆盖 4 厂商（OpenAI wire 协议）；`Router` 按模型名推断厂商；429/5xx 指数退避 3 次；SSE 增量拼装 tool_calls |
| `internal/agent` | 1281 | ReAct 主循环、函数式装配、6 个生命周期 Hook、权限审批桥、大结果落盘钩子 |
| `internal/config` | 559 | `providerRegistry` 作为厂商元数据单一来源；环境变量补全；`0600` 落盘 |
| `internal/memory` | 339 | 滑动窗口 + 轮次原子性裁剪；双层 Markdown 长期记忆 |
| `internal/permission` | 377 | 三道闸门：硬拒绝表 / 正则风险匹配 / 交互审批 + 会话信任 |
| `internal/tool` | 1069 | 注册表 + Pre/Post 钩子流水线；6 个内置工具；`SafePath` 沙箱 |
| `internal/tui` | 2882 | 7 状态机（聊天/模型看板/预设/密钥/自定义模型/JSON 追踪/思考看板） |

设计上值得肯定的几点：

1. **机制与策略分离彻底**。`tool.Registry` 不含任何安全策略，权限与结果落盘以 `PreToolUse`/`PostToolUse` 钩子挂载，内核循环零侵入。
2. **协议层真正无依赖**。`protocol` 不 import 任何内部包，`Agent` 接口只依赖 `context` 与纯数据类型，跨端复用成立。
3. **轮次原子性裁剪**正确。`sliding_window.go:76-94` 的回溯逻辑保证 `User → Assistant(ToolCalls) → Tool` 不被切散，避免了孤立 `RoleTool` 导致的 API 400。
4. **子进程治理到位**。`proc_unix.go` 用 `Setpgid` + 负数 PID `SIGKILL` 整组回收，避免 `bash` 派生进程残留。

---

## 三、问题清单（按严重度）

### P1 — 需优先处理

**P1-1 权限闸门可被 shell 包装绕过**

`internal/permission/permission.go:43`

```go
destructiveWordPattern = regexp.MustCompile(`(?i)(?:^|[;&|()\n])\s*(?:rm|rmdir|unlink|shred|del)(?:\s+-[a-zA-Z]+)*\s+`)
```

该正则要求危险命令位于命令段首（`^` 或 `; & | ( ) \n` 之后）。因此以下调用**不触发任何审批**：

- `sh -c "rm -rf ~/data"`（`rm` 前是双引号）
- `bash -c 'rm -rf /tmp/x'`（`rm` 前是单引号）
- `find . -name '*.tmp' -delete`、`xargs rm`、`python -c "import shutil; ..."`

`hardDenyList` 用 `strings.Contains` 全串匹配，只兜住 `rm -rf /` 这类字面量。结论：Gate 2 是**字面量特征匹配**，对包装执行无防护能力。`bash` 工具本身明确声明「纯执行器、不含策略」，因此这是唯一的防线。

**P1-2 TUI 跨厂商 API Key 污染**

`internal/tui/config_wizard.go:213 / 233 / 284 / 342`，状态字段在 `app.go:59`。

`m.currentAPIKey` 是全局单值，在厂商切换时从不清空。复现路径：

1. 为 Gemini 输入 Key → `m.currentAPIKey = "gemini-key"`；
2. 打开 `/model`，选中未配置的 DeepSeek → 进入 `stateInputAPIKey`，输入框被 `Reset()` 但 `currentAPIKey` 保留；
3. 直接回车（`keyVal` 为空，`currentAPIKey` 仍非空）→ `hasKey == true` 误判通过；
4. `UpdateConfig("deepseek", "gemini-key", ...)` → 把 Gemini 的密钥写入 DeepSeek 的 `providers` 配置。

后果：密钥被静默错配并落盘，用户只看到 401，排查成本高。

**P1-3 `UpdateConfig` 先改状态后校验，失败后内存态与网关态分裂**

`internal/agent/config.go:38-57`

```go
a.cfg.SwitchProvider(newProvider)   // ① 已改写 cfg.Provider/ModelName/APIKey
...
if !config.IsLocalProvider(newProvider) && strings.TrimSpace(a.cfg.APIKey) == "" {
    return fmt.Errorf(...)          // ② 直接返回，a.gw 未替换、config.json 未落盘
}
```

失败后 `a.cfg.Provider` 已是新厂商，`a.gw` 仍指向旧网关。`Config()` 返回的视图与真实请求链路不一致：Header 显示新模型，实际仍走旧模型；且 `SaveConfig` 未执行，重启后又变回旧值。

### P2 — 性能与一致性

**P2-1 每帧 5 次磁盘读取**

`internal/tui/chat.go:246` → `agent.go:61` → `storage.go:117`

`renderHeaderBar()` 每帧调用 `m.agent.MemoryCount()`，后者每次 `memory.LoadBundle(workDir)` 重新读取 5 个 Markdown 文件（全局 2 + 项目 3）。Bubble Tea 在**每个 token 增量后都重绘**，长回答期间相当于每秒数百次文件系统调用。

**P2-2 Markdown 全量重渲染，复杂度 O(n²)**

`internal/tui/chat.go:386-498` + `markdown.go:17`

每帧遍历全部历史消息块，对每个 `BlockText` 调用 `renderMarkdown`，而 `renderMarkdown` **每次都新建 `glamour.NewTermRenderer`**（内部解析样式表，成本高）。当前仅对「正在流式的最后一个块」做了跳过优化（`chat.go:454`），历史块仍全量重渲染。10 轮对话后，每个 token 会触发数十次 glamour 初始化。

**P2-3 会话消息无上限增长**

`internal/memory/sliding_window.go:31-36`

`Append` 只追加不裁剪，`maxMessages=40` 仅在 `BuildContext` 时生效。内存中 `messages` 随会话无限增长；`History()` 每次返回全量深拷贝，且 TUI 侧 `m.messages` 同样只增不减。长时间运行会持续占用内存并放大 P2-2 的渲染成本。

**P2-4 权限层与沙箱层判定重复且结论矛盾**

`permission.go:301-303` 对越界路径返回「需要审批」；用户批准后 `Evaluate` 返回 `allowed=true`，但工具内部的 `SafePath`（`safe_path.go:59`）仍会拒绝。结果是：**用户被要求审批一个注定失败的操作**，审批环节对越界写入毫无意义。同一套路径判定在两处独立实现（`isPathEscapingWorkspace` 与 `SafePath`），存在规则漂移风险。

**P2-5 Router 的模型名路由在线上是死路径**

`gateway/router.go:58-64` 支持按 `req.Model` 推断厂商，但 `agent/loop.go:160-163` 构造 `ChatRequest` 时只填 `Messages`/`Tools`，从不设置 `Model`。因此 `Route()` 的第 1 步永不命中，始终走「当前激活厂商」。真正的模型路由实际发生在 `config.InferProviderFromModel` + `UpdateConfig` 层。

**P2-6 启动不做本地服务健康检查**

`gateway.go:136` 的 `CheckHealth` 仅在测试中被调用。`llamacpp` 被标记为「恒就绪」（`config.go:543`），但 127.0.0.1:8080 未启动时用户会在首次提问时才拿到连接错误。

**P2-7 正常完成时不释放 context**

`internal/tui/app.go:327-342` 的 `EventDone` 分支只置 `isGenerating=false`，未调用 `m.cancel`。每轮对话的 `context.WithCancel` 及其派生资源保留到进程退出。

**P2-8 取消后仍继续执行工具**

`agent/loop.go:187/194/237/254` 忽略了 `sendEvent` 的返回值。ctx 取消后 `sendEvent` 返回 `false`，但代码继续向下执行，仍会调用 `tools.Execute`（该调用本身持有已取消的 ctx，多数工具会快速返回，但 `bash` 在极端情况下仍可能启动子进程）。

### P3 — 整洁度

**P3-1 仅被测试引用的导出 API**

- `agent.CoreAgent.TotalUsage()`（`agent.go:82`）：生产代码无调用方，TUI 的 Token 展示取自 `EventDone.Usage`。
- `agent.CoreAgent.SetGateway()`（`config.go:75`）：仅测试使用，生产路径走 `UpdateConfig`。
- `protocol.TraceEvent.PrettyJSON()`（`protocol.go:163`）：仅 `logger_test.go` 使用，TUI 用 `formatTraceJSON`。
- `gateway.Client.CheckHealth` 与 `NewLlamaCpp/NewDeepSeek/NewGemini/NewSpark`：仅测试使用。

按仓库「不为旧内部实现保留兼容层」的约定，这些应清理或补齐调用点。

**P3-2 TUI 直接依赖 config 包**

`internal/tui/config_wizard.go:7` import `internal/config`（用 `ProviderID` 做别名归一化）。这与「TUI 只依赖 protocol 契约」的分层目标不符，归一化能力应由 `ConfigView` 或协议层暴露。

**P3-3 Router 回退路径不确定**

`router.go:72-74` 遍历 map 取第一个可用厂商，Go map 迭代顺序随机，多厂商注册时回退结果不可复现。

**P3-4 `readSSE` 部分发送忽略取消信号**

`wire.go:247` 的 reasoning 分支未检查 `sendChunk` 返回值，取消后仍继续读取上游流。

---

## 四、验证结果

```
go build ./...   OK
go vet ./...     OK（无告警）
go test ./...    agent / config / gateway / memory / permission / tool / tool/builtin / tui 全部 ok
                 协议层与 cmd 无测试文件（纯数据契约，可接受）
```

测试质量评价：`agent_test.go`（1154 行）覆盖了 ReAct 多步、工具调用、权限审批桥、网关热切、ErrMaxSteps；`tui_test.go`（1243 行）覆盖了 7 个状态机的按键流转。测试使用 `httptest` 与 fake gateway，不依赖真实凭据，符合仓库约定。

**覆盖缺口**：`permission` 的用例集中在「危险命令被拦截」，缺少「包装执行绕过」的反向用例——这正是 P1-1 未被发现的原因。

---

## 五、建议的处理顺序

1. **P1-1**：Gate 2 改为「命令规范化后再匹配」——剥离引号/`-c` 包装、递归解析 `sh|bash|zsh|eval|xargs` 的内层命令；对无法静态判定的包装执行直接升级为需审批。此项建议先出设计文档。
2. **P1-2**：`currentAPIKey` 改为按厂商存放（`map[string]string`），或在切换厂商时清空。
3. **P1-3**：`UpdateConfig` 改为「先构造候选 cfg 副本 → 校验 → 构建网关 → 成功后一次性提交并落盘」。
4. **P2-1 / P2-2**：记忆篇数在 `NewModel` 时缓存、`/clear` 与配置变更时刷新；Markdown 渲染按「块内容哈希」做缓存，仅对变化块重渲染。
5. **P2-4**：删除权限层的路径越界判定，统一由 `SafePath` 单点裁决；或反之，二者只保留一处。
6. **P2-5 / P2-6 / P3-1**：清理死路径与死 API，避免读者误判系统能力边界。

> 按仓库约定，上述 1~6 项均属结构性变更，需先提交设计文档并通过评审后再改动代码。
