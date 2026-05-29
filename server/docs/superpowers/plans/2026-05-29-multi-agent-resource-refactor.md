# Multi-Agent Resource Generation System Refactor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the multi-agent resource generation system so each agent can run independently (for path planning's single-agent calls) while preserving the multi-agent orchestration flow (Planning → Workers → Review) for full resource generation.

**Architecture:** Remove the `ResourceGenerationWorkflow` class. Each agent inherits from a `BaseResourceAgent` and is registered in `AGENT_REGISTRY`. Service layer contains two flat orchestration functions: `generate_resources()` (multi-agent: Planning → parallel workers → Review) and `generate_single_resource()` (single-agent: direct call with learning_need + profile). Path planning calls `generate_single_resource()` instead of the heavy workflow.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, LangGraph/LangChain, asyncio

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `resource/agents/base.py` | BaseResourceAgent ABC + AGENT_REGISTRY + register_agent decorator |
| Delete | `resource/workflow.py` | Remove Workflow class entirely |
| Modify | `resource/agents/__init__.py` | Replace hardcoded AGENT_CLASSES with registry imports |
| Modify | `resource/agents/planning.py` | Inherit BaseResourceAgent, add agent_id, return blueprint+instructions in structured format |
| Modify | `resource/agents/content.py` | Inherit BaseResourceAgent, add agent_id, @register_agent |
| Modify | `resource/agents/quiz.py` | Inherit BaseResourceAgent, add agent_id, @register_agent |
| Modify | `resource/agents/mindmap.py` | Inherit BaseResourceAgent, add agent_id, @register_agent |
| Modify | `resource/agents/code.py` | Inherit BaseResourceAgent, add agent_id, @register_agent |
| Modify | `resource/agents/reading.py` | Inherit BaseResourceAgent, add agent_id, @register_agent |
| Modify | `resource/agents/ppt.py` | Inherit BaseResourceAgent, add agent_id, @register_agent |
| Modify | `resource/agents/review.py` | Inherit BaseResourceAgent, add agent_id, @register_agent |
| Modify | `resource/schemas.py` | WorkerState: blueprint/instruction default to None; add PlanningOutput schema |
| Modify | `resource/service.py` | Remove Workflow ref, add generate_resources() and generate_single_resource() functions, add bg_single_gen_task() |
| Modify | `resource/api.py` | Add single-agent endpoint; update multi-agent endpoint to use new service functions |
| Modify | `path/service.py` | generate_node_resources() calls start_single_resource_task() instead of start_resource_task() |

---

### Task 1: Create BaseResourceAgent + AGENT_REGISTRY

**Files:**
- Create: `server/app/resource/agents/base.py`

- [ ] **Step 1: Create base.py with BaseResourceAgent and registry**

```python
"""Agent base class and registry for resource generation agents."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.resource.schemas import WorkerState, WorkerResult
    from app.resource.events import AgentEventEmitter


AGENT_REGISTRY: dict[str, type["BaseResourceAgent"]] = {}


def register_agent(cls: type["BaseResourceAgent"]) -> type["BaseResourceAgent"]:
    """Decorator to register an agent class in the global registry."""
    AGENT_REGISTRY[cls.agent_id] = cls
    return cls


class BaseResourceAgent(ABC):
    """Base class for all resource generation agents.

    Each agent can run independently with just learning_need + profile,
    or with blueprint + instruction from PlanningAgent in multi-agent mode.
    """

    agent_id: str
    agent_name: str

    def __init__(self, emitter: "AgentEventEmitter | None" = None) -> None:
        self.emitter = emitter

    async def run(self, state: "WorkerState") -> "WorkerResult":
        """Unified entry point for both single-agent and multi-agent modes."""
        input_text = self._build_input(state)
        output = await self._execute(input_text)
        return self._validate(output)

    def _build_input(self, state: "WorkerState") -> str:
        """Build prompt input from WorkerState. Uses blueprint/instruction if present,
        falls back to learning_need + profile only."""
        from app.resource.agents.common import build_worker_base_context
        return build_worker_base_context(state, self.agent_id, self.agent_name)

    @abstractmethod
    async def _execute(self, input_text: str) -> dict:
        """Execute the agent's core logic and return raw output dict."""
        ...

    def _validate(self, output: dict) -> "WorkerResult":
        """Validate and wrap output. Override for agent-specific validation."""
        from app.resource.schemas import WorkerResult
        return WorkerResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            output=output,
        )
```

- [ ] **Step 2: Verify the file was created correctly**

