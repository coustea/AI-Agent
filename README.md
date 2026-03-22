# ReAct Agent Framework

A LangGraph-based Agent framework implementing the ReAct (Reasoning + Acting) pattern with a 5-node workflow: **Retrieve → Think → Plan → Act → Reflect**.

## Architecture

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

## Features

- **5-Node ReAct Workflow**: Retrieve → Think → Plan → Act → Reflect
- **Modular Design**: Decoupled tools, skills, and prompts
- **SOP-Driven**: Business knowledge managed as markdown files
- **Safe Execution**: Built-in security for shell commands
- **Multi-LLM Support**: Compatible with OpenAI, DeepSeek, and more
- **Streaming Output**: Real-time visibility into agent reasoning

## Installation

### Prerequisites

- Python 3.10 or higher
- uv (recommended) or pip

### Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

## Quick Start

### Basic Usage

```python
import asyncio
import os
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from agent.core import Agent
from agent.tools import get_tools
from dotenv import load_dotenv

load_dotenv()

async def main():
    # 1. Initialize LLM
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="deepseek-chat",
        temperature=0.7,
    )

    # 2. Initialize Agent
    agent = Agent(
        llm=llm,
        tools=get_tools(),
        prompts_dir="agent/prompts",
        skills_dir="agent/skills",
        system_prompt="你是一个温柔、善良、贴心的智能助手。"
    )

    # 3. Print agent configuration
    print(agent.print_agent_config())

    # 4. Execute task
    task = "去网上搜索什么是openclaw"
    
    # Stream execution
    async for output in agent.graph.astream({
        "task": task,
        "messages": [HumanMessage(content=task)],
        "current_sop": ""
    }):
        for node_name, state_update in output.items():
            print(f"[{node_name}]")

    # Get final result
    final_state = await agent.graph.ainvoke({
        "task": task,
        "messages": [HumanMessage(content=task)],
        "current_sop": ""
    })
    
    print(final_state["messages"][-1].content)

asyncio.run(main())
```

### Run the Demo

```bash
python src/main.py
```

## Components

### Core Agent (`src/agent/core/agent.py`)

5-node LangGraph workflow:

- **retrieve**: Loads business SOPs from skills directory
- **think**: Intent understanding and context analysis
- **plan**: Decides tool usage or final answer
- **act**: Executes tools via LangChain ToolNode
- **reflect**: Evaluates results and determines completion

**Key Features**:
- Three-layer prompt stitching (persona + SOP + framework logic)
- Automatic skill discovery and loading
- Configurable tool binding
- Streaming execution support

### LLM Layer (`src/agent/core/llm.py`)

Unified LLM interface compatible with OpenAI protocol:

```python
from agent.core.llm import LLM

llm = LLM.create(
    model="deepseek-chat",
    temperature=0.7,
    api_key="your_key",
    base_url="https://api.deepseek.com/v1"
)
```

### Tool System (`src/agent/tools/`)

Built-in tools using LangChain `@tool` decorator:

| Tool | Description | Features |
|------|-------------|----------|
| `shell_exec` | Safe shell command execution | Dangerous command blocking, async execution, timeout control |
| `web_fetch` | Async HTTP fetch | HTTP/HTTPS support, auto-redirect, content truncation |

**Adding Custom Tools**:

```python
from langchain_core.tools import tool

@tool
async def my_tool(param: str) -> str:
    """Tool description."""
    return f"Result: {param}"
```

### Skills System (`src/agent/skills/`)

Business knowledge as markdown files:

```
skills/
└── weather-1.0.0/
    └── SKILL.md
```

**Skill Structure**:

```markdown
---
name: weather
description: Get current weather and forecasts
homepage: https://wttr.in/:help
---

# Weather

## Usage
curl -s "wttr.in/London?format=3"
```

Skills are automatically loaded and injected into the agent's context during the `retrieve` phase.

### Prompt Templates (`src/agent/prompts/`)

Framework workflow logic:

- `01_think.md`: Intent understanding and persona guidelines
- `02_plan.md`: Decision-making and SOP following
- `03_act.md`: Tool constraints and safety rules
- `04_reflect.md`: Result evaluation and answer generation

## Project Structure

```
Agent/
├── src/
│   ├── agent/
│   │   ├── core/
│   │   │   ├── agent.py       # Main Agent class
│   │   │   └── llm.py         # LLM wrapper
│   │   ├── prompts/           # Framework prompts
│   │   │   ├── 01_think.md
│   │   │   ├── 02_plan.md
│   │   │   ├── 03_act.md
│   │   │   └── 04_reflect.md
│   │   ├── tools/             # Tool system
│   │   │   ├── __init__.py
│   │   │   └── builtin/
│   │   │       ├── shell_execute.py
│   │   │       └── web_fetch.py
│   │   └── skills/            # Business SOPs
│   │       └── weather-1.0.0/
│   │           └── SKILL.md
│   └── main.py                # Demo entry point
├── docs/
│   └── ARCHITECTURE.md        # Detailed architecture docs
├── .env                       # Environment variables
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

## Development

### Code Formatting

```bash
# Format code
ruff format .

# Lint code
ruff check .
```

### Testing

```bash
# Run tests
pytest
```

## Configuration

### Agent Configuration

```python
agent = Agent(
    llm=llm,
    tools=get_tools(),
    system_prompt="Your custom persona",
    prompts_dir="agent/prompts",
    skills_dir="agent/skills"
)
```

### View Current Configuration

```python
config = agent.get_agent_config()
print(agent.print_agent_config())
```

Output:
```
📦 [系统配置] 当前 Agent 已挂载能力：
   - 🧠 大语言模型 (LLM)  : deepseek-chat
   - 🛠️ 物理工具 (Tools) : shell_exec, web_fetch
   - 📚 业务技能 (Skills): weather-1.0.0
```

## Security

- **Shell Command Safety**: Dangerous commands (rm, sudo, etc.) are blocked
- **Parameter Validation**: Tool parameters are strictly validated
- **Timeout Control**: All tool executions have configurable timeouts
- **Error Handling**: Graceful error recovery with user-friendly messages

## Supported LLMs

The framework supports any LLM compatible with the OpenAI API protocol:

- OpenAI (GPT-4, GPT-3.5)
- DeepSeek (deepseek-chat, deepseek-coder)
- Azure OpenAI
- Local models via Ollama
- And more...

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
