from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


def test_resource_modules_import() -> None:
    import app.main  # noqa: F401
    import app.resource.api  # noqa: F401
    import app.resource.service  # noqa: F401


def test_resource_request_enabled_agent_ids_are_stable() -> None:
    from app.resource.schemas import ResourceGenerationRequest

    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "学习机器学习中的过拟合与正则化",
            "selected_agents": [
                {"agent_id": "quiz", "enabled": True, "priority": 2},
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "code", "enabled": False, "priority": 1},
            ],
            "agent_configs": {"content": {"depth_level": "deep"}},
        }
    )

    assert request.enabled_agent_ids() == ["content", "quiz"]


def test_agent_meta_is_single_source_for_runtime_contract() -> None:
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.schemas import AGENT_DEFAULT_ENABLED, AGENT_DEFAULT_ORDER, AGENT_META

    assert {"content", "mindmap", "quiz", "code", "reading", "ppt"} <= set(AGENT_META)
    worker_agents = {key for key in AGENT_REGISTRY if key not in {"planning", "review"}}
    assert set(AGENT_DEFAULT_ORDER) == worker_agents
    for agent_id in AGENT_DEFAULT_ENABLED:
        assert agent_id in AGENT_REGISTRY


def test_agent_classes_all_have_run_method() -> None:
    from app.resource.agents import AGENT_REGISTRY

    for agent_id, agent_cls in AGENT_REGISTRY.items():
        assert hasattr(agent_cls, "run"), f"{agent_id} Agent 缺少 run 方法"


def test_pre_audit_envelope_excludes_completeness_only_resource_content() -> None:
    from app.resource.review import build_pre_audit_envelope
    from app.resource.schemas import ResourceGenerationRequest, WorkerResult

    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "学习操作系统进程调度",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "quiz", "enabled": True, "priority": 1},
                {"agent_id": "mindmap", "enabled": True, "priority": 2},
                {"agent_id": "code", "enabled": True, "priority": 3},
                {"agent_id": "reading", "enabled": True, "priority": 4},
                {"agent_id": "ppt", "enabled": True, "priority": 5},
            ],
        }
    )
    results = {
        "content": WorkerResult(success=True, content="# 专业课程", title="课程", summary="课程摘要", metadata={"agent_id": "content"}),
        "reading": WorkerResult(success=True, content="# 拓展阅读", title="阅读", summary="阅读摘要", metadata={"agent_id": "reading"}),
        "quiz": WorkerResult(success=True, content="题库正文不应进入审核", title="题库", metadata={"agent_id": "quiz"}),
        "mindmap": WorkerResult(success=True, content="思维导图正文不应进入审核", title="思维导图", metadata={"agent_id": "mindmap"}),
        "code": WorkerResult(success=True, content="代码实操正文不应进入审核", title="代码实操", metadata={"agent_id": "code"}),
    }

    envelope, missing = build_pre_audit_envelope(
        request=request,
        results=results,
        profile={"profile_markdown": "学习者画像"},
        blueprint=None,
    )

    assert missing == []
    assert envelope["mode"] == "pre_audit"
    assert [item["agent_id"] for item in envelope["deep_audit_resources"]] == ["content", "reading"]
    assert [item["agent_id"] for item in envelope["completeness_only"]] == ["quiz", "mindmap", "code"]
    envelope_text = str(envelope)
    assert "题库正文不应进入审核" not in envelope_text
    assert "思维导图正文不应进入审核" not in envelope_text
    assert "代码实操正文不应进入审核" not in envelope_text


def test_pre_audit_envelope_reports_missing_selected_resources() -> None:
    from app.resource.review import build_pre_audit_envelope
    from app.resource.schemas import ResourceGenerationRequest, WorkerResult

    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "学习 TCP",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "reading", "enabled": True, "priority": 1},
                {"agent_id": "quiz", "enabled": True, "priority": 2},
            ],
        }
    )
    results = {
        "content": WorkerResult(success=True, content="# TCP", title="课程", metadata={"agent_id": "content"}),
        "reading": WorkerResult(success=True, content="", title="阅读", metadata={"agent_id": "reading"}),
        "quiz": WorkerResult(success=False, content="", title="题库", metadata={"agent_id": "quiz"}),
    }

    envelope, missing = build_pre_audit_envelope(
        request=request,
        results=results,
        profile={},
        blueprint=None,
    )

    assert missing == ["reading", "quiz"]
    assert envelope["completeness_only"] == [{"agent_id": "quiz", "title": "题库", "summary": "", "has_content": False}]