Run: `python -c "from app.resource.agents.base import BaseResourceAgent, AGENT_REGISTRY, register_agent; print('OK')"`
Expected: `OK` (run from `server/` directory)

- [ ] **Step 3: Commit**

```bash
git add server/app/resource/agents/base.py
git commit -m "feat(resource): add BaseResourceAgent base class and AGENT_REGISTRY"
```

---

### Task 2: Register all agents with BaseResourceAgent

**Files:**
- Modify: `server/app/resource/agents/planning.py`
- Modify: `server/app/resource/agents/content.py`
- Modify: `server/app/resource/agents/quiz.py`
- Modify: `server/app/resource/agents/mindmap.py`
- Modify: `server/app/resource/agents/code.py`
- Modify: `server/app/resource/agents/reading.py`
- Modify: `server/app/resource/agents/ppt.py`
- Modify: `server/app/resource/agents/review.py`
- Modify: `server/app/resource/agents/__init__.py`

Each agent needs three changes:
1. Add `from app.resource.agents.base import BaseResourceAgent, register_agent`
2. Add `@register_agent` decorator and `agent_id` / `agent_name` class attributes
3. Inherit from `BaseResourceAgent` instead of standalone class
4. Keep existing `run()` logic as `_execute()`, move the input-building part to rely on `BaseResourceAgent._build_input()`

**IMPORTANT:** The existing `run()` methods in each agent already contain the full execution flow (build input → call LLM → validate → retry). We need to restructure them to fit the `BaseResourceAgent.run()` template while preserving the retry/validation logic.

The pattern for each agent:

```python
@register_agent
class ContentAgent(BaseResourceAgent):
    agent_id = "content"
    agent_name = "内容生成"

    # Keep existing __init__ logic but call super().__init__(emitter)

    async def _execute(self, input_text: str) -> dict:
        """Core execution: call LLM with input_text, return raw output."""
        # Move the LLM call + retry logic from existing run() here
        # The input_text is already built by _build_input()
        ...
```

- [ ] **Step 1: Refactor planning.py**

Current `PlanningAgent.__init__` takes `emitter` and `agent_id`. Change to:
- Inherit `BaseResourceAgent`
- Set `agent_id = "planning"`, `agent_name = "规划"`
- `__init__` calls `super().__init__(emitter=emitter)`
- Move existing `run()` body into `_execute()`, using `self._build_input(state)` for input
- `_execute()` returns `{"blueprint": ..., "instructions": {...}}` — the instructions dict maps `agent_id → AgentInstruction`
- Add `_validate()` override to validate the planning output structure

Key: PlanningAgent's output must be structured so the service layer can extract `blueprint` and `instructions[agent_id]` to pass to each worker.

Current planning.py `run()` method:
1. Builds prompt via `build_worker_base_context(state, self.agent_id, self.agent_name)`
2. Calls `self.llm.ainvoke_json()`
3. Validates output has `blueprint` and `agent_instructions`
4. Returns `WorkerResult`

Restructured:
- `_build_input()` inherited from BaseResourceAgent (already calls `build_worker_base_context`)
- `_execute()` does the LLM call + returns raw dict
- `_validate()` wraps into WorkerResult

- [ ] **Step 2: Refactor content.py**

Current `ContentAgent.__init__` takes `emitter`, `agent_id`, `agent_config`. Change to:
- Inherit `BaseResourceAgent`
- Set `agent_id = "content"`, `agent_name = "内容生成"`
- `__init__(self, emitter=None, agent_config=None)` calls `super().__init__(emitter=emitter)`, stores `agent_config`
- Move existing `run()` LLM call + retry into `_execute()`
- Remove manual `build_worker_base_context` call (handled by `_build_input()`)

- [ ] **Step 3: Refactor quiz.py**

Same pattern as content.py. `agent_id = "quiz"`, `agent_name = "习题生成"`.

- [ ] **Step 4: Refactor mindmap.py**

Same pattern. `agent_id = "mindmap"`, `agent_name = "思维导图生成"`.

- [ ] **Step 5: Refactor code.py**

Same pattern. `agent_id = "code"`, `agent_name = "代码生成"`.

- [ ] **Step 6: Refactor reading.py**

Same pattern. `agent_id = "reading"`, `agent_name = "阅读生成"`.

- [ ] **Step 7: Refactor ppt.py**

Same pattern. `agent_id = "ppt"`, `agent_name = "PPT生成"`.

- [ ] **Step 8: Refactor review.py**

