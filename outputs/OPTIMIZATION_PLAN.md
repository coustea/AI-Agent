# coustea 优化方案设计文档（v1：待审核）

> 日期：2026-10-15｜状态：**设计草案，待用户审核**。审核通过前不修改任何业务代码。
> 依据：对全仓 32 个 Go 源文件的架构审查结论。每条问题均给出证据（文件:行）、候选方案、推荐项、影响面与验收标准。

---

## 0. 范围与原则

- **本方案只处理审查中确认的 5 个问题**，不夹带无关重构。
- 遵循项目既定约定：不留兼容层/别名/弃用代码；不引入并发或多用户协调；先设计后实施。
- 分三个可独立验收的阶段（A/B/C），每阶段结束提交并暂停等待审核。

---

## 1. 问题清单（含证据）

| 编号 | 问题 | 类别 | 严重度 |
|---|---|---|---|
| P1 | 长期记忆是「启动快照」，运行期不刷新；模板从未播种 | 设计缺陷 | 高 |
| P2 | `bash` 工具仅 5 条字面量黑名单，不构成沙箱 | 安全 | 高 |
| P3 | `Router` 的模型前缀路由是死代码 | 一致性 | 中 |
| P4 | 根 `main.go` 与 `cmd/coustea/main.go` 完全重复 | 可维护性 | 低 |
| P5 | `SlidingWindowMemory` 命名 stutter 遗留 | 命名 | 低 |

---

## 2. P1 —— 长期记忆闭环失效（最高优先级）

### 2.1 证据

- `internal/agent/agent.go:25-53` `BuildDefaultSystemPrompt` 调用 `memory.LoadBundle(workDir)`，把记忆内容烘焙进系统提示词。
- 调用点仅两处：`NewAgent`（`agent.go:181`）与 `WithWorkDir`（`agent.go:127`）。**运行期不再重建**。
- `internal/memory/storage.go:185` `InitTemplates` 在生产代码中**零调用**（仅 `storage_test.go:94` 使用）→ 模板文件从不生成，`LoadBundle` 永远读不到内容。
- `agent.go:45` 系统提示词明确要求模型用 `write_file` 沉淀记忆到上述目录 → 但同会话内写入**本进程内永不生效**。

### 2.2 根因

记忆注入与「系统提示词」耦合，且注入时机被固定在**构造期一次**。同时记忆系统缺少启动播种，导致「模型被要求写记忆，但记忆目录是空的、写了也看不到」的自相矛盾闭环。

### 2.3 方案

将系统提示词拆成两个正交部分，记忆部分**每轮动态重算**：

- **persona（静态）**：身份、准则、工作目录；可由 `WithSystemPrompt` 覆盖。
- **memoryBlock（动态）**：每轮 `StreamRun` 开始时重新 `LoadBundle(workDir).FormatForPrompt()`。

**具体改动点**

1. `CoreAgent` 用 `persona string` 取代现在的 `systemPrompt string` 语义（persona 为静态部分）。
2. 新增内部方法 `composeSystemPrompt() string`：`persona + "\n\n" + memory.LoadBundle(a.workDir).FormatForPrompt()`。
3. `StreamRun` 在 **ReAct 循环之外、每用户轮次一次** 调用 `composeSystemPrompt()`，结果传给 `memory.BuildContext`（替换 `agent.go:283` 处直接读取 `a.systemPrompt`）。
4. `SystemPrompt()` 改为返回 `composeSystemPrompt()`（用于 TUI 展示，实时反映）。
5. `NewAgent`（`agent.go:174`）与 `WithWorkDir`（`agent.go:126`）中的 `memory.EnsureDirs` 改为 `memory.InitTemplates`（其内部已调用 `EnsureDirs`），实现启动播种。

### 2.4 刷新粒度（**待用户决策**）

| 选项 | 说明 | 评价 |
|---|---|---|
| (a) 每用户轮次刷新 | 每次 `StreamRun` 重读一次 | **推荐**：成本可忽略（3 个小 md），语义清晰；本轮内工具写入下一轮可见 |
| (b) 每 ReAct step 刷新 | 循环内每步重读 | 本轮内即时可见，但每步读盘、且模型可能看到自身中间态，收益低 |
| (c) 手动 `/memory reload` | 由用户显式触发 | 可控但反直觉，模型写入仍需用户操作才生效 |

### 2.5 影响面与风险

- 影响文件：`internal/agent/agent.go`（核心）、`internal/agent/agent_test.go`（补测）。
- `memory` 包对外签名不变；TUI 无感。
- 风险：若用户通过 `WithSystemPrompt` 自定义了提示词，是否仍追加记忆块？**默认建议追加**（记忆是系统级能力），并提供 `WithMemoryInjection(false)` 显式关闭（**待用户确认**）。

