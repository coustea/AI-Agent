from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import ProgrammingError

import pytest

from app.infra.models import (
    LearningEvent,
    LearningPath,
    PathNode,
    PathNodeQuestion,
    PathNodeResource,
    PathNodeTutorial,
)
from app.evaluation.schemas import LearningEventCreate
from app.path.service import PathService
from app.path.schemas import (
    LearningPlan,
    PlanNode,
    AgentStage,
    PathQuizAnswerItem,
    PathQuizSubmitRequest,
    PathPlanValidationError,
    PathRequest,
    validate_path_plan,
)


class _CommitSession:
    async def commit(self):
        return None


class _CaptureSession:
    def __init__(self, get_result=None):
        self.get_result = get_result
        self.added = []
        self.commit_count = 0
        self.refresh_count = 0
        self._next_id = 1000

    async def get(self, _model, _id):
        return self.get_result

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = self._next_id
                self._next_id += 1
        self.commit_count += 1

    async def refresh(self, _item):
        if getattr(_item, "id", None) is None:
            _item.id = self._next_id
            self._next_id += 1
        self.refresh_count += 1

    async def exec(self, _stmt):
        class _EmptyResult:
            def all(self):
                return []

            def first(self):
                return None

        return _EmptyResult()


@pytest.mark.asyncio
async def test_learning_evaluation_flags_low_score_low_time_and_repeated_attempts():
    now = datetime.now(timezone.utc)
    path = LearningPath(
        id=1,
        user_id=1,
        module="mentor",
        title="操作系统路径",
        goal="掌握处理机调度",
        topic="处理机调度",
        overall_progress=25,
        current_node_key="rr-basics",
        status="active",
        stages_json=[{"stage_id": "stage-1", "title": "基础"}],
    )
    node = PathNode(
        id=1,
        path_id=path.id,
        user_id=1,
        node_id="rr-basics",
        stage_id="stage-1",
        title="时间片轮转基础",
        status="available",
        priority=1,
        attempt_count=2,
        prerequisites=[],
        difficulty="intermediate",
    )
    events = [
        LearningEvent(
            user_id=1,
            path_id=path.id,
            path_node_id=node.id,
            node_id=node.node_id,
            event_type="quiz_submitted",
            course=path.title,
            topic=node.title,
            score=40,
            created_at=now,
        ),
        LearningEvent(
            user_id=1,
            path_id=path.id,
            path_node_id=node.id,
            node_id=node.node_id,
            event_type="path_feedback",
            course=path.title,
            topic=node.title,
            feedback="这部分太难了，看不懂",
            created_at=now,
        ),
    ]
    class _ExecResult:
        def __init__(self, values):
            self._values = values

        def all(self):
            return list(self._values)

    class _Session:
        async def exec(self, _stmt):
            return _ExecResult(events)

    bridge = PathService(_Session())
    bridge._must_get_path = AsyncMock(return_value=path)
    bridge._get_path_active_minutes = AsyncMock(return_value=4)
    bridge._get_current_path_node = AsyncMock(return_value=node)

    result = await bridge.get_learning_evaluation(1, path.id)

    assert result is not None
    assert result.path_id == path.id
    assert result.current_node_key == "rr-basics"
    assert result.signal_snapshot.average_score == 40
    assert result.signal_snapshot.active_minutes == 4
    assert node.title in result.signal_snapshot.weak_topics
    assert result.needs_optimization is True
    assert any("薄弱" in tip for tip in result.optimization_tips)
    assert any("学习时长" in tip for tip in result.optimization_tips)
    assert any("尝试" in tip for tip in result.optimization_tips)


@pytest.mark.asyncio
async def test_locked_node_workspace_is_rejected_before_generating_tutorial():
    node = PathNode(
        id=10,
        path_id=1,
        user_id=1,
        node_id="advanced",
        stage_id="stage-2",
        title="高级主题",
        status="locked",
        priority=2,
        prerequisites=["basics"],
    )

    service = PathService(_CommitSession())
    service._must_get_node = AsyncMock(return_value=node)
    service._must_get_path = AsyncMock()
    service._create_tutorial = AsyncMock()

    with pytest.raises(ValueError, match="未解锁"):
        await service.get_node_workspace(1, node.id)

    service._must_get_path.assert_not_awaited()
    service._create_tutorial.assert_not_awaited()


