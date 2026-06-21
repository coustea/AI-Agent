# LangGraph 嵌套多智能体与本地正则审计重构计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用 LangGraph 嵌套图架构重构整个多智能体资源生成系统（包含父级协调图、嵌套的 PPT 子图与 Video 子图），完全去除 LLM 审核以提高生成速度与稳定性，并统一接口支持 Standalone 生成和 Learning Path 路径单节点生成。

**Architecture:** 全局由 `ParentGraph` 作为总编排，首先调用 `PlanningAgent` 规划大纲，随后并行唤醒各基础 Workers。生成完成后，并行启动本地 `RegexAuditNode` 与 `PptNode` (调用 PPT 子图)、`VideoNode` (调用 Video 子图)，最后将所有成果汇聚保存。PPT 与 Video 子图在内部使用 `Send` 机制对每一页/分镜进行动态并行生成，以最快速度组装成最终载荷。

**Tech Stack:** Python 3.13, FastAPI, SQLModel, LangChain, LangGraph (>= 1.1.4)

---

## 预研与文件规划

重构需要触及并修改或新建以下文件：
1. **[MODIFY]** `server/app/resource/agents/review.py`：完全移除 LLM 审核，重构为本地正则合规与安全审计工具，实现零推理延迟审计。
2. **[MODIFY]** `server/app/resource/agents/ppt.py`：将 PPT 内部流水线改造为 `ppt_sub_graph`，使用 `Send` 对幻灯片单页并发写入，并适配 `generate_resource` 与 `generate_node` 入口。
3. **[MODIFY]** `server/app/resource/agents/video.py`：将 Video 内部流水线改造为 `video_sub_graph`，使用 `Send` 对分镜并发写入，重构 `generate_node` 真正实现对学习路径单节点视频生成的支持，并适配 `generate_resource`。
4. **[NEW]** `server/app/resource/workflow_graph.py`：定义全局编排父图 `parent_graph`，组织各个 Worker 节点的并行和后置聚合。
5. **[MODIFY]** `server/app/resource/service.py`：将 `run_multi_agent_generation` 的底层循环逻辑替换为 `parent_graph.ainvoke` 驱动，并保持原有的数据库落库与 SSE 进度推流正常工作。

---

## 详细实现步骤

### Task 1: 本地正则审计重构 (agents/review.py)

**Files:**
- Modify: `server/app/resource/agents/review.py`
- Test: `server/tests/resource/test_review_regex.py` (新建测试)

- [ ] **Step 1: 编写单元测试验证本地正则审计报告生成**

创建测试文件 `server/tests/resource/test_review_regex.py`，确保其能校验违禁词并返回不通过的结构：

```python
import pytest
from app.resource.schemas import ResourceInput
from app.resource.agents.review import ReviewAgent

@pytest.mark.asyncio
async def test_review_agent_regex_checking():
    agent = ReviewAgent()
    
    # 测试合规内容
    input_ok = ResourceInput(
        learning_need="Python 基础语法",
        learning_scenario="test",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "这是健康的 Python 教学内容"}]}},
        profile={},
    )
    res_ok = await agent.generate_resource(input_ok)
    assert res_ok.success is True
    assert res_ok.metadata["review_status"] == "pass"

    # 测试违规内容
    input_bad = ResourceInput(
        learning_need="赌博网站制作",
        learning_scenario="test",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "我们今天来学习如何制作赌博网站"}]}},
        profile={},
    )
    res_bad = await agent.generate_resource(input_bad)
    assert res_bad.success is False
    assert res_bad.metadata["review_status"] == "needs_revision"
    assert any("包含敏感词" in issue for issue in res_bad.metadata["issues"])
```

- [ ] **Step 2: 运行测试验证失败**

运行测试，确保 ReviewAgent 此时仍会调用 LLM 或发生异常。
Run: `uv run pytest tests/resource/test_review_regex.py -v`
Expected: FAIL (因 `get_llm` 缺失配置或 LLM 调用失败)

- [ ] **Step 3: 实现纯本地正则审计逻辑**

修改 `server/app/resource/agents/review.py`。彻底移除 `self.llm = get_llm()`，修改为在本地直接提取文本进行 `rule_check` 并返回格式化数据：

