"""节点学习工作流 — 基于 LangGraph 的教程生成、测验、评分、推进闭环。

状态图节点：
- load_context          — 加载节点、路径、教程等上下文
- gen_primary_tutorial  — 生成主教程
- persist_tutorial_start — 持久化教程并标记节点开始
- gen_questions         — 生成测验题目
- persist_questions     — 持久化题目到数据库
- score_answers         — 评分并统计薄弱知识点
- advance_state         — 根据得分决定节点推进结果
- unlock_progress       — 解锁下游节点并更新路径进度
- gen_remediation_tutorial — 生成补救教程
- gen_reinforced_tutorial  — 生成强化教程
- record_event          — 记录学习事件
- gen_resource          — 生成辅助资源
- persist_resource      — 持久化资源到数据库
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlmodel import col, select

from app.config import PATH_PASS_SCORE, PATH_QUIZ_SIZE
from app.evaluation.request import LearningEventCreate
from app.evaluation.service import (
    EvaluationService,
    bg_apply_profile_update_from_learning_event,
)
from app.infra.logging import get_logger
from app.infra.models import (
    LearningPath,
    PathNode,
    PathNodeQuestion,
    PathNodeResource,
    PathNodeTutorial,
)
from app.path.agents.node_learning import NodeLearningAgent
from app.path.workflows.state import LearnState
from app.profile.service import get_profile_service
from app.resource.path_helpers import generate_path_node_resource
from app.resource.schemas import NodeInput

logger = get_logger(__name__)

# 已完成节点的状态集合
COMPLETED_NODE_STATUSES = frozenset({"completed", "completed_with_gaps"})
# 可学习节点的状态集合（包含已完成）
ACTIVE_NODE_STATUSES = frozenset(
    {"available", "in_progress", "remediation", "reinforced"}
)


def _route_by_phase(state: LearnState) -> str:
    """根据 state['phase'] 路由到对应的处理节点。"""
    return state["phase"]


def _route_by_outcome(state: LearnState) -> str:
    """根据测验结果路由：需补救 → 补救教程，有缺陷 → 强化教程，通过 → 解锁推进。"""
    outcome = state.get("outcome", "completed")
    if outcome == "remediation":
        return "gen_remediation_tutorial"
    if outcome == "completed_with_gaps" and state.get("tutorial_type") == "reinforced":
        return "gen_reinforced_tutorial"
    return "unlock_progress"


def _build_learn_workflow() -> StateGraph:
    """构建节点学习状态图。

    图结构：
    START → load_context → (根据 phase 路由)
        → start: gen_primary_tutorial → persist_tutorial_start → END
        → questions: gen_questions → persist_questions → END
        → quiz: score_answers → advance_state → (根据 outcome 路由)
            → remediation: gen_remediation_tutorial → persist → record_event → END
            → reinforced: gen_reinforced_tutorial → persist → unlock_progress → ...
            → completed: unlock_progress → record_event → END
        → resource: gen_resource → persist_resource → END
    """
    wf = StateGraph(LearnState)

    # 注册所有图节点
    wf.add_node("load_context", node_load_context)
    wf.add_node("gen_primary_tutorial", node_generate_tutorial)
    wf.add_node("persist_tutorial_start", node_persist_tutorial_and_mark)
    wf.add_node("gen_questions", node_generate_questions)
    wf.add_node("persist_questions", node_persist_questions)
    wf.add_node("score_answers", node_score_answers)
    wf.add_node("advance_state", node_advance_state)
    wf.add_node("unlock_progress", node_unlock_and_update_progress)
    wf.add_node("gen_remediation_tutorial", node_generate_tutorial)
    wf.add_node("persist_remediation_tutorial", node_persist_tutorial_and_mark)
    wf.add_node("gen_reinforced_tutorial", node_generate_tutorial)
    wf.add_node("persist_reinforced_tutorial", node_persist_tutorial_and_mark)
    wf.add_node("record_event", node_record_quiz_event)
    wf.add_node("gen_resource", node_generate_resource)
    wf.add_node("persist_resource", node_persist_resource)

    wf.add_edge(START, "load_context")

    # 入口：根据 phase 路由到不同处理分支
    wf.add_conditional_edges(
        "load_context",
        _route_by_phase,
        {
            "start": "gen_primary_tutorial",
            "questions": "gen_questions",
            "quiz": "score_answers",
            "resource": "gen_resource",
        },
    )

    # 主教程生成流程
    wf.add_edge("gen_primary_tutorial", "persist_tutorial_start")
    wf.add_edge("persist_tutorial_start", END)

    # 题目生成流程
    wf.add_edge("gen_questions", "persist_questions")
    wf.add_edge("persist_questions", END)

    # 测验评分 → 推进 → 根据结果路由
    wf.add_edge("score_answers", "advance_state")
    wf.add_conditional_edges(
        "advance_state",
        _route_by_outcome,
        {
            "gen_remediation_tutorial": "gen_remediation_tutorial",
            "gen_reinforced_tutorial": "gen_reinforced_tutorial",
            "unlock_progress": "unlock_progress",
        },
    )

    # 补救教程流程
    wf.add_edge("gen_remediation_tutorial", "persist_remediation_tutorial")
    wf.add_edge("persist_remediation_tutorial", "record_event")
    wf.add_edge("record_event", END)

    # 强化教程流程
    wf.add_edge("gen_reinforced_tutorial", "persist_reinforced_tutorial")
    wf.add_edge("persist_reinforced_tutorial", "unlock_progress")

    # 解锁推进 → 记录事件
    wf.add_edge("unlock_progress", "record_event")

    # 辅助资源生成流程
    wf.add_edge("gen_resource", "persist_resource")
    wf.add_edge("persist_resource", END)

    return wf.compile()


# 工作流单例缓存
_learn_workflow: StateGraph | None = None


def get_learn_workflow() -> StateGraph:
    """获取节点学习工作流的编译后状态图（单例）。"""
    global _learn_workflow
    if _learn_workflow is None:
        _learn_workflow = _build_learn_workflow()
    return _learn_workflow


# ── 图节点函数 ──────────────────────────────────────────────────────────────


async def node_load_context(state: LearnState) -> dict:
    """加载节点上下文 — 查询节点、路径、教程列表、当前教程、学习者画像。"""
    session = state["session"]
    user_id = state["user_id"]
    node_id = state["node_id"]

    node = await session.get(PathNode, node_id)
    if node is None or node.user_id != user_id:
        return {"error": "路径节点不存在"}

    path = await session.get(LearningPath, node.path_id)
    if path is None:
        return {"error": "学习路径不存在"}

    # 查询当前节点的所有教程（按版本号升序）
    stmt = (
        select(PathNodeTutorial)
        .where(PathNodeTutorial.node_id == node_id)
        .order_by(
            col(PathNodeTutorial.version_no).asc(),
            col(PathNodeTutorial.id).asc(),
        )
    )
    tutorials = list((await session.exec(stmt)).all())
    current_tutorial = next((t for t in tutorials if t.is_current), None)

    # 加载学习者画像（容错：画像表不可用时降级为空）
    try:
        profile_service = get_profile_service()
        profile_markdown = await profile_service.get_profile_markdown(user_id)
    except Exception:
        profile_markdown = ""

    return {
        "node": node,
        "path": path,
        "tutorials": tutorials,
        "current_tutorial": current_tutorial,
        "profile_markdown": profile_markdown,
    }


async def node_generate_tutorial(state: LearnState) -> dict:
    """生成教程 — 调用 NodeLearningAgent 生成指定类型的教程内容。"""
    if state.get("error"):
        return {}
    agent = NodeLearningAgent()
    node = state["node"]
    path = state["path"]
    result = await agent.generate_tutorial(
        path_goal=path.goal,
        node_title=node.title,
        mastery_target="掌握该节点核心能力",
        tutorial_type=state.get("tutorial_type", "primary"),
        weak_knowledge_points=state.get("weak_knowledge_points", []),
        profile_markdown=state.get("profile_markdown", ""),
    )
    return {"tutorial_content": result["content_markdown"]}


async def node_persist_tutorial_and_mark(state: LearnState) -> dict:
    """持久化教程并更新节点状态 — 将新教程写入数据库并标记为当前版本。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    path = state["path"]
    user_id = state["user_id"]
    tutorial_type = state.get("tutorial_type", "primary")

    # 将旧的当前教程取消激活
    prev_stmt = select(PathNodeTutorial).where(
        PathNodeTutorial.node_id == node.id,
        PathNodeTutorial.is_current.is_(True),
    )
    prev_current = (await session.exec(prev_stmt)).first()
    if prev_current is not None:
        prev_current.is_current = False

    # 创建新教程记录
    existing = state.get("tutorials", [])
    tutorial = PathNodeTutorial(
        path_id=path.id,
        node_id=node.id,
        user_id=user_id,
        tutorial_type=tutorial_type,
        version_no=len(existing) + 1,
        based_on_tutorial_id=state.get("based_on_tutorial_id"),
        is_current=True,
        title=f"{node.title} - {tutorial_type}",
        summary=tutorial_type,
        content_markdown=state["tutorial_content"],
        knowledge_points=[node.title],
        weak_knowledge_points=state.get("weak_knowledge_points", []),
    )
    session.add(tutorial)
    await session.flush()

    # 更新节点：绑定当前教程，标记为学习中
    node.current_tutorial_id = tutorial.id
    if node.status == "available":
        node.status = "in_progress"
    if node.started_at is None:
        node.started_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(tutorial)
    return {"tutorial": tutorial}