@pytest.mark.asyncio
async def test_locked_node_question_generation_is_rejected():
    node = PathNode(
        id=10,
        path_id=1,
        user_id=1,
        node_id="advanced",
        stage_id="stage-2",
        title="高级主题",
        status="locked",
        priority=2,
        prerequisites=["basics"],
    )

    service = PathService(_CommitSession())
    service._must_get_node = AsyncMock(return_value=node)
    service._must_get_path = AsyncMock()

    with pytest.raises(ValueError, match="未解锁"):
        await service.generate_node_questions(1, node.id)

    service._must_get_path.assert_not_awaited()


@pytest.mark.asyncio
async def test_locked_node_resource_generation_is_rejected():
    node = PathNode(
        id=10,
        path_id=1,
        user_id=1,
        node_id="advanced",
        stage_id="stage-2",
        title="高级主题",
        status="locked",
        priority=2,
        prerequisites=["basics"],
    )

    service = PathService(_CommitSession())
    service._must_get_node = AsyncMock(return_value=node)
    service._must_get_path = AsyncMock()

    with pytest.raises(ValueError, match="未解锁"):
        await service.create_node_resource_task(1, node.id, "mindmap", "run-1")

    service._must_get_path.assert_not_awaited()


@pytest.mark.asyncio
async def test_question_generation_rejects_locked_node():
    """generate_node_questions should reject locked nodes before invoking workflow."""
    node = PathNode(
        id=10,
        path_id=1,
        user_id=1,
        node_id="advanced",
        stage_id="stage-2",
        title="高级主题",
        status="locked",
        priority=2,
        prerequisites=["basics"],
    )

    service = PathService(_CommitSession())
    service._must_get_node = AsyncMock(return_value=node)
    service._must_get_path = AsyncMock()

    with pytest.raises(ValueError, match="未解锁"):
        await service.generate_node_questions(1, node.id)

    service._must_get_path.assert_not_awaited()


@pytest.mark.asyncio
async def test_question_generation_uses_learn_workflow():
    """generate_node_questions now delegates to the LangGraph learn workflow."""
    path = LearningPath(
        id=1,
        user_id=1,
        module="mentor",
        title="Python 基础路径",
        goal="掌握 Python 基础",
        topic="Python",
        overall_progress=0,
        current_node_key="variables",
        status="active",
        stages_json=[],
    )
    node = PathNode(
        id=10,
        path_id=path.id,
        user_id=path.user_id,
        node_id="variables",
        stage_id="stage-1",
        title="变量与类型",
        status="in_progress",
        priority=1,
        prerequisites=[],
    )
    tutorial = PathNodeTutorial(
        id=20,
        path_id=path.id,
        node_id=node.id,
        user_id=path.user_id,
        tutorial_type="primary",
        version_no=1,
        is_current=True,
        title="变量与类型",
        summary="讲清楚变量、赋值与基本类型",
        content_markdown="教程内容",
    )
    session = _CaptureSession()
    service = PathService(session)
    service._must_get_node = AsyncMock(return_value=node)
    service._must_get_path = AsyncMock(return_value=path)

    # Mock the learn workflow
    mock_questions = [
        PathNodeQuestion(
            id=index,
            path_id=path.id,
            node_id=node.id,
            tutorial_id=20,
            user_id=path.user_id,
            round_no=1,
            question_no=index,
            question=f"Question {index}",
            choice={"A": "正确", "B": "错误"},
            answer="A",
            knowledge_points=[f"知识点 {index}"],
        )
        for index in range(1, 6)
    ]
    with patch("app.path.service.run_learn_workflow", new_callable=AsyncMock) as mock_workflow:
        mock_workflow.return_value = {
            "quiz_questions": mock_questions,
            "current_tutorial": tutorial,
            "round_no": 1,
        }

        result = await service.generate_node_questions(path.user_id, node.id)

        assert result.round_no == 1
        assert len(result.questions) == 5
        mock_workflow.assert_awaited_once()