Same pattern as planning.py. `agent_id = "review"`, `agent_name = "审核"`.
ReviewAgent's `_execute()` receives the worker results as part of the state and validates them.

- [ ] **Step 9: Update __init__.py**

Replace the current hardcoded `AGENT_CLASSES` dict with registry-based imports:

```python
"""Resource generation agents — auto-registered via @register_agent."""

from app.resource.agents.base import AGENT_REGISTRY, register_agent

# Import all agents to trigger registration
from app.resource.agents.planning import PlanningAgent
from app.resource.agents.content import ContentAgent
from app.resource.agents.quiz import QuizAgent
from app.resource.agents.mindmap import MindmapAgent
from app.resource.agents.code import CodeAgent
from app.resource.agents.reading import ReadingAgent
from app.resource.agents.ppt import PptAgent
from app.resource.agents.review import ReviewAgent

__all__ = [
    "AGENT_REGISTRY",
    "PlanningAgent",
    "ContentAgent",
    "QuizAgent",
    "MindmapAgent",
    "CodeAgent",
    "ReadingAgent",
    "PptAgent",
    "ReviewAgent",
]
```

- [ ] **Step 10: Verify all agents register correctly**

Run: `cd server && python -c "from app.resource.agents import AGENT_REGISTRY; print(AGENT_REGISTRY.keys())"`
Expected: `dict_keys(['planning', 'content', 'quiz', 'mindmap', 'code', 'reading', 'ppt', 'review'])`

- [ ] **Step 11: Commit**

```bash
git add server/app/resource/agents/
git commit -m "refactor(resource): all agents inherit BaseResourceAgent and register via AGENT_REGISTRY"
```

---

### Task 3: Update WorkerState schemas

**Files:**
- Modify: `server/app/resource/schemas.py`

- [ ] **Step 1: Make blueprint and instruction default to None in WorkerState**

Current WorkerState likely has blueprint and instruction as required fields. Change to Optional with None defaults:

```python
class WorkerState(BaseModel):
    learning_need: str
    profile: dict[str, Any]
    blueprint: LearningBlueprint | None = None
    instruction: AgentInstruction | None = None
    agent_config: dict[str, Any] = {}
```

This is the key change that enables single-agent mode: when blueprint and instruction are None, agents fall back to learning_need + profile only.

- [ ] **Step 2: Add PlanningOutput schema for structured PlanningAgent output**

The service layer needs to extract blueprint and per-agent instructions from PlanningAgent's result. Add:

```python
class PlanningOutput(BaseModel):
    """Structured output from PlanningAgent."""
    blueprint: LearningBlueprint
    instructions: dict[str, AgentInstruction]  # agent_id → instruction
```

- [ ] **Step 3: Verify schemas load correctly**

Run: `cd server && python -c "from app.resource.schemas import WorkerState, PlanningOutput; s = WorkerState(learning_need='test', profile={}); print(s); print('blueprint:', s.blueprint)"`
Expected: WorkerState with `blueprint=None`

- [ ] **Step 4: Commit**

```bash
git add server/app/resource/schemas.py
git commit -m "refactor(resource): WorkerState blueprint/instruction default to None, add PlanningOutput schema"
```

---

### Task 4: Delete workflow.py and refactor service.py

**Files:**
- Delete: `server/app/resource/workflow.py`
- Modify: `server/app/resource/service.py`

This is the core refactor. Remove the Workflow class and replace with two flat service functions.

- [ ] **Step 1: Delete workflow.py**

```bash
rm server/app/resource/workflow.py
```

- [ ] **Step 2: Add generate_resources() function to service.py**

This replaces the multi-agent orchestration that was in `ResourceGenerationWorkflow.run()`. The logic is identical — just a flat function instead of a class method:

```python
async def generate_resources(
    *,
    user_id: int,
    learning_need: str,
    enabled_agents: list[str],
    enable_review: bool = True,
    event_sink: asyncio.Queue | None = None,
) -> list[WorkerResult]:
    """Multi-agent resource generation: Planning → parallel Workers → Review."""
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.events import AgentEventEmitter

    profile = await _get_user_profile(user_id)
    resource_id = await _create_resource_record(user_id, learning_need, enabled_agents)
    emitter = AgentEventEmitter(resource_id=resource_id, event_sink=event_sink)

    # 1. PlanningAgent
    planning_result = await AGENT_REGISTRY["planning"](emitter).run(
        WorkerState(learning_need=learning_need, profile=profile)
    )
    planning_output = PlanningOutput(**planning_result.output)
    blueprint = planning_output.blueprint
    instructions = planning_output.instructions

    # 2. Parallel worker agents
    worker_tasks = []
    for agent_id in enabled_agents:
        if agent_id in ("planning", "review"):
            continue
        if agent_id not in AGENT_REGISTRY:
            continue
        worker_tasks.append(
            AGENT_REGISTRY[agent_id](emitter).run(
                WorkerState(
                    learning_need=learning_need,
                    profile=profile,
                    blueprint=blueprint,
                    instruction=instructions.get(agent_id),
                )
            )
        )
    worker_results = await asyncio.gather(*worker_tasks)

    # 3. ReviewAgent (optional)
    if enable_review and "review" in AGENT_REGISTRY:
        review_result = await AGENT_REGISTRY["review"](emitter).run(
            WorkerState(
                learning_need=learning_need,
                profile=profile,
                blueprint=blueprint,
            )
        )
        # Apply review feedback if needed (existing logic)

    # 4. Save results
    await _save_resource_items(resource_id, worker_results, user_id)
    return worker_results
```

- [ ] **Step 3: Add generate_single_resource() function to service.py**

```python
async def generate_single_resource(
    *,
    user_id: int,
    agent_id: str,
    learning_need: str,
    event_sink: asyncio.Queue | None = None,
    node_id: int | None = None,
) -> WorkerResult:
    """Single-agent direct call: learning_need + profile → agent → save."""
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.events import AgentEventEmitter

    profile = await _get_user_profile(user_id)
    resource_id = await _create_resource_record(user_id, learning_need, [agent_id])
    emitter = AgentEventEmitter(resource_id=resource_id, event_sink=event_sink)

    result = await AGENT_REGISTRY[agent_id](emitter).run(
        WorkerState(learning_need=learning_need, profile=profile)
    )

    await _save_resource_items(resource_id, [result], user_id)

    # Update path node status if called from path planning
    if node_id is not None:
        await _update_node_resource_binding(node_id, resource_id, user_id)

    return result
```

- [ ] **Step 4: Add bg_single_gen_task() background task function**

```python
async def bg_single_gen_task(
    user_id: int,
    resource_id: int,
    agent_id: str,
    learning_need: str,
    node_id: int | None = None,
) -> None:
    """Background task for single-agent generation."""
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.events import AgentEventEmitter

    try:
        profile = await _get_user_profile(user_id)
        emitter = AgentEventEmitter(resource_id=resource_id, event_sink=None)

        result = await AGENT_REGISTRY[agent_id](emitter).run(
            WorkerState(learning_need=learning_need, profile=profile)
        )

        await _save_resource_items(resource_id, [result], user_id)

        if node_id is not None:
            await _update_node_resource_binding(node_id, resource_id, user_id)

    except Exception as e:
        logger.error(f"Single-agent generation failed: {e}")
        await _update_resource_status(resource_id, "failed")
```

- [ ] **Step 5: Add start_single_resource_task() entry point**

This mirrors the existing `start_resource_task()` but for single-agent mode:

```python
async def start_single_resource_task(
    *,
    user_id: int,
    agent_id: str,
    learning_need: str,
    node_id: int | None = None,
) -> int:
    """Create resource record and launch single-agent background task. Returns resource_id."""
    resource_id = await _create_resource_record(user_id, learning_need, [agent_id])
    asyncio.create_task(
        bg_single_gen_task(user_id, resource_id, agent_id, learning_need, node_id)
    )
    return resource_id
```

- [ ] **Step 6: Remove all Workflow imports and references from service.py**

Search for `from app.resource.workflow import` and `ResourceGenerationWorkflow` references. Remove them all. The existing `start_resource_task()` function's `bg_gen_task()` should call `generate_resources()` instead of `ResourceGenerationWorkflow.run()`.

- [ ] **Step 7: Verify service.py has no syntax errors**

Run: `cd server && python -c "from app.resource.service import generate_resources, generate_single_resource, start_single_resource_task; print('OK')"`
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add server/app/resource/service.py
git rm server/app/resource/workflow.py
git commit -m "refactor(resource): remove Workflow class, add flat generate_resources() and generate_single_resource() functions"
```

---

### Task 5: Update resource API endpoints

**Files:**
- Modify: `server/app/resource/api.py`

- [ ] **Step 1: Add single-agent generation endpoint**

Add a new endpoint that accepts `agent_id` + `learning_need` and calls `start_single_resource_task()`:

```python
@router.post("/generate/single")
async def generate_single(
    request: SingleResourceRequest,
    user: User = Depends(get_current_user),
):
    """Single-agent direct generation (for path planning or on-demand use)."""
    resource_id = await start_single_resource_task(
        user_id=user.id,
        agent_id=request.agent_id,
        learning_need=request.learning_need,
        node_id=request.node_id,
    )
    return HttpResponse.success(data={"resource_id": resource_id, "status": "generating"})
