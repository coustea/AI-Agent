# ReAct Agent Framework

<div align="center">

**基于 LangGraph 的 ReAct 模式智能体框架**

[5-Node Workflow](#architecture) • [快速开始](#quick-start) • [文档](docs/ARCHITECTURE.md) • [示例](src/agent/main.py)

</div>

---

## 📖 简介

ReAct Agent Framework 是一个模块化、可扩展的智能体框架，实现了经典的 **ReAct（Reasoning + Acting）模式**，通过 **5 节点工作流** 让 AI 智能体能够像人类一样思考和行动。

```
📚 Retrieve → 🤔 Think → 🛠️ Plan → ⚡ Act → 👀 Reflect → (循环)
```

### 核心特性

| 特性 | 描述 |
|------|------|
| 🔄 **5 节点工作流** | Retrieve → Think → Plan → Act → Reflect 完整闭环 |
| 🧩 **模块化设计** | 工具、技能、提示词完全解耦 |
| 📝 **SOP 驱动** | 业务知识通过 Markdown 管理，无需修改代码 |
| 🛡️ **安全执行** | 内置命令黑名单、超时控制、权限限制 |
| 🌐 **多模型支持** | 兼容所有 OpenAI API 协议的模型 |
| 📊 **流式输出** | 实时查看智能体的思考过程和决策 |

---

## 🏗️ 架构设计

### 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         ReAct Agent                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              LangGraph StateGraph                         │  │
│  │  Retrieve → Think → Plan → Act → Reflect → Think ...     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  LLM Layer   │    │  Tool System │    │ Skill System │
│  LangChain   │    │  BaseTool    │    │  SKILL.md    │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 5 节点说明

| 节点 | 职责 | 提示词文件 |
|------|------|-----------|
| **📚 Retrieve** | 加载业务 SOP 和用户记忆 | 无（自动扫描） |
| **🤔 Think** | 意图理解与情境分析 | `01_think.md` |
| **🛠️ Plan** | 决策工具调用或生成答案 | `02_plan.md` + `03_act.md` |
| **⚡ Act** | 执行工具（通过 ToolNode） | 无（LangChain） |
| **👀 Reflect** | 评估结果并决定继续/结束 | `04_reflect.md` |

### 提示词缝合策略

```
System Prompt (人设)
    ↓
+ Current SOP (动态业务知识)
    ↓
+ Internal Prompt (框架逻辑)
    ↓
= 完整的系统提示词
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.10 或更高版本
- **包管理器**: [uv](https://github.com/astral-sh/uv)（推荐）或 pip

### 1. 安装依赖

```bash
# 使用 uv（推荐，速度更快）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

> 💡 **支持的模型**: OpenAI GPT-4/3.5、DeepSeek、Azure OpenAI、Ollama 本地模型等所有兼容 OpenAI API 的模型

### 3. 运行示例

```bash
# 运行演示程序
python src/agent/main.py
```

### 4. 代码示例

```python
import asyncio
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from agent.core import Agent
from agent.tools import get_tools
from dotenv import load_dotenv

load_dotenv()

async def main():
    # 1️⃣ 初始化 LLM
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="deepseek-chat",
        temperature=0.7,
    )

    # 2️⃣ 初始化 Agent
    agent = Agent(
        llm=llm,
        tools=get_tools(),
        prompts_dir="agent/prompts",
        skills_dir="agent/skills",
        system_prompt="你是一个温柔、善良、贴心的智能助手。"
    )

    # 3️⃣ 查看当前配置
    print(agent.print_agent_config())
    # 📦 [系统配置] 当前 Agent 已挂载能力：
    #    - 🧠 大语言模型 (LLM)  : deepseek-chat
    #    - 🛠️ 物理工具 (Tools) : shell_exec, web_fetch
    #    - 📚 业务技能 (Skills): weather-1.0.0

    # 4️⃣ 执行任务（流式）
    task = "去网上搜索什么是 ReAct 框架"
    
    async for output in agent.graph.astream({
        "task": task,
        "messages": [HumanMessage(content=task)],
        "current_sop": ""
    }):
        for node_name, state_update in output.items():
            print(f"[{node_name}]")

    # 5️⃣ 获取最终结果
    final_state = await agent.graph.ainvoke({
        "task": task,
        "messages": [HumanMessage(content=task)],
        "current_sop": ""
    })
    
    print(final_state["messages"][-1].content)

asyncio.run(main())
```

---

## 📦 核心组件

### 1. 核心智能体 (`src/agent/core/agent.py`)

5 节点 LangGraph 工作流的实现核心。

**关键特性**:
- ✅ 三层提示词缝合（人设 + SOP + 框架逻辑）
- ✅ 自动技能发现和加载
- ✅ 可配置的工具绑定
- ✅ 流式执行支持

### 2. LLM 层 (`src/agent/core/llm.py`)

统一的 LLM 接口，兼容 OpenAI 协议。

```python
from agent.core.llm import LLM

llm = LLM.create(
    model="deepseek-chat",
    temperature=0.7,
    api_key="your_key",
    base_url="https://api.deepseek.com/v1"
)
```

### 3. 工具系统 (`src/agent/tools/`)

使用 LangChain `@tool` 装饰器构建的工具集。

| 工具 | 描述 | 特性 |
|------|------|------|
| `shell_exec` | 安全的 Shell 命令执行 | 危险命令拦截、异步执行、超时控制 |
| `web_fetch` | 异步 HTTP 抓取 | HTTP/HTTPS 支持、自动重定向、内容截断保护 |
| `file_append` | 安全的文件追加 | 自动创建目录、路径限制 |

**添加自定义工具**:

```python
# src/agent/tools/builtin/my_tool.py
from langchain_core.tools import tool
from typing import Optional

@tool
async def my_tool(query: str, timeout: int = 30) -> str:
    """工具的简短描述，让 LLM 知道何时使用此工具。"""
    # 实现代码
    return f"Result: {query}"

# src/agent/tools/builtin/__init__.py
from .my_tool import my_tool
AGENT_TOOLS = [shell_exec, web_fetch, file_append, my_tool]
```

### 4. 技能系统 (`src/agent/skills/`)

业务知识以 Markdown 文件（SKILL.md）形式管理。

**目录结构**:
```
skills/
└── weather-1.0.0/
    └── SKILL.md
```

**技能格式**:
```markdown
---
name: weather
description: 获取当前天气和预报
homepage: https://wttr.in/:help
---

# Weather Skill

## Usage
curl -s "wttr.in/London?format=3"
```

技能会在 `retrieve` 阶段自动加载并注入到智能体的上下文中。

### 5. 提示词模板 (`src/agent/prompts/`)

框架工作流逻辑的提示词文件。

| 文件 | 阶段 | 作用 |
|------|------|------|
| `01_think.md` | Think | 意图理解、人设指南 |
| `02_plan.md` | Plan | 决策制定、SOP 遵循 |
| `03_act.md` | Act | 工具约束、安全规则 |
| `04_reflect.md` | Reflect | 结果评估、答案生成 |

---

## 📂 项目结构

```
agent/
├── src/
│   ├── agent/
│   │   ├── core/
│   │   │   ├── agent.py       # 主 Agent 类（5 节点工作流）
│   │   │   ├── llm.py         # LLM 封装
│   │   │   └── logger.py      # 全局异步日志系统
│   │   ├── prompts/           # 框架工作流提示词
│   │   │   ├── 01_think.md
│   │   │   ├── 02_plan.md
│   │   │   ├── 03_act.md
│   │   │   └── 04_reflect.md
│   │   ├── tools/             # 工具实现
│   │   │   ├── __init__.py
│   │   │   └── builtin/
│   │   │       ├── shell_execute.py
│   │   │       ├── web_fetch.py
│   │   │       └── file_write.py
│   │   ├── skills/            # 业务知识库 (SKILL.md)
│   │   │   ├── weather-1.0.0/
│   │   │   └── self-improving-agent-3.0.5/
│   │   └── logs/              # 自动生成的日志文件
│   └── main.py                # 演示入口
├── docs/
│   └── ARCHITECTURE.md        # 详细架构文档
├── .env                       # 环境变量配置
├── pyproject.toml             # 项目配置
├── AGENTS.md                  # AI 编码助手指南
└── README.md                  # 本文件
```

---

## 🛠️ 开发指南

### 代码格式化

```bash
# 格式化代码
ruff format .

# 检查 lint
ruff check .

# 自动修复 lint 问题
ruff check . --fix
```

### 测试

```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_agent.py

# 运行单个测试函数
pytest tests/test_agent.py::test_retrieve_node

# 带覆盖率报告
pytest --cov=src --cov-report=term-missing
```

### 配置 Agent

```python
agent = Agent(
    llm=llm,
    tools=get_tools(),
    system_prompt="你的自定义人设",
    prompts_dir="agent/prompts",
    skills_dir="agent/skills"
)
```

### 查看配置

```python
config = agent.get_agent_config()
print(agent.print_agent_config())
```

输出示例:
```
📦 [系统配置] 当前 Agent 已挂载能力：
   - 🧠 大语言模型 (LLM)  : deepseek-chat
   - 🛠️ 物理工具 (Tools) : shell_exec, web_fetch, file_append
   - 📚 业务技能 (Skills): weather-1.0.0, self-improving-agent-3.0.5
```

---

## 🔒 安全性

### Shell 命令安全
- ✅ 危险命令黑名单（`rm -rf`, `sudo`, `chmod -R`, `dd`, `mkfs` 等）
- ✅ 最小权限原则
- ✅ 输出截断防止 Token 溢出

### 工具执行
- ✅ 可配置的超时控制
- ✅ 参数验证（类型、格式、范围）
- ✅ 文件操作路径限制

### 最佳实践
- ❌ 不要硬编码密钥（使用 `.env` 文件）
- ❌ 不要添加未经验证的外部依赖
- ✅ 所有工具使用 `async` 异步实现
- ✅ 完整的错误处理和日志记录

---

## 🌐 支持的 LLM 模型

框架支持所有兼容 OpenAI API 协议的模型：

| 提供商 | 模型 | 配置示例 |
|--------|------|----------|
| **OpenAI** | GPT-4, GPT-3.5 | `base_url="https://api.openai.com/v1"` |
| **DeepSeek** | deepseek-chat, deepseek-coder | `base_url="https://api.deepseek.com/v1"` |
| **Azure** | Azure OpenAI | `base_url="https://your-resource.openai.azure.com/"` |
| **Ollama** | 本地模型 | `base_url="http://localhost:11434/v1"` |
| **其他** | 任何 OpenAI 兼容 API | 自定义 `base_url` |

---

## 📚 文档

| 文档 | 描述 |
|------|------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 详细架构设计文档 |
| [AGENTS.md](AGENTS.md) | AI 编码助手开发指南 |
| [src/agent/main.py](src/agent/main.py) | 完整示例代码 |

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - 强大的 LLM 应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 状态图工作流引擎
- [ReAct Paper](https://arxiv.org/abs/2210.03629) - Reasoning + Acting 模式研究

---

<div align="center">

**Made with ❤️ by the ReAct Agent Team**

[⭐ Star this repo](javascript:void(0)) • [📖 Read Docs](docs/ARCHITECTURE.md) • [🚀 Get Started](#quick-start)

</div>