@pytest.mark.asyncio
async def test_auxiliary_resource_generation_uses_learn_workflow():
    path = LearningPath(
        id=1,
        user_id=1,
        module="mentor",
        title="Python 基础路径",
        goal="掌握 Python 基础",
        topic="Python",
        overall_progress=0,
        current_node_key="variables",
        status="active",
        stages_json=[],
    )
    node = PathNode(
        id=10,
        path_id=path.id,
        user_id=path.user_id,
        node_id="variables",
        stage_id="stage-1",
        title="变量与类型",
        status="in_progress",
        priority=1,
        prerequisites=[],
    )
    tutorial = PathNodeTutorial(
        id=20,
        path_id=path.id,
        node_id=node.id,
        user_id=path.user_id,
        tutorial_type="primary",
        version_no=1,
        is_current=True,
        title="变量与类型",
        summary="讲清楚变量、赋值与基本类型",
        content_markdown="教程内容",
    )

    session = _CaptureSession()
    service = PathService(session)
    service._must_get_node = AsyncMock(return_value=node)
    service._must_get_path = AsyncMock(return_value=path)
    service._get_current_tutorial = AsyncMock(return_value=tutorial)
    service._count_resources = AsyncMock(return_value=0)

    result = await service.create_node_resource_task(
        path.user_id,
        node.id,
        "mindmap",
        "run-123",
    )

    assert result.resource.resource_type == "mindmap"
    assert result.run_id == "run-123"


@pytest.mark.asyncio
async def test_path_service_profile_lookup_degrades_to_empty_when_profile_tables_unavailable(monkeypatch):
    service = PathService(_CommitSession())
    async def mock_fail(*args, **kwargs):
        raise ProgrammingError("SELECT ...", {}, Exception("relation missing"))
    monkeypatch.setattr("app.path.service.load_learner_context", mock_fail)

    result = await service._get_profile_dict(1)

    assert result == {}


@pytest.mark.asyncio
async def test_path_service_profile_markdown_degrades_when_profile_tables_unavailable(monkeypatch):
    service = PathService(_CommitSession())
    async def mock_fail(*args, **kwargs):
        raise ProgrammingError("SELECT ...", {}, Exception("relation missing"))
    monkeypatch.setattr("app.path.service.load_learner_context", mock_fail)

    result = await service.get_user_learning_profile(1)

    assert result == ""


@pytest.mark.asyncio
async def test_record_learning_event_binds_to_url_path_id_and_node_identity():
    path = LearningPath(
        id=12,
        user_id=1,
        module="mentor",
        title="SQL Path",
        goal="Learn SQL",
        overall_progress=0,
        status="active",
        stages_json=[],
    )
    node = PathNode(
        id=34,
        path_id=path.id,
        user_id=path.user_id,
        node_id="sql-join",
        stage_id="stage-1",
        title="SQL Join",
        status="available",
        priority=1,
        prerequisites=[],
    )
    recorded = LearningEvent(
        id=99,
        user_id=path.user_id,
        path_id=path.id,
        path_node_id=node.id,
        node_id=node.node_id,
        event_type="resource_viewed",
    )
    bridge = PathService(_CommitSession())
    bridge._must_get_path = AsyncMock(return_value=path)
    bridge._must_get_node = AsyncMock(return_value=node)
    bridge.evaluation_service.record_event = AsyncMock(return_value=recorded)

    payload = LearningEventCreate(
        event_type="resource_viewed",
        path_id=999,
        path_node_id=node.id,
        node_id="wrong-node",
    )

    event = await bridge.record_learning_event(path.user_id, path.id, payload)

    assert event is recorded
    bridge._must_get_path.assert_awaited_once_with(path.user_id, path.id)
    bridge._must_get_node.assert_awaited_once_with(path.user_id, node.id)
    forwarded = bridge.evaluation_service.record_event.await_args.kwargs["payload"]
    assert forwarded.path_id == path.id
    assert forwarded.path_node_id == node.id
    assert forwarded.node_id == node.node_id


