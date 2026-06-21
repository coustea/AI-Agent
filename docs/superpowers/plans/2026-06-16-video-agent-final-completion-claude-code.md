# Video Agent Final Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完整收口 standalone `videoAgent`：后端多智能体资源生成稳定、Video JSON 契约可预览、前端可选择/配置/展示 video、数据库模型无漂移，并保留但不接入智能辅导入口。

**Architecture:** `video` 与 `ppt` 同属 standalone resource 聚合型 agent，消费 `content/mindmap/quiz/code/reading` 等上游基础资源，不进入 path 域。`server/app/resource/agents/video.py` 保持单文件实现，内部用素材提取、结构规划、分镜写作、payload 构建四个子 agent/函数并行生成 `video/v1` JSON。前端只预览结构化脚本和分镜，不要求后端产出图片 URL 或真实 MP4。

**Tech Stack:** FastAPI + SQLModel + PostgreSQL JSONB；Pydantic v2；Vue 3 + TypeScript；Element Plus；pytest；`npm run build`。

---

## Execution Rules For Claude Code

- 所有 shell 命令都从仓库 `/Users/apple/Code/software` 或 `server/` 执行，并使用 `rtk` 前缀。
- 不要拆分 `server/app/resource/agents/video.py`，子 agent/函数都留在这个文件中。
- 不要把 video 接入 path 节点资源生成；`generate_node()` 继续返回“暂未接入”。
- 不要新增 video 专表；继续复用 `generated_resources` / `generated_resource_items`。
- 不要接入智能辅导路由；只保留 `generate_from_tutor_context()` adapter。
- 每个任务完成后运行该任务列出的测试，再进入下一个任务。

---

## File Map

- Modify: `server/app/resource/agents/video.py`  
  增加上游资源白名单、outline 修复、分镜局部容错、payload builder fallback、tutor adapter 输入容错。
- Modify: `server/tests/resource/test_video_agent.py`  
  覆盖 video payload 契约、上游过滤、outline 修复、场景局部失败 fallback、tutor adapter 容错。
- Modify: `server/app/resource/service.py`  
  确认 video 聚合 agent 不作为基础 worker；后端进度已基本有实现，只补必要注释或测试修正。
- Modify: `server/tests/resource/test_video_service_orchestration.py`  
  确认 video 聚合编排、review 读取、进度模型。
- Modify: `server/app/infra/models.py`  
  删除 `GeneratedResourceItem` 重复字段定义。
- Modify: `server/tests/resource/test_resource_contract.py`  
  增加 source-level smoke test，防止同一 SQLModel class 再出现重复字段定义。
- Modify: `src/features/resource/model/resource.ts`  
  加入 `video` agent 类型和 video config 类型。
- Modify: `src/features/resource/model/ResourceGeneratorConstants.ts`  
  加入 video/video_review 常量、元信息、默认配置、label、format、time、tone、输出描述。
- Modify: `src/features/resource/views/ResourceGenerator.vue`  
  让生成页可调度 video，DAG 与进度模型把 video 当聚合阶段处理，请求带上 `agent_configs.video`。
- Modify: `src/features/resource/views/ResourcePersonalize.vue`  
  增加 video 的配置面板。
- Modify: `src/features/resource/components/VideoView.vue`  
  强化 `video/v1` payload 归一化，去掉不稳定的 MP4 导出承诺，改为稳定导出 JSON 脚本。
- Verify: `server/app/resource/prompts/video_material.md`
- Verify: `server/app/resource/prompts/video_outline.md`
- Verify: `server/app/resource/prompts/video_scene.md`  
  确认 prompt 字段与 Pydantic 模型一致。

---

## Task 1: 后端 videoAgent 上游输入过滤与容错修复

**Files:**
- Modify: `server/app/resource/agents/video.py`
- Modify: `server/tests/resource/test_video_agent.py`

- [ ] **Step 1: Add failing tests for source filtering, scene fallback, payload fallback, and tutor adapter tolerance**

Append these tests to `server/tests/resource/test_video_agent.py`:

```python
@pytest.mark.asyncio
async def test_write_scenes_concurrently_falls_back_when_one_scene_fails():
    from app.resource.agents.video import (
        SceneContract,
        SceneDraft,
        VideoConstraints,
        VideoMaterialDigest,
        VideoOutline,
        write_scenes_concurrently,
    )

    class FakeWriter:
        async def run(self, contract, digest, constraints):
            if contract.scene_id == "scene-2":
                raise RuntimeError("scene failed")
            return SceneDraft(
                scene_id=contract.scene_id,
                index=contract.index,
                title=contract.title,
                narration=f"{contract.title} 正常旁白",
                captions=[contract.title],
                on_screen_text=[contract.learning_objective],
                visual_prompt=contract.content_hint,
                visual_type=contract.visual_type,
                source_agents=contract.required_sources,
            )

    constraints = VideoConstraints(duration_seconds=180, scene_count=3)
    digest = VideoMaterialDigest(topic="TCP", learning_goal="理解握手")
    outline = VideoOutline(
        title="TCP 讲解",
        topic="TCP",
        duration_seconds=180,
        scenes=[
            SceneContract(scene_id="scene-1", index=1, role="hook", title="开场", duration_seconds=60, learning_objective="引入", content_hint="问题", required_sources=["content"]),
            SceneContract(scene_id="scene-2", index=2, role="concept", title="概念", duration_seconds=60, learning_objective="解释", content_hint="流程", required_sources=["content"]),
            SceneContract(scene_id="scene-3", index=3, role="recap", title="总结", duration_seconds=60, learning_objective="复盘", content_hint="总结", required_sources=["content"]),
        ],
    )

    drafts = await write_scenes_concurrently(FakeWriter(), outline, digest, constraints)

    assert [draft.scene_id for draft in drafts] == ["scene-1", "scene-2", "scene-3"]
    assert "暂用场景契约生成" in drafts[1].narration
    assert drafts[1].visual_prompt == "流程"
```

```python
def test_video_payload_builder_falls_back_for_missing_draft():
    from app.resource.agents.video import (
        SceneContract,
        SceneDraft,
        VideoConstraints,
        VideoMaterialDigest,
        VideoOutline,
        VideoPayloadBuilder,
    )

    constraints = VideoConstraints(duration_seconds=180, scene_count=3)
    digest = VideoMaterialDigest(topic="TCP", learning_goal="理解握手")
    outline = VideoOutline(
        title="TCP 讲解",
        topic="TCP",
        duration_seconds=180,
        scenes=[
            SceneContract(scene_id="scene-1", index=1, role="hook", title="开场", duration_seconds=60, learning_objective="引入", content_hint="问题", required_sources=["content"]),
            SceneContract(scene_id="scene-2", index=2, role="concept", title="概念", duration_seconds=60, learning_objective="解释", content_hint="流程", required_sources=["content"]),
            SceneContract(scene_id="scene-3", index=3, role="recap", title="总结", duration_seconds=60, learning_objective="复盘", content_hint="总结", required_sources=["content"]),
        ],
    )
    drafts = [
        SceneDraft(scene_id="scene-1", index=1, title="开场", narration="开场旁白", visual_prompt="问题", source_agents=["content"]),
        SceneDraft(scene_id="scene-3", index=3, title="总结", narration="总结旁白", visual_prompt="总结", source_agents=["content"]),
    ]

    payload = VideoPayloadBuilder().build(outline, drafts, constraints, digest)

    assert len(payload.scenes) == 3
    assert payload.scenes[1].scene_id == "scene-2"
    assert "暂用场景契约生成" in payload.scenes[1].narration
    assert payload.metadata["repair_warnings"]
```

```python
def test_input_context_filters_previous_results_to_base_resource_agents():
    from app.resource.agents.video import _input_context

    input_data = ResourceInput(
        resource_id=1,
        learning_need="生成 TCP 视频",
        agent_name="video",
        previous_results={
            "content": AgentResult(success=True, content="content", metadata={"agent_id": "content"}),
            "mindmap": AgentResult(success=True, content="mindmap", metadata={"agent_id": "mindmap"}),
            "ppt": AgentResult(success=True, content="ppt", metadata={"agent_id": "ppt"}),
            "review": AgentResult(success=True, content="review", metadata={"agent_id": "review"}),
            "video": AgentResult(success=True, content="video", metadata={"agent_id": "video"}),
            "reading": AgentResult(success=False, content="reading", metadata={"agent_id": "reading"}),
        },
    )

    context = _input_context(input_data, {})

    assert set(context["previous_results"].keys()) == {"content", "mindmap"}
```

```python
@pytest.mark.asyncio
async def test_tutor_adapter_skips_invalid_previous_results(monkeypatch):
    from app.resource.agents.video import VideoAgent

    captured = {}

    async def fake_generate_resource(self, input_data):
        captured["previous_results"] = input_data.previous_results
        return AgentResult(success=True, content="{}", file_type="json", metadata={"agent_id": "video"})

    monkeypatch.setattr(VideoAgent, "generate_resource", fake_generate_resource)

    result = await VideoAgent().generate_from_tutor_context(
        {
            "topic": "TCP",
            "previous_results": {
                "content": {"success": True, "content": "ok", "metadata": {"agent_id": "content"}},
                "broken": {"success": True, "content": 123, "metadata": {"agent_id": "broken"}, "extra": object()},
                "raw": "not a dict",
            },
        }
    )

    assert result.success is True
    assert set(captured["previous_results"].keys()) == {"content"}
```

