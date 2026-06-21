# Resource Video Agent Completion Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 standalone resource 多智能体重构的收口，让 `PlanningAgent -> base agents -> PPT/Video` 全链路只使用 `TeachingPlan` 和 `DownstreamContext`，并让 VideoAgent 可从前端选择、生成、审查和落库。

**Architecture:** `PlanningAgent` 只产出全局 `TeachingPlan`；`content/mindmap/quiz/code/reading` 并行产出完整资源和受控 `downstream_context`；`ppt/video/review` 只读取 `teaching_plan + upstream_handoffs`，不读取基础资源全文。该计划是破坏式收口，不恢复 `LearningBlueprint`、`AgentInstruction`、`ExecutionPlan`、`previous_results`、`summary_data`、`blueprint`、`instruction` 旧契约。

**Tech Stack:** FastAPI, SQLModel, Pydantic v2, pytest, Vue 3, TypeScript, Vite, PostgreSQL JSONB.

---

## Execution Rules

- 所有 shell 命令使用 `rtk` 前缀。
- 后端命令从 `/Users/apple/Code/software/server` 执行。
- 前端命令从 `/Users/apple/Code/software` 执行。
- 不新增兼容旧字段的读取逻辑。
- 不把 standalone resource 的 `TeachingPlan`/`DownstreamContext` 持久化逻辑混入 path 域表。
- `server/app/resource/agents/video.py` 保持单文件内部多智能体实现。
- 每个任务完成后运行该任务列出的测试，再提交一个聚焦提交。

## Files To Modify

- `server/app/resource/prompts/video_material.md`  
  将视频素材提取 prompt 改为 `teaching_plan + upstream_handoffs` 输入契约。

- `server/app/resource/prompts/ppt_material.md`  
  将 PPT 素材提取 prompt 改为 `MaterialBundle.teaching_plan + upstream_handoffs + artifacts(由 handoff 生成)` 输入契约。

- `server/app/resource/agents/common.py`  
  增加 outline 覆盖选择与 coverage 汇总 helper，修复 handoff 默认覆盖全部大纲的问题。

- `server/app/resource/agents/content.py`  
  让 content handoff 显式声明覆盖全部大纲，并携带真实内容片段。

- `server/app/resource/agents/mindmap.py`  
  让 mindmap handoff 显式声明覆盖全部大纲，并携带结构分支。

- `server/app/resource/agents/quiz.py`  
  让 quiz handoff 显式声明覆盖全部大纲，并从题目知识点构造 key points。

- `server/app/resource/agents/code.py`  
  让 code handoff 只覆盖与代码/示例相关的大纲，找不到时只覆盖第一个大纲。

- `server/app/resource/agents/reading.py`  
  让 reading handoff 显式声明覆盖全部大纲，并携带资源标题作为可复用材料。

- `server/app/resource/agents/ppt.py`  
  PPT 结果 metadata 增加 `teaching_plan_outline_ids`、`covered_source_outline_ids`、`missing_source_outline_ids`。

- `server/app/resource/agents/video.py`  
  Video 结果 metadata 增加 coverage 字段；删除 tutor adapter 对 `previous_results` 的旧字段读取。

- `server/app/resource/review.py`  
  Review envelope 删除基础资源全文，只保留 handoff；PPT/Video 最终产物仍可作为被审查对象。

- `server/app/resource/service.py`  
  更新 workflow docstring 和 phase 名称，移除 `Blueprint/Instructions` 文案。

- `src/features/resource/model/resource.ts`  
  补齐 `video` agent id、video config、handoff DTO。

- `src/features/resource/model/ResourceGeneratorConstants.ts`  
  确认 video agent 常量和默认配置与后端一致。

- `server/tests/resource/test_prompt_contracts.py`  
  新增 prompt 契约测试。

- `server/tests/resource/test_handoff_coverage.py`  
  新增 handoff coverage 单元测试。

- `server/tests/resource/test_review_handoff_envelope.py`  
  新增 review envelope 上下文控制测试。

- `server/tests/resource/test_video_agent.py`  
  更新 video metadata、tutor adapter 测试。

- `server/tests/resource/test_ppt_internal_multi_agent.py`  
  更新 PPT metadata 测试。

- `server/tests/infra/test_schema_validation_all.py`  
  将 `ExecutionPlan` schema 测试改为 `TeachingPlan`。

- `server/tests/test_all_agents.py`  
  将旧 `LearningBlueprint/AgentInstruction/ExecutionPlan/summary_data` 演示测试改为 `TeachingPlan/metrics/downstream_context`。

- `server/tests/test_astron_code.py`  
  将结构化输出 schema 从 `ExecutionPlan` 改为 `TeachingPlan`。

- `server/tests/resource/test_database_session_resilience.py`  
  删除旧 `source` 列自动修复断言，改成验证 `init_db` 不执行 standalone 旧迁移修复。

---

### Task 1: Lock Prompt Contracts To TeachingPlan And Handoffs

**Files:**
- Create: `server/tests/resource/test_prompt_contracts.py`
- Modify: `server/app/resource/prompts/video_material.md`
- Modify: `server/app/resource/prompts/ppt_material.md`

- [ ] **Step 1: Write failing prompt contract tests**

Create `server/tests/resource/test_prompt_contracts.py`:

```python
from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parents[2] / "app" / "resource" / "prompts"
OLD_CONTRACT_TERMS = (
    "blueprint",
    "instruction",
    "previous_results",
    "LearningBlueprint",
    "AgentInstruction",
    "ExecutionPlan",
)


def _read_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def test_video_material_prompt_uses_teaching_plan_and_handoffs_only():
    text = _read_prompt("video_material.md")

    assert "teaching_plan" in text
    assert "upstream_handoffs" in text
    assert "DownstreamContext" in text
    for term in OLD_CONTRACT_TERMS:
        assert term not in text


def test_ppt_material_prompt_uses_teaching_plan_and_handoffs_only():
    text = _read_prompt("ppt_material.md")

    assert "teaching_plan" in text
    assert "upstream_handoffs" in text
    assert "DownstreamContext" in text
    for term in OLD_CONTRACT_TERMS:
        assert term not in text
```

- [ ] **Step 2: Run tests and confirm they fail on old prompt text**

Run:

```bash
rtk uv run pytest tests/resource/test_prompt_contracts.py -q
```

Expected: both tests fail because `video_material.md` and `ppt_material.md` still mention old fields.

- [ ] **Step 3: Replace `video_material.md` with the new contract**

Replace the whole file `server/app/resource/prompts/video_material.md` with:

```markdown
# 视频素材提取智能体 (VideoMaterialAgent)

你是一位教学视频策划专家，负责从上游资源交接摘要中提取可用于讲解视频的素材。

## 输入格式

系统将提供一份 JSON，包含：

- `learning_need`：用户学习需求
- `learning_scenario`：学习场景
- `profile`：学习者画像
- `teaching_plan`：PlanningAgent 生成的全局教学方向、概要、大纲和边界
- `upstream_handoffs`：上游基础资源 Agent 的 `DownstreamContext`，键为 content、mindmap、quiz、code、reading
- `config`：视频配置，如时长、场景数、风格、旁白风格、画幅

`upstream_handoffs` 中每个值包含：

- `source_agent`：来源 Agent
- `one_sentence_summary`：该资源生成内容的一句话摘要
- `covered_outline_ids`：该资源覆盖的 `teaching_plan.outline[].id`
- `materials`：可复用讲解素材列表
- `reusable_assets`：示例、误区、视觉想法、练习引用、代码引用
- `cautions`：下游生成时必须避免的问题

## 输出 JSON

必须返回对象：

```json
{
  "topic": "精确主题",
  "audience": "目标学习者描述",
  "learning_goal": "本视频结束后学习者能完成的动作",
  "core_concepts": ["核心概念1"],
  "facts": ["可讲解的事实点"],
  "examples": ["具体示例"],
  "process_steps": ["流程步骤"],
  "misconceptions": ["常见误区"],
  "practice_prompts": ["可插入的思考题"],
  "visual_opportunities": ["适合画成图、表、代码、流程或对比卡片的内容"],
  "source_map": {"facts": ["content"], "examples": ["reading"]}
}
```

## 约束

1. 只使用 `teaching_plan` 和 `upstream_handoffs` 中出现的信息。
2. 不读取、推断或要求上游完整正文。
3. 不为基础资源 Agent 分配新任务。
4. 优先选择适合视觉化表达的材料。
5. `source_map` 必须记录素材来源 Agent。
6. 输出必须是 JSON 对象，不要包含解释文字。
```

- [ ] **Step 4: Replace `ppt_material.md` with the new contract**

Replace the whole file `server/app/resource/prompts/ppt_material.md` with:

```markdown
# PPT 素材提取智能体 (MaterialAgent)

你是一位教学内容分析专家，负责从上游资源交接摘要中提取 PPT 可用的教学素材。

## 输入格式

系统将提供一份 `MaterialBundle` JSON，包含：

- `learning_need`：用户学习需求
- `learning_scenario`：学习场景
- `profile`：学习者画像
- `teaching_plan`：PlanningAgent 生成的全局教学方向、概要、大纲和边界
- `upstream_handoffs`：上游基础资源 Agent 的 `DownstreamContext`
- `artifacts`：由 `upstream_handoffs` 派生出的短素材，不包含上游完整正文
- `source_type`：resource 或 node
- `node_context`：路径节点场景的节点上下文，standalone resource 时为空

`DownstreamContext` 中可使用的信息包括：

- `source_agent`
- `one_sentence_summary`
- `covered_outline_ids`
- `materials`
- `reusable_assets`
- `cautions`

## 输出要求

必须返回 `MaterialDigest` JSON 对象，包含以下字段：

- `topic`：精确学习主题
- `audience`：目标受众描述
- `learning_goal`：核心学习目标
- `core_concepts`：核心概念列表，3 到 8 个
- `structure_points`：知识组织框架
- `examples`：具体案例和示例，3 到 6 个
- `process_steps`：流程步骤
- `comparisons`：对比分析点
- `misconceptions`：常见误区，2 到 4 个
- `practice_prompts`：练习提示，2 到 4 个
- `code_cases`：代码案例
- `source_map`：每个素材类别来自哪些上游 Agent

## 提取原则

1. 使用 `teaching_plan` 决定 PPT 叙事方向和大纲顺序。
2. 使用 `upstream_handoffs` 决定 PPT 的具体讲解素材。
3. 不要求上游完整正文。
4. 不编造 `upstream_handoffs` 中不存在的事实、示例、题目、代码或阅读材料。
5. 在 `source_map` 中记录每个素材类别使用了哪些 Agent。
6. 输出必须是 JSON 对象，不要包含解释文字。
```

- [ ] **Step 5: Verify prompt tests pass**

Run:

```bash
rtk uv run pytest tests/resource/test_prompt_contracts.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit Task 1**

```bash
rtk git add server/tests/resource/test_prompt_contracts.py server/app/resource/prompts/video_material.md server/app/resource/prompts/ppt_material.md
rtk git commit -m "fix: align resource material prompts with handoff contract"
```

---

### Task 2: Make Handoff Outline Coverage Accurate And Bounded

**Files:**
- Create: `server/tests/resource/test_handoff_coverage.py`
- Modify: `server/app/resource/agents/common.py`
- Modify: `server/app/resource/agents/content.py`
- Modify: `server/app/resource/agents/mindmap.py`
- Modify: `server/app/resource/agents/quiz.py`
- Modify: `server/app/resource/agents/code.py`
- Modify: `server/app/resource/agents/reading.py`

- [ ] **Step 1: Write failing coverage tests**

Create `server/tests/resource/test_handoff_coverage.py`:

```python
from app.resource.agents.common import (
    build_basic_handoff,
    outline_coverage_summary,
    outline_ids_from_plan,
    select_outline_ids_by_keywords,
)
from app.resource.schemas import DownstreamContext, TeachingOutlineItem, TeachingPlan


def _plan() -> TeachingPlan:
    return TeachingPlan(
        topic="TCP",
        outline=[
            TeachingOutlineItem(id="o1", title="连接建立", goal="理解三次握手", key_points=["SYN", "ACK"]),
            TeachingOutlineItem(id="o2", title="可靠传输", goal="理解重传", key_points=["超时重传", "滑动窗口"]),
            TeachingOutlineItem(id="o3", title="代码实践", goal="用代码观察 TCP", key_points=["socket", "抓包"]),
        ],
    )


def test_build_basic_handoff_does_not_claim_all_outline_ids_by_default():
    handoff = build_basic_handoff(
        source_agent="code",
        title="TCP 代码示例",
        summary="使用 socket 演示连接建立",
        teaching_plan=_plan(),
        material_type="code",
    )

    assert handoff.covered_outline_ids == ["o1"]
    assert handoff.materials[0].outline_id == "o1"


