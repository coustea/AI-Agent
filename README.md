# Mentorly Backend

Go + Gin + GORM + eino ADK + MySQL + Redis 的学习辅导后端。
核心能力是一个 Agent 驱动的 ChatAgent：多轮流式对话、会话隔离、
调用前上下文压缩、工具调用、会话工作目录与技能加载。

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

## 架构：按模块组织

系统由若干**限界上下文**模块组成，每个模块自包含：领域类型、存储、业务、HTTP 入口
都在同一个包里，按文件职责分层。

```
cmd/server/main.go          配置 → 日志 → 依赖 → api.New().Run

internal/
  chat/                     ★ 对话上下文（11 文件）
    entity.go    Session / Message / Role / Status（零框架依赖）
    store.go     GORM 行类型（私有）+ Store 仓储
    service.go   业务面：会话 CRUD、配置、异步标题
    turn.go      一轮对话：Begin → Run → Close
    window.go    token 估算与窗口裁剪（纯计算）
    compress.go  上下文滚动压缩
    agent.go     eino ADK 封装
    prompt.go    System Prompt 组装
    sandbox.go   文件系统沙箱（安全边界）
    handler.go   HTTP handlers + SSE writer
    dto.go       请求 / 响应结构
    route.go     路由注册

  auth/                     认证上下文（同构）
    user.go  store.go  service.go  jwt.go
    handler.go  middleware.go  dto.go  route.go

  config/                   配置读取 + 默认值唯一来源 + 启动校验
  log/                      zap + lumberjack
  infra/                    MySQL、Redis、分布式锁、eino 模型构建
  response/                 统一响应体

  api/                      组合根
    app.go        装配 + 路由表
    middleware.go RequestID / Logger / Recovery / CORS
    health.go     存活与就绪探针
```

**8 个包**，`internal/` 下无嵌套子包（除 `prompts/` 资源目录）。

### 为什么是这个粒度

判断标准只有一条：**改动一个需求时，要同时修改几个文件？**

| 需求 | 改后要改几处 |
| --- | --- |
| 加一个接口端点 | 1（对应 `handler.go`） |
| 改表结构 | 2（`store.go` + 相关用例） |
| 改 Prompt 文案 | 1（`prompt.go` + `prompts/tutor.md`） |
| 换 LLM 供应商 | 1（`config.yaml`，代码不动） |
| 改压缩阈值 | 1（`config.yaml`） |

`chat` 的 11 个文件是按**改动理由**切的，不是按代码类型：改 eino 相关只动 `agent.go`，
改 HTTP 契约只动 `handler.go`，改安全边界只动 `sandbox.go`。
`session.go` / `turn.go` 这类「按生命周期阶段」再细分是不做的——它们改动理由相同，
拆开只会增加跳转成本。

### 一轮对话

```
POST /api/v1/chat/sessions/:id/messages
 │
 ├─ Begin          加锁 · 归属校验 · 落库 user 消息
 │                 失败 → 404/409/400/503 标准 JSON（此时零字节已写出）
 ├─ defer Close    锁随 Turn 生命周期，幂等，无需在每个错误路径手动释放
 │
 ├─ 切换 SSE + 心跳
 └─ Run
    ├─ Pre-Run     压缩上下文 → 重建窗口与 Prompt
    ├─ 执行        构建 Agent → 流式推 Chunk → sink
    └─ 收口        终态裁决 → 落库 → 回写用量 → 首轮异步标题
```

**关键设计**：`Begin`/`Run`/`Close` 取代了旧版的 `Prepare`/`Run`/`Release`。
旧版的 `Release` 要求 handler 在每条错误路径手动调用（实际有 3 处），是泄漏 API；
新版靠 `defer` 兜住所有路径。

### 依赖方向

```
cmd/server → api → {chat, auth} → {config, infra, response}
                 ↘ log
```

规则三条：

1. **模块之间不互相 import**。`chat` 不知道 `auth` 存在——当前用户 id 由
   `api` 注入的 `UserID func(*gin.Context) string` 提供。
2. **配置不嵌入模块**。`chat` 只接收拍平后的 `chat.Config` 值对象，
   import 列表里没有 `internal/config`，对配置文件与数据库连接零知识。
3. **存储细节不上浮**。GORM 行类型（`sessionRow` / `messageRow`）只在
   `store.go` 内可见，对外一律 `Session` / `Message`。