async def node_generate_questions(state: LearnState) -> dict:
    """生成测验题目 — 如果无教程则先生成主教程，再调用 LLM 生成 5 道题。"""
    if state.get("error"):
        return {}
    node = state["node"]
    path = state["path"]
    current_tutorial = state.get("current_tutorial")

    # 如果没有当前教程，先生成主教程
    if current_tutorial is None:
        agent = NodeLearningAgent()
        result = await agent.generate_tutorial(
            path_goal=path.goal,
            node_title=node.title,
            mastery_target="掌握该节点核心能力",
            tutorial_type="primary",
            weak_knowledge_points=[],
            profile_markdown=state.get("profile_markdown", ""),
        )
        session = state["session"]
        tutorial = PathNodeTutorial(
            path_id=path.id,
            node_id=node.id,
            user_id=state["user_id"],
            tutorial_type="primary",
            version_no=1,
            is_current=True,
            title=f"{node.title} - primary",
            summary="primary",
            content_markdown=result["content_markdown"],
            knowledge_points=[node.title],
            weak_knowledge_points=[],
        )
        session.add(tutorial)
        await session.flush()
        node.current_tutorial_id = tutorial.id
        if node.started_at is None:
            node.started_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(tutorial)
        current_tutorial = tutorial

    # 获取当前轮次号并生成题目
    round_no = await _latest_round(state["session"], node.id) + 1
    agent = NodeLearningAgent()
    generated = await agent.generate_questions(
        path_goal=path.goal,
        node_title=node.title,
        mastery_target="掌握该节点核心能力",
        tutorial_title=current_tutorial.title,
        tutorial_summary=current_tutorial.summary or current_tutorial.title,
        round_no=round_no,
    )
    if len(generated) != PATH_QUIZ_SIZE:
        return {"error": "当前节点还没有生成完整的五道题，请稍后重试"}
    return {"generated_questions": generated, "round_no": round_no}


