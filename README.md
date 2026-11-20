# Mentorly Backend

Go + Gin + GORM + eino ADK + MySQL + Redis 的学习辅导后端。
核心能力是一个 **Agent Harness 架构**的 ChatAgent：多轮流式对话、会话隔离、
调用前上下文压缩、调用前长期记忆提取、工具调用、会话工作目录与技能加载。

## 技术栈

| 组件 | 库 | 版本 |
| --- | --- | --- |
| Web 框架 | `github.com/gin-gonic/gin` | v1.12.0 |
| 配置 | `github.com/spf13/viper` + `github.com/subosito/gotenv` | v1.21.0 / v1.6.0 |
| 日志 | `go.uber.org/zap` + `gopkg.in/natefinch/lumberjack.v2` | v1.28.0 / v2.2.1 |
| ORM | `gorm.io/gorm` + `gorm.io/driver/mysql` | v1.31.2 / v1.6.0 |
| Redis | `github.com/redis/go-redis/v9` | v9.23.0 |
| Agent | `github.com/cloudwego/eino` (ADK) | v0.9.23 |
| 模型 | `eino-ext/components/model/openai` | v0.1.13 |
| 鉴权 | `golang-jwt/jwt/v5` + `x/crypto/bcrypt` | v5.3.1 |

## 架构：以「一轮对话」为中心

本项目不采用 controller → service → dao 的传统后端分层。
系统的设计单元是**一轮对话（turn）**，不是任何一层：Agent 围绕它运转，
存储、窗口裁剪、记忆提取、HTTP 都只是这一轮对话的不同视角。

```
HTTP / CLI / 测试（任意驱动方）
  │
  ▼
internal/turn          编排者：一轮对话的完整生命周期
  ├─ 1. Acquire        Redis 会话锁 · 归属校验 · 落库 user 消息
  │                    （必须在流式响应头之前完成，404/409 才能是标准 JSON）
  ├─ 2. Prepare        记忆提取 → 上下文压缩 → 重建窗口与 Prompt
  ├─ 3. Run            构建 Agent · 流式执行 · 推送 Event
  └─ 4. Commit         按终态落库 · 回写用量 · 首轮异步标题
  │
  ▼  Event{Delta|Reset|Done|Error}
internal/httpapi       唯一知道传输格式的地方：把 Event 编码成 SSE
```

关键设计：**编排核心不产生 `sse.Frame`**。
旧实现里 harness 直接构造 SSE 帧，等于让核心逻辑绑定一种传输格式；
现在它只发出领域事件，HTTP、CLI 或测试可以各自解释。

### 分层与依赖方向

```
        httpapi  ─────────┐
                          ▼
        turn  ──►  memory / window / agent / capability
          │              │
          └──────►  chat / dialogue / identity
                          │
                          ▼
                   platform/store
```

规则只有三条：

1. **依赖只向下**。`dialogue` 不依赖任何框架，任何层都可以引用它。
2. **存储细节不上浮**。GORM 行类型只存在于各自的存储包内，
   对外一律暴露 `dialogue` 的领域类型，边界处只转换一次。
3. **不受框架污染的包不引入框架**。`window` 是纯计算，`agent` 不碰 DB/Gin，
   `memory` 只面对消息切片和最小 LLM 接口——因此都能被单测完全覆盖。

### 包职责

| 包 | 职责 | 依赖 |
| --- | --- | --- |
| `dialogue` | 领域模型：消息、会话、状态、轮数 | 无 |
| `window` | 上下文窗口裁剪与 token 估算（纯计算） | dialogue |
| `agent` | 无状态 ADK Agent 构建与流式消费 | dialogue |
| `capability` | 能力（工具）注册表 | agent, memory |
| `memory` | 长期记忆提取、会话摘要压缩、标题生成 | dialogue, window, chat |
| `chat` | 会话与消息存储、会话管理面 | dialogue |
| `turn` | **一轮对话的编排者** | 上述全部 |
| `identity` | 用户身份、注册登录、账号状态 | — |
| `platform/*` | 配置、日志、LLM、鉴权、存储连接 | — |
| `httpapi` | 参数绑定、事件编码、状态码映射 | turn, chat, memory, identity |

### 压缩基线的计算陷阱