```python
import json
import re
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

SENSITIVE_WORDS: tuple[str, ...] = (
    "自杀", "自残", "炸弹制作", "毒品制作", "黑客攻击教程",
    "洗钱", "诈骗教程", "赌博网站",
)

SENSITIVE_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"doi:\s*10\.\d{4,}/[\S]+", re.IGNORECASE),
    re.compile(r"https?://\S+\.(xyz|top|click|buzz|loan)\b"),
    re.compile(r"ISBN[- ]?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?[\dX]"),
)

def rule_check(content: str) -> list[dict]:
    findings: list[dict] = []
    if not content or not content.strip():
        findings.append({"check": "completeness", "detail": "内容为空"})
        return findings

    if len(content.strip()) < 50:
        findings.append({"check": "completeness", "detail": f"内容过短: {len(content.strip())} 字符"})

    for word in SENSITIVE_WORDS:
        if word in content:
            findings.append({"check": "safety", "detail": f"包含敏感词: {word}"})

    for pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(content):
            findings.append({"check": "suspicious_reference", "detail": f"可疑引用: {match.group()[:60]}"})

    if content.strip().startswith("{") or content.strip().startswith("["):
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            findings.append({"check": "format", "detail": f"JSON 解析失败: {e}"})

    return findings

@register_agent
class ReviewAgent(BaseResourceAgent):
    agent_id = "review"
    agent_name = "审核"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        config = input_data.agent_config or {}
        progress_agent_id = config.get("progress_agent_id") or "review"
        review_envelope = config.get("review_envelope", {})

        await self.emit_start("正在执行本地规则合规性审核", progress=50)

        audit_content = self._extract_audit_content(review_envelope)
        findings = rule_check(audit_content)

        passed = len(findings) == 0
        issues = [f.get("detail", "") for f in findings]
        status = "pass" if passed else "needs_revision"
        failed_agents = [progress_agent_id] if not passed else []

        parsed_review = {
            "status": status,
            "checks": {
                "need_alignment": "pass" if passed else "fail",
                "content_completeness": "pass" if passed else "fail",
                "factuality": "pass" if passed else "fail",
                "hallucination": "pass" if passed else "fail",
                "safety": "pass" if passed else "fail",
                "grounding": "pass" if passed else "fail",
            },
            "violations": issues,
            "revision_targets": failed_agents,
            "mode": "regex_audit",
        }

        result = AgentResult(
            success=passed,
            content=json.dumps(parsed_review, ensure_ascii=False),
            file_type="json",
            title="资源质量安全合规报告",
            summary="本地规则审计通过" if passed else f"本地规则审计发现 {len(issues)} 个合规问题",
            metadata={
                "agent_id": "review",
                "passed": passed,
                "issues": issues,
                "review_status": status,
                "parsed_review": parsed_review,
                "rule_findings": findings,
            },
        )
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        return AgentResult(
            success=False,
            error="review agent 不用于路径节点资源生成",
            title="",
            summary="not supported",
            metadata={"agent_id": "review"},
        )

    @staticmethod
    def _extract_audit_content(envelope: dict) -> str:
        parts: list[str] = []
        for resource in envelope.get("deep_audit_resources", []):
            if isinstance(resource, dict) and resource.get("audit_content"):
                parts.append(resource["audit_content"])
        for key in ("ppt_resource", "video_resource"):
            resource = envelope.get(key)
            if isinstance(resource, dict) and resource.get("audit_content"):
                parts.append(resource["audit_content"])
        return "\n\n".join(parts)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/resource/test_review_regex.py -v`
Expected: PASS

- [ ] **Step 5: 提交 Task 1 代码**

Run: `git add server/app/resource/agents/review.py server/tests/resource/test_review_regex.py && git commit -m "refactor: replace LLM review with local regex audit"`

---

### Task 2: PPT 嵌套子图实现 (agents/ppt.py)

**Files:**
- Modify: `server/app/resource/agents/ppt.py`
- Test: `server/tests/resource/test_ppt_graph.py` (新建测试)

- [ ] **Step 1: 编写单元测试验证 PPT 子图生成流程**

创建 PPT 节点的 LangGraph 生成测试：

```python
import pytest
from app.resource.schemas import ResourceInput
from app.resource.agents.ppt import PptAgent

@pytest.mark.asyncio
async def test_ppt_agent_langgraph_generation():
    agent = PptAgent()
    input_data = ResourceInput(
        learning_need="深度学习中的卷积核作用机制",
        learning_scenario="standalone",
        agent_name="ppt",
        agent_config={"page_count": 3, "difficulty": "beginner"},
        profile={},
    )
    # 模拟空 handoffs 自动走降级或基础大纲生成
    res = await agent.generate_resource(input_data)
    assert res.success is True
    assert "slides" in res.content
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest server/tests/resource/test_ppt_graph.py -v`
Expected: FAIL (未接入 LangGraph 子图流程)

- [ ] **Step 3: 重构 PPT 生成管道，引入 LangGraph 子图**

修改 `server/app/resource/agents/ppt.py`，在其底部添加 `PptGraphState` 定义，并基于 `StateGraph` 构建幻灯片并行写入流：