### 2.6 验收

- 单元测试：构造临时工作区 → `NewAgent` 后模板文件已生成 → 模拟写入 `learnings.md` → 下一轮 `StreamRun` 的 system message 中包含该内容（上一轮写入的可见）。
- `go test ./...`、`go build ./...` 通过。

---

## 3. P2 —— bash 工具安全加固

### 3.1 证据

- `internal/tool/builtin/bash.go:64-69`：`dangerous` 仅 5 条字面量子串（`rm -rf /`、`sudo`、`shutdown`、`reboot`、`> /dev/`）。`rm -rf ~`、`mkfs`、`dd`、`curl | sh` 全部放行。
- 对比 `internal/tool/builtin/safe_path.go:11-60`：read/write/edit 有「工作区 + `~/.coustea`」双边界校验，防护强度明显不对称。
- `internal/tool/tool.go:71-115`：`Registry.Execute` 直接「校验参数 → 执行」，**不存在中间件洋葱链**（`ARCHITECTURE_PLAN.md` 1C 曾计划，但代码中未实现）→ 安全接缝目前不存在。

### 3.2 候选方案

| 方案 | 内容 | 成本 | 强度 |
|---|---|---|---|
| **A. 静态策略层（本阶段）** | 归一化 + 三档分类（allow/confirm/deny） | 低 | 中（仍非沙箱） |
| **B. 审批中间件（对齐路线图阶段 3）** | 新增 `tool.Middleware` 洋葱链 + `Approver` 接口，confirm 档命令经 TUI 确认 | 中 | 高 |
| **C. 真沙箱** | macOS `sandbox-exec` / 容器 / 受限用户 | 高 | 最高 |

### 3.3 方案 A 具体设计（推荐本阶段实施）