async def node_persist_questions(state: LearnState) -> dict:
    """持久化题目 — 将生成的 5 道题目写入 PathNodeQuestion 表。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    path = state["path"]
    user_id = state["user_id"]
    current_tutorial = state.get("current_tutorial")
    round_no = state["round_no"]

    questions: list[PathNodeQuestion] = []
    for index, item in enumerate(
        state["generated_questions"][:PATH_QUIZ_SIZE], start=1
    ):
        question = PathNodeQuestion(
            path_id=path.id,
            node_id=node.id,
            tutorial_id=current_tutorial.id if current_tutorial else None,
            user_id=user_id,
            round_no=round_no,
            question_no=index,
            mode="quiz",
            type=item.get("type", "single_choice"),
            question=item["question"],
            choice=item.get("choice") or item.get("options") or {},
            answer=str(item["answer"]),
            analysis=item.get("analysis") or item.get("explanation"),
            knowledge_points=item.get("knowledge_points") or [],
        )
        session.add(question)
        questions.append(question)
    await session.commit()
    for q in questions:
        await session.refresh(q)
    return {"quiz_questions": questions}


async def node_score_answers(state: LearnState) -> dict:
    """评分 — 逐题比对用户答案，统计得分和薄弱知识点。"""
    if state.get("error"):
        return {}
    questions = state.get("quiz_questions", [])
    if len(questions) != PATH_QUIZ_SIZE:
        return {"error": "当前节点还没有完整的五道题"}
    answers = state.get("quiz_answers", [])
    answer_map = {item["question_id"]: item["response"] for item in answers}

    score = 0
    weak_points: list[str] = []
    for question in questions:
        response = answer_map.get(question.id)
        is_correct = response == question.answer
        # 更新题目记录：保存用户回答和正确性
        question.response = response
        question.is_correct = is_correct
        question.submitted_at = datetime.now(timezone.utc)
        question.updated_at = question.submitted_at
        if is_correct:
            score += 1
        else:
            # 收集答错题目涉及的薄弱知识点（去重）
            for point in question.knowledge_points or []:
                if point not in weak_points:
                    weak_points.append(point)
    return {
        "score": score,
        "passed": score >= PATH_PASS_SCORE,
        "weak_knowledge_points": weak_points,
    }


async def node_advance_state(state: LearnState) -> dict:
    """推进节点状态 — 根据测验结果决定节点下一步状态。

    结果逻辑：
    - 通过 → completed
    - 首次未通过 → remediation（触发补救教程）
    - 第二次未通过 → completed_with_gaps（触发强化教程）
    - 后续未通过 → completed_with_gaps
    """
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    passed = state["passed"]
    weak_points = state.get("weak_knowledge_points", [])

    node.attempt_count += 1

    if passed:
        node.status = "completed"
        node.completed_at = datetime.now(timezone.utc)
        outcome = "completed"
    elif node.attempt_count == 1:
        # 首次未通过 → 补救模式
        node.status = "remediation"
        outcome = "remediation"
    elif node.attempt_count == 2:
        # 第二次未通过 → 有缺陷完成，触发强化教程
        node.status = "completed_with_gaps"
        node.completed_at = datetime.now(timezone.utc)
        outcome = "completed_with_gaps"
    else:
        node.status = "completed_with_gaps"
        node.completed_at = datetime.now(timezone.utc)
        outcome = "completed_with_gaps"

    await session.commit()

    result: dict = {"outcome": outcome}
    if outcome == "remediation":
        result["tutorial_type"] = "remediation"
        result["weak_knowledge_points"] = weak_points
    elif outcome == "completed_with_gaps" and node.attempt_count == 2:
        # 第二次未通过时，基于主教程生成强化教程
        primary = await _primary_tutorial(session, node.id)
        result["tutorial_type"] = "reinforced"
        result["weak_knowledge_points"] = weak_points
        result["based_on_tutorial_id"] = primary.id if primary else None
    return result


async def node_unlock_and_update_progress(state: LearnState) -> dict:
    """解锁下游节点并更新路径总进度。

    逻辑：如果节点的所有前置依赖已完成，则将该节点从 locked 变为 available。
    同时更新路径的 overall_progress 和 current_node_key。
    """
    if state.get("error"):
        return {}
    session = state["session"]
    path = state["path"]

    nodes = await _path_nodes(session, path.id)
    completed = {n.node_id for n in nodes if n.status in COMPLETED_NODE_STATUSES}

    # 解锁前置依赖已满足的 locked 节点
    for n in nodes:
        if n.status == "locked" and set(n.prerequisites or []).issubset(completed):
            n.status = "available"

    if nodes:
        completed_count = sum(
            1 for n in nodes if n.status in COMPLETED_NODE_STATUSES
        )
        # 计算总进度百分比
        path.overall_progress = round(completed_count / len(nodes) * 100)
        # 定位下一个可学习节点
        next_node = next(
            (n for n in nodes if n.status in ACTIVE_NODE_STATUSES), None
        )
        path.current_node_key = next_node.node_id if next_node else None
        if completed_count == len(nodes):
            path.status = "completed"
        path.updated_at = datetime.now(timezone.utc)

    await session.commit()

    next_node = next(
        (n for n in nodes if n.status in ACTIVE_NODE_STATUSES), None
    )
    return {"next_node_id": next_node.id if next_node else None}


async def node_record_quiz_event(state: LearnState) -> dict:
    """记录测验学习事件 — 将测验结果写入 LearningEvent 表并更新学习者画像。"""
    if state.get("error"):
        return {}
    session = state["session"]
    user_id = state["user_id"]
    node = state["node"]
    path = state["path"]

    outcome = state.get("outcome", "completed")
    score = state.get("score", 0)
    weak_points = state.get("weak_knowledge_points", [])

    payload = LearningEventCreate(
        event_type="quiz_submitted",
        path_id=path.id,
        path_node_id=node.id,
        node_id=node.node_id,
        course=path.title,
        topic=node.title,
        score=float(score / PATH_QUIZ_SIZE * 100),
        feedback=None,
        metadata={"weak_knowledge_points": weak_points, "outcome": outcome},
    )
    eval_service = EvaluationService()
    event = await eval_service.record_event(session, user_id=user_id, payload=payload)

    # 异步更新学习者画像（容错处理）
    try:
        await bg_apply_profile_update_from_learning_event(
            user_id,
            {
                "event_type": event.event_type,
                "session_id": event.session_id,
                "resource_id": event.resource_id,
                "resource_item_id": event.resource_item_id,
                "path_id": event.path_id,
                "path_node_id": event.path_node_id,
                "node_id": event.node_id,
                "course": event.course,
                "topic": event.topic,
                "score": event.score,
                "feedback": event.feedback,
                "metadata": event.metadata_json or {},
            },
        )
    except Exception as exc:
        logger.warning("Profile update from quiz event failed: %s", exc)

    return {}


async def node_generate_resource(state: LearnState) -> dict:
    """生成辅助资源 — 根据资源类型调用对应的资源生成器。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    path = state["path"]
    resource_type = state.get("resource_type", "content")
    current_tutorial = state.get("current_tutorial")

    # 如果没有当前教程，先生成主教程
    if current_tutorial is None:
        agent = NodeLearningAgent()
        result = await agent.generate_tutorial(
            path_goal=path.goal,
            node_title=node.title,
            mastery_target="掌握该节点核心能力",
            tutorial_type="primary",
            weak_knowledge_points=[],
            profile_markdown=state.get("profile_markdown", ""),
        )
        tutorial = PathNodeTutorial(
            path_id=path.id,
            node_id=node.id,
            user_id=state["user_id"],
            tutorial_type="primary",
            version_no=1,
            is_current=True,
            title=f"{node.title} - primary",
            summary="primary",
            content_markdown=result["content_markdown"],
            knowledge_points=[node.title],
            weak_knowledge_points=[],
        )
        session.add(tutorial)
        await session.flush()
        node.current_tutorial_id = tutorial.id
        if node.started_at is None:
            node.started_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(tutorial)
        current_tutorial = tutorial

    # 构建节点输入参数，调用资源生成器
    node_input = NodeInput(
        path_id=path.id,
        node_id=node.id,
        node_key=node.node_id,
        stage_id=node.stage_id,
        path_title=path.title,
        path_goal=path.goal,
        node_title=node.title,
        difficulty=node.difficulty,
        mastery_target=None,
        knowledge_points=list(current_tutorial.knowledge_points or []),
        weak_knowledge_points=list(current_tutorial.weak_knowledge_points or []),
        generation_focus=[],
        tutorial_title=current_tutorial.title,
        tutorial_summary=current_tutorial.summary,
        tutorial_markdown=current_tutorial.content_markdown,
        profile={},
        agent_config={},
    )
    result = await generate_path_node_resource(resource_type, node_input)
    return {"resource_result": result, "resource_type": resource_type}


