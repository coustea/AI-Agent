# AGENTS.md

Guidelines for AI coding agents working in this ReAct Agent Framework repository.

## Project Overview

This is a **ReAct Agent Framework** built with LangGraph and LangChain, implementing a 5-node autonomous workflow: **Retrieve → Think → Plan → Act → Reflect**. Business logic is managed as markdown files (skills) rather than hardcoded.

**Core Architecture**:
- **Agent Runtime**: `/src/agent/core/agent.py` - 5-node LangGraph workflow
- **LLM Layer**: `/src/agent/core/llm.py` - Unified OpenAI-compatible interface
- **Prompts**: `/src/agent/prompts/` - Framework workflow logic (01_think.md, etc.)
- **Tools**: `/src/agent/tools/builtin/` - @tool decorated functions
- **Skills**: `/src/agent/skills/` - Business SOPs (SKILL.md files)

---

## Build / Test / Lint Commands

```bash
# Install dependencies (uv recommended)
uv sync

# Or with pip
pip install -r requirements.txt

# Run the main agent demo
python src/agent/main.py

# Run the FastAPI server
uvicorn src.api.main:app --reload

# Format code
ruff format .

# Lint code
ruff check .

# Fix lint issues automatically
ruff check . --fix

# Run all tests
pytest

# Run a single test file
pytest tests/test_agent.py

# Run a single test function
pytest tests/test_agent.py::test_retrieve_node

# Run tests with verbose output
pytest -v

# Run tests with coverage
pytest --cov=src --cov-report=term-missing
```

---

## Code Style Guidelines

### Python Standards

- **PEP 8** conventions (enforced via ruff)
- **Type annotations** on ALL function signatures
- **Async/await** for I/O-bound operations (agent nodes, tools, API handlers)
- **Immutability**: Prefer returning new objects over mutating existing ones

### Imports

```python
# Standard library first
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict

# Third-party libraries second
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# Local imports last
from agent.core.logger import get_logger
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `Agent`, `AgentState` |
| Functions/Methods | snake_case | `retrieve_node`, `get_logger` |
| Constants | UPPER_SNAKE | `AGENT_TOOLS`, `LOGS_DIR` |
| Private methods | _leading_underscore | `_build_graph`, `_load_internal_prompts` |
| Type aliases | PascalCase | `AgentState` (TypedDict) |

### Type Annotations

```python
# Always annotate function signatures
async def think_node(self, state: AgentState) -> dict[str, list[BaseMessage]]:
    ...

def get_agent_config(self) -> dict:
    ...

# Use Optional for nullable types
def __init__(self, tools: Optional[List[BaseTool]] = None):
    ...
```

### Formatting

- Line length: 88 characters (ruff default)
- Use double quotes for strings (or follow existing file style)
- Trailing commas in multi-line structures

---

## Error Handling

```python
# Always handle errors explicitly with informative messages
try:
    result = await some_async_operation()
except asyncio.TimeoutError:
    return "Error: Operation timed out"
except Exception as e:
    logger.error(f"Failed to process: {str(e)}")
    return f"Error: {str(e)}"

# Never use bare except or silently swallow errors
# WRONG:
try:
    do_something()
except:
    pass  # Never do this
```

---

## Logging

Use the global async logger throughout:

```python
from api.core.logger import setup_logger, get_logger, close_logger

# Initialize once at startup (main.py)
logger = setup_logger(name="agent", level=logging.INFO, log_prefix="agent")

# Get logger in any module
logger = get_logger()
if logger:
    logger.think("Analyzing user intent")
    logger.act("Executing tool")
    logger.error("Something went wrong")

# Stage-specific methods (use these instead of generic info):
# logger.retrieve() - 📚 Retrieve stage
# logger.think()    - 🤔 Think stage
# logger.plan()     - 🛠️ Plan stage
# logger.act()      - ⚡ Act stage
# logger.reflect()  - 👀 Reflect stage
# logger.success()  - ✅ Success
# logger.error()    - ❌ Error