压缩后的 `context_tokens` 不能简单用「本地估算的 system + 摘要 + 保留原文」。
eino 会在真实 prompt 里注入**工具 Schema 与技能清单**，这部分固定开销实测约
4500-4900 token，本地估算器完全看不到。

若直接用估算值当新基线（实测算出 3612，真实 6803），下一轮立刻又超阈值，
于是反复压缩却始终降不下来。正确做法是从真实基线里**剥离可压缩部分**
（旧摘要 + 被压缩的原文），保留固定开销，再加上压缩后的新内容。
日志里的 `fixed_overhead` 字段就是这项诊断值。

### 为什么压缩与记忆提取要前置

在构建上下文阶段先检查阈值，达到条件就先完成记忆提取和滚动压缩，
**再用更新后的摘要、记忆和剩余历史重建上下文**，最后才创建 Agent。
这样当轮模型拿到的记忆与上下文永远是最新的，也不会超限。

顺序不可交换：先提取记忆，才能在压缩丢弃原文前保住长期信息。

### 新增一个工具只需一行

```go
caps := capability.NewRegistry(
    capability.Memory(adapters),   // remember：主动记录学生信息
    // 新增能力在此追加，未启用时返回 nil 会被自动跳过
)
agentBuilder := agent.NewBuilder(model, skillsDir, caps.Tools())
```

旧实现里工具在 router 硬编码后作为可变参数传下去，加一个要改三处且无法按环境开关。

## 目录结构

```
internal/
  dialogue/              # 领域模型：Message / Session / 状态常量
  turn/                  # ★ 编排者：Prepare / Run / Commit
    turn.go              # 事件、状态、对外错误
    orchestrator.go      # 四阶段编排 + 三步上下文管线
    lock.go              # store.Lock → turn.Lock 适配
  window/                # 纯计算：预算裁剪 + 压缩窗口切分 + token 估算
  memory/                # 长期记忆与会话摘要（跨轮、跨会话）
    consolidator.go      # 阈值判断 + 长期记忆整合
    digest.go            # 阈值判断 + 滚动压缩 + Prompt 拼装
    store.go             # Markdown 读写、去围栏、空小节剔除、待整合小节
    adapter.go           # chat/memory 仓储 → Transcript/Store/Recorder
    service.go           # 记忆管理面 + 异步标题生成
    prompts/{summarize,consolidate}.md
  chat/                  # 会话与消息存储 + 会话管理面
    model.go             # sessionRow / messageRow / MessageMeta
    repo.go              # 仓储（对外只返回 dialogue 类型）
    service.go           # 创建/列表/重命名/删除/历史分页
  identity/              # 用户、注册登录、账号状态回查
  capability/            # 能力注册表
  agent/                 # 无状态 Agent（不碰 DB/Redis/Gin/SSE）
    prompt.go            # 静态底座(embed) + 唯一的 Prompt 拼装实现
    sandbox.go           # filesystem.Backend，三挂载点 + 越界防护
    tools.go             # remember 工具
    builder.go           # 按轮创建 adk.ChatModelAgent + Runner
    stream.go            # 流式消费、reset、用量捕获
    prompts/tutor.md
  httpapi/               # 唯一知道 HTTP/SSE 的地方
    chat.go              # 会话接口 + SSE 编码
    convert.go           # 领域类型 → dto
    dto/
  platform/
    config/ logger/ llm/ auth/
    store/               # MySQL/Redis 连接与分布式锁
  middleware/            # 请求 ID、访问日志、恢复、CORS
pkg/sse/sse.go           # SSE 帧与心跳
skills/modern-diagram/   # Mermaid 绘图技能
scripts/fake_llm.py      # 本地假模型，用于离线端到端验证
```

**依赖方向**：`httpapi → turn → {memory, window, agent, capability} → {chat, dialogue}`。
`agent` 不依赖 `memory`/`chat`/`gin`/`sse`；`turn` 只发出领域事件，
`httpapi` 才把它编码成 SSE。所有装配集中在 `router`。

## 配置

三段式加载，与 HyperWeaver 一致：

```
.env (gotenv) → config.yaml 的 ${ENV} 占位符 → os.ExpandEnv → viper → 结构体 → validate
```

**未定义的环境变量会让启动失败并报出变量名**；显式留空（如本机 Redis 无密码）放行。

### LLM 配置

