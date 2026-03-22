# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **ReAct Agent Framework** built with LangGraph and LangChain, implementing a 5-node autonomous workflow: **Retrieve → Think → Plan → Act → Reflect**. The framework is designed for modularity, allowing business logic to be managed as markdown files rather than code.

## Quick Start Commands

```bash
# Run the main agent demo
python src/main.py

# Install dependencies (using uv - recommended)
uv sync

# Or using pip
pip install -r requirements.txt

# Format code
ruff format .

# Lint code
ruff check .
```

## Logging System

The project implements a **global asynchronous logging system** that must be used throughout the codebase.

### Key Features

1. **Global Singleton Logger**: The logger is initialized once and shared across all modules
2. **Async Write Operations**: Uses Python's `QueueHandler` and `QueueListener` for non-blocking log writes
3. **Automatic Log File Rotation**: Creates a new timestamped log file on each application startup
4. **Centralized Log Storage**: All logs are saved to `/agent/logs` directory

### Logger Location

- **Implementation**: `src/agent/core/logger.py`
- **Log Directory**: `src/agent/logs/` (auto-created)
- **Log File Format**: `agent_YYYYMMDD_HHMMSS.log`

### Usage Pattern

```python
from api.core.logger import setup_logger, get_logger

# Initialize logger once at application startup (usually in main.py)
logger = setup_logger(
    name="agent",
    level=logging.INFO,
    log_prefix="agent"
)

# Get logger instance in any module
logger = get_logger()
if logger:
    logger.think("Analyzing user intent")
    logger.act("Executing tool")
    logger.error("Something went wrong")
```

### Specialized Logging Methods

The `AsyncLogger` class provides stage-specific methods aligned with the ReAct workflow:

- `logger.retrieve(message)` - 📚 Retrieve stage
- `logger.think(message)` - 🤔 Think stage
- `logger.plan(message)` - 🛠️ Plan stage
- `logger.act(message)` - ⚡ Act stage
- `logger.reflect(message)` - 👀 Reflect stage
- `logger.success(message)` - ✅ Success
- `logger.error(message)` - ❌ Error
- `logger.warning(message)` - ⚠️ Warning
- `logger.info(message)` - Standard info
- `logger.debug(message)` - Debug info

### Web Middleware Logging

For FastAPI/Starlette applications, use the built-in middleware:

```python
from api.core.logger import log_middleware

app.add_middleware(log_middleware)
```

### Cleanup

Always close the logger before application exit:

```python
from api.core.logger import close_logger

# At the end of main()
close_logger()
```

## Architecture

### 5-Node ReAct Workflow

The agent uses a LangGraph StateGraph with these nodes:

1. **retrieve** - Loads business knowledge (SOPs) from `skills/` directory
2. **think** - Intent understanding and context analysis
3. **plan** - Decides whether to use tools or generate final answer
4. **act** - Executes tools via LangChain ToolNode
5. **reflect** - Evaluates results and determines if task is complete

### State Management

The `AgentState` TypedDict maintains:
- `messages`: Conversation history with tool calls (add_messages annotation)
- `task`: Original user task string
- `current_sop`: Dynamic business knowledge loaded from skills

### Prompt Stitching Strategy

Three-layer prompt architecture:

1. **System Prompt** (user-defined): Agent persona and behavior
2. **Current SOP** (dynamic): Business knowledge loaded from skills/
3. **Internal Prompts** (framework): Fixed workflow logic from `prompts/` directory

Example from `src/agent/core/agent.py`:
```python
sys_content = (
    f"{self.system_prompt}\n\n"
    f"{state.get('current_sop', '')}\n\n"
    f"{self.internal_prompts['think']}"
)
```

### Tool System

Tools are LangChain `@tool` decorated functions registered in `src/agent/tools/builtin/__init__.py`.

**Available Tools**:
- `shell_exec` - Safe shell command execution with dangerous command blocking
- `web_fetch` - Async HTTP fetch with content truncation
- `file_append` - Safe local file writing

**Adding New Tools**:
```python
from langchain_core.tools import tool

@tool
async def my_tool(param: str) -> str:
    """Tool description for LLM."""
    return f"Result: {param}"

# Add to AGENT_TOOLS list in src/agent/tools/builtin/__init__.py
```

### Skills System

Business knowledge is stored as markdown files in `src/agent/skills/`.

**Directory Structure**:
```
skills/
└── skill-name-version/
    └── SKILL.md
```

**Skill Format** (SKILL.md):
```markdown
---
name: weather
description: Get weather information
---

# Weather Skill

## Usage
curl -s "wttr.in/London?format=3"
```

Any directory containing `SKILL.md` is automatically loaded during the `retrieve` phase.

### LLM Integration

Uses `langchain_openai.ChatOpenAI` for OpenAI-compatible API support.

**Supported Models**:
- OpenAI (GPT-4, GPT-3.5)
- DeepSeek
- Azure OpenAI
- Local models via Ollama
- Any OpenAI-compatible API

**Configuration** (`.env`):
```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

## Code Structure

```
src/
├── agent/
│   ├── core/
│   │   ├── agent.py       # Main Agent class with 5-node workflow
│   │   ├── llm.py         # LLM factory wrapper
│   │   └── logger.py      # Global async logging system
│   ├── prompts/           # Framework workflow prompts
│   │   ├── 01_think.md
│   │   ├── 02_plan.md
│   │   ├── 03_act.md
│   │   └── 04_reflect.md
│   ├── tools/             # Tool implementations
│   │   ├── __init__.py
│   │   └── builtin/
│   │       ├── shell_execute.py
│   │       ├── web_fetch.py
│   │       └── file_write.py
│   ├── skills/            # Business knowledge (SKILL.md files)
│   └── logs/              # Auto-generated log files
└── main.py                # Demo entry point
```

## Agent Configuration

View current agent capabilities:

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

## Development Guidelines

### When Working with the Agent

1. **Always use the logger**: Import and use `get_logger()` in any new module
2. **Follow the async pattern**: Most agent operations are asynchronous
3. **Add tools to builtin/**: New tools go in `src/agent/tools/builtin/`
4. **Skills over code**: Prefer adding business logic as skills rather than hardcoding
5. **Test with streaming**: Use `agent.graph.astream()` to see workflow execution

### Security Considerations

- Shell commands are validated against a dangerous command blacklist
- Tool execution includes timeout controls
- File operations are restricted to safe paths
- All tool outputs are truncated to prevent token overflow

### Common Patterns

**Streaming Agent Execution**:
```python
async for output in agent.graph.astream({
    "task": task,
    "messages": [HumanMessage(content=task)],
    "current_sop": ""
}):
    for node_name, state_update in output.items():
        # Handle node output
```

**Direct Invocation**:
```python
final_state = await agent.graph.ainvoke({
    "task": task,
    "messages": [HumanMessage(content=task)],
    "current_sop": ""
})
```

## Environment Setup

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

The logger system will automatically create log files in `src/agent/logs/` on each run.