- [ ] **Step 2: Run the failing tests**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_video_agent.py::test_write_scenes_concurrently_falls_back_when_one_scene_fails tests/resource/test_video_agent.py::test_video_payload_builder_falls_back_for_missing_draft tests/resource/test_video_agent.py::test_input_context_filters_previous_results_to_base_resource_agents tests/resource/test_video_agent.py::test_tutor_adapter_skips_invalid_previous_results -q
```

Expected before implementation: at least one failure from `asyncio.gather()` bubbling scene failure, unfiltered `previous_results`, or strict tutor adapter validation.

- [ ] **Step 3: Implement source filtering and fallback helpers in `video.py`**

Add this near the type aliases in `server/app/resource/agents/video.py`:

```python
VIDEO_SOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}
```

Replace `_input_context()` with:

```python
def _input_context(input_data: ResourceInput, config: dict[str, Any]) -> dict[str, Any]:
    previous_results = {
        agent_id: _result_excerpt(result)
        for agent_id, result in input_data.previous_results.items()
        if agent_id in VIDEO_SOURCE_AGENT_IDS and result.success
    }
    return {
        "learning_need": input_data.learning_need,
        "learning_scenario": input_data.learning_scenario,
        "profile": input_data.profile,
        "blueprint": input_data.blueprint.model_dump(mode="json") if input_data.blueprint else {},
        "instruction": input_data.instruction.model_dump(mode="json") if input_data.instruction else {},
        "previous_results": previous_results,
        "config": config,
    }
```

Add these helpers below `_duration_plan()`:

```python
def _fallback_scene_draft(contract: SceneContract, reason: str = "") -> SceneDraft:
    suffix = f"。原因：{reason}" if reason else ""
    return SceneDraft(
        scene_id=contract.scene_id,
        index=contract.index,
        title=contract.title,
        narration=f"{contract.title} 暂用场景契约生成旁白，请根据画面提示讲解：{contract.content_hint}{suffix}",
        captions=[contract.title],
        on_screen_text=[contract.learning_objective],
        visual_prompt=contract.content_hint,
        visual_type=contract.visual_type,
        interaction_prompt="",
        source_agents=contract.required_sources,
    )
```

- [ ] **Step 4: Make scene generation locally resilient**

Replace `write_scenes_concurrently()` with:

```python
async def write_scenes_concurrently(
    writer: SceneWriterAgent,
    outline: VideoOutline,
    digest: VideoMaterialDigest,
    constraints: VideoConstraints,
    *,
    concurrency: int = 4,
) -> list[SceneDraft]:
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(contract: SceneContract) -> SceneDraft:
        async with semaphore:
            try:
                return await writer.run(contract, digest, constraints)
            except Exception as exc:
                logger.warning("Video scene fallback: scene_id=%s error=%s", contract.scene_id, exc)
                return _fallback_scene_draft(contract, str(exc))

    drafts = await asyncio.gather(*(run_one(scene) for scene in outline.scenes))
    return sorted(drafts, key=lambda item: item.index)
```

- [ ] **Step 5: Make payload builder resilient to missing or mismatched drafts**

Inside `VideoPayloadBuilder.build()`, replace the `draft_by_id` and scene loop with this pattern:

```python
draft_by_id = {draft.scene_id: draft for draft in drafts}
repair_warnings: list[str] = []
scenes: list[VideoScene] = []
cursor_ms = 0
for contract in outline.scenes:
    draft = draft_by_id.get(contract.scene_id)
    if draft is None:
        repair_warnings.append(f"missing_draft:{contract.scene_id}")
        draft = _fallback_scene_draft(contract, "missing draft")
    elif draft.index != contract.index:
        repair_warnings.append(f"index_mismatch:{contract.scene_id}")

    duration_ms = contract.duration_seconds * 1000
    scenes.append(
        VideoScene(
            scene_id=contract.scene_id,
            index=contract.index,
            role=contract.role,
            title=draft.title or contract.title,
            start_ms=cursor_ms,
            duration_ms=duration_ms,
            visual_type=draft.visual_type,
            narration=draft.narration,
            captions=draft.captions if constraints.include_captions else [],
            on_screen_text=draft.on_screen_text,
            visual_prompt=draft.visual_prompt or contract.content_hint,
            interaction_prompt=draft.interaction_prompt,
            source_agents=[agent for agent in (draft.source_agents or contract.required_sources) if agent in VIDEO_SOURCE_AGENT_IDS],
        )
    )
    cursor_ms += duration_ms
