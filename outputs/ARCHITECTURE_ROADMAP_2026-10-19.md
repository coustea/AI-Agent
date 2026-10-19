# Tide 架构演进与重构路线图

> 日期：2026-10-19｜基线：HEAD `d7165ce`｜状态：**待评审，本文不含任何代码改动**
> 承接：`CODE_REVIEW_R2_2026-10-18.md`（问题清单）、`DESIGN_HARDENING_2026-10-18.md`（D1–D13 已实施）
> 约束：本地单用户 · 全模型 OpenAI Chat Completions · 不为旧内部实现保留兼容层 · 设计先行、每阶段独立验收

---

## 一、结论先行

tide 已经越过"能跑"的阶段：分层单向、事件纯数据、权限有三道闸门、工具流水线清晰，D1–D13 把中断污染、超时、软链穿透、写放大等一批硬伤收掉了。**本路线图不主张大重写。**

真正的问题是六个会持续收税的**结构性张力**：

| 编号 | 张力 | 一句话后果 |
|---|---|---|
| T1 | 配置中心反向耦合传输层 | 换宿主/换厂商注册方式要动传输层 |
| T2 | 契约层承载业务语义与持久化 | `protocol.Agent` 逼所有宿主接受"内核写配置" |
| T3 | 没有"会话"这个一等公民 | 重启即失忆，无法恢复、回放、压缩 |
| T4 | 上下文只会截断，不会压缩 | 长任务静默丢失早期约束 |
| T5 | 扩展面是编译期的 | 每加一个能力都要改内核并发版 |
| T6 | 前端是最大单体，跨端契约未被验证 | 状态机改动风险高，"可复用桌面端"只是声明 |
| T7 | 凭据边界与工作区沙箱冲突 | 模型可读 `~/.tide/config.json` 并外发 |
| T8 | 可观测性只有记录，没有治理 | 日志无轮转/无脱敏/无成本核算 |

路线图按**依赖顺序**拆成 8 个阶段（含一个安全快修），每阶段可独立发布、独立回滚。**阶段 0 与阶段 1 不改变任何用户可见行为**，先把地基与护栏做出来。

---

## 二、基线（实测，非估算）

### 2.1 规模与验证

| 指标 | 实测值 |
|---|---|
| Go 代码总量 | 13,689 行（生产 8,279 / 测试 5,410） |
| 测试 | 14 个测试文件、101 个用例，`go test ./...` 12 个包全绿（`cmd`、`protocol` 无测试） |
| 直接依赖 | 3 个（`bubbles`、`bubbletea`、`lipgloss`；`glamour` 为间接依赖），无 CGO |
| 最大模块 | `internal/tui` 3,043 行，占生产代码 **36.8%** |
| 内核规模 | `internal/agent` 977 行；`internal/gateway` 587 行；`internal/permission` 713 行 |
| 缺失能力 | 会话持久化、headless 宿主、架构守护测试、日志轮转、工具并发 |

### 2.2 依赖图（`go list` 实测）

```text
cmd/tide
  └─ agent ──> config, gateway, memory, permission, protocol, tool, tool/builtin
       gateway ──> config, protocol          ← 传输层反向依赖配置中心
       config  ──> protocol                  ← 领域配置依赖前端视图 DTO
       permission ──> fsutil, protocol
       memory   ──> protocol
       middleware ──> protocol, tool
       tool/builtin ──> fsutil, textutil
tui ──> protocol, textutil, net/http        ← UI 层直接做网络探测
```

### 2.3 已经扎实、本路线图**不动**的部分

- `internal/fsutil`：工作区边界唯一实现（含符号链接解析）。
- `tool.Registry.Execute` 的「钩子 → 校验 → 执行 → 钩子」流水线。
- `permission/normalize.go` 的引号感知切分与"无法静态判定即审批"策略。
- `memory/sliding_window.go` 的轮次原子性回溯。
- `middleware/spill.go` 的大结果落盘与 `gateway` 的 429/5xx 退避。
- 纯数据事件流本身（`protocol.Event`）——需要的是**补身份**，不是推翻。

