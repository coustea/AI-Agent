"""普通 Agent 唯一单次执行边界。

职责：
- 单次 timeout
- 实例化并调用 Agent
- 校验结果
- 立即提交
- 记录运行状态
- 观察事件（best-effort）

资源工作流只使用 generate_resource 这一条执行入口。
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from app.infra.database import session_scope
from app.infra.logging import get_module_logger
from app.resource.agents import AGENT_REGISTRY
from app.resource.catalog import AGENT_BY_ID
from app.resource.event import ResourceEvents
from app.resource.service import ResourceService
from app.resource.schemas.plan import DownstreamContext
from app.resource.workflow.extraction import extract_core_content
from app.resource.workflow.state import AgentFailure
from app.resource.workflow.validation import validate_agent_result

if TYPE_CHECKING:
    from app.resource.schemas import ResourceInput, AgentResult

logger = get_module_logger("resource", sub="execution")

# 一个资源生成进程内只允许有限数量的真实 Agent 同时占用 LLM/渲染资源。
# 队列中的 Agent 仍是 pending，开始后才进入 running；不做自动重试。
RESOURCE_GENERATION_CONCURRENCY = 3
_generation_slots = asyncio.Semaphore(RESOURCE_GENERATION_CONCURRENCY)


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
    input_data: "ResourceInput",
    generate_fn: Callable[["Any"], Awaitable["AgentResult"]],
) -> dict[str, Any]:
    """单个资源 Agent 的完整生命周期：运行态持久���、SSE 事件、超时、校验、保存。

    generate_fn 是唯一的资源生成入口。
    """
    started = time.perf_counter()
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    # 从注册表取出该 agent 的实例（注入事件通道）
    agent = AGENT_REGISTRY[agent_id](events)
    descriptor = AGENT_BY_ID[agent_id]
    timeout_seconds = descriptor.timeout_seconds

    try:
        await events.send(
            agent_id,
            "running",
            descriptor.start_message,
            0,
            data={"phase": "generation_started"},
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
    logger.info(
        "Agent[%s] 开始执行: resource_id=%s timeout=%ds",
        agent_id, resource_id, int(timeout_seconds),
    )

    # 执行 Agent（带超时保护）
    try:
        async with _generation_slots:
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
        logger.warning(
            "Agent[%s] 结果校验失败: resource_id=%s error=%s",
            agent_id, resource_id, exc,
        )
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
            # 产物、Agent 完成状态与 artifact_ready 事件必须同一事务提交。
            item, completed_event = await service.publish_agent_result(
                resource_id=resource_id,
                user_id=user_id,
                agent_id=agent_id,
                result=result,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
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

    await _observe(agent_id=agent_id, coro=events.publish_committed(completed_event))
    logger.info(
        "Agent[%s] 执行成功: resource_id=%s title=%s artifact_id=%s elapsed_ms=%d",
        agent_id, resource_id, result.title[:80], str(item.id), elapsed_ms,
    )

    output: dict[str, Any] = {"results": {agent_id: True}}
    if agent_id in {"content", "mindmap", "quiz", "code", "reading"}:
        content = result.content if isinstance(result.content, str) else json.dumps(result.content, ensure_ascii=False)
        materials = extract_core_content(
            markdown=content,
            agent_id=agent_id,
            config={key: value for key, value in input_data.agent_config.items() if key != "agent_id"},
        )
        output["handoffs"] = {
            agent_id: DownstreamContext(
                source_agent=agent_id,
                title=result.title,
                one_sentence_summary=" ".join(content.split())[:300],
                materials=materials,
            )
        }
    return output


async def execute_resource_agent(
    *,
    user_id: int,
    resource_id: int,
    agent_id: str,
    input_data: "ResourceInput",
) -> dict[str, Any]:
    """执行单个资源 Agent 的 generate_resource 入口。"""
    logger.info(
        "[Execution] 执行Agent: resource_id=%s agent_id=%s",
        resource_id, agent_id,
    )
    # 走多智能体资源流程（generate_resource）
    return await _run_agent_lifecycle(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=agent_id,
        input_data=input_data,
        generate_fn=lambda a: a.generate_resource(input_data),
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
        await events.send(
            agent_id,
            "failed",
            error_message,
            0,
            data={"phase": stage, "elapsed_ms": elapsed_ms},
        )
    except Exception as e:
        logger.error("Agent[%s] 记录失败状态到数据库失败: %s", agent_id, e)

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