def test_ppt_audit_envelope_reviews_only_ppt_with_approved_sources() -> None:
    from app.resource.review import build_ppt_audit_envelope
    from app.resource.schemas import ResourceGenerationRequest, WorkerResult

    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "学习数据库事务",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "reading", "enabled": True, "priority": 1},
                {"agent_id": "ppt", "enabled": True, "priority": 2},
                {"agent_id": "quiz", "enabled": True, "priority": 3},
            ],
        }
    )
    results = {
        "content": WorkerResult(success=True, content="# 事务课程", title="课程", metadata={"agent_id": "content"}),
        "reading": WorkerResult(success=True, content="# 事务阅读", title="阅读", metadata={"agent_id": "reading"}),
        "ppt": WorkerResult(success=True, content='{"slides":[]}', title="PPT", summary="PPT 摘要", metadata={"agent_id": "ppt"}),
        "quiz": WorkerResult(success=True, content="题库正文不应进入 PPT 审核", title="题库", metadata={"agent_id": "quiz"}),
    }

    envelope, missing = build_ppt_audit_envelope(
        request=request,
        results=results,
        profile={},
        blueprint=None,
    )

    assert missing == []
    assert envelope["mode"] == "ppt_audit"
    assert envelope["ppt_resource"]["agent_id"] == "ppt"
    assert [item["agent_id"] for item in envelope["approved_sources"]] == ["content", "reading"]
    assert "题库正文不应进入 PPT 审核" not in str(envelope)


@pytest.mark.asyncio
async def test_review_agent_maps_json_status_to_worker_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.resource.agents import review as review_module
    from app.resource.agents.review import ReviewAgent
    from app.resource.schemas import WorkerState

    emitted_agents: list[tuple[tuple, dict]] = []

    class FakeEmitter:
        async def emit_agent(self, *args, **kwargs):
            emitted_agents.append((args, kwargs))

    class FakeLLM:
        async def ainvoke(self, *args, **kwargs):
            return SimpleNamespace(
                content='{"status":"needs_revision","checks":{"safety":"fail"},"violations":["unsafe"],"revision_targets":["content"]}'
            )

    monkeypatch.setattr(review_module, "get_llm", lambda: FakeLLM())
    agent = ReviewAgent(emitter=FakeEmitter())

    result = await agent.run(
        WorkerState(
            learning_need="学习安全审计",
            agent_config={
                "progress_agent_id": "pre_review",
                "review_envelope": {
                    "mode": "pre_audit",
                    "deep_audit_resources": [{"agent_id": "content", "audit_content": "存在风险"}],
                },
            },
        )
    )

    assert result.success is False
    assert result.metadata["review_status"] == "needs_revision"
    assert result.metadata["parsed_review"]["revision_targets"] == ["content"]
    assert emitted_agents[-1][0][0] == "pre_review"
    assert emitted_agents[-1][1]["status"] == "failed"