---

## 三、结构性张力（证据与后果）

### T1 配置中心是事实上的上帝包，传输层反向依赖它

**证据**：`internal/config/config.go` 一个文件 586 行承担五种职责——厂商元数据（`:55-115`）、配置结构（`:166-179`）、路径发现（`:199-215`）、环境变量补全（`:277-315`）、加载/保存（`:359-467`）、模型名推断与默认值（`:476-537`）、前端视图映射（`:538+`）。`internal/gateway/gateway.go:17` 直接 import `config`，`NewClient` 的签名是 `NewClient(provider config.Provider, ...)`（`:67`），内部调用 `config.DefaultBaseURL`（`:75`）、`config.NormalizeModelName`（`:84`）、`config.IsLocalProvider`（`:79`）。

**后果**：
- 传输层无法脱离"用户配置"语义独立测试与复用；新增厂商要同时改三处（catalog、gateway 构造、TUI 硬编码列表）。
- 模型能力（上下文窗口、是否支持 tools/reasoning）**完全没有声明**，上下文预算只能拍一个 160KB 常量（`agent/builder.go:156`）。
- `config → protocol` 让领域配置依赖前端视图，视图字段变更会反向牵动配置层。

### T2 契约层承载了业务语义与持久化职责

**证据**：`protocol.go:208-230` 的 `Agent` 接口包含 `UpdateConfig(provider, apiKey, model)`；其实现 `agent/config.go:12-77` 在校验后**直接落盘配置文件**。`protocol.go:148-202` 又把 Trace DTO（审计结构）放进同一契约包。

**后果**：
- "纯数据契约"名不副实：任何新宿主（headless、桌面端）都被迫接受"内核负责持久化用户配置"这一业务决定。
- 观测契约与前端契约混在一起，`/log` 面板的字段演进会污染宿主契约。
- `protocol` 目前还 import `context` 与 `time`，接口方法直接暴露 `context.Context`，跨进程/跨语言序列化时不可用（未来桌面端只能走进程内嵌）。

### T3 没有"会话"这个一等公民

**证据**：`CoreAgent`（`agent.go:26-43`）同时持有网关、配置、工作目录、记忆、工具、权限、钩子、挂起审批；`Reset()` 只做 `memory.Clear()`（`:72-76`）。会话只存在于内存，进程退出即消失。事件没有 turn/message 身份（`protocol.Event` 仅 7 个字段），TUI 靠 `messages[lastIdx]` 定位当前轮（`tui/app.go:313-316`）。

**后果**：
- 崩溃/重启即失忆，`/resume`、审计回放、跨轮统计都无处落地。
- 前端与内核靠"最后一条消息"这种隐式约定对齐，新增宿主必须复刻同一套推断。
- 摘要压缩没有可靠的"全量原文"来源（transcript），只能对内存里已经被裁过的窗口做二次加工。

### T4 上下文只有截断，没有压缩

**证据**：`sliding_window.go:73-129` 固定 40 条 + 160,000 字符预算，超预算时**整轮丢弃**最老的 user 起点，最后一轮永远保留。

**后果**：
- 长任务里用户最初的目标、约束、验收标准被静默丢掉，模型行为漂移且没有任何提示。
- 预算是全局常量，不感知具体模型的上下文窗口；换 32k 模型会直接撞上游 400。
- 工具结果虽有 8000 字符落盘阈值，但落盘后仍把前缀塞回上下文，多轮累积仍会挤爆窗口。

### T5 扩展面是编译期的

**证据**：`builder.go:87-98` 在装配时把 6 个具体内置工具写死进 registry；`tool.Tool` 接口（`tool.go:12-18`）只有 `Name/Description/Schema/Execute`，没有超时、并发安全、只读、输出预算、信任级别等元数据。