```bash
LLM_PROVIDER=spark                              # spark / openai
LLM_MODEL=spark-x2.6
LLM_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2
LLM_API_KEY=...
```

> **注意**：`LLM_BASE_URL` **不能**带 `/chat/completions`——eino 会自行拼接，
> 带了就变成 `/v2/chat/completions/chat/completions` 并 404。
> 代码里 `normalizeBaseURL` 会提前拦下并给出正确写法。

### 记忆与压缩阈值

见 `internal/config/config.yaml` 的 `chat` 段。默认值面向真实使用：

| 配置项 | 默认 | 含义 |
| --- | --- | --- |
| `compress_trigger_tokens` | 6000 | 上下文达此 token 数触发压缩 |
| `compress_trigger_messages` | 16 | 未压缩消息达此条数触发压缩 |
| `keep_recent_turns` | 2 | 压缩时保留最近几轮原文 |
| `memory_min_turns` | 4 | 未提取 user 轮数达此值提取记忆 |
| `memory_min_tokens` | 4000 | 未提取消息达此 token 数提取记忆 |
| `memory_max_chars` | 2000 | 长期记忆文档上限 |
| `llm.timeout` | 480s | 单次模型调用超时，须 ≥ `run_timeout` 的一半 |

> **`llm.timeout` 必须足够大**：它是单次模型调用的 HTTP 上限，而
> `chat.run_timeout`（600s）是整轮上限。「详细讲解 Go 内存分配器」这类
> 长回答实测需要 3~4 分钟，120s 会在流式传输中途被掐断，
> 表现为整轮 `cancelled` 且 `prompt_tokens` 为空。启动期会校验两者关系。

调低这些值可以让压缩与记忆提取在几轮对话内就被触发，便于验证。

## 数据库

| 表 | 说明 |
| --- | --- |
| `chat_sessions` | 会话；`summary` 与两个游标直接挂在行上，不存 system 消息 |
| `chat_messages` | 消息；自增 id 作为游标依据，`meta` 存真实 usage |
| `user_memories` | 每用户一份 Markdown 记忆，`version` 做乐观锁 |

游标推进用条件更新（`WHERE summary_cursor < ?`），防止并发回退。

## 接口