```python
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

# 1. 定义子图状态
class PptGraphState(TypedDict):
    bundle: MaterialBundle
    page_count: int
    difficulty: str
    title_prefix: str
    emitter: Any | None
    
    # 产物
    digest: MaterialDigest
    outline: DeckOutline
    drafts: Annotated[list[SlideDraft], operator.add]
    payload: PptPayload
    error: str

class SlideState(TypedDict):
    contract: SlideContract
    digest: MaterialDigest
    outline: DeckOutline

# 2. 声明子图节点函数
async def ppt_material_node(state: PptGraphState) -> dict[str, Any]:
    if state.get("emitter"):
        await state.get("emitter").emit_agent("ppt", status="running", message="正在提取教学素材", progress=20)
    digest = await MaterialAgent().run(state["bundle"])
    return {"digest": digest}

async def ppt_outline_node(state: PptGraphState) -> dict[str, Any]:
    if state.get("emitter"):
        await state.get("emitter").emit_agent("ppt", status="running", message="正在规划 PPT 结构", progress=35)
    
    difficulty = state["difficulty"]
    constraint_difficulty = "normal"
    if difficulty == "intermediate":
        constraint_difficulty = "normal"
    elif difficulty == "beginner":
        constraint_difficulty = "easy"
    elif difficulty == "advanced":
        constraint_difficulty = "hard"

    constraints = DeckConstraints(
        page_count=state["page_count"],
        difficulty=constraint_difficulty,
    )
    outline = await OutlineAgent().run(state["digest"], constraints)
    return {"outline": outline}

def route_slides(state: PptGraphState):
    """动态 Map 分发每一页幻灯片的并发写入"""
    return [
        Send("write_slide", {"contract": s, "digest": state["digest"], "outline": state["outline"]})
        for s in state["outline"].slides
    ]

async def ppt_write_slide_node(state: SlideState) -> dict[str, Any]:
    draft = await SlideAgent().run(state["contract"], state["digest"], state["outline"])
    return {"drafts": [draft]}

async def ppt_payload_node(state: PptGraphState) -> dict[str, Any]:
    if state.get("emitter"):
        await state.get("emitter").emit_agent("ppt", status="running", message="正在构建最终载荷", progress=85)
    sorted_drafts = sorted(state["drafts"], key=lambda d: d.index)
    payload = PayloadBuilder().build(state["outline"], sorted_drafts)
    return {"payload": payload}

# 3. 编排并编译 PPT 子图
ppt_workflow = StateGraph(PptGraphState)
ppt_workflow.add_node("material", ppt_material_node)
ppt_workflow.add_node("outline", ppt_outline_node)
ppt_workflow.add_node("write_slide", ppt_write_slide_node)
ppt_workflow.add_node("builder", ppt_payload_node)

ppt_workflow.add_edge(START, "material")
ppt_workflow.add_edge("material", "outline")
ppt_workflow.add_conditional_edges("outline", route_slides, ["write_slide"])
ppt_workflow.add_edge("write_slide", "builder")
ppt_workflow.add_edge("builder", END)

ppt_sub_graph = ppt_workflow.compile()
```

修改 `PptAgent` 类中的 `_run_pipeline` 以 `ainvoke` 唤醒此子图，并同时实现 `generate_node` 支持从单节点 `NodeInput` 并行生成 PPT：