**后果**：
- 接入 MCP、技能、子代理都必须改内核包并重新发版。
- 模型一次返回多个 `tool_calls` 时，`loop.go:241-318` 严格串行执行；两个独立的只读检索无法并行。
- 权限策略只能按工具名 + 参数做通用判断，无法利用"该工具只读/可并发"的声明降低误报。

### T6 前端是最大单体，跨端契约未被验证

**证据**：`tui/app.go:50-112` 的 `Model` 有 30+ 字段，7 个界面状态（`:20-28`）共用一个 `Update`（`:233-481`），全局按键路由与聊天逻辑交织；厂商列表在 `app.go:147` 硬编码兜底；UI 层在 `config_wizard.go:22-50` 直接用 `net/http` 探测本地服务。

**后果**：
- 任何新交互都要在 500 行的 `Update` 里加分支，回归面大。
- `protocol` 号称"可复用于桌面端与无头宿主"，但**从未有第二个宿主消费过它**，契约的完整性没有被证伪的机会。

### T7 凭据边界与工作区沙箱冲突

**证据**：`fsutil.go:46-51` 把整个 `~/.tide` 目录加入白名单，而 `~/.tide/config.json` 正是存放 API Key 的位置（`config.go:190-193`）。`bash.go:90-96` 未设置 `cmd.Env`，子进程继承父进程全部环境变量（含 `DEEPSEEK_API_KEY` 等）。

**后果**：模型可以用 `read_file ~/.tide/config.json` 或 `bash: env` 拿到密钥，再通过 `curl` 外发。沙箱防的是"路径逃逸"，但没有防"凭据读取"。这是当前最值得优先处理的安全缺口。

### T8 可观测性只有记录，没有治理

**证据**：`middleware/logging.go:65-85` 每次事件向 `agent.jsonl` 追加一行，永不轮转；`:227-259` 轮末写 `latest.json` 全量快照。没有级别、没有脱敏、没有成本核算。

**后果**：长期使用后日志无限增长；prompt 中可能包含用户敏感内容；Token 成本只能看单轮数字，无法按天/按模型汇总。

---

## 四、目标架构 v2

### 4.1 分层与职责

```text
┌──────────────────────────────────────────────────────────────┐
│ cmd/tide  (唯一组合根：知道所有具体实现，只做装配与启动)        │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
        ┌───────▼────────┐            ┌────────▼────────┐
        │ host/tui       │            │ host/headless   │
        │ (Bubble Tea)   │            │ (JSON 事件流)    │
        └───────┬────────┘            └────────┬────────┘
                └──────────┬───────────────────┘
                    ┌──────▼──────┐
                    │  protocol   │  纯数据契约：Event / DTO / 宿主门面
                    └──────┬──────┘
                    ┌──────▼──────────────────────────────┐
                    │  runtime：Session / Turn / Budget    │
                    │  只依赖端口接口，不依赖具体实现        │
                    └──┬────────┬─────────┬────────┬──────┘
                       │        │         │        │
              ┌────────▼──┐ ┌───▼────┐ ┌──▼─────┐ ┌▼─────────┐
              │ context   │ │capabil-│ │ policy │ │ provider │
              │ transcript│ │ ity    │ │ 权限/  │ │ wire +   │
              │ 压缩/记忆 │ │ 工具/  │ │ 沙箱/  │ │ catalog  │
              │           │ │ MCP/技能│ │ 脱敏   │ │          │
              └───────────┘ └────────┘ └────────┘ └──────────┘
                       └──────────┬─────────┘
                            ┌─────▼─────┐
                            │  config   │ 只做加载/保存/发现/环境变量
                            └───────────┘
```

### 4.2 依赖规则（必须自动化守护）

| 编号 | 规则 | 违反示例（现状） |
|---|---|---|
| R1 | `protocol` 不得 import 任何 `internal/*` | 当前满足，需锁死 |
| R2 | `provider`（含 wire）不得 import `config` | 现状违反（`gateway.go:17`） |
| R3 | `runtime` 不得 import 具体 capability/context/policy 实现，只依赖端口接口 | 现状 `agent` import `builtin` |
| R4 | `host/*` 只能 import `protocol` 与 runtime 门面，不得 import `config`/`gateway`/`tool` | 现状 TUI import `net/http` 做探测 |
| R5 | 只有 `cmd/`（或 `bootstrap`）可以同时 import 全部实现包 | 现状 `agent.NewFromConfig` 越位装配 |