```

Then include repair metadata in the returned `VideoPayload`:

```python
"repair_warnings": repair_warnings,
```

The final metadata block should include at least:

```python
metadata={
    "source_agent_ids": source_agent_ids,
    "internal_pipeline": "material/outline/scenes/payload",
    "delivery_mode": "preview",
    "repair_warnings": repair_warnings,
}
```

- [ ] **Step 6: Make tutor adapter skip invalid previous results**

Replace the `normalized_results = {...}` comprehension in `generate_from_tutor_context()` with:

```python
normalized_results: dict[str, AgentResult] = {}
for agent_id, result in previous_results.items():
    if not isinstance(result, (dict, AgentResult)):
        continue
    try:
        normalized_results[agent_id] = result if isinstance(result, AgentResult) else AgentResult.model_validate(result)
    except Exception:
        logger.warning("跳过非法 tutor previous_result: agent_id=%s", agent_id, exc_info=True)
```

- [ ] **Step 7: Run Task 1 tests**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_video_agent.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 1**

```bash
rtk git add server/app/resource/agents/video.py server/tests/resource/test_video_agent.py
rtk git commit -m "fix: harden video agent payload generation"
```

---

## Task 2: 修复 outline 严格失败，增加可恢复 normalize 层

**Files:**
- Modify: `server/app/resource/agents/video.py`
- Modify: `server/tests/resource/test_video_agent.py`

- [ ] **Step 1: Add failing test for outline repair**

Append this test to `server/tests/resource/test_video_agent.py`:

```python
def test_repair_outline_matches_constraints_and_scene_roles():
    from app.resource.agents.video import (
        SceneContract,
        VideoConstraints,
        VideoMaterialDigest,
        VideoOutline,
        repair_outline_for_constraints,
    )

    constraints = VideoConstraints(duration_seconds=180, scene_count=3)
    digest = VideoMaterialDigest(topic="TCP", learning_goal="理解三次握手")
    outline = VideoOutline.model_construct(
        title="TCP 讲解",
        topic="TCP",
        duration_seconds=90,
        style="explainer",
        aspect_ratio="16:9",
        narrative="",
        scenes=[
            SceneContract(scene_id="scene-a", index=4, role="concept", title="概念", duration_seconds=20, learning_objective="解释概念", content_hint="概念卡", required_sources=["content"]),
            SceneContract(scene_id="scene-b", index=8, role="process", title="流程", duration_seconds=70, learning_objective="解释流程", content_hint="流程图", required_sources=["content"]),
        ],
    )

    repaired = repair_outline_for_constraints(outline, constraints, digest)

    assert repaired.duration_seconds == 180
    assert len(repaired.scenes) == 3
    assert [scene.index for scene in repaired.scenes] == [1, 2, 3]
    assert repaired.scenes[0].role == "hook"
    assert repaired.scenes[-1].role == "recap"
    assert sum(scene.duration_seconds for scene in repaired.scenes) == 180
```

- [ ] **Step 2: Run the failing test**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_video_agent.py::test_repair_outline_matches_constraints_and_scene_roles -q
```

Expected before implementation: FAIL because `repair_outline_for_constraints` does not exist.

- [ ] **Step 3: Implement outline repair helper**

Add this helper below `_fallback_scene_draft()`:

```python
def repair_outline_for_constraints(
    outline: VideoOutline,
    constraints: VideoConstraints,
    digest: VideoMaterialDigest,
) -> VideoOutline:
    durations = _duration_plan(constraints.duration_seconds, constraints.scene_count)
    source_scenes = list(outline.scenes)
    if not source_scenes:
        source_scenes = [
            SceneContract(
                scene_id="scene-1",
                index=1,
                role="hook",
                title=digest.topic,
                duration_seconds=durations[0],
                learning_objective=digest.learning_goal or digest.topic,
                visual_type="card",
                content_hint=digest.topic,
                required_sources=["content"],
            )
        ]

    repaired_scenes: list[SceneContract] = []
    for idx in range(1, constraints.scene_count + 1):
        source = source_scenes[min(idx - 1, len(source_scenes) - 1)]
        if idx == 1:
            role: SceneRole = "hook"
        elif idx == constraints.scene_count:
            role = "recap"
        else:
            role = source.role if source.role not in {"hook", "recap"} else "concept"
        repaired_scenes.append(
            SceneContract(
                scene_id=f"scene-{idx}",
                index=idx,
                role=role,
                title=source.title or f"{digest.topic} {idx}",
                duration_seconds=durations[idx - 1],
                learning_objective=source.learning_objective or digest.learning_goal or digest.topic,
                visual_type=source.visual_type,
                content_hint=source.content_hint or digest.topic,
                required_sources=[agent for agent in source.required_sources if agent in VIDEO_SOURCE_AGENT_IDS] or ["content"],
            )
        )

    return VideoOutline(
        title=outline.title or f"{digest.topic}讲解",
        topic=outline.topic or digest.topic,
        duration_seconds=constraints.duration_seconds,
        style=constraints.style,
        aspect_ratio=constraints.aspect_ratio,
        narrative=outline.narrative or digest.learning_goal,
        scenes=repaired_scenes,
    )
```