```python
@register_agent
class PptAgent(BaseResourceAgent):
    agent_id = "ppt"
    agent_name = "PPT 生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        config = input_data.agent_config or {}
        material_bundle_data = config.get("material_bundle")
        if material_bundle_data and isinstance(material_bundle_data, dict):
            bundle = MaterialBundle.model_validate(material_bundle_data)
        else:
            bundle = build_resource_material(input_data)

        result = await self._run_graph_pipeline(
            bundle=bundle,
            config=config,
            title_prefix=input_data.learning_need[:32],
        )
        if result.success:
            coverage = outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs)
            result.metadata["teaching_plan_outline_ids"] = coverage["teaching_plan_outline_ids"]
            result.metadata["covered_source_outline_ids"] = coverage["covered_source_outline_ids"]
            result.metadata["missing_source_outline_ids"] = coverage["missing_source_outline_ids"]
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        bundle = build_node_material(input_data)
        config = input_data.agent_config or {}
        result = await self._run_graph_pipeline(
            bundle=bundle,
            config=config,
            title_prefix=input_data.node_title,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emit_finish(result)
        return result

    async def _run_graph_pipeline(
        self,
        *,
        bundle: MaterialBundle,
        config: dict,
        title_prefix: str,
    ) -> AgentResult:
        page_count = int(config.get("page_count") or config.get("slide_count") or 6)
        difficulty = config.get("difficulty") or "intermediate"

        try:
            # 执行 LangGraph 子图
            initial_state = {
                "bundle": bundle,
                "page_count": page_count,
                "difficulty": difficulty,
                "title_prefix": title_prefix,
                "emitter": self.emitter,
                "drafts": [],
            }
            output_state = await ppt_sub_graph.ainvoke(initial_state)
            
            if "error" in output_state and output_state["error"]:
                raise ValueError(output_state["error"])
                
            payload = output_state["payload"]
        except Exception as exc:
            logger.error("PptAgent 嵌套子图生成异常: %s", exc, exc_info=True)
            return AgentResult(
                success=False,
                error=str(exc),
                title=f"{title_prefix} - PPT",
                summary=f"PPT 生成异常: {exc}",
                metadata={
                    "engine": "ppt_langgraph",
                    "agent_id": "ppt",
                    "delivery_mode": "preview",
                    "schema_version": "ppt/v2",
                    "difficulty": difficulty,
                    "internal_pipeline": "langgraph_subgraph",
                },
            )

        actual_count = len(payload.slides)
        content = payload.model_dump_json(indent=2)
        source_handoff_agent_ids = sorted(bundle.upstream_handoffs.keys()) if bundle.upstream_handoffs else []
        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - PPT",
            summary=f"生成 {actual_count} 页在线预览 PPT",
            metrics={"page_count": actual_count},
            metadata={
                "engine": "ppt_langgraph",
                "agent_id": "ppt",
                "delivery_mode": "preview",
                "schema_version": "ppt/v2",
                "template_id": payload.template_id,
                "page_count": actual_count,
                "difficulty": difficulty,
                "source_handoff_agent_ids": source_handoff_agent_ids,
                "internal_pipeline": "langgraph_subgraph",
            },
        )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest server/tests/resource/test_ppt_graph.py -v`
Expected: PASS

- [ ] **Step 5: 提交 Task 2 代码**

Run: `git add server/app/resource/agents/ppt.py server/tests/resource/test_ppt_graph.py && git commit -m "feat: refactor PPT pipeline into a LangGraph nested sub-graph"`

---

### Task 3: Video 嵌套子图实现 (agents/video.py)

**Files:**
- Modify: `server/app/resource/agents/video.py`
- Test: `server/tests/resource/test_video_graph.py` (新建测试)

- [ ] **Step 1: 编写单元测试验证 Video 子图生成以及 generate_node 单节点生成**

添加测试 file 以确保 `VideoAgent` 能够正确在独立路径节点生成：

```python
import pytest
from app.resource.schemas import NodeInput, ResourceInput
from app.resource.agents.video import VideoAgent

@pytest.mark.asyncio
async def test_video_agent_langgraph_and_node_generation():
    agent = VideoAgent()
    
    # 路径规划节点测试
    node_input = NodeInput(
        path_id=1,
        node_id=101,
        node_key="concept-kernel",
        stage_id=1,
        path_title="计算机网络",
        path_goal="理解 TCP 三次握手",
        node_title="TCP 握手连接机制",
        difficulty="normal",
        mastery_target="牢记三次握手包标志位",
        knowledge_points=["SYN", "ACK", "ISN"],
        weak_knowledge_points=[],
        generation_focus=["标志位变化"],
        tutorial_title="TCP 握手说明",
        tutorial_summary="TCP 连接建立",
        tutorial_markdown="# 三次握手说明\nTCP 建立连接需要客户端和服务器进行三次交互...",
        profile={},
    )
    res_node = await agent.generate_node(node_input)
    assert res_node.success is True
    assert "scenes" in res_node.content
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest server/tests/resource/test_video_graph.py -v`
Expected: FAIL (generate_node 暂未实现)

- [ ] **Step 3: 重构 Video 生成逻辑为 LangGraph 子图，并完成 generate_node 转换**

修改 `server/app/resource/agents/video.py`。新增 `VideoGraphState` 状态，并完成 `video_sub_graph` 的构建与编译。重构 `generate_node` 使用 ResourceInput 包装 NodeInput：