@pytest.mark.asyncio
async def test_run_multi_agent_generation_runs_ppt_only_after_pre_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.infra import database as database_module
    from app.resource import agents as agents_module
    from app.resource import service as service_module
    from app.resource.schemas import ResourceGenerationRequest, WorkerResult

    calls: list[str] = []
    persisted: dict[str, WorkerResult] = {}
    saved_review = None
    service_instances = []

    class FakeSessionScope:
        async def __aenter__(self):
            return SimpleNamespace()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeService(service_module.ResourceService):
        def __init__(self, session):
            self.status = "completed"
            self._write_locks = {}
            service_instances.append(self)

        async def save_worker_result(self, *, resource_id, user_id, result):
            persisted[result.metadata["agent_id"]] = result
            return SimpleNamespace(id=len(persisted), agent_type=result.metadata["agent_id"])

        async def results_for_review(self, user_id, resource_id, failures):
            return {**persisted, **failures}

        async def save_generation_results(self, *, user_id, resource_id, request, results, review_result, plan):
            nonlocal saved_review
            saved_review = review_result
            self.status = "completed" if review_result.passed else "partial_completed"

        async def list_resource_items(self, user_id, resource_id):
            return [SimpleNamespace(id=index, agent_type=agent_id) for index, agent_id in enumerate(persisted, start=1)]

        async def get_resource(self, user_id, resource_id):
            return SimpleNamespace(status=self.status)

        async def update_resource_status(self, resource_id, status):
            self.status = status

    class FakePlanningAgent:
        def __init__(self, emitter=None):
            self.emitter = emitter

        async def run(self, state):
            calls.append("planning")
            return WorkerResult(success=True, metadata={})

    class FakeWorkerAgent:
        def __init__(self, emitter=None, agent_id=""):
            self.emitter = emitter
            self.agent_id = agent_id

        async def run(self, state):
            if self.agent_id == "ppt":
                assert state.agent_config["approved_sources"][0]["agent_id"] == "content"
            calls.append(self.agent_id)
            return WorkerResult(
                success=True,
                content=f"{self.agent_id} content",
                file_type="json" if self.agent_id == "ppt" else "markdown",
                title=self.agent_id,
                summary=self.agent_id,
                metadata={"agent_id": self.agent_id},
            )

    class FakeReviewAgent:
        def __init__(self, emitter=None):
            self.emitter = emitter

        async def run(self, state):
            mode = state.agent_config["review_envelope"]["mode"]
            calls.append(f"review:{mode}")
            return WorkerResult(
                success=True,
                content='{"status":"pass","checks":{},"violations":[],"revision_targets":[]}',
                file_type="json",
                metadata={
                    "agent_id": "review",
                    "review_status": "pass",
                    "parsed_review": {
                        "status": "pass",
                        "checks": {},
                        "violations": [],
                        "revision_targets": [],
                    },
                },
            )

    def worker_factory(agent_id: str):
        return type(
            f"Fake{agent_id.title()}Agent",
            (FakeWorkerAgent,),
            {"__init__": lambda self, emitter=None, agent_id=agent_id: FakeWorkerAgent.__init__(self, emitter, agent_id)},
        )

    fake_registry = {
        "planning": FakePlanningAgent,
        "content": worker_factory("content"),
        "reading": worker_factory("reading"),
        "quiz": worker_factory("quiz"),
        "ppt": worker_factory("ppt"),
        "review": FakeReviewAgent,
    }
    monkeypatch.setattr(database_module, "session_scope", lambda: FakeSessionScope())
    monkeypatch.setattr(service_module, "ResourceService", FakeService)
    monkeypatch.setattr(agents_module, "AGENT_REGISTRY", fake_registry)

    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "学习数据库事务",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "reading", "enabled": True, "priority": 1},
                {"agent_id": "quiz", "enabled": True, "priority": 2},
                {"agent_id": "ppt", "enabled": True, "priority": 3},
            ],
        }
    )

    await service_module.run_multi_agent_generation(
        user_id=1,
        request=request,
        profile={},
        resource_id=123,
    )

    assert service_instances
    assert saved_review is not None
    assert saved_review.passed is True
    ppt_index = calls.index("ppt")
    ppt_review_index = calls.index("review:ppt_audit")
    assert calls.index("content") < ppt_index
    assert calls.index("reading") < ppt_index
    assert calls.index("quiz") < ppt_index
    assert ppt_index < ppt_review_index
    assert "review:pre_audit" in calls
    assert "review:ppt_audit" in calls


@pytest.mark.asyncio
async def test_resource_service_get_resource_bundle_rebuilds_saved_generation_result() -> None:
    from app.resource.service import ResourceService

    class FakeService(ResourceService):
        def __init__(self):
            self.resource = SimpleNamespace(
                id=88,
                user_id=1,
                learning_need="复习 TCP",
                selected_agents=["content"],
                status="completed",
                personalization={
                    "review_result": {"passed": True, "overall_score": 91},
                    "failed_agents": [],
                },
                created_at=None,
                updated_at=None,
            )
            self.items = [
                SimpleNamespace(
                    id=1001,
                    agent_type="content",
                    status="completed",
                    error_message=None,
                    created_at=None,
                    updated_at=None,
                    content_format="markdown",
                    title="TCP 课程内容",
                    summary="讲解 TCP",
                    content_json={
                        "title": "TCP 课程内容",
                        "summary": "讲解 TCP",
                        "summary_data": {"keywords": ["TCP"]},
                        "metadata": {"agent_id": "content"},
                        "format": "markdown",
                        "content": "# TCP",
                    },
                    content_text="# TCP",
                    metadata_json={"agent_id": "content"},
                    execution_report=None,
                )
            ]

        async def get_resource(self, user_id, resource_id, *, allowed_sources=None):
            return self.resource if user_id == 1 and resource_id == 88 else None

        async def list_resource_items(self, user_id, resource_id):
            return self.items if user_id == 1 and resource_id == 88 else []

    bundle = await FakeService().get_resource_bundle(user_id=1, resource_id=88)

    assert bundle is not None
    assert bundle.id == "88"
    assert bundle.resources[0].title == "TCP 课程内容"
    assert bundle.resources[0].content == "# TCP"
    assert bundle.resources[0].status == "completed"
    assert bundle.review_result.overall_score == 91