- [ ] **Step 4: Use repair helper in `VideoAgent.generate_resource()`**

Replace:

```python
outline = await VideoOutlineAgent().run(digest, constraints)
if len(outline.scenes) != constraints.scene_count:
    raise ValueError(f"视频场景数与预期不符：期望 {constraints.scene_count}，实际 {len(outline.scenes)}")
```

with:

```python
outline = await VideoOutlineAgent().run(digest, constraints)
outline = repair_outline_for_constraints(outline, constraints, digest)
```

- [ ] **Step 5: Run Task 2 tests**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_video_agent.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
rtk git add server/app/resource/agents/video.py server/tests/resource/test_video_agent.py
rtk git commit -m "fix: repair video outline contracts"
```

---

## Task 3: 前端完整接入 video 选择、配置、DAG 与请求

**Files:**
- Modify: `src/features/resource/model/resource.ts`
- Modify: `src/features/resource/model/ResourceGeneratorConstants.ts`
- Modify: `src/features/resource/views/ResourceGenerator.vue`
- Modify: `src/features/resource/views/ResourcePersonalize.vue`

- [ ] **Step 1: Update TypeScript request model**

In `src/features/resource/model/resource.ts`, change:

```ts
export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt'
```

to:

```ts
export type ResourceAgentId = 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt' | 'video'
```

Add `output_format` to `ppt`, and add `video` under `agent_configs`:

```ts
ppt: {
  page_count: number
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  output_format: 'preview'
}
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

- [ ] **Step 2: Update resource generator constants**

In `src/features/resource/model/ResourceGeneratorConstants.ts`, update the import:

```ts
import {
  Cpu, CircleCheckFilled, Position,
  Document, Share, Edit, Collection, DataBoard, VideoCamera,
} from '@element-plus/icons-vue'
```

Add constants:

```ts
export const VIDEO_AGENT_ID = 'video'
export const VIDEO_REVIEW_AGENT_ID = 'video_review'
```

Update `SYSTEM_AGENT_IDS`:

```ts
export const SYSTEM_AGENT_IDS = ['planning', COORDINATOR_AGENT_ID, PRE_REVIEW_AGENT_ID, PPT_REVIEW_AGENT_ID, VIDEO_REVIEW_AGENT_ID, 'review', BUNDLE_AGENT_ID]
```

Add display rows:

```ts
video: { label: '讲解视频助手', icon: '🎬' },
video_review: { label: '视频安全审核', icon: '🔍' },
```

Add `video` to `agentMetaList`:

```ts
{ id: 'video', name: '讲解视频助手', icon: VideoCamera, colorClass: 'text-teal' },
```

Update `AnyAgentConfigs`:

```ts
video: {
  duration_seconds: number
  scene_count: number
  style: string
  voice: string
  aspect_ratio: string
  include_captions: boolean
  output_format: string
}
```

Add video defaults to every `SCENARIO_DEFAULTS` entry:

```ts
video: { duration_seconds: 180, scene_count: 6, style: 'explainer', voice: 'teacher', aspect_ratio: '16:9', include_captions: true, output_format: 'preview' }
```

Update helper maps:

```ts
video: '讲解视频',
video: '通过结构化分镜和旁白脚本快速理解抽象过程。',
video: 'Video JSON',
video: '8-12 分钟',
video: 'tone-teal',
video: 'Video 分镜脚本',
```

- [ ] **Step 3: Update `ResourceGenerator.vue` agent config and aggregation model**

Import video constants:

```ts
  VIDEO_AGENT_ID,
  VIDEO_REVIEW_AGENT_ID,
```

Add video to default `agentConfigs`:

```ts
video: { duration_seconds: 180, scene_count: 6, style: 'explainer', voice: 'teacher', aspect_ratio: '16:9', include_captions: true, output_format: 'preview' },
```

Update `getPlanStepTitle()` map:

```ts
video: '生成讲解视频分镜',
```

Update `getPlanStepSummary()` map:

```ts
video: '汇总上游资源并生成结构化讲解视频脚本',
```

Replace:

```ts
const baseGenerationAgentIds = computed(() => dagSelectedAgentIds.value.filter(id => id !== PPT_AGENT_ID))
```

with:

```ts
const baseGenerationAgentIds = computed(() => dagSelectedAgentIds.value.filter(id => id !== PPT_AGENT_ID && id !== VIDEO_AGENT_ID))
```

In `dagNodesV2`, after the PPT block add:

```ts
if (selected.includes(VIDEO_AGENT_ID as ResourceAgentId)) {
  nodes.push(dagNodeStates.value[VIDEO_AGENT_ID] || { id: VIDEO_AGENT_ID, label: '讲解视频助手', icon: '🎬', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
  nodes.push(dagNodeStates.value[VIDEO_REVIEW_AGENT_ID] || { id: VIDEO_REVIEW_AGENT_ID, label: '视频安全审核', icon: '🔍', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
}
```

In `updateOverallProgressFromDag()`, add video weighted stages before bundle:

```ts
...(dagSelectedAgentIds.value.includes(VIDEO_AGENT_ID as ResourceAgentId) ? [
  { weight: 15, progress: getStageNode(VIDEO_AGENT_ID).progress },
  { weight: 5, progress: getStageNode(VIDEO_REVIEW_AGENT_ID).progress },
] : []),
```

In `initializeWaitingNodes()`, add:

```ts
if (enabledAgentIds.value.includes(VIDEO_AGENT_ID as ResourceAgentId)) {
  nodes[VIDEO_REVIEW_AGENT_ID] = createDagNode(VIDEO_REVIEW_AGENT_ID, true)
}
```

In `startGeneration()`, include `video` config:

```ts
agent_configs: {
  content: agentConfigs.content,
  mindmap: agentConfigs.mindmap,
  quiz: agentConfigs.quiz,
  code: agentConfigs.code,
  reading: agentConfigs.reading,
  ppt: agentConfigs.ppt,
  video: agentConfigs.video,
} as any,
```

- [ ] **Step 4: Add video controls to `ResourcePersonalize.vue`**

After the PPT template block, add:

```vue
<template v-if="agent.id === 'video'">
  <div class="config-grid">
    <div class="config-field">
      <label>视频风格</label>
      <el-select v-model="agentConfigs.video.style" size="default" class="w-full custom-select">
        <el-option label="讲解型" value="explainer" />
        <el-option label="课堂型" value="lecture" />
        <el-option label="录屏型" value="screencast" />
        <el-option label="案例 walkthrough" value="case_walkthrough" />
      </el-select>
    </div>
    <div class="config-field">
      <label>旁白语气</label>
      <el-radio-group v-model="agentConfigs.video.voice" size="small" class="custom-radio-group">
        <el-radio-button label="teacher">教师</el-radio-button>
        <el-radio-button label="coach">教练</el-radio-button>
        <el-radio-button label="concise">简洁</el-radio-button>
      </el-radio-group>
    </div>
    <div class="config-field">
      <label>画幅</label>
      <el-radio-group v-model="agentConfigs.video.aspect_ratio" size="small" class="custom-radio-group">
        <el-radio-button label="16:9">横屏</el-radio-button>
        <el-radio-button label="9:16">竖屏</el-radio-button>
        <el-radio-button label="1:1">方形</el-radio-button>
      </el-radio-group>
    </div>
    <div class="config-field">
      <label>总时长</label>
      <span class="slider-value"><b>{{ agentConfigs.video.duration_seconds }}</b> 秒</span>
      <el-slider v-model="agentConfigs.video.duration_seconds" :min="60" :max="600" :step="30" class="custom-slider-v2" />
    </div>
    <div class="config-field">
      <label>分镜数量</label>
      <span class="slider-value"><b>{{ agentConfigs.video.scene_count }}</b> 段</span>
      <el-slider v-model="agentConfigs.video.scene_count" :min="3" :max="12" :step="1" class="custom-slider-v2" />
    </div>
    <div class="config-field switch-row">
      <span>生成字幕短句</span>
      <el-switch v-model="agentConfigs.video.include_captions" />
    </div>
  </div>
</template>
```

- [ ] **Step 5: Run frontend build**

From repo root, run:

```bash
rtk npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
rtk git add src/features/resource/model/resource.ts src/features/resource/model/ResourceGeneratorConstants.ts src/features/resource/views/ResourceGenerator.vue src/features/resource/views/ResourcePersonalize.vue
rtk git commit -m "feat: wire video agent into resource frontend"
```

---

## Task 4: 稳定 VideoView 对 `video/v1` payload 的预览与导出

**Files:**
- Modify: `src/features/resource/components/VideoView.vue`

- [ ] **Step 1: Replace payload parsing with a reusable parser**

In `VideoView.vue`, add this above `videoPayload`:

```ts
function parseMaybeJson(value: any): any {
  if (value == null) return null
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}
```

Replace `videoPayload` with:

```ts
const videoPayload = computed(() => {
  const raw = props.resultData
  if (!raw) return null
  if (raw.schema_version === 'video/v1') return raw
  const contentJson = raw.content_json || raw.contentJson
  if (contentJson?.content) return parseMaybeJson(contentJson.content)
  if (contentJson?.schema_version === 'video/v1') return contentJson
  if (raw.content) return parseMaybeJson(raw.content)
  return parseMaybeJson(raw)
})
```