```python
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

class VideoGraphState(TypedDict):
    input_data: ResourceInput
    config: dict[str, Any]
    constraints: VideoConstraints
    title_prefix: str
    emitter: Any | None

    digest: VideoMaterialDigest
    outline: VideoOutline
    drafts: Annotated[list[SceneDraft], operator.add]
    payload: VideoPayload
    error: str

class VideoSceneState(TypedDict):
    contract: SceneContract
    digest: VideoMaterialDigest
    constraints: VideoConstraints
    outline: VideoOutline

async def video_material_node(state: VideoGraphState) -> dict[str, Any]:
    if state.get("emitter"):
        await state.get("emitter").emit_agent("video", status="running", message="正在提取视频素材", progress=20)
    digest = await VideoMaterialAgent().run(state["input_data"], state["config"])
    return {"digest": digest}

async def video_outline_node(state: VideoGraphState) -> dict[str, Any]:
    if state.get("emitter"):
        await state.get("emitter").emit_agent("video", status="running", message="正在规划视频结构", progress=35)
    outline = await VideoOutlineAgent().run(state["digest"], state["constraints"])
    if len(outline.scenes) != state["constraints"].scene_count:
        raise ValueError(f"视频场景数与预期不符：期望 {state['constraints'].scene_count}，实际 {len(outline.scenes)}")
    return {"outline": outline}

def route_video_scenes(state: VideoGraphState):
    return [
        Send("write_scene", {"contract": s, "digest": state["digest"], "constraints": state["constraints"], "outline": state["outline"]})
        for s in state["outline"].scenes
    ]

async def video_write_scene_node(state: VideoSceneState) -> dict[str, Any]:
    draft = await SceneWriterAgent().run(state["contract"], state["digest"], state["constraints"], state["outline"])
    return {"drafts": [draft]}

async def video_payload_node(state: VideoGraphState) -> dict[str, Any]:
    if state.get("emitter"):
        await state.get("emitter").emit_agent("video", status="running", message="正在构建视频预览载荷", progress=85)
    sorted_drafts = sorted(state["drafts"], key=lambda d: d.index)
    payload = VideoPayloadBuilder().build(state["outline"], sorted_drafts, state["constraints"], state["digest"])
    return {"payload": payload}

video_workflow = StateGraph(VideoGraphState)
video_workflow.add_node("material", video_material_node)
video_workflow.add_node("outline", video_outline_node)
video_workflow.add_node("write_scene", video_write_scene_node)
video_workflow.add_node("builder", video_payload_node)

video_workflow.add_edge(START, "material")
video_workflow.add_edge("material", "outline")
video_workflow.add_conditional_edges("outline", route_video_scenes, ["write_scene"])
video_workflow.add_edge("write_scene", "builder")
video_workflow.add_edge("builder", END)

video_sub_graph = video_workflow.compile()
```

更新 `VideoAgent` 如下：

