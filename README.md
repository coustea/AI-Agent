# Mentorly

基于 **CloudWeGo Eino ADK** 的教学智能体系统。核心是一个能自主决策的 TutorAgent：
它理解多轮对话、检索长期记忆、读取文档与图片附件、按需联网搜索，
并能生成真实的**图解（SVG）**、**课件（PPTX）**与**讲解视频（MP4）**。

## 快速开始

```bash
# 1. 配置
cp .env.example .env      # 填入 LLM_API_KEY 与 MYSQL_PASSWORD

# 2. 迁移数据库（保留现有用户数据）
mysql -uroot -p mentorly < migrations/001_agent_first.sql

# 3. 运行
go build -o bin/mentorly ./cmd/server && ./bin/mentorly

# 4. 验证
curl http://127.0.0.1:8080/readyz
```

依赖：Go 1.26+、MySQL 8、Redis（可选）、ffmpeg（视频能力）。

## 架构

系统围绕 **TutorAgent** 组织，不是传统的 Controller / Service / Repository 三层。

```
Frontend
   │
   ▼
internal/transport/http        SSE 编码 · 协议转换 · 权限入口
   │
   ▼
internal/agents/tutor
   ├── harness.go   运行上下文：历史 / 附件 / 工作区 / 消息组装
   ├── agent.go     Agent 构建：模型 · 工具 · Middleware · Skills
   ├── runtime.go   执行与事件转换：消费 Eino Runner 事件 → 业务事件
   ├── events.go    面向前端的事件定义
   ├── store.go     会话与消息持久化
   ├── sandbox.go   文件系统边界
   └── prompt.md    教学约束
   │
   ▼
Eino Runner  →  ChatModelAgent  →  ReAct 循环（框架原生）
   │
   ├── Middleware（官方）
   │   ├── filesystem     读写文件
   │   ├── skill          技能渐进式加载
   │   ├── summarization  上下文压缩
   │   └── reduction      工具结果卸载
   │
   └── ToolGuard（自定义）
   │
   ▼
internal/capabilities          能力模块
   ├── memory        长期记忆（跨会话）
   ├── attachments   附件解析与多模态
   ├── search        联网搜索（可选）
   ├── diagram       图解 → SVG
   ├── presentation  课件 → PPTX
   ├── video         讲解视频 → MP4
   └── artifacts     产物存储与异步任务
```

### 目录

| 目录 | 职责 | 非测试行数 |
|---|---|---|
| `internal/agents/tutor` | TutorAgent 全部代码 | 1986 |
| `internal/agents/tutor/middleware` | ToolGuard | 170 |
| `internal/capabilities/attachments` | 附件上传与解析 | 1147 |
| `internal/capabilities/diagram` | 图解生成 | 1045 |
| `internal/capabilities/video` | 视频生成 | 838 |
| `internal/capabilities/artifacts` | 产物与任务 | 777 |
| `internal/capabilities/presentation` | 课件生成 | 688 |
| `internal/capabilities/memory` | 长期记忆 | 436 |
| `internal/capabilities/search` | 联网搜索 | 190 |
| `internal/transport/http` | HTTP + SSE | 993 |
| `internal/runtime` | 模型 · 身份 · 回调 · 任务 | 678 |
| `internal/app` | 组合根 | 474 |
| `internal/auth` | 认证上下文 | 629 |
| `internal/config` | 配置 | 385 |
| `internal/infra` | MySQL / Redis | 131 |
| `internal/log` `response` | 日志 / 响应体 | 235 |

合计 **10971 行非测试代码 + 2310 行测试**，17 个包，无空目录、无占位实现。

### 设计原则

**1. Agent 自主决策，不写分类路由**

没有 `direct_answer` / `search_answer` / `attachment_answer` 分支，
没有手写 ReAct 循环、Tool Dispatcher 或 LLM ToolCall JSON 解析。
是否调用工具、调用哪个，完全由 Eino 原生 ReAct 机制决定。

**2. Harness 与 Agent 推理解耦**

Harness 只负责把一次请求变成可执行环境：加载历史、校验附件、建工作区、组装消息。
它不决定是否调用工具，也不管理 Agent 内部状态。

**3. Middleware 优先用官方实现**

上下文压缩、技能加载、工具结果卸载全部用 Eino 官方 Middleware。
唯一自定义的 ToolGuard 只做框架没覆盖的事：工具级权限与配额。

**4. 产物必须真实**

