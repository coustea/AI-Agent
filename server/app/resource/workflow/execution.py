"""普通 Agent 唯一单次执行边界。

职责：
- 单次 timeout
- 实例化并调用 Agent
- 校验结果
- 立即提交
- 记录运行状态
- 观察事件（best-effort）
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from app.infra.database import session_scope
from app.infra.logging import get_module_logger
from app.resource.agents import AGENT_REGISTRY
from app.resource.event import ResourceEvents
from app.resource.service import ResourceService
from app.resource.workflow.state import AgentFailure
from app.resource.workflow.validation import validate_agent_result

if TYPE_CHECKING:
    from app.resource.schemas import ResourceInput

logger = get_module_logger("resource", sub="execution")

# Agent 超时配置（秒）
# 基础 Agent 需要搜索+LLM 生成，300s LLM 超时加上搜索耗时容易触发 agent 级超时。
AGENT_TIMEOUTS: dict[str, float] = {
    "content": 600.0,
    "mindmap": 600.0,
    "quiz": 600.0,
    "code": 600.0,
    "reading": 600.0,
    "ppt": 900.0,
    "video": 1200.0,
    "cartoon": 1800.0,
}


async def _observe(*, agent_id: str, coro: Any) -> None:
    """执行观察事件，失败只记录日志。"""
    try:
        await coro
    except Exception as e:
        logger.warning("Agent[%s] 事件发送失败: %s", agent_id, e)


async def execute_resource_agent(
    *,
    user_id: int,
    resource_id: int,
    agent_id: str,
    input_data: ResourceInput,
) -> dict[str, Any]:
    """执行单个资源 Agent，包含完整的生命周期管理、状态变更、数据持久化及 SSE 事件分发。"""
    started = time.perf_counter()
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
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
            "开始生成...",
            0,
            data={"phase": "generation"},
        ),
    )
    logger.info(
        "Agent[%s] 开始执行: resource_id=%s timeout=%ds",
        agent_id, resource_id, int(timeout_seconds),
    )

    # 执行 Agent（带超时）
    try:
        async with asyncio.timeout(timeout_seconds):
            result = await agent.generate_resource(input_data)
    except TimeoutError as exc:
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage="timeout",
            exception=exc,
            started_at=started,
            events=events,
        )
    except Exception as exc:
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage="generation",
            exception=exc,
            started_at=started,
            events=events,
        )

    # 校验结果
    try:
        validate_agent_result(agent_id, result, input_data)
    except Exception as exc:
        return await _record_failure(
            resource_id=resource_id,
            agent_id=agent_id,
            stage="validation",
            exception=exc,
            started_at=started,
            events=events,
        )

    # 持久化结果
    try:
        async with session_scope() as session:
            service = ResourceService(session)
            item = await service.save_agent_result(
                resource_id=resource_id,
                user_id=user_id,
                agent_id=agent_id,
                result=result,
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id=agent_id,
                status="completed",
                elapsed_ms=elapsed_ms,
            )
    except Exception as exc:
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
            result.title,
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

    return {"results": {agent_id: True}}


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

    # 输出失败日志
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