- [ ] **Step 2: Make scene normalization use backend field names only**

Replace `activeScenes` map with:

```ts
const activeScenes = computed(() => {
  const scenes = videoPayload.value?.scenes
  return Array.isArray(scenes)
    ? scenes.map((scene: any) => ({
        id: scene.scene_id || `scene-${scene.index}`,
        duration: Number(scene.duration_ms || 4000),
        title: scene.title || `分镜 ${scene.index || ''}`.trim(),
        desc: scene.narration || scene.visual_prompt || '',
        visualPrompt: scene.visual_prompt || '',
        visualType: scene.visual_type || 'card',
        captions: Array.isArray(scene.captions) ? scene.captions : [],
        onScreenText: Array.isArray(scene.on_screen_text) ? scene.on_screen_text : [],
      }))
    : []
})
```

Remove `imageUrl`, `animation`, and `filter` dependencies from the no-image path. Keep the canvas card rendering path as the default renderer.

- [ ] **Step 3: Replace MP4 export with deterministic JSON export**

Remove:

```ts
import { Muxer, ArrayBufferTarget } from 'mp4-muxer'
```

Replace the button text:

```vue
{{ isExporting ? `导出中... ${exportProgress}%` : '导出 JSON' }}
```

Replace `startExportMP4` with:

```ts
const exportVideoJson = async () => {
  if (!videoPayload.value || isExporting.value) return
  isExporting.value = true
  exportProgress.value = 100
  try {
    const blob = new Blob([JSON.stringify(videoPayload.value, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${resourceTitle.value.replace(/\s+/g, '_')}_video_script.json`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    window.setTimeout(() => {
      isExporting.value = false
      exportProgress.value = 0
    }, 300)
  }
}
```

Change the button handler:

```vue
@click="exportVideoJson"
```

Remove `isWebCodecsSupported`.

- [ ] **Step 4: Run frontend build**

From repo root, run:

```bash
rtk npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
rtk git add src/features/resource/components/VideoView.vue
rtk git commit -m "fix: stabilize video resource preview"
```

---

## Task 5: 清理数据库模型重复字段并加强 schema contract test

**Files:**
- Modify: `server/app/infra/models.py`
- Modify: `server/tests/resource/test_resource_contract.py`

- [ ] **Step 1: Add failing source-level duplicate-field test**

Append this to `server/tests/resource/test_resource_contract.py`:

```python
def _class_source(class_name: str, next_class_name: str) -> str:
    source = Path(__file__).resolve().parents[2].joinpath("app/infra/models.py").read_text()
    start = source.index(f"class {class_name}(")
    end = source.index(f"class {next_class_name}(", start)
    return source[start:end]


def test_generated_resource_item_declares_status_fields_once():
    class_source = _class_source("GeneratedResourceItem", "QuizQuestion")

    assert class_source.count("\n    status: str = Field(") == 1
    assert class_source.count("\n    error_message: str | None = Field(") == 1
```

- [ ] **Step 2: Run the failing test**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_resource_contract.py::test_generated_resource_item_declares_status_fields_once -q
```

Expected before implementation: FAIL because `GeneratedResourceItem` declares `status` and `error_message` twice.

- [ ] **Step 3: Remove the duplicate status block**

In `server/app/infra/models.py`, inside `GeneratedResourceItem`, keep the first status block:

```python
status: str = Field(default="pending", max_length=50)
error_message: str | None = Field(default=None, sa_column=Column(Text))
```

Delete the later duplicate block:

```python
# 状态
status: str = Field(default="pending", max_length=50)
error_message: str | None = Field(default=None, sa_column=Column(Text))
```

Do not modify `PathNodeResource.summary/status/error_message/input_json`; those columns exist in `server/init_schema.sql`.

- [ ] **Step 4: Run contract tests**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_resource_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
rtk git add server/app/infra/models.py server/tests/resource/test_resource_contract.py
rtk git commit -m "fix: clean resource item model contract"
```

---

## Task 6: 补齐后端 orchestration 测试并确认 review/进度契约

**Files:**
- Modify: `server/tests/resource/test_video_service_orchestration.py`
- Verify: `server/app/resource/service.py`
- Verify: `server/app/resource/agents/review.py`

- [ ] **Step 1: Ensure orchestration test expects video at 80% before video stages**

Update `test_overall_progress_treats_video_as_aggregation_stage_not_worker()` to use video progress at 50, review at 0:

```python
def test_overall_progress_treats_video_as_aggregation_stage_not_worker():
    from app.resource.service import ResourceService
    from app.resource.review import VIDEO_AGENT_ID, VIDEO_REVIEW_AGENT_ID

    progress = ResourceService._calculate_overall_progress(
        status="generating",
        selected_agents=["content", "reading", "video"],
        agent_snapshots={
            "planning": {"progress": 100},
            "content": {"progress": 100},
            "reading": {"progress": 100},
            "pre_review": {"progress": 100},
            "bundle": {"progress": 100},
            VIDEO_AGENT_ID: {"progress": 50},
            VIDEO_REVIEW_AGENT_ID: {"progress": 0},
        },
    )

    assert 80 <= progress < 100
