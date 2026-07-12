"""普通 Agent 唯一单次执行边界。

职责：
- 单次 timeout
- 实例化并调用 Agent
- 校验结果
- 立即提交
- 记录运行状态
- 观察事件（best-effort）

execute_resource_agent 与 execute_node_agent 共享同一生命周期，
仅调用 generate_resource / generate_node 的不同入口。
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from app.infra.database import session_scope
from app.infra.logging import get_module_logger
from app.resource.agents import AGENT_REGISTRY
from app.resource.event import ResourceEvents
from app.resource.service import ResourceService
from app.resource.workflow.state import AgentFailure
from app.resource.workflow.validation import validate_agent_result

if TYPE_CHECKING:
    from app.resource.schemas import ResourceInput, NodeInput, AgentResult

logger = get_module_logger("resource", sub="execution")

# Agent 超时配置（秒）
# 基础 Agent 需要搜索+LLM 生成，300s LLM 超时加上搜索耗时容易触发 agent 级超时。
# 聚合/视频类耗时更长，超时依次放宽
AGENT_TIMEOUTS: dict[str, float] = {
    "content": 600.0,
    "mindmap": 600.0,
    "quiz": 600.0,
    "code": 600.0,
    "reading": 600.0,
    "ppt": 900.0,
    "cartoon": 1800.0,
}

# Agent 开始执行时面向用户的文案（统一由 execute_resource_agent 发送开始消息）
AGENT_START_MESSAGES: dict[str, str] = {
    "content": "开始生成课程讲解资源...",
    "mindmap": "开始生成知识结构导图...",
    "quiz": "开始生成随堂练习题...",
    "code": "开始生成代码实操案例...",
    "reading": "开始生成拓展阅读资源...",
    "ppt": "开始生成教学课件...",
    "cartoon": "开始生成动画讲解视频...",
}


async def _observe(*, agent_id: str, coro: Any) -> None:
    """执行观察事件，失败只记录日志。"""
    # best-effort 发送事件，异常不影响主流程
    try:
        await coro
    except Exception as e:
        logger.warning("Agent[%s] 事件发送失败: %s", agent_id, e)


async def _run_agent_lifecycle(
    *,
    user_id: int,
    resource_id: int,
    agent_id: str,
    input_data: "ResourceInput | NodeInput",
    generate_fn: Callable[["Any"], Awaitable["AgentResult"]],
) -> dict[str, Any]:
    """单个资源 Agent 的完整生命周期：运行态持久���、SSE 事件、超时、校验、保存。

    generate_fn 决定调用 generate_resource 还是 generate_node，二者共享其余逻辑。
    """
    started = time.perf_counter()
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    # 从注册表取出该 agent 的实例（注入事件通道）
    agent = AGENT_REGISTRY[agent_id](events)
    timeout_seconds = AGENT_TIMEOUTS.get(agent_id, 300.0)

    # 先持久化运行态，使页面刷新后仍能恢复本次选中的 Agent 和当前阶段。
    try:
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id=agent_id,
                status="running",
            )
    except Exception as exc:
        # 持久化失败直接进入失败流程
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage="persistence",
            exception=exc,
            started_at=started,
            events=events,
        )

    # 发送开始事件
    await _observe(
        agent_id=agent_id,
        coro=events.send(
            agent_id,
            "running",
            AGENT_START_MESSAGES.get(agent_id, "开始生成资源..."),
            0,
            data={"phase": "generation_started"},
        ),
    )
    logger.info(
        "Agent[%s] 开始执行: resource_id=%s timeout=%ds",
        agent_id, resource_id, int(timeout_seconds),
    )

    # 执行 Agent（带超时保护）
    try:
        async with asyncio.timeout(timeout_seconds):
            result = await generate_fn(agent)
    except TimeoutError as exc:
        # 超时失败
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage="timeout",
            exception=exc,
            started_at=started,
            events=events,
        )
    except Exception as exc:
        # 生成过程异常
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage="generation",
            exception=exc,
            started_at=started,
            events=events,
        )

    if result.success is not True:
        generation_stage = str(result.metadata.get("generation_stage") or "generation")
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage=generation_stage,
            exception=RuntimeError(result.error or "Agent returned success=False"),
            started_at=started,
            events=events,
        )

    # 校验结果
    await _observe(
        agent_id=agent_id,
        coro=events.send(
            agent_id,
            "running",
            "正在校验资源结构与内容完整性...",
            88,
            data={"phase": "validation"},
        ),
    )
    try:
        validate_agent_result(agent_id, result, input_data)
    except Exception as exc:
        # 校验失败
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage="validation",
            exception=exc,
            started_at=started,
            events=events,
        )

    # 持久化结果
    await _observe(
        agent_id=agent_id,
        coro=events.send(
            agent_id,
            "running",
            "正在保存资源成果...",
            94,
            data={"phase": "persistence"},
        ),
    )
    try:
        async with session_scope() as session:
            service = ResourceService(session)
            # 保存成功产物并建立资源项
            item = await service.save_agent_result(
                resource_id=resource_id,
                user_id=user_id,
                agent_id=agent_id,
                result=result,
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            # 标记该 agent 运行完成并记录耗时
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id=agent_id,
                status="completed",
                elapsed_ms=elapsed_ms,
            )
    except Exception as exc:
        # 保存失败
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage="persistence",
            exception=exc,
            started_at=started,
            events=events,
        )

    # 发送成功事件
    await _observe(
        agent_id=agent_id,
        coro=events.send(
            agent_id,
            "completed",
            f"{result.title} 已保存",
            100,
            data={
                "phase": "artifact_saved",
                "artifact_id": str(item.id),
                "elapsed_ms": elapsed_ms,
            },
        ),
    )
    logger.info(
        "Agent[%s] 执行成功: resource_id=%s title=%s artifact_id=%s elapsed_ms=%d",
        agent_id, resource_id, result.title[:80], str(item.id), elapsed_ms,
    )

    # 以成功结果字典返回，供图状态合并
    return {"results": {agent_id: True}}


async def execute_resource_agent(
    *,
    user_id: int,
    resource_id: int,
    agent_id: str,
    input_data: "ResourceInput",
) -> dict[str, Any]:
    """执行单个资源 Agent 的 generate_resource 入口。"""
    # 走多智能体资源流程（generate_resource）
    return await _run_agent_lifecycle(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=agent_id,
        input_data=input_data,
        generate_fn=lambda a: a.generate_resource(input_data),
    )


async def execute_node_agent(
    *,
    user_id: int,
    resource_id: int,
    agent_id: str,
    node_input: "NodeInput",
) -> dict[str, Any]:
    """执行单个资源 Agent 的 generate_node 入口（单智能体 PPT/Cartoon 调用、路径节点资源）。"""
    # 走路径节点流程（generate_node）
    return await _run_agent_lifecycle(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=agent_id,
        input_data=node_input,
        generate_fn=lambda a: a.generate_node(node_input),
    )


async def _record_failure(
    *,
    resource_id: int,
    agent_id: str,
    stage: str,
    exception: Exception,
    started_at: float,
    events: ResourceEvents,
) -> dict[str, Any]:
    """记录失败并返回失败结果字典供有向图状态合并。"""
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    error_type = type(exception).__name__
    error_message = str(exception)[:300]

    # 记录结构化失败日志
    logger.error(
        "Agent[%s] 执行失败: resource_id=%s stage=%s error_type=%s error=%s elapsed_ms=%d",
        agent_id,
        resource_id,
        stage,
        error_type,
        error_message,
        elapsed_ms,
    )

    try:
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id=agent_id,
                status="failed",
                error_message=f"[{error_type}] {error_message}",
                elapsed_ms=elapsed_ms,
            )
    except Exception as e:
        logger.error("Agent[%s] 记录失败状态到数据库失败: %s", agent_id, e)

    await _observe(
        agent_id=agent_id,
        coro=events.send(
            agent_id,
            "failed",
            error_message,
            0,
            data={"phase": stage, "elapsed_ms": elapsed_ms},
        ),
    )

    return {
        "results": {},
        "failures": {
            agent_id: AgentFailure(
                agent_id=agent_id,
                stage=stage,
                error_type=error_type,
                message=error_message,
            )
        },
    }