def test_build_basic_handoff_filters_unknown_outline_ids():
    handoff = build_basic_handoff(
        source_agent="content",
        title="TCP 内容",
        summary="讲解 TCP",
        teaching_plan=_plan(),
        material_type="explanation",
        covered_outline_ids=["o1", "missing", "o2"],
        material_outline_id="missing",
    )

    assert handoff.covered_outline_ids == ["o1", "o2"]
    assert handoff.materials[0].outline_id == "o1"


def test_select_outline_ids_by_keywords_prefers_matching_outline():
    ids = select_outline_ids_by_keywords(_plan(), ["代码", "socket"])

    assert ids == ["o3"]


def test_outline_coverage_summary_reports_missing_ids():
    plan = _plan()
    handoffs = {
        "content": DownstreamContext(source_agent="content", covered_outline_ids=["o1", "o2"]),
        "code": DownstreamContext(source_agent="code", covered_outline_ids=["o3"]),
        "reading": DownstreamContext(source_agent="reading", covered_outline_ids=["bad"]),
    }

    summary = outline_coverage_summary(plan, handoffs)

    assert summary["teaching_plan_outline_ids"] == ["o1", "o2", "o3"]
    assert summary["covered_source_outline_ids"] == ["o1", "o2", "o3"]
    assert summary["missing_source_outline_ids"] == []
    assert outline_ids_from_plan(plan) == ["o1", "o2", "o3"]
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
rtk uv run pytest tests/resource/test_handoff_coverage.py -q
```

Expected: import failure for new helpers or assertion failure because coverage defaults to all outline ids.

- [ ] **Step 3: Update `common.py` helpers**

In `server/app/resource/agents/common.py`, replace the current helper block from `outline_ids_from_plan` through `build_basic_handoff` with:

```python
from app.resource.schemas import DownstreamContext, DownstreamMaterial, ReusableAssets, TeachingPlan


def outline_ids_from_plan(plan: TeachingPlan | None) -> list[str]:
    if not plan:
        return []
    return [item.id for item in plan.outline]


def first_outline_id(plan: TeachingPlan | None) -> str:
    ids = outline_ids_from_plan(plan)
    return ids[0] if ids else ""


def _valid_outline_ids(plan: TeachingPlan | None, outline_ids: list[str] | None) -> list[str]:
    allowed = set(outline_ids_from_plan(plan))
    if not allowed:
        return []
    result: list[str] = []
    for outline_id in outline_ids or []:
        if outline_id in allowed and outline_id not in result:
            result.append(outline_id)
    return result


def select_outline_ids_by_keywords(plan: TeachingPlan | None, keywords: list[str]) -> list[str]:
    if not plan:
        return []
    normalized = [item.strip().lower() for item in keywords if item.strip()]
    if not normalized:
        return [first_outline_id(plan)] if first_outline_id(plan) else []
    matched: list[str] = []
    for item in plan.outline:
        haystack = " ".join([
            item.title,
            item.goal,
            " ".join(item.key_points),
            " ".join(item.suggested_examples),
            " ".join(item.suggested_visuals),
        ]).lower()
        if any(keyword in haystack for keyword in normalized):
            matched.append(item.id)
    return matched or ([first_outline_id(plan)] if first_outline_id(plan) else [])


def outline_coverage_summary(
    plan: TeachingPlan | None,
    handoffs: dict[str, DownstreamContext],
) -> dict[str, list[str]]:
    plan_ids = outline_ids_from_plan(plan)
    allowed = set(plan_ids)
    covered: list[str] = []
    for handoff in handoffs.values():
        for outline_id in handoff.covered_outline_ids:
            if outline_id in allowed and outline_id not in covered:
                covered.append(outline_id)
    return {
        "teaching_plan_outline_ids": plan_ids,
        "covered_source_outline_ids": covered,
        "missing_source_outline_ids": [outline_id for outline_id in plan_ids if outline_id not in covered],
    }


def clip_text(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def first_content_excerpt(content: str, limit: int = 180) -> str:
    for line in str(content or "").splitlines():
        stripped = line.strip().strip("#").strip("-").strip()
        if stripped:
            return clip_text(stripped, limit)
    return ""


def build_basic_handoff(
    *,
    source_agent: str,
    title: str,
    summary: str,
    teaching_plan: TeachingPlan | None,
    material_type: str,
    covered_outline_ids: list[str] | None = None,
    material_outline_id: str | None = None,
    key_points: list[str] | None = None,
    evidence: str = "",
    examples: list[str] | None = None,
    visual_ideas: list[str] | None = None,
    practice_refs: list[str] | None = None,
    code_refs: list[str] | None = None,
    cautions: list[str] | None = None,
) -> DownstreamContext:
    filtered_covered_ids = _valid_outline_ids(
        teaching_plan,
        covered_outline_ids or ([first_outline_id(teaching_plan)] if first_outline_id(teaching_plan) else []),
    )
    valid_material_ids = _valid_outline_ids(teaching_plan, [material_outline_id or ""])
    resolved_material_outline_id = (
        valid_material_ids[0]
        if valid_material_ids
        else (filtered_covered_ids[0] if filtered_covered_ids else "")
    )
    material = DownstreamMaterial(
        outline_id=resolved_material_outline_id,
        type=material_type,
        summary=clip_text(summary, 500),
        key_points=(key_points or [])[:8],
        evidence_excerpt=clip_text(evidence, 180),
        priority=1,
    )
    return DownstreamContext(
        source_agent=source_agent,
        title=clip_text(title, 120),
        one_sentence_summary=clip_text(summary, 180),
        covered_outline_ids=filtered_covered_ids,
        materials=[material] if material.summary else [],
        reusable_assets=ReusableAssets(
            examples=(examples or [])[:6],
            visual_ideas=(visual_ideas or [])[:6],
            practice_refs=(practice_refs or [])[:6],
            code_refs=(code_refs or [])[:6],
        ),
        cautions=(cautions or [])[:6],
    )
```

- [ ] **Step 4: Update content handoff**

In `server/app/resource/agents/content.py`, update imports:

```python
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    first_content_excerpt,
    outline_ids_from_plan,
)
```

Replace the `handoff = build_basic_handoff(...)` block in `generate_resource()` with:

```python
        outline_ids = outline_ids_from_plan(input_data.teaching_plan)
        first_outline = input_data.teaching_plan.outline[0] if input_data.teaching_plan and input_data.teaching_plan.outline else None
        handoff = build_basic_handoff(
            source_agent="content",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            material_type="explanation",
            covered_outline_ids=outline_ids,
            material_outline_id=outline_ids[0] if outline_ids else "",
            key_points=first_outline.key_points if first_outline else [],
            evidence=first_content_excerpt(result.content),
            examples=first_outline.suggested_examples if first_outline else [],
            visual_ideas=first_outline.suggested_visuals if first_outline else [],
        )
