# -*- coding: utf-8 -*-
"""Agent 运行器。

负责单个 Agent 的执行和结果处理。
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from app.infra.logging import get_logger
from app.resource.registry import (
    AGENT_CLASSES,
    agent_difficulty,
    agent_format,
    agent_objectives,
    agent_priority,
    agent_role,
    agent_stage,
    agent_time,
    layer_stage,
)
from app.resource.schemas import (
    AgentTask,
    GeneratedResourceItem,
    ResourceAgentId,
    ResourceGenerationRequest,
    WorkerState,
)

logger = get_logger(__name__)


class AgentRunner:
    """Agent 运行器：执行单个 Agent 并处理结果。"""

    def __init__(self, emitter: Any, store: Any) -> None:
        self.emitter = emitter
        self.store = store

    async def run(
        self,
        *,
        agent_task: AgentTask,
        ctx: Any,  # WorkflowContext
        request: ResourceGenerationRequest,
        upstream: dict[str, dict[str, Any]],
        degraded: bool,
        missing: list[str],
        failed_deps: list[str],
    ) -> tuple[str, dict[str, Any], bool, AgentTask]:
        """执行单个 Agent。"""
        task = agent_task  # 兼容内部变量命名
        agent_id = task.agent_id
        agent_cls = AGENT_CLASSES.get(agent_id)
        if agent_cls is None:
            return agent_id, {"success": False, "error": f"Unknown agent: {agent_id}"}, task.is_explicit, task

        stage = layer_stage(task.layer)
        self.emitter.bind_agent_stage(agent_id, stage)

        await self._emit_prepare(agent_id, task, stage, request, upstream, ctx)

        worker = agent_cls(ctx.user_id, ctx.resource_id, emitter=self.emitter)
        task_payload = {
            "learning_need": request.learning_need,
            "task_description": task.task_description,
            "planning_reason": task.planning_reason,
        }
        dep_reports = {
            dep: upstream[dep].get("summary", "")
            for dep in task.depends_on
            if dep in upstream
        }

        await self._emit_generating(agent_id, task, stage)

        state = WorkerState(
            user_id=ctx.user_id,
            resource_id=ctx.resource_id,
            agent_name=agent_id,
            task=task_payload,
            learner_profile=ctx.profile,
            agent_config=task.config,
            workflow_plan=[],
            layer_index=task.layer,
            upstream_results=upstream,
            dependency_reports=dep_reports,
            learning_scenario=request.learning_scenario.value,
            planner_input_params=task.input_params,
            output_requirements=task.output_requirements,
            personalized_constraints=task.personalized_constraints,
            degraded=degraded,
            missing_dependencies=missing,
            failed_dependencies=failed_deps,
        )

        result = await worker.run(state)
        return agent_id, result.model_dump() if hasattr(result, "model_dump") else dict(result), task.is_explicit, task

    async def handle_result(
        self,
        agent_id: str,
        agent_result: dict[str, Any],
        is_explicit: bool,
        task: AgentTask,
        ctx: Any,  # WorkflowContext
        result: Any,  # DagResult
        done: set[str],
        failed_set: set[str],
        layer_terminal: dict[int, set[str]],
        start_time: float | None = None,
    ) -> None:
        """处理 Agent 执行结果。"""
        agent_elapsed_ms = 0
        if start_time:
            agent_elapsed_ms = int((time.time() - start_time) * 1000)

        if ctx.timing is not None and agent_id:
            ctx.timing["agents"][agent_id] = agent_elapsed_ms
            logger.info("[AgentRunner] Agent %s 完成: %dms", agent_id, agent_elapsed_ms)

        result.results[agent_id] = agent_result
        stage = layer_stage(task.layer)

        if agent_result.get("success"):
            try:
                saved = await self._save_result(
                    agent_id, agent_result, is_explicit, task, ctx, stage
                )
                if saved:
                    done.add(agent_id)
                    result.resources.append(saved)
                    layer_terminal.setdefault(task.layer, set()).add(agent_id)
            except Exception as exc:
                agent_result = {"success": False, "error": str(exc)}
                result.results[agent_id] = agent_result
                failed_set.add(agent_id)
                result.failed.append(agent_id)
                result.errors.append(f"{agent_id} 生成失败: {exc}")
        else:
            failed_set.add(agent_id)
            result.failed.append(agent_id)
            result.errors.append(f"{agent_id} 生成失败: {agent_result.get('error', 'unknown')}")
            await self.emitter.emit_agent(
                agent=agent_id,
                status="failed",
                stage=stage,
                message=f"{agent_role(agent_id)}生成失败",
                payload={
                    "error": agent_result.get("error", "unknown"),
                    "layer": task.layer,
                    "layer_name": task.layer_name,
                    "task_description": task.task_description,
                    "elapsed_ms": agent_elapsed_ms,
                },
            )
            layer_terminal.setdefault(task.layer, set()).add(agent_id)

    async def _emit_prepare(
        self,
        agent_id: str,
        task: AgentTask,
        stage: str,
        request: ResourceGenerationRequest,
        upstream: dict[str, dict[str, Any]],
        ctx: Any,
    ) -> None:
        """发送准备事件。"""
        await self.emitter.emit_agent_step(
            agent=agent_id,
            message=f"{agent_role(agent_id)}正在准备生成",
            stage=stage,
            status="running",
            action="prepare_generation",
            current_step=1,
            total_steps=3,
            step_label="准备生成",
            payload={
                "layer": task.layer,
                "layer_name": task.layer_name,
                "agent_id": agent_id,
                "agent_role": agent_role(agent_id),
                "task_description": task.task_description,
                "depends_on": task.depends_on,
                "resource_type": task.resource_type or agent_id,
                "upstream_agents": list(upstream.keys()),
                "has_profile": bool(ctx.profile),
                "learning_need_preview": request.learning_need[:120],
                "input_params": task.input_params,
                "output_requirements": task.output_requirements,
                "personalized_constraints": task.personalized_constraints,
                "planning_reason": task.planning_reason,
            },
        )

    async def _emit_generating(
        self,
        agent_id: str,
        task: AgentTask,
        stage: str,
    ) -> None:
        """发送生成中事件。"""
        await self.emitter.emit_agent_step(
            agent=agent_id,
            stage=stage,
            status="running",
            message=f"{agent_role(agent_id)}正在调用模型生成内容",
            action="llm_generating",
            current_step=2,
            total_steps=3,
            step_label="模型生成",
            payload={"agent_id": agent_id, "depends_on": task.depends_on},
        )

    async def _save_result(
        self,
        agent_id: str,
        result: dict[str, Any],
        is_explicit: bool,
        task: AgentTask,
        ctx: Any,
        stage: str,
    ) -> GeneratedResourceItem | None:
        """保存成功 Agent 的产物。"""
        item = self._make_resource(agent_id, result, task.depends_on, task)
        try:
            saved = await self.store.save_resource_item(
                resource_id=ctx.resource_id,
                user_id=ctx.user_id,
                item=item,
            )
            if saved.id is not None:
                item.id = str(saved.id)
            await self.emitter.emit_agent(
                agent=agent_id,
                status="success",
                stage=stage,
                message=f"{agent_role(agent_id)}生成完成",
                payload={
                    "resource_id": item.id,
                    "resource_type": item.type.value,
                    "title": item.title,
                    "summary": item.summary,
                    "is_explicit": is_explicit,
                },
            )
            await self.emitter.emit_resource(
                agent=agent_id,
                resource=item,
                stage=stage,
                message=f"{agent_role(agent_id)}生成完成",
            )
            return item
        except Exception as exc:
            await self.emitter.emit_agent(
                agent=agent_id,
                status="failed",
                stage=stage,
                message=f"{agent_role(agent_id)}数据库保存失败",
            )
            raise RuntimeError(f"{agent_id} 保存失败: {exc}") from exc

    def _make_resource(
        self,
        agent_id: str,
        result: dict[str, Any],
        depends_on: list[str],
        task: AgentTask | None = None,
    ) -> GeneratedResourceItem:
        """构建资源项。"""
        raw = result.get("content", "")
        parsed: Any = raw
        fmt = agent_format(agent_id)

        if agent_id == "diagram":
            parsed = self._normalize_diagram(raw)
            fmt = "mermaid" if parsed.get("render_format") == "mermaid" else "json"
        elif agent_id == "code":
            parsed = self._normalize_code(raw)
            fmt = "json"
        elif agent_id == "reading":
            parsed = self._normalize_reading(raw)
            fmt = "json"
        elif fmt == "json":
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                parsed = {"raw": raw}

        summary_data = result.get("summary_data") or {}
        metadata = dict(result.get("metadata") or {})
        metadata["summary_data"] = summary_data
        metadata.update({
            "agent": f"{agent_id.capitalize()}Agent",
            "agent_role": agent_role(agent_id),
            "depends_on": depends_on,
            "knowledge_points": self._extract_knowledge_points(agent_id, result, task),
            "difficulty": metadata.get("difficulty") or agent_difficulty(agent_id),
            "suitable_stage": metadata.get("suitable_stage") or agent_stage(agent_id),
            "estimated_time": metadata.get("estimated_time") or agent_time(agent_id),
            "personalized_reason": (task.planning_reason if task else None) or metadata.get("personalized_reason") or "",
            "learning_objectives": metadata.get("learning_objectives") or agent_objectives(agent_id),
            "prerequisites": metadata.get("prerequisites") or depends_on,
            "resource_priority": metadata.get("resource_priority") or agent_priority(agent_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        return GeneratedResourceItem(
            type=ResourceAgentId(agent_id),
            title=result.get("title") or f"学习资源 - {agent_id}",
            format=fmt,
            content=parsed,
            summary=result.get("summary") or f"{agent_id} 资源已生成",
            summary_data=summary_data,
            execution_report=result.get("execution_report"),
            metadata=metadata,
        )

    def _normalize_diagram(self, raw: Any) -> dict[str, Any]:
        """标准化 diagram 内容。"""
        if isinstance(raw, dict):
            if "source" in raw:
                return raw
            render = raw.get("render")
            if isinstance(render, dict) and render.get("source"):
                return {
                    "diagram_type": raw.get("diagram_type") or raw.get("type") or "hierarchy",
                    "render_format": render.get("engine", "mermaid"),
                    "source": render.get("source", ""),
                    "description": raw.get("description") or raw.get("summary", "知识图解"),
                }
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return self._normalize_diagram(parsed)
            except Exception:
                return {
                    "diagram_type": "hierarchy",
                    "render_format": "mermaid",
                    "source": raw,
                    "description": "知识图解",
                }
        return {
            "diagram_type": "hierarchy",
            "render_format": "mermaid",
            "source": "",
            "description": "知识图解",
        }

    def _normalize_code(self, raw: Any) -> dict[str, Any]:
        """标准化 code 内容。"""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            return {
                "language": "python",
                "code": raw,
                "explanation": "代码实操案例",
                "input_example": "",
                "output_example": "",
                "complexity": {"time": "", "space": ""},
                "run_steps": [],
                "debug_tips": [],
                "exercises": [],
            }
        return {
            "language": "python",
            "code": "",
            "explanation": "",
            "input_example": "",
            "output_example": "",
            "complexity": {"time": "", "space": ""},
            "run_steps": [],
            "debug_tips": [],
            "exercises": [],
        }

    def _normalize_reading(self, raw: Any) -> dict[str, Any]:
        """标准化 reading 内容。"""
        if isinstance(raw, dict):
            if "items" in raw:
                return raw
            return {"items": [raw]}
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return self._normalize_reading(parsed)
            except Exception:
                return {
                    "items": [{
                        "title": "拓展阅读",
                        "type": "article",
                        "description": raw,
                        "reason": "",
                        "difficulty": "medium",
                        "url": "",
                    }]
                }
        return {"items": []}

    def _extract_knowledge_points(
        self,
        agent_id: str,
        result: dict[str, Any],
        task: AgentTask | None,
    ) -> list[str]:
        """提取知识点。"""
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        points = metadata.get("knowledge_points")
        if not points and task:
            points = task.input_params.get("knowledge_points")
        if isinstance(points, list):
            return [str(item) for item in points if item]
        return [agent_id]