# Cleanup at shutdown
close_logger()
```

---

## Architecture Patterns

### 5-Node ReAct Workflow

```
Retrieve → Think → Plan → Act → Reflect → Think (loop)
   ↓         ↓       ↓      ↓       ↓
 Load    Intent   Decide  Execute Evaluate
 SOPs   Analysis  Action  Tools   Results
```

**Node Implementation** (`/src/agent/core/agent.py`):

1. **Retrieve** (`retrieve_node`): Loads SOPs from skills directory
2. **Think** (`think_node`): Intent understanding using 01_think.md
3. **Plan** (`plan_node`): Decision-making using 02_plan.md + 03_act.md
4. **Act** (`tools_node`): Tool execution via LangChain ToolNode
5. **Reflect** (`reflect_node`): Result evaluation using 04_reflect.md

### Prompt System

**Location**: `/src/agent/prompts/`

| File | Stage | Purpose |
|------|-------|---------|
| `01_think.md` | Think | Intent recognition, information decomposition, boundary checks |
| `02_plan.md` | Plan | SOP-driven planning, tool mapping, fallback strategies |
| `03_act.md` | Act | Tool invocation rules, safety constraints, silent execution |
| `04_reflect.md` | Reflect | Result evaluation, failure handling, final answer generation |

**Prompt Loading** (in `Agent.__init__`):
```python
self.internal_prompts = self._load_internal_prompts(prompts_dir)
# Loads: 01_think.md, 02_plan.md, 03_act.md, 04_reflect.md
```

**Prompt Stitching** (example from `think_node`):
```python
sys_content = (
    f"{self.system_prompt}\n\n"           # User-defined persona
    f"{state.get('current_sop', '')}\n\n" # Dynamic SOPs from skills
    f"{self.internal_prompts['think']}"   # Framework logic
)
```

### Adding New Tools

1. Create file in `src/agent/tools/builtin/`
2. Use `@tool` decorator from `langchain_core.tools`
3. Register in `src/agent/tools/builtin/__init__.py`

```python
# src/agent/tools/builtin/my_tool.py
from langchain_core.tools import tool
from typing import Optional

@tool
async def my_tool(param: str, timeout: int = 30) -> str:
    """Brief description for the LLM to understand when to use this tool."""
    # Implementation
    return f"Result: {param}"

# src/agent/tools/builtin/__init__.py
from .my_tool import my_tool
AGENT_TOOLS = [shell_exec, web_fetch, file_append, my_tool]
```

### Adding New Skills

Create directory with SKILL.md:

```
src/agent/skills/
└── skill-name-version/
    └── SKILL.md
```

```markdown
---
name: skill-name
description: What this skill does
homepage: https://example.com
---

# Skill Title

## Usage
Instructions for the agent...
```

Skills are automatically loaded during the `retrieve` phase by scanning for folders containing `SKILL.md`.

### State Management

Use TypedDict for LangGraph state:

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    task: str
    current_sop: str
```

**State Flow**:
- `messages`: Conversation history with tool calls (auto-managed by add_messages)
- `task`: Original user task (set at initialization)
- `current_sop`: Dynamic SOPs loaded by retrieve_node

---

## Development Guidelines

### Working with Prompts

1. **Maintain structure**: Keep the numbered naming convention (01_, 02_, etc.)
2. **Stage headers**: Each prompt should start with "# 阶段 X：[Name]"
3. **Clear sections**: Use ### for subsections within each stage
4. **Output format**: Specify expected output structure when relevant
5. **End marker**: Include `(End of file - total X lines)` at the end

### Working with Skills

1. **Version folders**: Use `skill-name-version/` format (e.g., `weather-1.0.0/`)
2. **Required file**: Must contain `SKILL.md` to be auto-discovered
3. **Markdown only**: Skills are instructions, not code
4. **Front matter**: Include name and description in YAML front matter

### Testing Agent Flow