async def node_persist_resource(state: LearnState) -> dict:
    """持久化资源 — 将生成的辅助资源写入 PathNodeResource 表。

    处理两种情况：
    - 生成失败：创建 status=failed 的记录，保存错误信息
    - 生成成功：根据内容格式（json/markdown）分别存储
    """
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    path = state["path"]
    user_id = state["user_id"]
    current_tutorial = state.get("current_tutorial")
    resource_type = state.get("resource_type", "content")
    result = state["resource_result"]

    # 计算版本号（同类型资源数量 + 1）
    existing_count = await _count_resources(session, node.id, resource_type)
    version_no = existing_count + 1
    title = (
        result.title
        if hasattr(result, "title") and result.title
        else f"{node.title} - {resource_type}"
    )

    # 处理生成失败的情况
    if hasattr(result, "success") and not result.success:
        resource = PathNodeResource(
            path_id=path.id,
            node_id=node.id,
            tutorial_id=current_tutorial.id if current_tutorial else None,
            user_id=user_id,
            resource_type=resource_type,
            version_no=version_no,
            title=title,
            content_format="markdown",
            status="failed",
            error_message=(
                result.error if hasattr(result, "error") else "unknown"
            ),
            summary=result.summary if hasattr(result, "summary") else None,
            metadata_json=(
                result.metadata if hasattr(result, "metadata") else None
            ),
        )
        session.add(resource)
        await session.commit()
        await session.refresh(resource)
        return {"resource_dto": _resource_to_dict(resource)}

    # 处理生成成功的情况：区分 JSON 和 Markdown 格式
    content_text = None
    content_json_val = None
    file_type = getattr(result, "file_type", "markdown")
    raw_content = getattr(result, "content", "")
    if file_type == "json":
        try:
            content_json_val = (
                json.loads(raw_content)
                if isinstance(raw_content, str)
                else raw_content
            )
        except (json.JSONDecodeError, TypeError):
            content_text = str(raw_content)
    else:
        content_text = str(raw_content)

    resource = PathNodeResource(
        path_id=path.id,
        node_id=node.id,
        tutorial_id=current_tutorial.id if current_tutorial else None,
        user_id=user_id,
        resource_type=resource_type,
        version_no=version_no,
        title=title,
        content_format=file_type,
        content_text=content_text,
        content_json=content_json_val,
        summary=result.summary if hasattr(result, "summary") else None,
        status="completed",
        metadata_json=result.metadata if hasattr(result, "metadata") else None,
    )
    session.add(resource)
    await session.commit()
    await session.refresh(resource)
    return {"resource_dto": _resource_to_dict(resource)}