### 上下文压缩的水位线

压缩后的 `context_tokens` 不能简单用「本地估算的 system + 摘要 + 保留原文」。
eino 会在真实 prompt 里注入**工具 Schema 与技能清单**，这部分固定开销实测约
4500-4900 token，本地估算器完全看不到。

若直接用估算值当新基线（实测算出 3612，真实 6803），下一轮立刻又超阈值，
于是反复压缩却始终降不下来。正确做法是从真实基线里**剥离可压缩部分**
（旧摘要 + 被压缩的原文），保留固定开销，再加上压缩后的新内容。
日志里的 `fixed_overhead` 字段就是这项诊断值，对应 `compress.go` 的 `newBaseline`。

### 终态裁决的顺序陷阱

`turn.go` 的 `resolveOutcome` 必须**先判 ctx 是否取消，再判 streamErr 是否为 nil**。

客户端断开时，写失败发生在传输层，`Stream` 本身可能正常返回 `nil` 错误，
但 ctx 已被调用方取消。若顺序反了，这一轮会被误记为 `completed`——
用户看到的是「回答完整」，实际只收到半截。
`TestResolveOutcomeCtxCancelledWithoutError` 是这个 bug 的回归测试。

### 目录

```
cmd/server/main.go
internal/
  chat/       entity store service turn window compress agent prompt sandbox handler dto route doc
  auth/       user store service jwt handler middleware dto route
  config/     config.go  config.yaml
  log/        logger.go
  infra/      database.go  llm.go  lock.go
  response/   response.go
  api/        router.go  middleware.go  health.go
```

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

### 压缩阈值

见 `internal/config/config.yaml` 的 `chat` 段。默认值面向真实使用：

| 配置项 | 默认 | 含义 |
| --- | --- | --- |
| `compress_trigger_tokens` | 6000 | 上下文达此 token 数触发压缩 |
| `compress_trigger_messages` | 16 | 未压缩消息达此条数触发压缩 |
| `keep_recent_turns` | 2 | 压缩时保留最近几轮原文 |
| `compress_source_max_chars` | 8000 | 单次送入压缩的原文上限（按整轮截断） |
| `llm.timeout` | 480s | 单次模型调用超时，须 ≥ `run_timeout` 的一半 |

> **`llm.timeout` 必须足够大**：它是单次模型调用的 HTTP 上限，而
> `chat.run_timeout`（600s）是整轮上限。「详细讲解 Go 内存分配器」这类
> 长回答实测需要 3~4 分钟，120s 会在流式传输中途被掐断，
> 表现为整轮 `cancelled` 且 `prompt_tokens` 为空。启动期会校验两者关系。

调低这些值可以让压缩在几轮对话内就被触发，便于验证。

## 数据库

| 表 | 说明 |
| --- | --- |
| `users` | 账号；`status` 为 0 时登录与鉴权都拒绝 |
| `chat_sessions` | 会话；`summary` 与 `summary_cursor` 直接挂在行上，不存 system 消息 |
| `chat_messages` | 消息；自增 id 作为游标依据，`meta` 存真实 usage |

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

- `chat` / 窗口裁剪：预算裁剪（交替规则、user 开头、跳过 failed、预算紧张时回补锚点）、
  压缩窗口切分（按整轮截断、cutoff 正确性）、token 估算器
- `chat` / 压缩基线：`newBaseline` 剥离固定开销（对应实测 3612 vs 6803）
- `chat` / 终态判定：**ctx 已取消但 streamErr 为 nil 必须记 cancelled**，
  而非 completed——这个 bug 就是被这条测试抓出来的
- `chat` / Turn 生命周期：`Close` 幂等、nil 安全、错误路径不泄锁
- `chat` / 沙箱：`../` 逃逸、符号链接逃逸、`/skills` 只读、读写落盘
- `chat` / 流式消费：reset 语义、最终回答提取、用量捕获、ctx 取消
- `auth`：JWT 签发解析、中间件四种状态（active/missing/disabled/checker 出错）
- `config`：加载、缺失环境变量、短密钥拒绝、超时一致性
- `infra`：BaseURL 归一化（含 `/chat/completions` 拒绝）

## 常用命令

```bash
make help    # 列出命令
make check   # fmt + vet + build
make test    # -race 全量测试
make build   # 编译到 bin/
make clean   # 清理产物与日志
```