```

- [ ] **Step 5: Update mindmap handoff**

In `server/app/resource/agents/mindmap.py`, update imports:

```python
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    first_content_excerpt,
    outline_ids_from_plan,
)
```

Replace the `handoff = build_basic_handoff(...)` block in `generate_resource()` with:

```python
        outline_ids = outline_ids_from_plan(input_data.teaching_plan)
        handoff = build_basic_handoff(
            source_agent="mindmap",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            material_type="structure",
            covered_outline_ids=outline_ids,
            material_outline_id=outline_ids[0] if outline_ids else "",
            key_points=branches[:8],
            evidence=first_content_excerpt(result.content),
            visual_ideas=branches,
        )
```

- [ ] **Step 6: Update quiz handoff**

In `server/app/resource/agents/quiz.py`, update imports:

```python
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    first_content_excerpt,
    outline_ids_from_plan,
)
```

Replace the parsing block and handoff block in `generate_resource()` with:

```python
        try:
            quiz_data = json.loads(result.content)
            questions = quiz_data.get("questions", [])
            q_ids = [str(q.get("id")) for q in questions if q.get("id") is not None]
            knowledge_points = []
            for question in questions:
                if isinstance(question, dict):
                    for point in question.get("knowledge_points", []):
                        if isinstance(point, str) and point not in knowledge_points:
                            knowledge_points.append(point)
        except Exception:
            q_ids = []
            knowledge_points = []
        outline_ids = outline_ids_from_plan(input_data.teaching_plan)
        handoff = build_basic_handoff(
            source_agent="quiz",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            material_type="practice",
            covered_outline_ids=outline_ids,
            material_outline_id=outline_ids[0] if outline_ids else "",
            key_points=knowledge_points[:8],
            evidence=first_content_excerpt(result.content),
            practice_refs=q_ids,
        )
```

- [ ] **Step 7: Update code handoff**

In `server/app/resource/agents/code.py`, update imports:

```python
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    first_content_excerpt,
    select_outline_ids_by_keywords,
)
```

Replace the `handoff = build_basic_handoff(...)` block in `generate_resource()` with:

```python
        code_outline_ids = select_outline_ids_by_keywords(
            input_data.teaching_plan,
            [lang, case_type, "代码", "示例", "实践", "编程", "实现", "code"],
        )
        handoff = build_basic_handoff(
            source_agent="code",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            material_type="code",
            covered_outline_ids=code_outline_ids,
            material_outline_id=code_outline_ids[0] if code_outline_ids else "",
            key_points=[lang, case_type, difficulty],
            evidence=first_content_excerpt(result.content),
            code_refs=[lang, case_type],
        )
```

- [ ] **Step 8: Update reading handoff**

In `server/app/resource/agents/reading.py`, update imports:

```python
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    first_content_excerpt,
    outline_ids_from_plan,
)
```

Replace the `handoff = build_basic_handoff(...)` block in `generate_resource()` with:

```python
        try:
            reading_data = json.loads(result.content)
            resource_titles = [
                item.get("title")
                for item in reading_data.get("resources", [])
                if isinstance(item, dict) and item.get("title")
            ]
        except Exception:
            resource_titles = []
        outline_ids = outline_ids_from_plan(input_data.teaching_plan)
        handoff = build_basic_handoff(
            source_agent="reading",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            material_type="reading",
            covered_outline_ids=outline_ids,
            material_outline_id=outline_ids[0] if outline_ids else "",
            key_points=resource_titles[:8],
            evidence=first_content_excerpt(result.content),
            examples=resource_titles[:6],
        )
```

- [ ] **Step 9: Verify coverage tests and integration tests**

Run:

```bash
rtk uv run pytest tests/resource/test_handoff_coverage.py tests/resource/test_agent_integration.py -q
```

Expected: all selected tests pass.

- [ ] **Step 10: Commit Task 2**

```bash
rtk git add server/tests/resource/test_handoff_coverage.py server/app/resource/agents/common.py server/app/resource/agents/content.py server/app/resource/agents/mindmap.py server/app/resource/agents/quiz.py server/app/resource/agents/code.py server/app/resource/agents/reading.py
rtk git commit -m "fix: make resource handoff outline coverage explicit"
```

---

### Task 3: Add PPT And Video Coverage Metadata

**Files:**
- Modify: `server/app/resource/agents/video.py`
- Modify: `server/app/resource/agents/ppt.py`
- Modify: `server/tests/resource/test_video_agent.py`
- Modify: `server/tests/resource/test_ppt_internal_multi_agent.py`

- [ ] **Step 1: Add video metadata test**

In `server/tests/resource/test_video_agent.py`, add this test:

```python
@pytest.mark.asyncio
async def test_video_agent_metadata_reports_outline_coverage(monkeypatch):
    from app.resource.agents.video import VideoAgent
    from app.resource.schemas import DownstreamContext, ResourceInput, TeachingOutlineItem, TeachingPlan

    class FakeMaterialAgent:
        async def run(self, input_data, config):
            from app.resource.agents.video import VideoMaterialDigest

            return VideoMaterialDigest(
                topic="TCP",
                learning_goal="理解 TCP",
                facts=["三次握手"],
                source_map={"facts": ["content"]},
            )

    class FakeOutlineAgent:
        async def run(self, digest, constraints):
            from app.resource.agents.video import SceneContract, VideoOutline

            return VideoOutline(
                title="TCP 讲解",
                topic="TCP",
                duration_seconds=180,
                scenes=[
                    SceneContract(scene_id="scene-1", index=1, role="hook", title="引入", duration_seconds=60, learning_objective="理解问题", visual_type="card", content_hint="为什么需要连接", required_sources=["content"]),
                    SceneContract(scene_id="scene-2", index=2, role="concept", title="概念", duration_seconds=60, learning_objective="理解握手", visual_type="diagram", content_hint="SYN ACK", required_sources=["content"]),
                    SceneContract(scene_id="scene-3", index=3, role="recap", title="总结", duration_seconds=60, learning_objective="复盘", visual_type="card", content_hint="总结", required_sources=["content"]),
                ],
            )

    async def fake_write_scenes_concurrently(writer, outline, digest, constraints, *, concurrency=4):
        from app.resource.agents.video import SceneDraft

        return [
            SceneDraft(scene_id="scene-1", index=1, title="引入", narration="n1", visual_prompt="v1", source_agents=["content"]),
            SceneDraft(scene_id="scene-2", index=2, title="概念", narration="n2", visual_prompt="v2", source_agents=["content"]),
            SceneDraft(scene_id="scene-3", index=3, title="总结", narration="n3", visual_prompt="v3", source_agents=["content"]),
        ]

    import app.resource.agents.video as video_module

    monkeypatch.setattr(video_module, "VideoMaterialAgent", lambda: FakeMaterialAgent())
    monkeypatch.setattr(video_module, "VideoOutlineAgent", lambda: FakeOutlineAgent())
    monkeypatch.setattr(video_module, "write_scenes_concurrently", fake_write_scenes_concurrently)

    result = await VideoAgent().generate_resource(
        ResourceInput(
            learning_need="TCP",
            teaching_plan=TeachingPlan(
                topic="TCP",
                outline=[
                    TeachingOutlineItem(id="o1", title="连接建立"),
                    TeachingOutlineItem(id="o2", title="可靠传输"),
                ],
            ),
            upstream_handoffs={
                "content": DownstreamContext(source_agent="content", covered_outline_ids=["o1"]),
            },
            agent_config={"duration_seconds": 180, "scene_count": 3},
        )
    )

    assert result.success
    assert result.metadata["teaching_plan_outline_ids"] == ["o1", "o2"]
    assert result.metadata["covered_source_outline_ids"] == ["o1"]
    assert result.metadata["missing_source_outline_ids"] == ["o2"]
    assert result.metadata["source_handoff_agent_ids"] == ["content"]
