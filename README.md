# 多智能体个性化学习资源平台

全栈项目：Vue 3 + TypeScript 前端 + FastAPI + SQLModel 后端。

## 快速开始

### 前端

```bash
npm install
npm run dev        # http://localhost:5173
```

### 后端

```bash
cd server
uv sync            # 安装 Python 依赖
uv run fastapi dev app/main.py   # http://localhost:9999
```

API 文档：`http://localhost:9999/docs`

## 系统依赖

以下系统级库需要手动安装（Docker 部署时请一并配置）：

### OCR 图片识别（必需）

Chat Agent 使用 Tesseract OCR 识别图片中的文字：

```bash
# Ubuntu / Debian
sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

# macOS
brew install tesseract tesseract-lang

# 验证安装
tesseract --version
```

- `tesseract-ocr` — OCR 引擎（>= 5.0）
- `tesseract-ocr-chi-sim` — 中文简体语言包
- `tesseract-ocr-eng` — 英文语言包

### Node.js（思维导图 MCP 服务需要）

```bash
# 推荐使用 nvm 安装
nvm install --lts
node --version   # >= 18
```

## 环境变量

复制 `server/.env.example` 为 `server/.env`，填写以下配置：

```bash
cp server/.env.example server/.env
```

| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_BASE` | LLM API 地址 | `https://spark-api-open.xf-yun.com/v1/` |
| `OPENAI_API_KEY` | LLM API 密钥 | `APIPassword` |
| `OPENAI_MODEL` | 主模型 | `generalv3.5` |
| `FAST_LLM_API_KEY` | 轻量模型密钥 | `APIPassword` |
| `FAST_LLM_MODEL` | 轻量模型名称 | `general` |
| `DB_HOST` / `DB_PORT` | MySQL 连接 | `localhost` / `3306` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | 随机字符串 |
| `NODE_PATH` | Node.js 可执行文件路径 | `/usr/bin/node` |

## MCP 工具服务

后端通过 MCP（Model Context Protocol）连接外部工具服务，配置文件位于各模块的 `mcp/settings.json`：

| MCP 服务 | 功能 | 配置文件 |
|----------|------|----------|
| **markmap** | Markdown → 交互式思维导图 HTML | `app/modules/chat/mcp/settings.json` |
| **ocr** | 图片 OCR 文字提取（中英文） | `app/modules/chat/mcp/settings.json` |
| **pdf** | PDF 文档解析、文本提取、语义搜索 | `app/modules/chat/mcp/settings.json` |

### MCP 相关 Python 包

```bash
uv add mcp-ocr "pdf-mcp[semantic]"
```

- `mcp-ocr` — 图片 OCR MCP 服务（依赖 Tesseract）
- `pdf-mcp[semantic]` — PDF 解析 MCP 服务（含语义搜索，依赖 PyMuPDF）

## 项目结构

```
├── src/                    # Vue 3 前端
├── server/
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── core/           # 基础设施（数据库、JWT、日志）
│   │   ├── models/         # SQLModel 数据模型
│   │   ├── modules/
│   │   │   ├── chat/       # 辅导聊天模块
│   │   │   ├── resource/   # 多智能体资源生成模块
│   │   │   ├── knowledge_base/  # 知识库模块
│   │   │   └── user/       # 用户认证模块
│   │   ├── services/       # 跨模块服务（记忆、知识库）
│   │   └── utils/          # 工具类（PluginManager、路径）
│   ├── .env                # 环境变量（不提交）
│   └── .env.example        # 环境变量模板
└── CLAUDE.md               # Claude Code 开发指引
```

## 常用命令

```bash
# 后端
cd server
uv sync                                    # 安装依赖
uv run fastapi dev app/main.py             # 开发服务器
uv run python app/main.py                  # 生产服务器

# 前端
npm run dev        # 开发服务器
npm run build      # 生产构建
```