### 4.3 关键模型

**Session（新）**

```go
type Session struct {
    ID        string        // 稳定标识，用于 /resume 与审计
    WorkDir   string
    CreatedAt time.Time
    Transcript Transcript     // 追加式、落盘、全量原文
    Settings  SettingsSnapshot // provider/model/预算，随会话固化
}
```

**Turn（新）**

```go
type Turn struct {
    ID     string
    Seq    uint64   // 会话内单调递增
    Budget Budget   // MaxSteps / MaxDuration / MaxTokens
    Status TurnStatus
}
```

**Event（演进，不推翻）**：在现有 7 个字段上增加 `TurnID`、`Seq`、`MessageID`。前端不再靠 `lastIdx` 推断归属。

**上下文三层**

| 层 | 内容 | 生命周期 | 用途 |
|---|---|---|---|
| L0 Transcript | 全量消息（含工具结果完整版） | 落盘，永不丢 | 恢复、审计、重新压缩 |
| L1 Working Set | 预算内的最近若干轮 | 每步重建 | 实际发给模型 |
| L2 Summary | 被淘汰轮次的滚动摘要 | 随淘汰增量更新 | 保留远期目标与约束 |

**Tool 元数据（演进）**

```go
type Spec struct {
    Name, Description string
    Schema            json.RawMessage
    Timeout           time.Duration
    ConcurrencySafe   bool
    ReadOnly          bool
    OutputBudget      int
    Trust             TrustLevel // builtin / workspace / external
}
```

### 4.4 关键决策（ADR）

| 编号 | 决策 | 理由 | 代价 |
|---|---|---|---|
| ADR-1 | 会话持久化采用**追加式 JSONL transcript**，不用数据库 | 单用户、可读、可 diff、崩溃安全；与现有 JSONL 审计一致 | 需要自己处理轮转与索引 |
| ADR-2 | 事件补 `TurnID/Seq/MessageID`，前端禁止位置推断 | 多宿主与回放的硬前提 | 一次性改 TUI 事件处理 |
| ADR-3 | 上下文治理采用**三层 + 滚动摘要**，裁剪单位是轮，压缩单位是段 | 保留远期约束，避免整轮丢失 | 摘要调用本身消耗 token |
| ADR-4 | 能力注册在组合根完成，内核只认 `Tool` 接口与 `Spec` | 加 MCP/技能/子代理不必改内核 | 装配代码变长（可接受） |
| ADR-5 | 厂商目录（catalog）与传输、配置**三方分离**；模型能力显式声明 | 上下文预算、工具支持、reasoning 字段都需要能力位 | 迁移面较大 |
| ADR-6 | 凭据与工作区分离：`~/.tide` 白名单收窄到 `memory/`；配置只经专用 API 访问 | 消除"读配置拿密钥"路径 | 需调整 `fsutil` 白名单与测试 |
| ADR-7 | 保持 OpenAI-only，不引入第二套原生协议 | 单一适配器是当前最大简化来源 | Gemini 原生能力不可用（已知取舍） |

---

## 五、路线图

> 规模用 S/M/L 表示相对投入，不排日历时间。每阶段结束**暂停验收**，通过后才进入下一阶段。

### 阶段 0：架构守护与基线（S｜无用户可见变化）

**目标**：让"结构退化"在 CI 里立刻失败，而不是等到下一轮评审才发现。

**范围**：
- 新增 `internal/archtest`：用 `go list -deps` 断言 R1–R5（先允许 R2/R3 的现状豁免，随阶段 1 逐步收紧）。
- 固化基线：各包生产/测试行数、依赖边、关键 benchmark（`renderChatMessages`、`BuildContext`、首 token 路径）。
- 统一「不变量清单」：轮次原子性、tool_calls 配对、出站无 `reasoning_content`、路径边界、权限默认拒绝。