图解是能打开的 SVG，课件是能在 PowerPoint 打开的 PPTX，
视频是 ffmpeg 编码的真 MP4。没有外部依赖时明确降级（不注册工具），
绝不用 Mock 或占位文件冒充成功。

## TutorAgent 运行链路

```
POST /api/v1/conversations/:id/messages
   │
   ├─ 1. 认证中间件 → userID
   ├─ 2. Harness.Prepare
   │      ├─ 会话归属校验（不属于 → 404，不泄露存在性）
   │      ├─ 统计消息数（判断首轮）
   │      ├─ 建沙箱：workspace/{uid}/{cid} + offload + skills
   │      ├─ 落库 user 消息（必须在写 SSE 头之前）
   │      └─ 构造消息：历史 + 本轮（含附件多模态）
   ├─ 3. 写 SSE 响应头（此后无法改状态码）
   ├─ 4. Runtime.Run
   │      ├─ 注入 Principal（用户身份唯一来源）
   │      ├─ Agent.Build → 5 个 Middleware + 9 个工具
   │      ├─ Runner.Run → 消费 AgentEvent
   │      │     ├─ assistant 文本 → EventMessage
   │      │     ├─ ToolCalls    → reset + EventToolStart
   │      │     └─ tool 结果   → EventToolEnd + reset
   │      └─ finish：判定终态 → 落库 → EventDone
   └─ 5. 首轮成功 → 异步生成标题
```

### 终态判定顺序（不可调换）

```go
cancelled := errors.Is(runErr, context.Canceled) ||
             errors.Is(runErr, context.DeadlineExceeded) ||
             ctx.Err() != nil
if cancelled { ... }        // 必须先判取消
if runErr == nil { ... }    // 再判成功
```

客户端断开时 `Runner` 可能正常返回 `nil`，但 `ctx` 已取消。
若先判 `runErr == nil`，这一轮会被误记为 `completed`——
用户看到「回答完整」，实际只收到半截。

## SSE 事件契约

```
event: message           data: {"text":"...","reset":false}
event: tool_start        data: {"name":"...","call_id":"...","args":"..."}
event: tool_end          data: {"name":"...","result":"...","elapsed_ms":123}
event: artifact_created  data: {"artifact_id":"...","kind":"...","status":"queued"}
event: artifact_progress data: {"artifact_id":"...","progress":45}
event: artifact_completed data: {"artifact_id":"...","download_url":"..."}
event: error             data: {"message":"...","retryable":false}
event: done              data: {"message_id":1,"status":"completed","elapsed_ms":1234}
: ping                   心跳注释行
```

`reset` 语义：模型调用工具前常先输出过渡语（「让我看一下」），
那段话不属于最终回答，收到 `reset` 时前端应清空已渲染内容。

## Eino Middleware 职责划分

| Middleware | 来源 | 职责 |
|---|---|---|
| `filesystem` | 官方 | ls / read / write / edit / glob / grep |
| `skill` | 官方 | 渐进式加载 SKILL.md，只注入名称与简介 |
| `summarization` | 官方 | 超阈值时把旧对话压成摘要 |
| `reduction` | 官方 | 工具结果过大时卸载到 `/offload` |
| `ToolGuard` | **自定义** | 工具级身份校验与调用配额 |

ToolGuard 必须覆盖四种工具类型，缺一种就会留下完全绕过校验的通道：

```go
WrapInvokableToolCall            // 同步
WrapStreamableToolCall           // 流式
WrapEnhancedInvokableToolCall    // 增强同步
WrapEnhancedStreamableToolCall   // 增强流式
```

`TestAllWrapMethodsImplemented` 守住这一点。

## 工具清单

| 工具 | 能力 | 需要身份 | 配额 |
|---|---|---|---|
| `memory_search` | 检索长期记忆 | ✓ | — |
| `memory_save` | 写入长期记忆 | ✓ | — |
| `memory_delete` | 删除记忆 | ✓ | — |
| `read_attachment` | 读取附件正文 | ✓ | — |
| `list_attachments` | 列出会话附件 | ✓ | — |
| `generate_diagram` | 生成 SVG 图解 | ✓ | 6/轮 |
| `generate_presentation` | 生成 PPTX 课件 | ✓ | 4/轮 |
| `generate_explainer_video` | 生成 MP4 视频 | ✓ | 3/轮 |
| `get_artifact_status` | 查询产物进度 | ✓ | — |
| `web_search` | 联网搜索 | — | — |

配额存在的原因：模型可能陷入「反复生成同类产物」的循环，
视频渲染尤其昂贵。`MaxIterations` 只能在轮次层面兜底。