```

- [ ] **Step 2: Update video implementation**

In `server/app/resource/agents/video.py`, add import near the other imports:

```python
from app.resource.agents.common import outline_coverage_summary
```

In `VideoAgent.generate_resource()`, replace metadata coverage construction with:

```python
        source_handoff_agent_ids = sorted(
            agent_id
            for agent_id in input_data.upstream_handoffs.keys()
            if agent_id in VIDEO_SOURCE_AGENT_IDS
        )
        coverage = outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs)
```

Then include these keys in `metadata`:

```python
                "source_handoff_agent_ids": source_handoff_agent_ids,
                "teaching_plan_outline_ids": coverage["teaching_plan_outline_ids"],
                "covered_source_outline_ids": coverage["covered_source_outline_ids"],
                "missing_source_outline_ids": coverage["missing_source_outline_ids"],
```

- [ ] **Step 3: Add PPT metadata test**

In `server/tests/resource/test_ppt_internal_multi_agent.py`, add this test:

```python
def test_ppt_result_metadata_reports_outline_coverage():
    from app.resource.agents.ppt import PptAgent
    from app.resource.schemas import DownstreamContext, ResourceInput, TeachingOutlineItem, TeachingPlan

    input_data = ResourceInput(
        learning_need="TCP",
        teaching_plan=TeachingPlan(
            topic="TCP",
            outline=[
                TeachingOutlineItem(id="o1", title="连接建立"),
                TeachingOutlineItem(id="o2", title="可靠传输"),
            ],
        ),
        upstream_handoffs={
            "content": DownstreamContext(source_agent="content", covered_outline_ids=["o1"]),
        },
        agent_config={
            "material_bundle": {
                "learning_need": "TCP",
                "learning_scenario": "self_study",
                "profile": {},
                "teaching_plan": {
                    "topic": "TCP",
                    "outline": [
                        {"id": "o1", "title": "连接建立"},
                        {"id": "o2", "title": "可靠传输"},
                    ],
                },
                "upstream_handoffs": {
                    "content": {
                        "schema_version": "resource_handoff/v1",
                        "source_agent": "content",
                        "covered_outline_ids": ["o1"],
                    },
                },
                "artifacts": {},
                "source_type": "resource",
                "node_context": None,
            },
            "page_count": 3,
        },
    )

    coverage = PptAgent._coverage_metadata(input_data)

    assert coverage["teaching_plan_outline_ids"] == ["o1", "o2"]
    assert coverage["covered_source_outline_ids"] == ["o1"]
    assert coverage["missing_source_outline_ids"] == ["o2"]
```

- [ ] **Step 4: Update PPT implementation**

In `server/app/resource/agents/ppt.py`, add imports:

```python
from app.resource.agents.common import outline_coverage_summary
from app.resource.schemas import DownstreamContext
```

Inside `class PptAgent`, add this method:

```python
    @staticmethod
    def _coverage_metadata(input_data: ResourceInput) -> dict[str, list[str]]:
        return outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs)
```

In `PptAgent.generate_resource()`, before returning the successful `AgentResult`, compute:

```python
        coverage = self._coverage_metadata(input_data)
```

Add these metadata keys to the successful `AgentResult`:

```python
                "teaching_plan_outline_ids": coverage["teaching_plan_outline_ids"],
                "covered_source_outline_ids": coverage["covered_source_outline_ids"],
                "missing_source_outline_ids": coverage["missing_source_outline_ids"],
```

- [ ] **Step 5: Verify PPT and Video tests**

Run:

```bash
rtk uv run pytest tests/resource/test_video_agent.py tests/resource/test_ppt_internal_multi_agent.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit Task 3**

```bash
rtk git add server/app/resource/agents/video.py server/app/resource/agents/ppt.py server/tests/resource/test_video_agent.py server/tests/resource/test_ppt_internal_multi_agent.py
rtk git commit -m "fix: expose outline coverage metadata for ppt and video"
```

---

### Task 4: Make Review Envelopes Use Handoffs For Base Resources

**Files:**
- Create: `server/tests/resource/test_review_handoff_envelope.py`
- Modify: `server/app/resource/review.py`

- [ ] **Step 1: Write failing review envelope tests**

Create `server/tests/resource/test_review_handoff_envelope.py`:

```python
from app.resource.review import build_ppt_audit_envelope, build_pre_audit_envelope, build_video_audit_envelope
from app.resource.schemas import AgentResult, AgentSelection, DownstreamContext, ResourceGenerationRequest, ResourceAgentId, TeachingPlan


def _request() -> ResourceGenerationRequest:
    return ResourceGenerationRequest(
        learning_need="TCP",
        selected_agents=[
            AgentSelection(agent_id=ResourceAgentId.CONTENT, enabled=True, priority=0),
            AgentSelection(agent_id=ResourceAgentId.READING, enabled=True, priority=1),
            AgentSelection(agent_id=ResourceAgentId.PPT, enabled=True, priority=2),
            AgentSelection(agent_id=ResourceAgentId.VIDEO, enabled=True, priority=3),
        ],
    )


def _base_results() -> dict[str, AgentResult]:
    return {
        "content": AgentResult(
            success=True,
            content="VERY_LONG_CONTENT_SHOULD_NOT_BE_INCLUDED",
            title="内容",
            summary="内容摘要",
            downstream_context=DownstreamContext(source_agent="content", covered_outline_ids=["o1"]),
            metadata={"agent_id": "content"},
        ),
        "reading": AgentResult(
            success=True,
            content="VERY_LONG_READING_SHOULD_NOT_BE_INCLUDED",
            title="阅读",
            summary="阅读摘要",
            downstream_context=DownstreamContext(source_agent="reading", covered_outline_ids=["o1"]),
            metadata={"agent_id": "reading"},
        ),
        "ppt": AgentResult(success=True, content='{"slides":[]}', title="PPT", summary="PPT", metadata={"agent_id": "ppt"}),
        "video": AgentResult(success=True, content='{"scenes":[]}', title="视频", summary="视频", metadata={"agent_id": "video"}),
    }


def test_pre_audit_envelope_does_not_include_base_resource_content():
    envelope, missing = build_pre_audit_envelope(
        request=_request(),
        results=_base_results(),
        profile={},
        teaching_plan=TeachingPlan(topic="TCP"),
    )

    serialized = str(envelope)
    assert missing == []
    assert "VERY_LONG_CONTENT_SHOULD_NOT_BE_INCLUDED" not in serialized
    assert "VERY_LONG_READING_SHOULD_NOT_BE_INCLUDED" not in serialized
    assert envelope["upstream_handoffs"]["content"]["source_agent"] == "content"
    assert envelope["deep_audit_resources"] == []


def test_ppt_and_video_audit_keep_final_product_but_not_base_content():
    ppt_envelope, ppt_missing = build_ppt_audit_envelope(
        request=_request(),
        results=_base_results(),
        profile={},
        teaching_plan=TeachingPlan(topic="TCP"),
    )
    video_envelope, video_missing = build_video_audit_envelope(
        request=_request(),
        results=_base_results(),
        profile={},
        teaching_plan=TeachingPlan(topic="TCP"),
    )

    assert ppt_missing == []
    assert video_missing == []
    assert ppt_envelope["ppt_resource"]["audit_content"] == '{"slides":[]}'
    assert video_envelope["video_resource"]["audit_content"] == '{"scenes":[]}'
    assert "VERY_LONG_CONTENT_SHOULD_NOT_BE_INCLUDED" not in str(ppt_envelope)
    assert "VERY_LONG_READING_SHOULD_NOT_BE_INCLUDED" not in str(video_envelope)
    assert ppt_envelope["approved_sources"] == []
    assert video_envelope["approved_sources"] == []
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
rtk uv run pytest tests/resource/test_review_handoff_envelope.py -q
```

Expected: tests fail because base `audit_content` or `source_content` is still included.

- [ ] **Step 3: Update `build_pre_audit_envelope()`**

In `server/app/resource/review.py`, replace `deep_audit_resources = [...]` with:

```python
    deep_audit_resources: list[dict[str, Any]] = []
```

Keep `upstream_handoffs` exactly as the source context for base resources.

- [ ] **Step 4: Update PPT and Video audit sources**

In `build_ppt_audit_envelope()`, replace `approved_sources = [...]` with:

```python
    approved_sources: list[dict[str, Any]] = []
```

In `build_video_audit_envelope()`, replace `approved_sources = [...]` with:

```python
    approved_sources: list[dict[str, Any]] = []
```

Do not remove `ppt_resource` or `video_resource`; those are final aggregate products under review.

- [ ] **Step 5: Verify review tests and resource tests**

Run:

```bash
rtk uv run pytest tests/resource/test_review_handoff_envelope.py tests/resource -q
```

Expected: the new review tests pass. If `tests/resource/test_database_session_resilience.py::test_init_db_repairs_generated_resource_source_column` still fails, leave it for Task 7.

- [ ] **Step 6: Commit Task 4**

```bash
rtk git add server/tests/resource/test_review_handoff_envelope.py server/app/resource/review.py
rtk git commit -m "fix: keep review base context bounded to handoffs"
```

---

### Task 5: Remove Old Tutor Adapter Compatibility And Update Workflow Labels

**Files:**
- Modify: `server/app/resource/agents/video.py`
- Modify: `server/app/resource/service.py`
- Modify: `server/tests/resource/test_video_agent.py`

- [ ] **Step 1: Add tutor adapter test**

In `server/tests/resource/test_video_agent.py`, add:

```python
@pytest.mark.asyncio
async def test_video_tutor_adapter_rejects_previous_results(monkeypatch):
    from app.resource.agents.video import VideoAgent

    async def fail_if_called(_input_data):
        raise AssertionError("generate_resource should not be called for old previous_results input")

    agent = VideoAgent()
    monkeypatch.setattr(agent, "generate_resource", fail_if_called)

    result = await agent.generate_from_tutor_context(
        {
            "learning_need": "TCP",
            "previous_results": {"content": {"source_agent": "content"}},
        }
    )

    assert not result.success
    assert "upstream_handoffs" in result.error
    assert result.metadata["reserved_for_tutor"] is True
```

- [ ] **Step 2: Update tutor adapter**

In `server/app/resource/agents/video.py`, replace:

```python
        raw_handoffs = tutor_context.get("upstream_handoffs") or tutor_context.get("previous_results") or {}
```

with:

```python
        if "previous_results" in tutor_context:
            return AgentResult(
                success=False,
                error="tutor_context 只接受 upstream_handoffs，不接受 previous_results",
                metadata={"agent_id": "video", "reserved_for_tutor": True},
            )
        raw_handoffs = tutor_context.get("upstream_handoffs") or {}
```

- [ ] **Step 3: Update service workflow docstring and phase**

In `server/app/resource/service.py`, replace lines in the workflow docstring that mention old planning output with:

```python
    [ 阶段 1 ] : PlanningAgent (规划智能体) — 串行，必须先完成
                 ↓
                 生成全局 TeachingPlan：教学方向、概要、大纲和边界
                 ↓
    [ 阶段 2 ] : 并行调度基础 Worker Agents (Content, Quiz, Code, Mindmap, Reading)
                 每个 Worker 使用 TeachingPlan 生成完整资源，并输出 DownstreamContext
                 ↓
    [ 阶段 3 ] : 前置审核、PPT、Video 聚合生成并行执行
                 PPT/Video 只读取 TeachingPlan 和基础资源 handoff
```

Replace the planning tracker phase string:

```python
                phase="planning_blueprint",
```

with:

```python
                phase="planning_teaching_plan",
```

- [ ] **Step 4: Verify no old runtime references remain in resource app**

Run:

```bash
rtk rg -n "previous_results|LearningBlueprint|AgentInstruction|ExecutionPlan|summary_data|instruction_map|resource_guidance" server/app/resource
```

Expected: no output.

- [ ] **Step 5: Verify tests**

Run:

```bash
rtk uv run pytest tests/resource/test_video_agent.py tests/resource/test_video_service_orchestration.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit Task 5**

```bash
rtk git add server/app/resource/agents/video.py server/app/resource/service.py server/tests/resource/test_video_agent.py
rtk git commit -m "fix: remove old video tutor adapter contract"
```

---

### Task 6: Complete Frontend Video Resource Types

**Files:**
- Modify: `src/features/resource/model/resource.ts`
- Modify: `src/features/resource/model/ResourceGeneratorConstants.ts`

- [ ] **Step 1: Update `ResourceAgentId` and DTO types**

In `src/features/resource/model/resource.ts`, replace:

```ts
export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt'
```

with:

```ts
export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'video'
```

Add these types after `ResourceAgentSnapshot`:

```ts
export interface DownstreamMaterial {
  outline_id: string
  type: 'explanation' | 'structure' | 'practice' | 'code' | 'reading' | 'example' | 'visual'
  summary: string
  key_points: string[]
  evidence_excerpt: string
  priority: number
}

export interface DownstreamContext {
  schema_version: 'resource_handoff/v1'
  source_agent: string
  title: string
  one_sentence_summary: string
  covered_outline_ids: string[]
  materials: DownstreamMaterial[]
  reusable_assets: {
    examples: string[]
    misconceptions: string[]
    visual_ideas: string[]
    practice_refs: string[]
    code_refs: string[]
  }
  cautions: string[]
}

export interface GeneratedResourceItem {
  id: string
  type: ResourceAgentId
  title: string
  format: string
  content: any
  summary: string
  metrics: Record<string, any>
  downstream_context?: DownstreamContext | null
  execution_report?: string | null
  metadata: Record<string, any>
  status: string
  error_message?: string | null
  created_at?: string | null
  updated_at?: string | null
}
```

Change `ResourceTaskStatus.resources?: any[]` to:

```ts
  resources?: GeneratedResourceItem[]
```

- [ ] **Step 2: Add video config to request type**

Inside `ResourceGenerationRequest.agent_configs`, after `ppt`, add:

```ts
    video: {
      duration_seconds: number
      scene_count: number
      style: 'explainer' | 'lecture' | 'screencast' | 'case_walkthrough'
      voice: 'teacher' | 'coach' | 'concise'
      aspect_ratio: '16:9' | '9:16' | '1:1'
      include_captions: boolean
      output_format: 'preview'
    }
```

Also add `output_format: 'preview'` to the existing `ppt` type:

```ts
    ppt: {
      page_count: number
      difficulty: 'beginner' | 'intermediate' | 'advanced'
      output_format: 'preview'
    }
```

- [ ] **Step 3: Check generator constants**

Open `src/features/resource/model/ResourceGeneratorConstants.ts` and verify the exported agent/config structures include video. If video is absent, add:

```ts
  {
    id: 'video',
    name: '讲解视频',
    description: '结构化讲解视频脚本与分镜',
    icon: 'Video',
    defaultEnabled: false
  }
```

Add default video config to the same default config object used by the generator:

```ts
  video: {
    duration_seconds: 180,
    scene_count: 6,
    style: 'explainer',
    voice: 'teacher',
    aspect_ratio: '16:9',
    include_captions: true,
    output_format: 'preview'
  }
```

If the file already has video constants, adjust them to match these literal values exactly.

- [ ] **Step 4: Verify frontend resource type audit**

Run:

```bash
rtk rg -n "summary_data|execution_plan|previous_results|LearningBlueprint|ExecutionPlan" src/features/resource
```

Expected: no output.

Run:

```bash
rtk npm run build
```

Expected: no new `src/features/resource` type errors. The current repository may still report pre-existing errors in `src/features/auth/components/OnboardingDialog.vue` and `src/features/dashboard/views/Home.vue`; do not fix those files in this task.

- [ ] **Step 5: Commit Task 6**

```bash
rtk git add src/features/resource/model/resource.ts src/features/resource/model/ResourceGeneratorConstants.ts
rtk git commit -m "fix: complete frontend video resource contract"
```

---

### Task 7: Migrate Or Remove Old Contract Tests

**Files:**
- Modify: `server/tests/infra/test_schema_validation_all.py`
- Modify: `server/tests/test_all_agents.py`
- Modify: `server/tests/test_astron_code.py`
- Modify: `server/tests/resource/test_database_session_resilience.py`

- [ ] **Step 1: Update schema validation imports and fixture**

In `server/tests/infra/test_schema_validation_all.py`, replace:

```python
from app.resource.schemas import ExecutionPlan
```

with:

```python
from app.resource.schemas import TeachingPlan
```

Replace the old execution plan fixture with:

```python
TEACHING_PLAN_JSON = {
    "topic": "Python 爬虫入门",
    "learning_goal": "能够解释 HTTP 请求并写出基础爬虫",
    "audience": "具备 Python 基础的学习者",
    "difficulty": "beginner",
    "teaching_strategy": "概念引入 -> 请求流程 -> 代码示例 -> 误区辨析",
    "summary": "围绕 HTTP、HTML 解析和反爬边界建立爬虫入门知识框架",
    "outline": [
        {
            "id": "o1",
            "title": "HTTP 请求基础",
            "goal": "理解请求与响应",
            "key_points": ["GET", "status code"],
            "common_misconceptions": ["把 HTML 和 API 响应混为一谈"],
            "suggested_examples": ["请求一个公开页面"],
            "suggested_visuals": ["请求响应流程图"],
            "must_not_miss": True,
        }
    ],
    "boundaries": ["不讲绕过登录、验证码或付费墙"],
}
```

Replace `TestExecutionPlanSchema` with:

```python
class TestTeachingPlanSchema:
    def test_valid_teaching_plan(self):
        result = TeachingPlan.model_validate(TEACHING_PLAN_JSON)
        assert result.topic == "Python 爬虫入门"
        assert result.outline[0].id == "o1"

    def test_invalid_outline_id(self):
        data = {
            **TEACHING_PLAN_JSON,
            "outline": [{**TEACHING_PLAN_JSON["outline"][0], "id": "section-1"}],
        }
        with pytest.raises(Exception):
            TeachingPlan.model_validate(data)