**交付物**：`internal/archtest/`、`outputs/ARCH_BASELINE.md`（自动生成脚本）。

**验收**：
- `go test ./internal/archtest` 通过；人为在 `gateway` 加一行 `config` import 时测试失败。
- `make verify` 纳入 archtest。
- 基线文件可由 `go run ./internal/archtest -update` 重生成。

**风险**：低。仅新增测试与文档。

---

### 阶段 0.5：凭据边界快修（S｜安全，建议紧随阶段 0）

**目标**：关掉"模型可读密钥并外发"的路径（T7）。

**范围**：
- `fsutil.ResolveInWorkspace` 白名单从整个 `~/.tide` 收窄为 `~/.tide/memory`。
- 配置文件访问改由 `config` 包专用 API 提供；文件工具不再可达。
- `bash` 子进程环境变量白名单化：剥离 `*_API_KEY`、`*_TOKEN`、`*_SECRET`（可配置保留项）。
- 工具输出与日志增加基础脱敏：`sk-`、`AIza`、`Bearer ` 模式替换为 `[REDACTED]`。

**验收**：
- `read_file ~/.tide/config.json` 被拒绝；`read_file ~/.tide/memory/preferences.md` 允许。
- `bash: env` 输出不含已配置的 provider 密钥。
- 单测覆盖三类密钥模式脱敏。

**风险**：中低。环境变量剥离可能影响依赖凭据的合法命令（如 `gh`、`aws`），需提供显式放行名单并在错误信息中说明。

---

### 阶段 1：依赖收敛（M｜无用户可见变化）

**目标**：拆掉上帝包与反向依赖，把组合根移出内核（T1、T2、R2–R5）。

**范围**：
1. 新建 `internal/provider`：厂商目录（元数据、别名、默认端点/模型、**能力位**：上下文窗口、tools、reasoning 字段）+ `Endpoint` 值对象（BaseURL/APIKey/Model/AuthStyle）+ OpenAI wire 客户端。`gateway` 包并入或薄封装 `provider`，不再 import `config`。
2. `internal/config` 收缩为：路径发现、加载、保存、环境变量补全，产出 `Settings` 值对象；删除元数据表、模型推断、`ToView()`。
3. 新建 `internal/bootstrap`（或直接放 `cmd/tide`）：负责 `Settings → provider.Endpoint → runtime → tools → hooks` 的装配。删除 `agent.NewFromConfig`、`agent.WithDefaultTools`。
4. `protocol` 拆分：Trace DTO 迁至 `internal/trace`；`Agent` 接口移除 `UpdateConfig`，改由 `bootstrap.SettingsService` 提供给宿主；`ConfigView` 保留为纯 DTO，由 host adapter 组装。
5. TUI 删除硬编码厂商列表与 `net/http` 探测，改由 `protocol.ConfigView` + provider 目录提供；探测移到 `bootstrap` 的健康检查端口。

**验收**：
- `go list -deps ./internal/provider | grep internal/config` 为空。
- `go list -deps ./internal/runtime（或 agent）| grep tool/builtin` 为空。
- 现有 101 个用例全绿；`/model` 向导、四厂商切换、日志面板手工回归通过。
- 二进制行为等价：同一 prompt 的事件序列与改造前一致（golden 对比）。

**风险**：中。属于大面积机械重构，但无行为变更；用 archtest + golden 事件序列兜底。**这是全路线图唯一一次"动地基"的阶段，之后不再做大搬迁。**

---

### 阶段 2：会话与单轮运行时（L｜用户可见：可恢复）

**目标**：把"会话"变成一等公民（T3）。

**范围（建议拆 2A/2B 两个独立提交批次）**：
- **2A 持久化与恢复**：`internal/session`（ID、transcript JSONL、索引、保留策略）；`--continue` / `/resume`；崩溃后从未完成轮次恢复（补齐未配对 tool_calls，复用现有取消补齐逻辑）。
- **2B 事件身份与预算**：`Event` 增加 `TurnID/Seq/MessageID`；TUI 改为按 `MessageID` 归并；单轮预算（步数/时长/token）可配置；审批增加超时（默认拒绝）。