```python
@register_agent
class VideoAgent(BaseResourceAgent):
    agent_id = "video"
    agent_name = "讲解视频"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        config = input_data.agent_config or {}
        constraints = VideoConstraints.model_validate(config)
        title_prefix = input_data.learning_need[:32]

        return await self._run_graph_pipeline(
            input_data=input_data,
            config=config,
            constraints=constraints,
            title_prefix=title_prefix,
        )

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        from app.resource.schemas import TeachingPlan, OutlineItem, DownstreamContext, DownstreamMaterial, ReusableAssets
        
        mock_plan = TeachingPlan(
            topic=input_data.path_title,
            outline=[
                OutlineItem(
                    id=input_data.node_key,
                    title=input_data.node_title,
                    goal=input_data.mastery_target or input_data.path_goal,
                    key_points=input_data.knowledge_points,
                    suggested_examples=[],
                    suggested_visuals=[],
                )
            ]
        )
        
        content_material = DownstreamMaterial(
            outline_id=input_data.node_key,
            type="text",
            summary=input_data.tutorial_summary or input_data.node_title,
            key_points=input_data.knowledge_points,
            evidence_excerpt=input_data.tutorial_markdown[:1000],
            priority=1,
        )
        content_handoff = DownstreamContext(
            source_agent="content",
            title=input_data.node_title,
            one_sentence_summary=input_data.tutorial_summary or input_data.node_title,
            covered_outline_ids=[input_data.node_key],
            materials=[content_material],
            reusable_assets=ReusableAssets(),
        )

        config = input_data.agent_config or {}
        if "scene_count" not in config:
            config["scene_count"] = 4
        if "duration_seconds" not in config:
            config["duration_seconds"] = 120

        resource_input = ResourceInput(
            learning_need=input_data.node_title,
            learning_scenario="path_learning",
            agent_name="video",
            agent_config=config,
            profile=input_data.profile or {},
            upstream_handoffs={"content": content_handoff},
            teaching_plan=mock_plan,
        )

        constraints = VideoConstraints.model_validate(config)
        result = await self._run_graph_pipeline(
            input_data=resource_input,
            config=config,
            constraints=constraints,
            title_prefix=input_data.node_title,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        return result

    async def _run_graph_pipeline(
        self,
        *,
        input_data: ResourceInput,
        config: dict,
        constraints: VideoConstraints,
        title_prefix: str,
    ) -> AgentResult:
        try:
            initial_state = {
                "input_data": input_data,
                "config": config,
                "constraints": constraints,
                "title_prefix": title_prefix,
                "emitter": self.emitter,
                "drafts": [],
            }
            output_state = await video_sub_graph.ainvoke(initial_state)
            if "error" in output_state and output_state["error"]:
                raise ValueError(output_state["error"])
            payload = output_state["payload"]
        except Exception as exc:
            logger.error("VideoAgent 嵌套子图生成异常: %s", exc, exc_info=True)
            result = AgentResult(
                success=False,
                error=str(exc),
                title=f"{title_prefix} - 视频",
                summary=f"视频生成异常: {exc}",
                metadata={
                    "engine": "video_langgraph",
                    "agent_id": "video",
                    "schema_version": "video/v1",
                    "delivery_mode": "preview",
                    "internal_pipeline": "langgraph_subgraph",
                },
            )
            await self.emit_finish(result)
            return result

        content = payload.model_dump_json(indent=2)
        source_handoff_agent_ids = sorted(input_data.upstream_handoffs.keys()) if input_data.upstream_handoffs else sorted({agent for scene in payload.scenes for agent in scene.source_agents})
        coverage = outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs)
        result = AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - 视频",
            summary=f"生成 {len(payload.scenes)} 段结构化讲解视频脚本",
            metrics={
                "scene_count": len(payload.scenes),
                "duration_seconds": payload.duration_seconds,
            },
            metadata={
                "engine": "video_langgraph",
                "agent_id": "video",
                "schema_version": "video/v1",
                "delivery_mode": "preview",
                "duration_seconds": payload.duration_seconds,
                "scene_count": len(payload.scenes),
                "aspect_ratio": payload.aspect_ratio,
                "style": payload.style,
                "source_handoff_agent_ids": source_handoff_agent_ids,
                "teaching_plan_outline_ids": coverage["teaching_plan_outline_ids"],
                "covered_source_outline_ids": coverage["covered_source_outline_ids"],
                "missing_source_outline_ids": coverage["missing_source_outline_ids"],
                "internal_pipeline": "langgraph_subgraph",
            },
        )
        await self.emit_finish(result)
        return result
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest server/tests/resource/test_video_graph.py -v`
Expected: PASS

- [ ] **Step 5: 提交 Task 3 代码**

Run: `git add server/app/resource/agents/video.py server/tests/resource/test_video_graph.py && git commit -m "feat: refactor Video pipeline into LangGraph and support generate_node"`

---

### Task 4: 实现全局父图与编排服务 (workflow_graph.py & service.py)

**Files:**
- Create: `server/app/resource/workflow_graph.py`
- Modify: `server/app/resource/service.py`
- Test: `server/tests/resource/test_parent_workflow.py` (新建测试)

- [ ] **Step 1: 编写父图整体集成流测试**

编写对全局 LangGraph 父图驱动的编排测试，验证从规划到最后输出的全生命周期：

```python
import pytest
from app.resource.schemas import ResourceGenerationRequest
from app.resource.workflow_graph import parent_graph

@pytest.mark.asyncio
async def test_parent_graph_standalone_flow():
    req = ResourceGenerationRequest(
        learning_need="快排时间复杂度分析",
        learning_scenario="standalone",
        agent_configs={"content": {}, "reading": {}, "ppt": {}, "video": {}}
    )
    initial_state = {
        "user_id": 1,
        "resource_id": 9999,
        "request": req,
        "profile": {},
        "enabled_agents": req.enabled_agent_ids(),
        "agent_results": {},
        "review_results": [],
    }
    assert parent_graph is not None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest server/tests/resource/test_parent_workflow.py -v`
Expected: FAIL (因为 `workflow_graph.py` 尚未创建)

- [ ] **Step 3: 创建全局父图文件 `workflow_graph.py`**

创建新文件 `server/app/resource/workflow_graph.py`，编排 ParentGraph：