```

Update any parameterized schema list that includes `ExecutionPlan` to include `(TeachingPlan, TEACHING_PLAN_JSON)` instead.

- [ ] **Step 2: Update `test_astron_code.py` schema output test**

In `server/tests/test_astron_code.py`, replace the test that imports `ExecutionPlan` with:

```python
@pytest.mark.asyncio
async def test_multi_agent_planning_outputs_teaching_plan():
    """测试多智能体系统资源生成的规划输出 (TeachingPlan)。"""
    from app.infra.llm import get_llm
    from app.resource.schemas import TeachingPlan

    llm = get_llm()
    prompt = """
    请为“Python 异步编程”生成一个 TeachingPlan JSON。
    必须包含 topic、learning_goal、summary、outline。
    outline 的 id 必须从 o1 开始。
    """

    plan = await llm.ainvoke_json(TeachingPlan, prompt)

    assert plan.topic != ""
    assert len(plan.outline) > 0
    assert plan.outline[0].id == "o1"
```

- [ ] **Step 3: Update `test_all_agents.py` old imports and metrics usage**

In `server/tests/test_all_agents.py`, replace the old schema imports with:

```python
from app.resource.schemas import AgentResult, DownstreamContext, ResourceInput, TeachingPlan
```

Replace code that reads `plan_result.summary_data.get("execution_plan", {})` with:

```python
    teaching_plan_data = plan_result.metadata.get("teaching_plan", {})
    if isinstance(teaching_plan_data, dict):
        teaching_plan = TeachingPlan.model_validate(teaching_plan_data)
    else:
        teaching_plan = TeachingPlan(topic="Python 异步编程")
```

Replace assignments to `downstream_state.blueprint` and `downstream_state.instruction` with:

```python
    downstream_state.teaching_plan = teaching_plan
    downstream_state.upstream_handoffs = {}
```

Replace `review_res.summary_data.get("overall_score", "N/A")` with:

```python
review_res.metrics.get("overall_score", "N/A")
```

- [ ] **Step 4: Replace legacy DB repair test**

In `server/tests/resource/test_database_session_resilience.py`, replace function `test_init_db_repairs_generated_resource_source_column` with:

```python
def test_resource_schema_no_longer_uses_generated_resource_personalization():
    from pathlib import Path

    schema_sql = (Path(__file__).resolve().parents[2] / "init_schema.sql").read_text(encoding="utf-8")
    generated_resources_sql = schema_sql.split("CREATE TABLE IF NOT EXISTS generated_resources", 1)[1].split(");", 1)[0]

    assert "teaching_plan" in generated_resources_sql
    assert "review_result" in generated_resources_sql
    assert "failed_agents" in generated_resources_sql
    assert "workflow_metadata" in generated_resources_sql
    assert "personalization" not in generated_resources_sql
```

- [ ] **Step 5: Run migrated tests**

Run:

```bash
rtk uv run pytest tests/infra/test_schema_validation_all.py tests/test_all_agents.py tests/test_astron_code.py tests/resource/test_database_session_resilience.py -q
```

Expected: collection succeeds. Tests that call live models may be skipped by existing marks or require configured keys; collection must not fail from removed resource schemas.

- [ ] **Step 6: Commit Task 7**

```bash
rtk git add server/tests/infra/test_schema_validation_all.py server/tests/test_all_agents.py server/tests/test_astron_code.py server/tests/resource/test_database_session_resilience.py
rtk git commit -m "test: migrate old resource contract tests to teaching plan"
```

---

### Task 8: Final Contract Audit And Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run old contract audit for runtime code**

Run:

```bash
rtk rg -n "LearningBlueprint|AgentInstruction|ExecutionPlan|summary_data|previous_results|instruction_map|resource_guidance" server/app src/features/resource
```

Expected: no output.

- [ ] **Step 2: Run prompt old contract audit**

Run:

```bash
rtk rg -n "blueprint|instruction|previous_results|LearningBlueprint|AgentInstruction|ExecutionPlan" server/app/resource/prompts
```

Expected: no output.

- [ ] **Step 3: Run resource tests**

Run from `/Users/apple/Code/software/server`:

```bash
rtk uv run pytest tests/resource -q
```

Expected: all resource tests pass.

- [ ] **Step 4: Run schema and agent contract tests**

Run from `/Users/apple/Code/software/server`:

```bash
rtk uv run pytest tests/infra/test_schema_validation_all.py tests/resource/test_prompt_contracts.py tests/resource/test_handoff_coverage.py tests/resource/test_review_handoff_envelope.py tests/resource/test_video_agent.py tests/resource/test_ppt_internal_multi_agent.py tests/resource/test_video_service_orchestration.py tests/resource/test_agent_integration.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Run frontend build**

Run from `/Users/apple/Code/software`:

```bash
rtk npm run build
```

Expected: if the build fails only in `src/features/auth/components/OnboardingDialog.vue` and `src/features/dashboard/views/Home.vue`, record those as pre-existing unrelated errors. If any error mentions `src/features/resource`, fix the resource type or usage in this task before committing.

- [ ] **Step 6: Commit final audit fixes**

If Task 8 required edits, commit them:

```bash
rtk git add server/app src/features/resource server/tests
rtk git commit -m "chore: finish resource handoff contract audit"
```

If Task 8 made no edits, do not create an empty commit.

---

## Acceptance Criteria

- `PlanningAgent` 只输出 `TeachingPlan`，不输出 agent 分工。
- 基础资源 agent 都输出 `downstream_context`，并且 `covered_outline_ids` 不再由 helper 默认声明全部大纲。
- PPT 和 Video 只消费 `teaching_plan + upstream_handoffs`，不读取基础资源完整正文。
- PPT 和 Video metadata 都包含：
  - `source_handoff_agent_ids`
  - `teaching_plan_outline_ids`
  - `covered_source_outline_ids`
  - `missing_source_outline_ids`
- Review envelope 不再包含 content/reading 基础资源全文。
- Video tutor 预留接口只接受 `upstream_handoffs`，拒绝 `previous_results`。
- 前端 resource 类型支持 `video` agent 和 video config。
- `server/app/resource/prompts` 中没有旧契约字段。
- `server/app` 和 `src/features/resource` 中没有旧 standalone resource 契约读取。
- `tests/resource -q` 通过，旧 schema collection 不再因删除的 `ExecutionPlan/LearningBlueprint` 失败。

## Notes For Claude Code

- 这次不要恢复旧 Pydantic 模型来让测试过；测试必须迁移到新契约。
- 这次不要新增兼容旧请求字段的 adapter。
- 这次不要把 review 的基础资源全文重新放进 envelope；上下文控制靠 handoff。
- 如果 `rtk npm run build` 因 auth/dashboard 既有类型错误失败，只记录；只修 `src/features/resource` 相关错误。