全部需要 `Authorization: Bearer <token>`。未配置 `llm.api_key` 时对话接口返回 503。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/chat/sessions` | 创建会话 |
| GET | `/api/v1/chat/sessions?limit=` | 会话列表 |
| PATCH | `/api/v1/chat/sessions/:id` | 重命名 |
| DELETE | `/api/v1/chat/sessions/:id` | 软删除 |
| GET | `/api/v1/chat/sessions/:id/messages?before_id=&limit=` | 游标分页历史 |
| POST | `/api/v1/chat/sessions/:id/messages` | **SSE 流式对话** |
| GET | `/api/v1/chat/memory` | 查看长期记忆 |
| PUT | `/api/v1/chat/memory` | 手动编辑（上限为 `memory_max_chars` 的 2 倍） |
| DELETE | `/api/v1/chat/memory` | 清空记忆 |

认证接口：`POST /api/v1/auth/register`、`POST /api/v1/auth/login`、`GET /api/v1/profile`。

### 认证

登录/注册返回 HS256 JWT，payload 携带 `user_id` 与 `username`：

```json
{
  "user_id": "c8974b9e-6670-48b9-8f29-a102d58aad99",
  "username": "alice",
  "iss": "Mentorly",
  "sub": "c8974b9e-6670-48b9-8f29-a102d58aad99",
  "exp": 1795757143,
  "nbf": 1795152343,
  "iat": 1795152343
}
```

校验分两层，缺一不可：

1. **签名与有效期** — 验 HS256 签名、`iss` 必须匹配、`exp` 必须存在且未过期。
   篡改签名、换密钥、换 issuer 均拒绝。
2. **用户状态回查** — 签名只证明 token 是本服务签发的，**不能证明账号此刻仍可用**。
   因此每次请求都按 `user_id` 回查数据库：已删除返回 401，`status=0` 返回 403。
   否则停用和删号要等到 token 自然过期（默认 168h）才生效。

回查失败（数据库故障）一律 500 拒绝，**不放行**——一次故障不能让认证退化。

登录同样校验 `status`，避免被停用的账号重新登录换取新 token。

`handler` 通过 `auth.CurrentUserID(c)` / `auth.CurrentUsername(c)` 取身份。
用户名来自 token 载荷，仅用于展示与日志；需要权威信息时以 `user_id` 回查。

### SSE 帧

```
event: delta    data: {"text":"增量文本"}
event: reset    data:{}                      # 工具调用前的过渡语作废，前端应清空已渲染内容
event: done     data:{"message_id":34,"status":"completed"}
event: error    data:{"message":"..."}
: ping                                        # 心跳，默认 15s
```

### 一轮对话的状态

| status | 含义 |
| --- | --- |
| `completed` | 正常完成；若模型只调工具没输出文本，内容为 `[已完成工具操作]` |
| `cancelled` | 客户端断开或超时；保留已生成的半截文本 |
| `failed` | 生成失败，`meta.error` 记录原因 |

## 工具与沙箱

Agent 可用的工具由 eino 中间件注册：

- **filesystem**：`ls` / `read_file` / `write_file` / `edit_file` / `glob` / `grep`
- **skill**：渐进式加载 `SKILL.md`（只注入技能名与简介，需要细节时再读）
- **reduction**：单轮内工具结果过大时卸载到 `/.offload`

三个挂载点：

| 虚拟路径 | 宿主机 | 权限 |
| --- | --- | --- |
| `/workspace` | `workspace/chat/{uid}/{sid}` | 读写 |
| `/.offload` | `workspace/.offload/{uid}/{sid}` | 读写 |
| `/skills` | `skills/` | 只读 |

路径经过 `Clean` + `filepath.Rel` 前缀校验 + `EvalSymlinks`，拦住 `../` 与符号链接逃逸。

**越界访问返回说明文本而非 error**：eino 会把工具 error 升级为节点错误导致整轮失败，
而「读错路径」是模型能自行纠正的常规情况。返回拒绝原因让它换个合法路径重试，
既安全（坚决不执行）又不中断对话。

## 快速开始

```bash
make env       # 生成 .env
# 编辑 .env：填 LLM_API_KEY、MYSQL_PASSWORD
make db        # 创建数据库
make run       # 启动，自动建表
```

```bash
# 拿 token
TOKEN=$(curl -s -X POST localhost:8080/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"me","email":"me@example.com","password":"secret123"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["token"])')

# 建会话
SID=$(curl -s -X POST localhost:8080/api/v1/chat/sessions \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["id"])')

# 流式对话
curl -N -X POST "localhost:8080/api/v1/chat/sessions/$SID/messages" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"content":"用一句话说明 Go 的 GMP 模型"}'
```

## 离线验证

没有 LLM key 时，用本地假模型跑通整条链路（真实的 eino 流式、tool_call、SSE）：

```bash
python3 scripts/fake_llm.py 18081 &
LLM_API_KEY=test LLM_BASE_URL=http://127.0.0.1:18081/v1 LLM_MODEL=fake ./bin/mentorly
```

## 测试

```bash
gofmt -l . && go vet ./... && go build ./...
go test ./... -race
```

单测不依赖数据库与网络：

- `window`：预算裁剪（交替规则、user 开头、跳过 failed、预算紧张时回补 user 锚点）、
  压缩窗口切分（按整轮截断、cutoff 正确性）、token 估算器
- `memory`：Markdown 结构校验（去围栏/缺标题保护/空小节剔除/待整合小节）
- `agent`：沙箱 `../` 逃逸、符号链接逃逸、`/skills` 只读、读写落盘；
  用伪造 `adk.Agent` 验证 reset、最终回答提取、用量捕获、ctx 取消；prompt 条件拼装
- `turn`：**终态判定**（ctx 已取消但 streamErr 为 nil 必须记 cancelled，
  而非 completed——这个 bug 就是被这条测试抓出来的）、错误翻译、内部错误不泄露
- `capability`：nil 能力自动跳过、nil 注册表安全、能力名正确
- `sse`：`httptest` 验证帧格式、心跳、断连回调
- `llm`：BaseURL 归一化（含 `/chat/completions` 拒绝）

## 常用命令

```bash
make help    # 列出命令
make check   # fmt + vet + build
make test    # -race 全量测试
make build   # 编译到 bin/
make clean   # 清理产物与日志
```