- **归一化**：折叠连续空白、去除 `\` 续行、小写化后再匹配，规避 `rm    -rf   /` 之类的变体绕过。
- **三档分类**：
  - `allow`：只读类（`ls`、`cat`、`grep`、`rg`、`find`、`git status` 等）。
  - `confirm`：写盘/网络/包管理（`rm`、`mv`、`curl`、`wget`、`npm`、`pip`、`git push` 等）。
  - `deny`：破坏性（危险目标的 `rm -rf`、`mkfs`、`dd of=/dev/`、fork bomb、`> /dev/`、`chmod -R 777 /`、`shutdown`/`reboot` 等）。
- **当前阶段行为**：`deny` → 拒绝；`confirm` → 在无 UI 审批的情况下**默认拒绝并提示需人工确认**（为阶段 3 预留）。
- 落地为独立文件 `internal/tool/builtin/policy.go`（策略与 `bash.go` 解耦，便于测试与后续替换）。

### 3.4 是否同时落中间件接缝（**待用户决策**）

- 选项一：**仅做 A**，接缝留到阶段 3（更聚焦，改动最小）。
- 选项二：**A + 定义接缝接口**（新增 `tool.Middleware` 类型与 `Registry` 的链式调用点，但**不接 TUI**），让阶段 3 只写 TUI 侧。

### 3.5 影响面与风险

- 影响文件：`internal/tool/builtin/bash.go`、新增 `policy.go`、`builtin_test.go`（补用例）；若选选项二则含 `internal/tool/tool.go`。
- 风险：黑名单/分类永远不完美，**文档中如实声明「这是纵深防御的一层，不是沙箱」**。
- 风险：`confirm` 档默认拒绝会降低可用性（模型可能反复尝试被拒）；需在系统提示词中说明该约束，减少无效重试。

### 3.6 验收

- 表驱动测试：各类变体（含空白折叠、`curl | sh`、`rm -rf ~`）命中预期档位；`deny` 被拒、`confirm` 被拒并返回明确提示、`allow` 正常执行。
- 现有 `TestBashTool` 保持通过（或按新语义更新）。

---

## 4. P3 —— Router 前缀路由死代码

### 4.1 证据

- `internal/gateway/router.go:57-74`：前缀分支仅在 `req.Model != ""` 时生效。
- `internal/agent/agent.go:294-297`：构造 `ChatRequest{Messages, Tools}`，**从不设置 `Model`**。
- `req.Model` 仅出现在 `gateway_test.go:439/448`；`Router.SetActive` 仅被测试调用（`agent_test.go:705`、`gateway_test.go:464`）。
- 结论：前缀路由在生产路径上**永不可达**。

### 4.2 方案

| 选项 | 内容 | 评价 |
|---|---|---|
| **A（推荐，最小）** | 删除 `router.go:57-74` 前缀分支；Router 收敛为「激活厂商选择器」，补注释说明单一 OpenAI 协议下 model 已固化在 provider 实例内 | 去死代码，行为不变 |
| B | 让 Agent 感知并写入 `ChatRequest.Model` 以真正启用路由 | 需把 model 从 config 透传到 agent，破坏「Agent 不感知厂商/模型」边界，收益低 |
| C（后续评估） | v0.4 已统一协议、TUI 靠 `SetGateway` 热切换，评估 Router 退化为「单 Gateway」 | 较大重构，单独评审 |

### 4.3 影响面

- `internal/gateway/router.go`；`gateway_test.go` 中依赖前缀路由的用例需相应调整。
- 推荐本阶段只做 A，C 列入「后续评审」清单。

---

## 5. P4 —— 双入口冗余

### 5.1 证据

- 根 `main.go` 与 `cmd/coustea/main.go` 逐行相同（各 36 行）。
- `AGENTS.md:5` 已声明以 `cmd/coustea/` 为准；`Makefile` 只用 `./cmd/coustea`。

### 5.2 方案

- 删除根 `main.go`。
- 修订 `AGENTS.md` 中「`main.go` is a root-level entry point」措辞，明确单一入口。
- `go build ./...`、`make build`、`make run` 均不受影响。

### 5.3 影响面

- 删 1 个文件 + 改 1 处文档。零行为风险。

---

## 6. P5 —— 命名 stutter

### 6.1 证据

- `internal/memory/sliding_window.go:13/20`：`SlidingWindowMemory` / `NewSlidingWindowMemory`。
- 同包内 `MemoryFile`/`MemoryBundle` 已在上一轮清理为 `File`/`Bundle`，命名风格尚未统一。

### 6.2 方案

| 项 | 现状 | 建议 | 优先级 |
|---|---|---|---|
| 记忆实现 | `memory.SlidingWindowMemory` | `memory.SlidingWindow`（`NewSlidingWindow`） | **必做** |
| Agent 核心 | `agent.CoreAgent` | `agent.Core` | 可选（待定） |
| 网关接口 | `gateway.Gateway` | `gateway.Client` | 可选（待定） |

> 说明：`tool.Tool`、`config.Config` 属 Go 惯用（类比 `io.Reader`），**建议保留**。

### 6.3 影响面

- 必做项：`sliding_window.go`、`agent.go:179`、`memory_test.go`、`agent_test.go:313`。
- 可选项若采纳，影响面更大，建议单独一次提交。

---

## 7. 实施阶段与顺序

| 阶段 | 内容 | 风险 | 验收 |
|---|---|---|---|
| **A. 低风险清理** | P4（删双入口）+ P5 必做项 + P3 方案 A | 极低（纯删除/改名/去死代码） | `go build`/`go test`/`make build` 通过 |
| **B. 记忆闭环** | P1（persona/memory 拆分 + 每轮刷新 + `InitTemplates` 播种） | 中 | 记忆写入下一轮可见的单元测试通过 |
| **C. 安全加固** | P2 方案 A（策略层），按决策决定是否含接缝 | 中 | 表驱动策略测试通过 |

- 每阶段独立提交、独立验收，**验收后暂停等待审核**再进入下一阶段。

---

## 8. 明确不做（边界）

- 不实现路线图阶段 3 的 TUI 交互审批（除非用户选择在本轮定义接缝接口）。
- 不实现真沙箱（`sandbox-exec`/容器/受限用户）。
- 不引入并发或多用户协调机制。
- 不为旧命名保留别名或包装层。

---

## 9. 待用户决策的开放问题

1. **P1 刷新粒度**：每用户轮次（推荐）/ 每 ReAct step / 手动命令？
2. **P1 记忆注入**：用户自定义 `WithSystemPrompt` 时，是否仍追加动态记忆块（默认建议追加）？
3. **P2 范围**：本阶段只做策略层 A，还是同时定义中间件接缝接口（选项二）？
4. **P2 confirm 档行为**：无 UI 审批时默认「拒绝」（推荐）还是「放行 + 警告」？
5. **P5 范围**：是否连同 `agent.CoreAgent`、`gateway.Gateway` 一并改名？
6. **P3 后续**：是否将「Router 退化为单 Gateway」（方案 C）列入后续评审？

---

## 10. 附：本次审查新增确认的事实

- `memory.InitTemplates` 在生产代码零调用 → 记忆系统实际处于未启用状态。
- `tool` 包不存在中间件洋葱链 → 安全接缝需新建（若采纳选项二）。
- `Router.SetActive` / `req.Model` 前缀路由在生产路径零调用 → 确认为死代码。
