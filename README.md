# Mentorly

Mentorly 是基于 Go、Eino DeepAgent 和 MySQL 的单 TutorAgent 服务。TutorAgent 负责教学对话、附件理解与联网搜索；它通过官方 Skills、基础文件工具和受控 Shell 创建文档、图解、PPT 与视频。项目没有独立的 ResourceAgent 或 `generate_*` 业务工具。

## 运行环境与依赖

Agent 运行期间不主动探测宿主机工具链，请在部署或本机开发环境中预先安装所需依赖：

### 1. 基础必需依赖

| 依赖 | 用途 | 安装 / 说明 |
|---|---|---|
| Go `1.26+` | 编译与运行服务端 | [go.dev](https://go.dev/dl/) |
| MySQL `8.0+` | 用户、会话、消息、压缩检查点与附件元数据存储 | 启动时 AutoMigrate 自动建表，请使用空库 |
| macOS `sandbox-exec` | Agent `execute` 命令的内核级沙箱隔离 | macOS 系统内置 |
| ripgrep (`rg`) | Eino 文件工具 `grep` 的底层检索引擎 | `brew install ripgrep` |

### 2. 文档、课件与视频 Skills 依赖

Agent 通过只读挂载的 [`internal/agent/skills/`](internal/agent/skills) 调用以下宿主机命令工具链；服务端代码不硬编码任何编译器或运行时路径，直接透传宿主机 `PATH`（以及已设置的 `NODE_PATH`、`DYLD_FALLBACK_LIBRARY_PATH`、`XDG_CACHE_HOME`），由 Agent 通过 bash 自行定位并执行：

- **Python `3.12` + `uv`**（运行 `make skills-deps` 安装到 `~/.local/share/mentorly/skills-python`，并将其 `bin` 加入 `PATH`）：
  - 安装清单见 [`internal/agent/skills/requirements.txt`](internal/agent/skills/requirements.txt)：`python-pptx`、`python-docx`、`openpyxl`、`pypdf`、`pdfplumber`、`reportlab`、`pandas`、`pillow`、`defusedxml`、`lxml`、`cairosvg`
- **Node.js + 全局 npm 包**（供 `pptx`/`docx` 脚本及 HyperFrames 视频渲染调用，建议在环境中配置 `NODE_PATH=$(npm root -g)`）：
  ```bash
  npm install -g pptxgenjs docx react-icons react react-dom sharp hyperframes
  ```
- **文档转换、视频与视觉自检 CLI**（供 LibreOffice 转 PDF/图片、SVG 渲染、音视频处理与格式转换）：
  ```bash
  brew install libreoffice poppler pandoc cairo ffmpeg
  ```
  提供 `soffice`、`pdftoppm`、`pdftotext`、`pandoc`、`ffmpeg` 及 Homebrew `libcairo`（使用 `cairosvg` 时在环境中设置 `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`）。

### 3. 附件解析与可选能力

- **附件解析**（仅支持 `.doc`、`.docx`、`.pdf`、`.md`）：`.pdf` 依赖 `pdftotext`（随 `poppler` 安装）；`.doc` 依赖 macOS 内置 `textutil`；`.docx` 使用 Eino 官方解析扩展；`.md` 直接读取。
- **联网搜索（可选）**：在 `.env` 配置 Tavily 凭据（`SEARCH_PROVIDER=tavily`、`SEARCH_API_KEY`），未配置时不注册 `web_search`。
- **模型凭据**：未配置 `LLM_API_KEY` 时服务仍可启动，对话接口返回 `503`。

## 启动

1. 将 `.env.example` 复制为 `.env`，配置 MySQL、JWT 和模型。使用新的空数据库；启动时 AutoMigrate 建立 `users`、`conversations`、`messages`、`attachments`，不会删除旧数据，也不负责旧表迁移。
2. 安装上方依赖并按需将工具目录加入 `PATH`（可用 `make doctor` 与 `hyperframes doctor` 快速核对基础命令）。
3. 运行 `make run` 启动 HTTP 服务；`GET /readyz` 检查数据库。

## 分层

```text
cmd/server/                    启动、依赖装配、优雅退出
internal/router/               HTTP 路径注册
internal/handlers/             请求解析、响应编码、SSE、文件下载
internal/dto/                  HTTP 请求与响应数据结构
internal/middleware/           Gin 认证、请求日志、恢复、CORS
internal/service/              会话与认证流程、附件、工作区、首问截取标题
internal/agent/                DeepAgent、Harness、自定义工具、Shell、Skills
internal/repository/           MySQL 仓储与文件存储
internal/config/               配置
internal/utils/                安全路径与日志初始化
```

Handler 顺序调用 `Service.Prepare → Harness.Prepare → Service.SaveUser → Agent.Run → Service.SaveResult`。Service 校验会话与附件归属并持有会话锁；Harness 独立读取历史、组装上下文；读取历史后才保存本轮用户消息。SSE 在准备成功后开启，工具与文本事件写入失败会取消运行；结果落库后发送 `done`，最后释放锁。首轮用户消息保存后，以问题前 20 个字符作为标题，不调用模型。Service 不持有 Harness 或 Agent 实例。

**System Prompt 与每轮状态严格分离。** System Prompt 在 `agent.New` 时构建一次并长期复用，只写启动后不变的内容：行为约束、挂载点（`/workspace`、`/skills`）、沙箱命令规范与支持的文档格式。日期、工作区文件列表、本轮附件路径每轮都在变，它们随用户消息以 `<turn_context>` 送入，本轮附件带有 ID、文件名、路径及最多 12000 字的提取文本；历史附件只在原用户消息中保留引用。这样后续轮次新上传的附件只需追加到当轮消息，System Prompt 保持稳定，上游前缀缓存不会被逐轮破坏。

附件关联以 `messages.attachment_ids` 为准。`list_attachments` 查询本用户、本会话中实际引用附件的用户消息，按消息顺序返回消息 ID、时间、问题摘要和附件引用；上下文压缩后也能重新定位。仅上传而未发送的文件不进入该列表。`read_attachment` 从运行上下文取得身份，校验用户与会话，再读取原件、提取并按字符分页返回文本。原件缺失、提取失败或元数据不可用时保留引用并返回明确状态，不增加关联表或向量检索。

会话消息接口按消息记录的 `attachment_ids` 顺序返回 `attachments` 数组（文件名、类别、大小、下载地址），一次请求即可按顺序渲染，不需要为每条消息再查一次附件。附件摘要用一次 `IN` 查询批量取回后在内存中分发，避免 N+1。

Agent 使用 Eino 官方 `Skill`、`PatchToolCalls`、`Reduction`、`Summarization` 中间件，以及自定义 `toolGuard` 中间件和 Eino DeepAgent 提供的文件工具。`internal/agent/skills/` 包含官方 `docx`、`pdf`、`pptx`、`xlsx` Skills、Excalidraw 图解 Skill 以及 HyperFrames 官方视频 Skills（`hyperframes`、`hyperframes-cli`、`media-use`）。会话工作区默认固定在 `workspace/chat/{user_id}/{conversation_id}`，附件与工具大结果卸载（`/workspace/.offload`）统一落在该目录下，Agent 通过 `/workspace/` 直接读写。Skills 默认固定在 `internal/agent/skills` 且严格只读，Shell 受 macOS 沙箱约束并直接通过 bash 调用宿主机环境中的渲染与脚本命令。

## HTTP 与数据

- `/api/v1/auth/register`、`/api/v1/auth/login`、`/api/v1/profile`：认证。
- `/api/v1/conversations` 及 `/:id/messages`：会话管理与 SSE 对话。
- `/api/v1/attachments`：上传、查看和下载附件。
- `/api/v1/workspaces/:id/files`：列出和下载本会话生成的文件。

SSE 事件为 `message`、`tool_start`、`tool_end`、`error`、`done`。MySQL 历史记录保留 ToolCall 与 ToolResult 的关联字段；对用户展示的消息列表只包含问答。Agent 执行器不持有数据库依赖；Harness 通过 Repository 读取历史，Service 负责业务校验和持久化。附件工具从运行上下文取得身份后访问 Repository。

认证通过后中间件把 `user_id` 与 `username` 合成一个 `middleware.Identity` 写入 `gin.Context`，handler 用 `middleware.MustUser(c)` 一次取全。未挂认证中间件的路由调用 `MustUser` 会 panic 并由 Recovery 转成 500，而不是带着空 `user_id` 继续写库。`username` 来自 token 载荷，用户改名后会落后于 `users` 表，需要权威资料时仍以 `UserID` 回查（`/api/v1/profile` 即如此）。访问日志在认证之后记录，因此会带上 `user_id`。

## 开发检查

```bash
make build
make vet
make test
```

`make test` 运行 Go 测试；文档、图解、PPT、视频的真实生成效果需要配置外部依赖后另行调试。

Agent 输入、最终回答及 Transcript 使用 Eino `schema.Message`；Repository 在持久化边界转换记录。`messages.model_message` 是新增的可空 JSON 列，随 AutoMigrate 创建，保存原生消息字段，包括推理、扩展与模型元信息；既有消息仍可从原列恢复。消息 ID、状态、附件关联和 HTTP/SSE 契约保持原状。

文件操作委托给 Eino 官方 Local Backend；本地适配层管理身份、虚拟路径（`/workspace`、`/skills`）、只读挂载及返回路径映射。Shell 继续使用 macOS 隔离实现。文件默认按 2000 行分页读取，长文件用 offset/limit 继续读取。

工具调用中出现路径不存在、越界、只读写入或非致命工具报错时，`toolGuard` 中间件与 `UnknownToolsHandler` 会将脱敏原因作为工具结果交回模型，使模型能够自愈继续；取消、超时、身份缺失与中断信号原样透传。

## Agent 调试日志

日志沿用终端输出与 `logs/YYYY-MM-DD/app.log` JSON 文件，默认 `info` 级别即可看到完整调用过程：用户输入、本轮上下文（含附件引用与预览）、模型调用、模型响应统计、Agent 输出、工具名称与模型参数、工具返回、上下文压缩摘要、保存结果和 SSE 错误。日志以 `conversation_id` 关联会话；`[模型响应统计]` 记录 `finish_reason`、耗时、Token 用量与推理字符长度，不记录模型推理原文。

正文来自实际消息与框架事件，阶段名称是固定标签。流式文本合并后记录；中断文本标记为 `[Agent 输出中断]`。工具返回记录的是经过 Eino Middleware 后送给模型的结果，可能包含 `/workspace/.offload` 卸载文件的引用；不把返回内容改写成“成功”。Skills 的读取、Shell 命令及其结果都通过同一工具日志展示。

模型无可用输出（包括空流、仅空白或仅推理内容）时，通过 Eino 原生重试机制按策略处理：429/瞬时故障按剩余 deadline 退避重试；`finish_reason=length` 推理耗尽时对 `spark` 仅单次关闭思考降级重试，避免盲目原样重试耗死超时；非 `length` 的偶发空响应允许原样重试 1 次。日志记录 `[模型空响应]`、`[模型降级重试]`、`[模型输出截断]` 与 `[模型重试失败]`。

每段内容最多记录 16000 个字符，超出时明确标记 `[日志已截断]`；常见凭据字段脱敏。日志仍可能包含用户问题和文档正文，仅供有权限的开发人员排查。HTTP/SSE 协议与数据库字段保持不变。