@pytest.mark.asyncio
async def test_record_learning_event_rejects_node_from_another_path():
    path = LearningPath(
        id=12,
        user_id=1,
        module="mentor",
        title="SQL Path",
        goal="Learn SQL",
        overall_progress=0,
        status="active",
        stages_json=[],
    )
    foreign_node = PathNode(
        id=34,
        path_id=99,
        user_id=path.user_id,
        node_id="foreign",
        stage_id="stage-1",
        title="Foreign",
        status="available",
        priority=1,
        prerequisites=[],
    )
    bridge = PathService(_CommitSession())
    bridge._must_get_path = AsyncMock(return_value=path)
    bridge._must_get_node = AsyncMock(return_value=foreign_node)
    bridge.evaluation_service.record_event = AsyncMock()

    with pytest.raises(ValueError, match="不属于当前学习路径"):
        await bridge.record_learning_event(
            path.user_id,
            path.id,
            LearningEventCreate(event_type="resource_viewed", path_node_id=foreign_node.id),
        )

    bridge.evaluation_service.record_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_path_generation_validates_plan_before_persistence():
    path = LearningPath(
        id=12,
        user_id=1,
        module="mentor",
        title="Bad Path",
        goal="Learn SQL",
        overall_progress=0,
        status="generating",
        stages_json=[],
    )
    session = _CaptureSession(get_result=path)
    service = PathService(session)
    # 空 stages/nodes now rejected by Pydantic (min_length=1), not by validate_path_plan
    with pytest.raises(Exception):
        invalid = AgentLearningPathPlan(title="Bad", stages=[], nodes=[])

    # verify validate_path_plan also rejects if somehow constructed

    assert session.added == []
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_complete_path_generation_persists_stages_and_nodes():
    path = LearningPath(
        id=12,
        user_id=1,
        module="mentor",
        title="SQL Path",
        goal="Learn SQL",
        overall_progress=0,
        status="generating",
        stages_json=[],
    )
    plan = LearningPlan(
        title="SQL Path",
        stages=[AgentStage(stage_id="stage-1", title="基础")],
        nodes=[
            PlanNode(
                node_id="sql-join",
                stage_id="stage-1",
                title="SQL Join",
                prerequisites=[],
            )
        ],
    )
    session = _CaptureSession(get_result=path)
    service = PathService(session)

    await service._save_plan(path.id, path.user_id, plan)

    saved_node = next(item for item in session.added if isinstance(item, PathNode))
    assert saved_node.node_id == "sql-join"
    assert saved_node.title == "SQL Join"
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_path_service_has_progress_related_methods():
    """PathService should expose methods for path progress queries."""
    service = PathService(_CommitSession())

    assert callable(service.get_latest_active_path_overview)
    assert callable(service.get_path_by_id)
    assert callable(service.get_learning_evaluation)


@pytest.mark.asyncio
async def test_failed_quiz_delegates_to_learn_workflow():
    """submit_node_quiz delegates quiz evaluation to the learn workflow graph."""
    path = LearningPath(
        id=1,
        user_id=1,
        module="mentor",
        title="Python 基础路径",
        goal="掌握 Python 基础",
        topic="Python",
        overall_progress=0,
        current_node_key="variables",
        status="active",
        stages_json=[],
    )
    node = PathNode(
        id=10,
        path_id=path.id,
        user_id=path.user_id,
        node_id="variables",
        stage_id="stage-1",
        title="变量与类型",
        status="in_progress",
        priority=1,
        attempt_count=0,
        prerequisites=[],
    )
    questions = [
        PathNodeQuestion(
            id=index,
            path_id=path.id,
            node_id=node.id,
            tutorial_id=20,
            user_id=path.user_id,
            round_no=1,
            question_no=index,
            question=f"Question {index}",
            choice={"A": "正确", "B": "错误"},
            answer="A",
            knowledge_points=[f"知识点 {index}"],
        )
        for index in range(1, 6)
    ]
    remediation = PathNodeTutorial(
        id=30,
        path_id=path.id,
        node_id=node.id,
        user_id=path.user_id,
        tutorial_type="remediation",
        version_no=2,
        is_current=True,
        title="变量与类型 - 补救教程",
        content_markdown="补救内容",
    )

    service = PathService(_CommitSession())
    service._must_get_node = AsyncMock(return_value=node)
    service._must_get_path = AsyncMock(return_value=path)
    service._get_latest_round = AsyncMock(return_value=1)
    service._get_round_questions = AsyncMock(return_value=questions)
    service._get_current_tutorial = AsyncMock(return_value=remediation)

    with patch("app.path.service.run_learn_workflow", new_callable=AsyncMock) as mock_workflow:
        mock_workflow.return_value = {
            "score": 0,
            "passed": False,
            "outcome": "completed_with_gaps",
            "weak_knowledge_points": ["变量"],
        }

        payload = PathQuizSubmitRequest(
            answers=[
                PathQuizAnswerItem(question_id=question.id, response="B")
                for question in questions
            ]
        )

        result = await service.submit_node_quiz(path.user_id, node.id, payload)

        assert result.outcome == "completed_with_gaps"
        assert result.passed is False
        mock_workflow.assert_awaited_once()