# ── 内部辅助函数 ──────────────────────────────────────────────────────────


async def _latest_round(session, node_id: int) -> int:
    """获取节点的最新测验轮次号。"""
    stmt = select(PathNodeQuestion).where(PathNodeQuestion.node_id == node_id)
    questions = list((await session.exec(stmt)).all())
    return max((q.round_no for q in questions), default=0)


async def _primary_tutorial(session, node_id: int) -> PathNodeTutorial | None:
    """获取节点的主教程（版本号最小的 primary 类型教程）。"""
    stmt = (
        select(PathNodeTutorial)
        .where(
            PathNodeTutorial.node_id == node_id,
            PathNodeTutorial.tutorial_type == "primary",
        )
        .order_by(col(PathNodeTutorial.version_no).asc())
    )
    return (await session.exec(stmt)).first()


async def _path_nodes(session, path_id: int) -> list[PathNode]:
    """获取路径下所有节点，按优先级升序排列。"""
    stmt = (
        select(PathNode)
        .where(PathNode.path_id == path_id)
        .order_by(col(PathNode.priority).asc(), col(PathNode.id).asc())
    )
    return list((await session.exec(stmt)).all())


async def _count_resources(session, node_id: int, resource_type: str) -> int:
    """统计节点下指定类型的资源数量。"""
    stmt = select(PathNodeResource).where(
        PathNodeResource.node_id == node_id,
        PathNodeResource.resource_type == resource_type,
    )
    return len(list((await session.exec(stmt)).all()))


def _resource_to_dict(resource) -> dict:
    """将 PathNodeResource ORM 实例转换为字典。"""
    return {
        "id": resource.id,
        "resource_type": resource.resource_type,
        "version_no": resource.version_no,
        "title": resource.title,
        "content_format": resource.content_format,
        "content_text": resource.content_text,
        "content_json": resource.content_json,
        "summary": resource.summary,
        "status": resource.status or "completed",
        "error_message": resource.error_message,
        "created_at": (
            resource.created_at.isoformat() if resource.created_at else ""
        ),
    }