```python
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from agent.core import Agent
from agent.tools import get_tools

async def test_agent():
    llm = ChatOpenAI(model="deepseek-chat", temperature=0.7)
    
    agent = Agent(
        llm=llm,
        tools=get_tools(),
        prompts_dir="agent/prompts",
        skills_dir="agent/skills",
        system_prompt="你是一个温柔、善良、贴心的智能助手。"
    )

    # Test streaming
    async for output in agent.graph.astream({
        "task": "测试任务",
        "messages": [HumanMessage(content="测试任务")],
        "current_sop": ""
    }):
        for node_name, state_update in output.items():
            print(f"[{node_name}]")

    # Test direct invocation
    final_state = await agent.graph.ainvoke({
        "task": "测试任务",
        "messages": [HumanMessage(content="测试任务")],
        "current_sop": ""
    })
    
    print(final_state["messages"][-1].content)

asyncio.run(test_agent())
```

---

## File Organization

```
src/
├── agent/
│   ├── core/           # Core Agent, LLM wrapper, Logger
│   │   ├── agent.py    # 5-node workflow implementation
│   │   ├── llm.py      # LLM factory wrapper
│   │   └── logger.py   # Global async logging system
│   ├── prompts/        # Framework workflow prompts (.md)
│   │   ├── 01_think.md
│   │   ├── 02_plan.md
│   │   ├── 03_act.md
│   │   └── 04_reflect.md
│   ├── tools/          # Tool implementations
│   │   ├── __init__.py
│   │   └── builtin/    # @tool decorated functions
│   │       ├── shell_execute.py
│   │       ├── web_fetch.py
│   │       └── file_write.py
│   └── skills/         # Business knowledge (SKILL.md)
│       ├── weather-1.0.0/
│       └── self-improving-agent-3.0.5/
├── api/                # FastAPI endpoints
│   ├── core/           # Logger, shared utilities
│   ├── router/         # API routers
│   └── services/       # Business logic services
└── main.py             # Demo entry point
```

---

## Security Considerations

- **Shell commands**: Validated against dangerous command blacklist
- **Timeout controls**: All tool executions have configurable timeouts
- **File operations**: Restricted to safe paths
- **Output truncation**: Tool outputs truncated to prevent token overflow
- **Never hardcode secrets**: Use `.env` file for API keys

**Dangerous Command Blacklist**:
- `rm -rf`, `sudo`, `chmod -R`, `dd`, `mkfs`, etc.
- See `shell_execute.py` for complete list

---

## Pre-Commit Checklist

- [ ] Code formatted: `ruff format .`
- [ ] Lint passes: `ruff check .`
- [ ] Type annotations on all function signatures
- [ ] Logger used instead of `print()` statements
- [ ] Error handling is comprehensive
- [ ] No hardcoded secrets or paths
- [ ] New tools registered in `builtin/__init__.py`
- [ ] New skills have `SKILL.md` in versioned folder

---

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

---

## Common Issues & Solutions

### Prompt Not Loading
**Symptom**: Agent runs but ignores stage-specific instructions
**Check**: Verify prompt files exist in `agent/prompts/` directory
**Fix**: Ensure files are named `01_think.md`, `02_plan.md`, etc.

### Skills Not Discovered
**Symptom**: `print_agent_config()` shows empty skills list
**Check**: Verify folder structure: `skills/skill-name-version/SKILL.md`
**Fix**: Ensure `SKILL.md` exists at the root of versioned folder

### Tool Not Available
**Symptom**: LLM doesn't call expected tool
**Check**: Verify tool is in `AGENT_TOOLS` list in `builtin/__init__.py`
**Fix**: Import and add tool to `AGENT_TOOLS` list

### Tool Execution Timeout
**Symptom**: Tools fail with timeout error
**Check**: Review tool implementation for async/await
**Fix**: Add timeout parameter or optimize operation

---

## Environment Setup

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

The logger system will automatically create log files in `src/agent/logs/` on each run.