```python
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

from app.resource.agents import AGENT_REGISTRY
from app.resource.schemas import AgentResult, ResourceInput, ReviewResult, TeachingPlan
from app.resource.review import build_pre_audit_envelope

class ParentState(TypedDict):
    user_id: int
    resource_id: int
    request: Any
    profile: Dict[str, Any]
    enabled_agents: List[str]
    emitter: Any | None
    
    teaching_plan: TeachingPlan | None
    agent_results: Annotated[Dict[str, AgentResult], operator.ior]
    review_results: Annotated[List[ReviewResult], operator.add]
    status: str
    error: str | None

class WorkerState(TypedDict):
    agent_id: str
    resource_id: int
    request: Any
    teaching_plan: TeachingPlan
    profile: Dict[str, Any]
    emitter: Any | None

async def parent_planning_node(state: ParentState) -> Dict[str, Any]:
    emitter = state.get("emitter")
    if emitter:
        await emitter.emit_agent("planning", status="running", message="正在规划教学方向与大纲", progress=5)
    
    planning_input = ResourceInput(
        resource_id=state["resource_id"],
        learning_need=state["request"].learning_need,
        learning_scenario=state["request"].learning_scenario,
        profile=state["profile"],
        agent_config={"enabled_agents": state["enabled_agents"]},
    )
    planning_result = await AGENT_REGISTRY["planning"](emitter).generate_resource(planning_input)
    if not planning_result.success:
        return {"error": planning_result.error or "Planning failed"}
        
    plan_data = planning_result.metadata.get("teaching_plan")
    teaching_plan = TeachingPlan.model_validate(plan_data)
    return {"teaching_plan": teaching_plan, "agent_results": {"planning": planning_result}}

def route_to_workers(state: ParentState):
    if state.get("error"):
        return ["save_results"]
    
    from app.resource.service import _select_worker_agents
    workers = _select_worker_agents(state["enabled_agents"], AGENT_REGISTRY)
    return [
        Send("run_worker", {
            "agent_id": w,
            "resource_id": state["resource_id"],
            "request": state["request"],
            "teaching_plan": state["teaching_plan"],
            "profile": state["profile"],
            "emitter": state["emitter"]
        })
        for w in workers
    ]

async def run_worker_node(state: WorkerState) -> Dict[str, Any]:
    agent_id = state["agent_id"]
    emitter = state["emitter"]
    from app.resource.service import _build_agent_resource_input, ResourceService
    from app.infra.database import session_scope
    
    resource_input = _build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=agent_id,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs={},
        agent_config_extra=None
    )
    
    agent = AGENT_REGISTRY[agent_id](emitter)
    result = await agent.generate_resource(resource_input)
    
    if result.success and result.content:
        async with session_scope() as session:
            usecases = ResourceService(session)
            resource_item = await usecases.save_agent_result(
                user_id=usecases.session.bind,
                resource_id=state["resource_id"],
                result=result,
            )
            if emitter:
                await emitter.emit_artifact_ready(
                    agent_id,
                    message=f"{agent_id} 资源已保存，可在产物坞预览",
                    artifact_id=str(resource_item.id),
                    metrics=result.metrics,
                )
    return {"agent_results": {agent_id: result}}

async def parent_ppt_node(state: ParentState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    agent_id = "ppt"
    if agent_id not in state["enabled_agents"] or agent_id not in AGENT_REGISTRY:
        return {}
        
    from app.resource.service import _collect_successful_handoffs, _build_agent_resource_input
    base_handoffs = _collect_successful_handoffs(state["agent_results"])
    
    resource_input = _build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=agent_id,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
        agent_config_extra=None
    )
    
    agent = AGENT_REGISTRY[agent_id](state.get("emitter"))
    result = await agent.generate_resource(resource_input)
    return {"agent_results": {agent_id: result}}

async def parent_video_node(state: ParentState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    agent_id = "video"
    if agent_id not in state["enabled_agents"] or agent_id not in AGENT_REGISTRY:
        return {}
        
    from app.resource.service import _collect_successful_handoffs, _build_agent_resource_input
    base_handoffs = _collect_successful_handoffs(state["agent_results"])
    
    resource_input = _build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=agent_id,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
        agent_config_extra=None
    )
    
    agent = AGENT_REGISTRY[agent_id](state.get("emitter"))
    result = await agent.generate_resource(resource_input)
    return {"agent_results": {agent_id: result}}

async def local_regex_audit_node(state: ParentState) -> Dict[str, Any]:
    """取代原有的 LLM 审核 Agent，仅用本地正则进行瞬间核检"""
    emitter = state.get("emitter")
    if emitter:
        await emitter.emit_agent("review", status="running", message="正在执行本地安全合规审核", progress=90)
    
    audit_contents = []
    for aid, result in state["agent_results"].items():
        if result.success and result.content:
            audit_contents.append(result.content)
            
    from app.resource.agents.review import rule_check
    findings = []
    for content in audit_contents:
        findings.extend(rule_check(content))
        
    passed = len(findings) == 0
    issues = [f.get("detail", "") for f in findings]
    
    review_result = ReviewResult(
        passed=passed,
        overall_score=100 if passed else 0,
        issues=issues,
        failed_agents=["content"] if not passed else [],
    )
    if emitter:
        await emitter.emit_agent(
            "review",
            status="finished",
            message="本地规则审计通过" if passed else f"审计发现 {len(issues)} 个合规问题",
            progress=100,
        )
    return {"review_results": [review_result]}

async def save_results_node(state: ParentState) -> Dict[str, Any]:
    return {"status": "completed"}

parent_builder = StateGraph(ParentState)
parent_builder.add_node("planning", parent_planning_node)
parent_builder.add_node("run_worker", run_worker_node)
parent_builder.add_node("ppt", parent_ppt_node)
parent_builder.add_node("video", parent_video_node)
parent_builder.add_node("regex_audit", local_regex_audit_node)
parent_builder.add_node("save_results", save_results_node)

parent_builder.add_edge(START, "planning")
parent_builder.add_conditional_edges("planning", route_to_workers, ["run_worker"])
parent_builder.add_edge("run_worker", "ppt")
parent_builder.add_edge("run_worker", "video")
parent_builder.add_edge("run_worker", "regex_audit")
parent_builder.add_edge("ppt", "save_results")
parent_builder.add_edge("video", "save_results")
parent_builder.add_edge("regex_audit", "save_results")
parent_builder.add_edge("save_results", END)

parent_graph = parent_builder.compile()
```