**验收**：
- 生成中 `kill -9`，重启 `--continue` 后上下文完整，且不会出现孤立 tool_calls。
- 事件 `Seq` 在会话内单调递增；同一 `MessageID` 的 delta 可正确归并。
- 预算触顶时以 `EventError` 收敛，历史仍完整可继续对话。
- 审批无人响应超时后返回 Deny，且模型收到可读原因。

**风险**：高（状态迁移最大）。用 2A/2B 分批降低单次风险；transcript 格式先定为版本化 JSONL（首行 `{"v":1}`）。

---

### 阶段 3：上下文治理（M｜用户可见：长任务不丢约束）

**目标**：从"截断"升级为"压缩 + 保留"（T4）。

**范围**：
- L1 预算改为由 `provider` 能力位推导（上下文窗口 − 系统提示 − 工具 Schema 预留）。
- L2 滚动摘要：被淘汰的轮次按段摘要，摘要作为一条 system/assistant 注记进入工作集；**pinned 消息**（首条用户目标、用户显式约束、最近 N 轮）永不淘汰。
- 长期记忆改为**按需检索**：系统提示只注入记忆索引（标题 + 一行摘要），正文通过 `memory_search` 工具读取；写入走 `memory_write` 工具并做冲突提示。
- 压缩可观测：记录压缩次数、被压缩轮次、摘要 token 成本。

**验收**：
- 构造 200 轮合成会话，最终请求的估算 token 始终低于模型窗口的 80%。
- 首轮用户约束在 200 轮后仍出现在请求 payload 中（pinned 断言）。
- 关闭摘要开关时行为回退到阶段 2 的截断语义（便于对照）。
- 记忆正文不再全量注入：系统提示体积较现状下降（基线对比）。

**风险**：中。摘要可能丢信息——用 pinned + transcript 可回读兜底；摘要调用失败时降级为截断并发出可见提示。

---

### 阶段 4：能力扩展面（L｜用户可见：可接外部工具）

**目标**：让"加能力"不再等于"改内核发版"（T5）。

**范围（按 4A→4D 递进，每批独立验收）**：
- **4A 工具生命周期**：`Spec` 元数据落地；单工具超时、输出预算、`ReadOnly`/`ConcurrencySafe`；同一 assistant 消息内多个 `tool_calls` 在声明可并发时并行执行（并发上限可配），结果按调用顺序回填。
- **4B MCP 适配**：stdio 优先，工具命名空间 `mcp__<server>__<tool>`，默认 `TrustExternal`（首次调用必须审批）；服务器生命周期由 bootstrap 管理。
- **4C 技能加载**：目录约定 `SKILL.md`；系统提示只放索引，正文按需读取（渐进披露）。
- **4D 子代理**：`task` 工具启动受限子会话（独立 transcript、受限工具集、独立预算），返回结构化摘要；依赖阶段 2 的 Session 抽象。

**验收**：
- 本地 echo MCP server 接入后，模型可发现并调用其工具；未审批时被拒绝。
- 两个只读工具的并发执行总耗时显著低于串行（基准断言），结果顺序稳定。
- 技能正文不进入初始系统提示（payload 断言）。
- 子代理的上下文与主会话隔离，预算独立核算。

**风险**：中高。MCP 引入外部进程与新的信任边界——默认最严策略，且不引入远程 MCP（仅 stdio）直到有真实需求。

---

### 阶段 5：宿主收敛与前端拆分（M｜用户可见：新增 headless）

**目标**：用第二个宿主证伪/证实契约，并把 TUI 从单体状态机拆开（T6）。