```

- [ ] **Step 2: Add explicit frontend/backend parity note as code comment in service**

In `server/app/resource/service.py`, above `AGGREGATION_AGENT_IDS`, ensure this comment exists:

```python
# Aggregation agents run after base resource workers and consume previous_results.
# Keep this aligned with ResourceGenerator.vue baseGenerationAgentIds.
AGGREGATION_AGENT_IDS = (PPT_AGENT_ID, VIDEO_AGENT_ID)
```

- [ ] **Step 3: Run orchestration tests**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_video_service_orchestration.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit Task 6**

```bash
rtk git add server/app/resource/service.py server/tests/resource/test_video_service_orchestration.py
rtk git commit -m "test: lock video orchestration contract"
```

---

## Task 7: Final Verification

**Files:**
- Verify all files changed in previous tasks.

- [ ] **Step 1: Run targeted backend video/resource tests**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_video_agent.py tests/resource/test_video_service_orchestration.py tests/resource/test_resource_contract.py -q
```

Expected: PASS.

- [ ] **Step 2: Run broader resource regression tests**

From `server/`, run:

```bash
rtk uv run pytest tests/resource/test_resource_request_schema.py tests/resource/test_agent_integration.py tests/resource/test_agent_dual_entry.py tests/resource/test_ppt_internal_multi_agent.py tests/resource/test_ppt_agent.py tests/resource/test_ppt_standalone.py -q
```

Expected: PASS. If unrelated failures appear, record exact failing tests and confirm they are outside video/resource aggregation changes.

- [ ] **Step 3: Run frontend build**

From repo root, run:

```bash
rtk npm run build
```

Expected: PASS.

- [ ] **Step 4: Manual smoke test for standalone video**

Start backend from `server/`:

```bash
rtk uv run fastapi dev app/main.py --port 9999
```

Start frontend from repo root in another terminal:

```bash
rtk npm run dev
```

Manual checks:

- Resource generation personalize page shows “讲解视频助手”.
- User can enable video and configure duration, scene count, style, voice, aspect ratio, captions.
- Generation DAG shows video after base workers, plus video review.
- Generated result contains a video card.
- Clicking video opens `VideoView`.
- Canvas preview renders scenes from `schema_version: "video/v1"`.
- JSON export downloads the video script.
- No path resource page is used for standalone video.
- No tutor/chat route calls `generate_from_tutor_context()`.

- [ ] **Step 5: Final commit if verification changes were needed**

Only if Task 7 required additional fixes, commit them:

```bash
rtk git add server/app/resource src/features/resource
rtk git commit -m "fix: complete video agent integration"
```

---

## Acceptance Criteria

- `server/app/resource/agents/video.py` remains the only video agent implementation file.
- `VideoAgent.generate_resource()` consumes only successful base resource `previous_results`.
- Scene generation is parallel and locally resilient; one scene failure does not fail the whole video.
- Outline timing/count/roles are repaired before payload build.
- Output payload conforms to `video/v1`:
  - top-level `schema_version`, `title`, `topic`, `duration_seconds`, `aspect_ratio`, `style`, `voice`, `language`, `scenes`, `assets`, `metadata`
  - scene fields include `scene_id`, `index`, `role`, `title`, `start_ms`, `duration_ms`, `visual_type`, `narration`, `captions`, `on_screen_text`, `visual_prompt`, `interaction_prompt`, `source_agents`
- `video` is treated like `ppt`: standalone resource aggregation stage, not a base worker.
- `video_review` receives real `video_resource.audit_content`.
- Frontend can select and configure video.
- Frontend DAG/progress does not treat video as a base worker.
- `VideoView` previews backend `video/v1` payload without requiring `imageUrl`, `visual_data`, or MP4.
- `generate_from_tutor_context()` exists but no chat/tutor route calls it.
- `GeneratedResourceItem` SQLModel has no duplicate status/error fields and remains aligned with `server/init_schema.sql`.

---

## Suggested Commit Order

1. `fix: harden video agent payload generation`
2. `fix: repair video outline contracts`
3. `feat: wire video agent into resource frontend`
4. `fix: stabilize video resource preview`
5. `fix: clean resource item model contract`
6. `test: lock video orchestration contract`