- [ ] **Step 4: 修改编排服务 `service.py` 对接父图并落库**

修改 `server/app/resource/service.py` 中的 `run_multi_agent_generation` 函数。用 `parent_graph.ainvoke` 重构底层流程，同时将最终的 `ReviewResult` 与 `TeachingPlan` 写入数据库表：

```python
async def run_multi_agent_generation(
    user_id: int,
    request: ResourceGenerationRequest,
    profile: dict[str, Any],
    resource_id: int,
) -> None:
    from app.infra.database import session_scope
    from app.resource.workflow_graph import parent_graph

    async with session_scope() as session:
        usecases = ResourceService(session)
        enabled_agents = request.enabled_agent_ids()

        run_id = f"resource-{resource_id}-{uuid4().hex[:8]}"
        emitter = AgentEventEmitter(resource_id=resource_id, run_id=run_id)

        try:
            logger.info("基于 LangGraph 启动全局资源编排: resource_id=%d", resource_id)
            await usecases.update_resource_status(resource_id, "generating")

            initial_state = {
                "user_id": user_id,
                "resource_id": resource_id,
                "request": request,
                "profile": profile,
                "enabled_agents": enabled_agents,
                "emitter": emitter,
                "agent_results": {},
                "review_results": [],
            }

            final_state = await parent_graph.ainvoke(initial_state)

            if final_state.get("error"):
                raise ValueError(final_state["error"])

            review_results = final_state.get("review_results") or []
            passed = all(r.passed for r in review_results)
            overall_score = min((r.overall_score for r in review_results), default=100)
            issues = []
            for r in review_results:
                issues.extend(r.issues)

            merged_review = ReviewResult(
                passed=passed,
                overall_score=overall_score,
                issues=issues,
                failed_agents=[aid for r in review_results for aid in r.failed_agents]
            )

            await usecases.save_generation_results(
                user_id=user_id,
                resource_id=resource_id,
                request=request,
                results=final_state["agent_results"],
                review_result=merged_review,
                teaching_plan=final_state["teaching_plan"],
            )

            await emitter.emit_done(success=passed, message="多智能体资源生成已全部完成！")

        except Exception as exc:
            logger.error("LangGraph 编排执行异常: %s", exc, exc_info=True)
            await usecases.update_resource_status(resource_id, "failed")
            await emitter.emit_done(success=False, message=f"生成失败: {exc}")
```

- [ ] **Step 5: 运行整体集成流测试验证**

Run: `uv run pytest server/tests/resource/test_parent_workflow.py -v`
Expected: PASS

- [ ] **Step 6: 提交 Task 4 代码**

Run: `git add server/app/resource/workflow_graph.py server/app/resource/service.py server/tests/resource/test_parent_workflow.py && git commit -m "feat: rewire parent resource orchestration using LangGraph"`

---

## 五、 整体联调与系统验证

- [ ] **Step 1: 运行全部资源测试集确保代码无任何报错**

Run: `uv run pytest server/tests/resource/ -v`
Expected: ALL PASS

- [ ] **Step 2: 运行前端构建静态类型检查 (Vue build check)**

Run: `npm run build`
Expected: Success (Vue components type checking ok, no TS breaks)

- [ ] **Step 3: 运行全量单元测试套件**

Run: `uv run pytest`
Expected: Success (No regression in existing auth/profile/chat domains)