@pytest.mark.asyncio
async def test_code_agent_consumes_current_frontend_config_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.resource.agents import code as code_module
    from app.resource.agents.code import CodeAgent
    from app.resource.schemas import WorkerState

    captured_prompt = ""

    class FakeLLM:
        async def ainvoke(self, prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return SimpleNamespace(content="# Demo\n```go\npackage main\n```")

    monkeypatch.setattr(code_module, "get_llm", lambda: FakeLLM())
    result = await CodeAgent().run(
        WorkerState(
            learning_need="学习 goroutine",
            agent_config={"programming_language": "go", "case_type": "debug_demo", "difficulty": "advanced"},
        )
    )

    assert result.success is True
    assert "- programming_language: go" in captured_prompt
    assert "- case_type: debug_demo" in captured_prompt
    assert "- difficulty: advanced" in captured_prompt
    assert result.metadata["language"] == "go"


@pytest.mark.asyncio
async def test_reading_agent_returns_json_payload_for_frontend(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.resource.agents import reading as reading_module
    from app.resource.agents.reading import ReadingAgent, ReadingPayload
    from app.resource.schemas import WorkerState

    class FakeLLM:
        async def ainvoke_json(self, schema, prompt, **kwargs):
            assert schema is ReadingPayload
            assert "- reading_depth: frontier" in prompt
            assert "- max_items: 2" in prompt
            return ReadingPayload.model_validate(
                {
                    "title": "阅读推荐",
                    "summary": "两条资源",
                    "resources": [
                        {"id": "R1", "type": "documentation", "title": "官方文档"},
                        {"id": "R2", "type": "article", "title": "技术文章"},
                    ],
                }
            )

    monkeypatch.setattr(reading_module, "get_llm", lambda: FakeLLM())
    result = await ReadingAgent().run(
        WorkerState(
            learning_need="学习 TCP",
            agent_config={"reading_depth": "frontier", "max_items": 2, "language_preference": "english"},
        )
    )

    assert result.success is True
    assert result.file_type == "json"
    assert len(json.loads(result.content)["resources"]) == 2
    assert result.metadata["reading_depth"] == "frontier"


def test_ppt_receives_all_upstream_artifacts_in_material_bundle():
    """PPT material_bundle includes all successful upstream worker results."""
    from app.resource.agents.ppt_sources import build_material_bundle
    from app.resource.agents.ppt_models import MaterialBundle
    from app.resource.schemas import WorkerResult

    results = {
        "content": WorkerResult(
            success=True, content="课程内容" * 500,  # long content
            title="课程", summary="课程摘要",
            metadata={"agent_id": "content"},
        ),
        "mindmap": WorkerResult(
            success=True, content="思维导图",
            title="思维导图", metadata={"agent_id": "mindmap"},
        ),
        "quiz": WorkerResult(
            success=False, content="", error="生成失败",
            title="练习题", metadata={"agent_id": "quiz"},
        ),
        "code": WorkerResult(
            success=True, content="代码示例",
            title="代码", metadata={"agent_id": "code"},
        ),
    }

    bundle = build_material_bundle(
        learning_need="学习 TCP",
        learning_scenario="exam_prep",
        profile={"level": "intermediate"},
        results=results,
    )

    assert isinstance(bundle, MaterialBundle)
    assert bundle.learning_need == "学习 TCP"
    assert bundle.learning_scenario == "exam_prep"
    assert bundle.profile == {"level": "intermediate"}

    # All 4 agents present in artifacts
    assert "content" in bundle.artifacts
    assert "mindmap" in bundle.artifacts
    assert "quiz" in bundle.artifacts
    assert "code" in bundle.artifacts

    # Successful artifacts have content
    assert bundle.artifacts["content"].success is True
    assert bundle.artifacts["content"].content != ""
    # Content was bounded (original was 2000 chars, limit is 6000, so not truncated here)
    assert len(bundle.artifacts["content"].content) <= 6000

    assert bundle.artifacts["mindmap"].success is True
    assert bundle.artifacts["code"].success is True

    # Failed artifact has no content but is present
    assert bundle.artifacts["quiz"].success is False
    assert bundle.artifacts["quiz"].content == ""

    # Missing agents are not in artifacts
    assert "reading" not in bundle.artifacts


def test_material_bundle_bounds_content_to_limits():
    """Each artifact's content is truncated to its source limit."""
    from app.resource.agents.ppt_sources import build_material_bundle
    from app.resource.schemas import WorkerResult

    # Create content longer than the content limit (6000)
    long_content = "x" * 10000
    results = {
        "content": WorkerResult(
            success=True, content=long_content,
            title="课程", metadata={"agent_id": "content"},
        ),
    }

    bundle = build_material_bundle(
        learning_need="测试截断",
        results=results,
    )

    assert len(bundle.artifacts["content"].content) == 6000
    assert bundle.artifacts["content"].content == "x" * 6000