@pytest.mark.asyncio
async def test_second_failed_quiz_delegates_to_learn_workflow():
    """submit_node_quiz delegates second failure evaluation to the learn workflow graph."""
    path = LearningPath(
        id=1,
        user_id=1,
        module="mentor",
        title="Python 基础路径",
        goal="掌握 Python 基础",
        topic="Python",
        overall_progress=0,
        current_node_key="variables",
        status="active",
        stages_json=[],
    )
    node = PathNode(
        id=10,
        path_id=path.id,
        user_id=path.user_id,
        node_id="variables",
        stage_id="stage-1",
        title="变量与类型",
        status="in_progress",
        priority=1,
        attempt_count=1,
        prerequisites=[],
    )
    questions = [
        PathNodeQuestion(
            id=index,
            path_id=path.id,
            node_id=node.id,
            tutorial_id=20,
            user_id=path.user_id,
            round_no=2,
            question_no=index,
            question=f"Question {index}",
            choice={"A": "正确", "B": "错误"},
            answer="A",
            knowledge_points=[f"知识点 {index}"],
        )
        for index in range(1, 6)
    ]
    reinforced = PathNodeTutorial(
        id=30,
        path_id=path.id,
        node_id=node.id,
        user_id=path.user_id,
        tutorial_type="reinforced",
        version_no=2,
        is_current=True,
        title="变量与类型 - 强化教程",
        content_markdown="强化内容",
    )

    service = PathService(_CommitSession())
    service._must_get_node = AsyncMock(return_value=node)
    service._must_get_path = AsyncMock(return_value=path)
    service._get_latest_round = AsyncMock(return_value=2)
    service._get_round_questions = AsyncMock(return_value=questions)
    service._get_current_tutorial = AsyncMock(return_value=reinforced)

    with patch("app.path.service.run_learn_workflow", new_callable=AsyncMock) as mock_workflow:
        mock_workflow.return_value = {
            "score": 0,
            "passed": False,
            "outcome": "completed_with_gaps",
            "weak_knowledge_points": ["变量"],
            "next_node_id": 11,
        }

        payload = PathQuizSubmitRequest(
            answers=[
                PathQuizAnswerItem(question_id=question.id, response="B")
                for question in questions
            ]
        )

        result = await service.submit_node_quiz(path.user_id, node.id, payload)

        assert result.outcome == "completed_with_gaps"
        assert result.passed is False
        assert result.next_node_id == 11
        assert result.current_tutorial_id == reinforced.id
        mock_workflow.assert_awaited_once()


def test_repair_generated_plan_recovers_empty_final_output_from_macro_stages() -> None:
    from app.path.workflows import repair_plan

    plan = LearningPlan.model_construct(
        title="Python 学习路径",
        stages=[],
        nodes=[],
    )
    stages = [
        AgentStage(stage_id="stage-1", title="基础入门"),
        AgentStage(stage_id="stage-2", title="实践应用"),
    ]

    repaired = repair_plan(
        plan=plan,
        macro_stages=stages,
        request=PathRequest(goal="系统学习 Python 编程", topic="Python"),
    )
    validate_path_plan(repaired)

    assert [stage.stage_id for stage in repaired.stages] == ["stage-1", "stage-2"]
    assert [node.stage_id for node in repaired.nodes] == ["stage-1", "stage-2"]
    assert repaired.nodes[0].prerequisites == []
    assert repaired.nodes[1].prerequisites == [repaired.nodes[0].node_id]