```

- [ ] **Step 2: Add SingleResourceRequest schema to schemas.py**

```python
class SingleResourceRequest(BaseModel):
    """Request for single-agent resource generation."""
    agent_id: str
    learning_need: str
    node_id: int | None = None
```

- [ ] **Step 3: Update existing generate endpoint to use generate_resources()**

The existing `/generate` endpoint should call `generate_resources()` instead of `ResourceGenerationWorkflow`. The SSE streaming logic stays the same — it still creates an event_sink Queue and streams to the frontend.

- [ ] **Step 4: Verify API endpoints load**

Run: `cd server && python -c "from app.resource.api import router; print(len(router.routes), 'routes'); print('OK')"`
Expected: Route count + `OK`

- [ ] **Step 5: Commit**

```bash
git add server/app/resource/api.py server/app/resource/schemas.py
git commit -m "feat(resource): add single-agent generation endpoint, update multi-agent endpoint"
```

---

### Task 6: Update path planning to use single-agent mode

**Files:**
- Modify: `server/app/path/service.py`
- Modify: `server/app/path/schemas.py`

- [ ] **Step 1: Update CoursePathService.generate_node_resources()**

Current code constructs a full `ResourceGenerationRequest` and calls `ResourceUsecases.start_resource_task()`. Replace with:

```python
async def generate_node_resources(self, *, user_id: int, node_id: int, selected_agents: list[str]):
    """Generate resources for a path node using single-agent mode."""
    from app.resource.service import start_single_resource_task

    node = ...  # existing node lookup logic
    learning_need = self._build_node_learning_need(node, path)  # existing logic

    resource_ids = []
    for agent_id in selected_agents:
        resource_id = await start_single_resource_task(
            user_id=user_id,
            agent_id=agent_id,
            learning_need=learning_need,
            node_id=node_id,
        )
        resource_ids.append(resource_id)

    return {"resource_ids": resource_ids, "node_id": node_id, "status": "generating"}
```

- [ ] **Step 2: Simplify path schemas**

Remove heavy dependencies on `AgentConfigs` / `AgentSelection` from resource schemas. Path planning only needs:
- `selected_agents: list[str]` — which agents to call
- `node_id: int` — which path node

Update the path request/response schemas accordingly.

- [ ] **Step 3: Verify path service loads**

Run: `cd server && python -c "from app.path.service import CoursePathService; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add server/app/path/service.py server/app/path/schemas.py
git commit -m "refactor(path): use single-agent mode for node resource generation"
```

---

### Task 7: Integration verification

- [ ] **Step 1: Verify full import chain works**

Run: `cd server && python -c "from app.resource.agents import AGENT_REGISTRY; from app.resource.service import generate_resources, generate_single_resource, start_single_resource_task; from app.path.service import CoursePathService; print('All imports OK')"`

- [ ] **Step 2: Verify AGENT_REGISTRY has all 8 agents**

Run: `cd server && python -c "from app.resource.agents import AGENT_REGISTRY; expected = {'planning','content','quiz','mindmap','code','reading','ppt','review'}; assert set(AGENT_REGISTRY.keys()) == expected, f'Missing: {expected - set(AGENT_REGISTRY.keys())}'; print('All 8 agents registered')"`

- [ ] **Step 3: Verify WorkerState works in both modes**

Run: `cd server && python -c "
from app.resource.schemas import WorkerState
# Single-agent mode
s1 = WorkerState(learning_need='FastAPI', profile={})
assert s1.blueprint is None
assert s1.instruction is None
print('Single-agent mode: OK')
# Multi-agent mode would set blueprint + instruction
print('Both modes: OK')
"`

- [ ] **Step 4: Verify no remaining references to workflow.py**

Run: `cd server && grep -r "workflow" app/resource/ app/path/ --include="*.py" | grep -v __pycache__ | grep -v ".pyc"`
Expected: No references to `ResourceGenerationWorkflow` or `from app.resource.workflow`

- [ ] **Step 5: Start dev server and verify no startup errors**

Run: `cd server && timeout 5 uv run python -c "from app.main import app; print('App loaded OK')" || true`

- [ ] **Step 6: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: integration fixes for multi-agent refactor"
```