**范围**：
- 新增 `host/headless`：`tide run "<prompt>" --output-format json|text`，直接消费 `protocol.Event` 流；用于脚本、CI、自动化。
- TUI 状态机拆分：每个 state 独立 `Update/View` 处理器，`Model` 只保留共享依赖（agent、traces、尺寸）与路由；删除 `Update` 中的聊天分支堆积。
- 事件 golden 测试：同一 mock agent 下，TUI 与 headless 消费到的事件序列一致。

**验收**：
- `tide run "..." --output-format json` 输出可被 `jq` 逐行解析，字段与协议文档一致。
- 同一脚本对两种宿主产生一致的事件序列（归一化后逐条相等）。
- TUI 每个状态有独立单测；`app.go` 行数较基线下降 50% 以上。

**风险**：中。TUI 视觉回归——用 golden frame 测试 + 手工清单（聊天/工具卡/审批/思考/日志/向导）。

---

### 阶段 6：可观测性与运维治理（M｜用户可见：doctor 与成本）

**目标**：把"记录"变成"可治理"（T8）。

**范围**：
- 日志分级 + 按大小/天数轮转 + 脱敏（复用阶段 0.5 的脱敏器）。
- `trace` 包统一 Sink 接口：JSONL、内存环形缓冲（TUI）、未来 OTLP。
- 成本核算：按 provider/model 单价累计，`/cost` 查看本会话/本日。
- `tide doctor`：配置有效性、provider 连通性、工作区权限、日志体积、版本一致性。

**验收**：
- 日志达到阈值自动轮转，旧文件按策略清理。
- 日志与工具输出中不出现任何已配置密钥（自动化扫描断言）。
- `/cost` 与会话 transcript 的 usage 汇总一致。
- `doctor` 能在缺 key、端点不可达、工作区不可写三种场景给出可执行建议。

**风险**：低。以增量能力为主。

---

## 六、优先级与依赖

```text
阶段0 ──> 阶段0.5 ──> 阶段1 ──> 阶段2A ──> 阶段2B ──> 阶段3 ──> 阶段4A ──> 4B/4C ──> 4D
                                                              └──> 阶段5 ──> 阶段6
```

| 阶段 | 价值 | 成本 | 风险 | 建议 |
|---|---|---|---|---|
| 0 架构守护 | 高（防退化） | S | 低 | **立即做** |
| 0.5 凭据快修 | 高（安全） | S | 中低 | **立即做** |
| 1 依赖收敛 | 高（地基） | M | 中 | 做，且只做一次 |
| 2 会话运行时 | 很高（可用性） | L | 高 | 做，拆两批 |
| 3 上下文治理 | 高（长任务） | M | 中 | 做 |
| 4 能力扩展 | 高（生态） | L | 中高 | 按需，4A 优先 |
| 5 宿主收敛 | 中高（契约验证） | M | 中 | headless 优先，TUI 拆分随后 |
| 6 可观测治理 | 中（运维） | M | 低 | 最后 |

**关键路径**：0 → 0.5 → 1 → 2 → 3。这五步决定 tide 能不能从"一个好用的终端工具"变成"一个有稳定内核的 Agent 平台"。阶段 4/5/6 可以在关键路径完成后按实际需求调整顺序。

---

## 七、度量与门禁

### 7.1 每阶段必须通过

1. `make verify`（gofmt + vet + `-race` + build）全绿。
2. `go test ./internal/archtest` 全绿，且依赖规则只收紧不放松。
3. 该阶段验收项逐条有对应测试或可复现手工步骤。
4. 新增/修改的公开行为有 golden 或表驱动用例。

### 7.2 结构指标（ratchet，只降不升）

| 指标 | 现状 | 目标 |
|---|---|---|
| `internal/config` 生产行数 | 586 | ≤ 250（阶段 1 后） |
| `internal/tui/app.go` 行数 | 503 | ≤ 250（阶段 5 后） |
| 单文件行数上限 | 728（`config_wizard.go`） | ≤ 600，新增文件不得超过 |
| `protocol` 的 internal 依赖 | 0 | 恒为 0 |
| 每个 `internal/*` 包的测试文件 | 11/12 包有 | 新增包必须有 |

