# ReAct Agent 架构设计

## 概览

本文档描述了 ReAct Agent 框架的架构设计。该框架基于 **LangGraph** 和 **LangChain**，实现了一个标准的 Think-Plan-Act-Reflect 自治智能体工作流。

## 核心设计原则

1. **工作流驱动**：利用 LangGraph 状态机严格控制思考与执行的生命周期。
2. **提示词分层（Prompt Stitching）**：将底层框架逻辑、业务知识（SOP）和用户人设解耦。
3. **SOP 动态加载**：非代码人员可以通过编写 Markdown 文件直接为 Agent 注入新能力。
4. **状态隔离**：将对话上下文、当前任务目标、动态注入的知识分离在强类型的状态字典中。

---

## 5 节点 ReAct 循环

本框架的工作流由 5 个节点构成：

```text
┌─────────────────────────────────────────────────────────────┐
│                        ReAct 状态机                          │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ Retrieve │───▶│  Think   │───▶│  Plan    │───▶│   Act  │ │
│  └──────────┘    └──────────┘    └──────────┘    └────────┘ │
│                       ▲                │              │     │
│                       │                │              ▼     │
│                       │                │         ┌────────┐ │
│                       │                └────────▶│  END   │ │
│                       │                          └────────┘ │
│                       │                                     │
│                       └──────────────────────────┌────────┐ │
│                                                  │Reflect │ │
│                                                  └────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 节点说明

#### 0. Retrieve (`retrieve_node`)
- **职责**：加载业务领域知识。
- **行为**：扫描 `skills_dir`，读取所有的 `SKILL.md`，组装成文本。
- **输出状态**：`current_sop`。

#### 1. Think (`think_node`)
- **职责**：意图理解与状态分析。
- **输入**：`system_prompt` + `current_sop` + `01_think.md` + 对话历史。
- **行为**：LLM 深入分析当前局面与目标。
- **输出状态**：追加一条 `🤔 [思考分析]: ...` 的 AIMessage 到 `messages`。

#### 2. Plan (`plan_node`)
- **职责**：制定动作或生成最终答案。
- **输入**：`system_prompt` + `current_sop` + `02_plan.md` + `03_act.md` + 对话历史。
- **行为**：LLM 决定是否需要调用工具。如果调用工具，则返回 `tool_calls`；否则返回最终文本。
- **路由**：如果有 `tool_calls`，路由到 `Act`；如果没有，路由到 `END`。

#### 3. Act (`tools_node`)
- **职责**：执行工具。
- **实现**：直接使用 LangGraph 预置的 `ToolNode`。
- **行为**：执行系统物理工具（如 shell, web_fetch）。
- **输出状态**：将工具执行结果作为 ToolMessage 追加到 `messages`。

#### 4. Reflect (`reflect_node`)
- **职责**：评估工具返回结果。
- **输入**：`system_prompt` + `04_reflect.md` + 包含工具结果的对话历史。
- **行为**：评估工具数据是否满足需求，产生反思记录。
- **输出状态**：追加一条 `👀 [结果反思]: ...` 的 AIMessage 到 `messages`，随后循环回到 `Think`。

---

## 状态管理 (State Management)

框架使用 LangGraph 的 `TypedDict` 定义状态，在各节点之间流转。

代码位置：[src/agent/core/agent.py](../src/agent/core/agent.py)

```python
class AgentState(TypedDict):
    """LangGraph 状态机"""
    messages: Annotated[list[BaseMessage], add_messages]  # 对话历史与工具调用记录
    task: str                                             # 当前执行的原始任务目标
    current_sop: str                                      # Retrieve 节点加载的知识库文本
```

---

## 提示词缝合策略 (Prompt Stitching)

为了兼顾通用性与可扩展性，Prompt 被划分为三层：

1. **业务人设层 (`system_prompt`)**：
   - 由调用方初始化 Agent 时外部注入（如："你是一个温柔的助手..."）。
2. **业务知识层 (`current_sop`)**：
   - `Retrieve` 节点自动从 `skills/` 目录下读取并拼接的动态上下文。
3. **框架逻辑层 (`internal_prompts`)**：
   - 框架内部的固定约束规范，存储在 `src/agent/prompts/` 目录下（`01_think.md` 等）。

**缝合示例（Think 节点）：**
```python
sys_content = (
    f"{self.system_prompt}\n\n"
    f"{state.get('current_sop', '')}\n\n"
    f"{self.internal_prompts['think']}"
)
```

---

## 物理工具系统 (Tools)

工具系统负责赋予 Agent 与外部世界交互的能力。

代码位置：[src/agent/tools/](../src/agent/tools/)

### 设计规范
- 工具直接采用 LangChain 的 `@tool` 装饰器实现，自动推导 JSON Schema。
- 工具集合在 `src/agent/tools/builtin/__init__.py` 的 `AGENT_TOOLS` 列表中集中注册。
- 工具函数建议使用 `async` 异步实现。

### 内置工具
- **`shell_exec`**：支持异步执行 shell 命令，内置安全黑名单（拦截 `rm`, `sudo` 等高危操作），包含超时控制。
- **`web_fetch`**：基于 `httpx` 的异步网页抓取工具，包含字符截断防护。
- **`file_append`**：安全的本地文件写入工具，支持自动创建缺失目录。

---

## 业务技能系统 (Skills / SOP)

技能系统用于为 Agent 提供高层次的领域知识和处理步骤。

目录位置：[src/agent/skills/](../src/agent/skills/)

### 设计规范
- 采用 **Markdown** 作为载体（`SKILL.md`），大幅降低了业务人员编写 SOP 的门槛。
- 不包含 Python 逻辑代码，纯粹作为 LLM 的 Instruction Context。

### 目录结构要求
```text
src/agent/skills/
└── weather-1.0.0/      # 技能文件夹名称
    └── SKILL.md        # 必须存在此文件
```
*注：只要含有 `SKILL.md` 的文件夹都会在 Retrieve 阶段被 Agent 自动捕获。*

---

## 模型接入层 (LLM Layer)

代码位置：[src/agent/core/llm.py](../src/agent/core/llm.py)

- 统一采用 `langchain_openai.ChatOpenAI` 接口接入模型。
- 通过修改 `base_url`，可以无缝兼容所有支持 OpenAI API 协议的模型（如 DeepSeek, 通义千问, 本地 Ollama 等）。
- 提供了统一的 `LLM.create()` 工厂方法初始化模型。

---

## 异常与安全性处理

1. **工具级安全**：`shell_exec` 内部对命令进行了正则校验，直接返回 `Error` 而非抛出异常，让 LLM 能够感知到权限受限。
2. **输出截断**：网络请求和命令执行都限制了最大输出长度，防止 Token 溢出导致图状态崩溃。
3. **容错机制**：如果未找到 `prompts_dir`，Agent 会警告并降级运行，而不会直接崩溃。