## Skills

| 技能 | 指导内容 |
|---|---|
| `skills/diagram` | 何时画图、图类型选择、Mermaid 写法、构图原则 |
| `skills/presentation` | 大纲规划、单页结构、要点精简、硬限制 |
| `skills/explainer-video` | 脚本规划、分镜设计、按画面思考 |

Skill 只给工作指导，真实文件处理仍由 Tool 与渲染器完成。

## 产物生成实现

| 产物 | 技术方案 | 外部依赖 |
|---|---|---|
| 图解 SVG | 纯 Go 手写 SVG，内置分层布局 | 无 |
| 课件 PPTX | 纯 Go 手写 OOXML + `archive/zip` | 无 |
| 讲解视频 MP4 | Go 逐帧绘制 → raw RGBA 管道 → ffmpeg | ffmpeg |
| 附件 PDF | 纯 Go 解压内容流 + 提取文本层 | 无 |
| 附件 DOCX/PPTX | 纯 Go 解 `archive/zip` + XML | 无 |

**为什么手写 OOXML 而不引库**：`unioffice` 是商业授权；
社区没有许可宽松且维护中的纯 Go pptx 写入库。
手写约 500 行即可产出 PowerPoint 能打开的合法文件。

**为什么视频不用 ffmpeg 的 drawtext**：本机 ffmpeg 未编译该滤镜。
文字由 Go 用 `golang.org/x/image/font` 光栅化进帧，
raw RGBA 通过 stdin 管道交给 ffmpeg，不落中间 PNG。

## 数据模型

```
users          认证（既有表，结构不变）
conversations  会话
messages       消息（含 attachment_ids）
memories       长期记忆
attachments    附件元数据 + 提取文本
artifacts      产物元数据 + 异步任务状态
```

### 迁移

`migrations/001_agent_first.sql` 幂等，可重复执行：

- `chat_sessions` → `conversations`（保留全部行）
- `chat_messages` → `messages`（保留全部行）
- `session_id` → `conversation_id`
- 删除 `summary` / `summary_cursor` / `context_tokens` / `memory_cursor`
  （上下文压缩改由官方 Middleware 在运行时完成，原始消息不删）
- `last_active_at` → `updated_at`
- 新增 `messages.attachment_ids`

**破坏性变更不走 AutoMigrate**：启动时只建表与加列，不删列改类型。

## 用户与文件隔离

- **身份唯一来源**是 `runtime.Principal`，由 Harness 注入 context；
  模型无法通过工具参数伪造 `user_id`。
- **归属校验**在 Store 层统一完成，不属于该用户时返回与「不存在」
  相同的错误，避免通过状态码探测他人资源。
- **文件路径**由服务端生成（UUID），绝不拼接用户输入；
  沙箱对每个路径做 Clean + 前缀校验 + 符号链接解析。

已验证：跨用户读取会话 / 发消息 / 查询产物 / 下载产物均返回 404。

## 开发

```bash
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
```

需要外部环境的测试会自行跳过（缺 ffmpeg、缺字体、缺测试文件），
不会把环境缺失伪装成测试通过。

## 配置要点

| 配置 | 说明 |
|---|---|
| `llm.base_url` | **不能**含 `/chat/completions`，eino 会自行拼接 |
| `llm.timeout` | 必须 ≥ `chat.run_timeout` 的一半，否则长回答会被截断 |
| `llm.vision` | 模型不支持图片时必须设 `false`，否则请求被供应商拒绝 |
| `chat.summary_trigger_*` | 官方压缩中间件的触发阈值 |
| `artifacts.ffmpeg_path` | 留空时用 PATH 里的 ffmpeg；找不到则不注册视频工具 |
| `search.api_key` | 留空时不注册搜索工具 |

## 未来扩展：多 Agent 资源生成

当前 diagram / presentation / video 是独立 Capability。
升级为多 Agent 时：

```
internal/agents/
├── tutor/                 现有，负责交互与任务委派
└── resource/              新增
    ├── planner/           大纲与分镜规划
    ├── diagram/           图解制作
    ├── presentation/      课件制作
    └── video/             视频制作
```

改造点只在 `app.buildTools`：把当前的 `tool.BaseTool` 换成
`adk.NewAgentTool(resourceAgent, ...)`。TutorAgent 主体不需要改动。

**现在不创建空目录**，也不提前实现 `AgentRegistry` / `AgentFactory`——
没有第二个 Agent 时，这些抽象只会增加阅读成本。