### 7.3 行为不变量（回归清单）

- assistant(`tool_calls`) 与 tool 结果严格配对（含取消/panic/超时路径）。
- 出站 payload 永不含 `reasoning_content`。
- 所有路径裁决经 `fsutil`；所有工具执行经 `Registry.Execute` 钩子链。
- 无审批通道时默认拒绝；硬拒绝表不可被配置清空。
- 事件流在轮次结束时必然以 `Done` 或 `Error` 收敛，通道必然关闭。

---

## 八、风险登记

| 风险 | 触发条件 | 影响 | 缓解 |
|---|---|---|---|
| 阶段 1 重构引入隐性行为变化 | 机械搬迁时顺手"优化" | 高 | 严格 no-behavior-change；golden 事件序列对比；分批提交 |
| 会话文件无限增长 | 长期使用 | 中 | 保留策略（按大小/天数）+ 启动时清理 + 压缩后归档 |
| 摘要丢失关键约束 | 长任务 | 高 | pinned 消息 + transcript 可回读 + 摘要失败降级为截断并提示 |
| MCP 引入不可信工具 | 外部 server | 高 | 默认 `TrustExternal` 必审批；仅 stdio；工具名命名空间隔离 |
| 并发工具破坏权限串行假设 | 4A | 中 | 审批仍在调度前串行完成；只对 `ConcurrencySafe` 工具并发 |
| TUI 拆分导致视觉回归 | 阶段 5 | 中 | golden frame + 手工清单 + 分批迁移状态 |
| 凭据剥离破坏合法命令 | 阶段 0.5 | 中 | 显式放行名单 + 错误信息说明 + 可配置 |

---

## 九、非目标（明确不做）

- **多用户 / 多租户 / 并发请求队列**：本地单用户，不为并发设计协调与锁。
- **第二套模型协议**（Anthropic 原生等）：保持 OpenAI-only；需要原生能力时单独立项评审。
- **云同步 / 远程执行沙箱**：超出本地个人助手定位。
- **向量数据库 / RAG**：先做结构化文件记忆 + 关键词检索，等真实召回问题出现再评估。
- **插件市场 / 远程 MCP**：阶段 4 只做 stdio 本地 server。
- **TUI 视觉重写**：只拆状态机，不动既有美学与交互语言。
- **重写 `fsutil` / 权限规范化 / 工具流水线**：这些是已验证的资产。

---

## 十、待决策（需要你确认）

| 编号 | 决策点 | 推荐 | 影响 |
|---|---|---|---|
| D1 | 会话持久化默认开启还是 opt-in | **默认开启**，保留 30 天/500MB 上限 | 影响阶段 2A 的默认行为与隐私预期 |
| D2 | MCP 是否作为一等扩展面 | **是**，但只做 stdio + 默认必审批 | 影响阶段 4 的范围与安全模型 |
| D3 | 桌面端是否纳入路线图 | **暂不**；先做 headless 验证契约，桌面端单独立项 | 影响阶段 5 的投入与协议稳定化节奏 |
| D4 | 长期记忆是否引入向量检索 | **暂不**；先做索引 + 按需读取 | 影响阶段 3 的复杂度 |
| D5 | 阶段顺序是否接受"先地基后会话语义" | **建议接受**：0→0.5→1→2→3 | 若不接受，需把阶段 2 提前，但会在上帝包上叠会话状态，返工风险更高 |

---

## 十一、下一步

1. 你评审本路线图，确认第十节的 D1–D5（尤其 D5 的阶段顺序）。
2. 批准后，我先产出**阶段 0 + 阶段 1 的详细设计文档**：文件级迁移清单、`provider`/`config`/`bootstrap` 的接口签名、archtest 规则实现方式、101 个用例的改造清单、golden 事件对比方案。
3. 阶段 0 与 0.5 可并行实施（互不触碰同一批文件），各自独立提交、独立验收。
4. 每阶段结束暂停，验收通过后再进入下一阶段。
