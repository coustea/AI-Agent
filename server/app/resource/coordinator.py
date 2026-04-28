"""
Coordinator Agent：画像加载 + 任务规划 + 分阶段编排 + SSE 实时推送。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from app.infra.llm import get_llm_manager

from app.infra.logging import get_logger
from app.resource.events import AgentEventEmitter
from app.resource.exceptions import PlanningError
from app.resource.schemas import LearnerProfileSnapshot, PersonalizedTaskContext, ResourcePlan
from app.shared.json_utils import parse_first_json_object
from app.resource.utils import (
    get_agent_registry,
    build_default_resource_plan,
    merge_planner_plan_into_default,
    normalize_selected_resources,
    merge_extra,
    load_profile_snapshot,
    build_personalized_context,
)
from app.shared.paths import RESOURCE_DIR

logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompts"
PLANNER_PROMPT_PATH = PROMPT_DIR / "planner.md"


def _attach_file_url(result: dict, resource_id: int) -> dict:
    file_path = result.get("file_path")
    if not file_path:
        return result
    filename = Path(str(file_path)).name
    if not filename:
        return result
    return {
        **result,
        "file_url": f"/api/v1/ai/resources/{resource_id}/files/{filename}",
    }


def _relocate_ppt_to_resource_dir(result: dict, user_id: int, resource_id: int) -> dict:
    """将 PPT agent 输出的文件从 workplace/ppt/ 复制到 resource/{user_id}/{resource_id}/ 下，
    以便统一通过 /resources/{id}/files/{name} 端点下载。"""
    file_path = result.get("file_path")
    if not file_path:
        return result
    src = Path(str(file_path))
    if not src.exists():
        return result
    target_dir = RESOURCE_DIR / str(user_id) / str(resource_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / src.name
    shutil.copy2(str(src), str(dst))
    logger.info("[Coordinator] PPT 文件已复制: %s -> %s", src, dst)
    return {**result, "file_path": str(dst)}


def _filter_kwargs_for_callable(fn, kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(fn)
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
        return kwargs

    allowed = {
        name
        for name, param in signature.parameters.items()
        if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    return {key: value for key, value in kwargs.items() if key in allowed}


class PlannerTaskParameterSchema(BaseModel):
    topic: str = ""
    major: str = ""
    course: str = ""
    gap: str = ""
    need: str = ""
    extra: str = ""
    target_md_path: str = ""
    edit_instruction: str = ""
    output_md_path: str = ""


class PlannerTaskSchema(BaseModel):
    agent: str
    description: str = ""
    parameters: PlannerTaskParameterSchema = Field(default_factory=PlannerTaskParameterSchema)


class PlannerPlanOutput(BaseModel):
    tasks: list[PlannerTaskSchema] = Field(default_factory=list)
    execution_groups: list[list[str]] = Field(default_factory=list)
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    failure_policy: dict[str, str] = Field(default_factory=dict)
    visible_agents: list[str] = Field(default_factory=list)
    hidden_dependency_agents: list[str] = Field(default_factory=list)
    execution_agents: list[str] = Field(default_factory=list)
    agent_parameters: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CoordinatorAgent:
    def __init__(self, emitter: AgentEventEmitter, resource_store):
        self.emitter = emitter
        self.resource_store = resource_store
        self.llm_manager = get_llm_manager()
        self.planner_model_kwargs = {"streaming": False}
        logger.info("[Coordinator] 初始化完成: planner_model=deepseek strict_function_calling")

    async def run(
        self,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ) -> dict:
        logger.info(
            "[Coordinator] 开始执行资源生成: user_id=%s course=%r need=%r selected_resources=%s",
            user_id,
            task.get("course", ""),
            task.get("need", "review"),
            selected_resources,
        )
        await self.emitter.emit_workflow("profile_loading", "正在读取学习者画像...")
        snapshot = await self._safe_load_profile(user_id)
        personalized_context = build_personalized_context(snapshot, task)
        logger.info(
            "[Coordinator] 个性化上下文已生成: difficulty=%s styles=%s emphasis_count=%s",
            personalized_context.target_difficulty,
            personalized_context.explanation_style,
            len(personalized_context.emphasis),
        )

        allowed_agents = self._normalize_selected_resources(selected_resources)
        logger.info("[Coordinator] 归一化资源范围: %s", allowed_agents or "ALL")
        await self.emitter.emit_workflow("planning", "正在生成个性化资源计划...")
        resource_plan = await self._safe_build_plan(
            task=task,
            snapshot=snapshot,
            personalized_context=personalized_context,
            allowed_agents=allowed_agents,
        )
        logger.info(
            "[Coordinator] 资源计划已确定: groups=%s requested=%s execution=%s visible=%s hidden=%s failure_policy=%s",
            resource_plan.execution_groups,
            resource_plan.requested_agents,
            resource_plan.execution_agents,
            resource_plan.visible_agents,
            resource_plan.hidden_dependency_agents,
            resource_plan.failure_policy,
        )

        # 先创建主表记录，获取 resource_id
        await self.emitter.emit_workflow("persisting", "正在创建资源记录...")
        resource_record = await self.resource_store.create_resource(
            user_id=user_id,
            course=task.get("course", ""),
            gap=task.get("gap", ""),
            need=task.get("need", "review"),
            request_extra=task.get("extra", ""),
        )
        resource_id = resource_record.id
        logger.info("[Coordinator] 主表记录已创建: resource_id=%s", resource_id)

        # 更新主表的规划结果
        await self.resource_store.update_resource_status(
            resource_id=resource_id,
            status="running",
            plan_result=json.dumps(resource_plan.model_dump(), ensure_ascii=False),
        )

        final: dict[str, dict] = {}
        context_bag: dict[str, dict] = {}
        completed_count = 0
        total_agents = len(resource_plan.ordered_agents)
        visible_set = set(resource_plan.visible_agents)
        hidden_set = set(resource_plan.hidden_dependency_agents)
        visible_completed_count = 0
        visible_total = len(resource_plan.visible_agents)

        for group_index, group_agents in enumerate(resource_plan.execution_groups, start=1):
            if not group_agents:
                logger.info("[Coordinator] 跳过空执行组: index=%s", group_index)
                continue

            # 每个执行组只读取此前已完成的黑板结果，避免下游拿到半成品。
            logger.info(
                "[Coordinator] 进入执行组: index=%s/%s agents=%s shared_memory_keys=%s",
                group_index,
                len(resource_plan.execution_groups),
                group_agents,
                list(context_bag.keys()),
            )
            await self.emitter.emit_workflow(
                "execution_group",
                f"第 {group_index}/{len(resource_plan.execution_groups)} 组已启动：{', '.join(group_agents)}",
                group_index=group_index,
                group_total=len(resource_plan.execution_groups),
                agents=group_agents,
                execution_group=group_agents,
            )

            futures = []
            skipped_results: list[tuple[str, dict]] = []
            for agent_name in group_agents:
                dependency_failures = self._dependency_failures(agent_name, resource_plan, final)
                policy = resource_plan.failure_policy.get(agent_name, "independent_fail")
                await self.emitter.emit_agent_status(
                    agent_name,
                    "queued",
                    f"等待进入第 {group_index} 组",
                    stage="execution_group",
                    visible=agent_name in visible_set,
                    dependency_only=agent_name in hidden_set,
                    dependencies=resource_plan.dependencies.get(agent_name, []),
                    failure_policy=policy,
                )
                if dependency_failures and policy == "skip_on_dependency_failed":
                    skipped_result = await self._skip_agent(
                        agent_name=agent_name,
                        dependency_failures=dependency_failures,
                        visible_agents=visible_set,
                    )
                    skipped_results.append((agent_name, skipped_result))
                    continue

                agent_memory = self._shared_memory_for_agent(agent_name, resource_plan, context_bag)
                if dependency_failures and policy == "degraded_run":
                    await self.emitter.emit_agent_log(
                        agent_name,
                        f"上游依赖未全部成功，将降级生成：{', '.join(dependency_failures)}",
                        dependency_failures=dependency_failures,
                    )
                futures.append(
                    asyncio.create_task(
                        self._run_agent_with_name(
                            agent_name=agent_name,
                            params=resource_plan.agent_parameters.get(agent_name, {}),
                            profile=snapshot.as_agent_profile(),
                            personalized_context=personalized_context,
                            shared_memory=agent_memory,
                            visible_agents=visible_set,
                            user_id=user_id,
                            resource_id=resource_id,
                        )
                    )
                )

            for agent_name, result in skipped_results:
                final[agent_name] = result
                completed_count += 1
                if agent_name in visible_set:
                    visible_completed_count += 1
                await self.emitter.emit_bundle_update(
                    completed=completed_count,
                    total=total_agents,
                    core_ready=self._core_ready(resource_plan, final),
                    latest_agent=agent_name,
                    visible_completed=visible_completed_count,
                    visible_total=visible_total,
                )

            for future in asyncio.as_completed(futures):
                agent_name, result = await future
                final[agent_name] = result
                if result.get("success"):
                    # 只有成功产物才写回黑板，避免坏结果污染后续依赖链。
                    context_bag[agent_name] = result
                    logger.info("[Coordinator] 黑板已更新: agent=%s keys=%s", agent_name, list(context_bag.keys()))
                else:
                    logger.warning(
                        "[Coordinator] Agent 未产出可用结果: agent=%s error=%r",
                        agent_name,
                        result.get("error"),
                    )
                completed_count += 1
                if agent_name in visible_set:
                    visible_completed_count += 1
                await self.emitter.emit_bundle_update(
                    completed=completed_count,
                    total=total_agents,
                    core_ready=self._core_ready(resource_plan, final),
                    latest_agent=agent_name,
                    visible_completed=visible_completed_count,
                    visible_total=visible_total,
                )
            logger.info("[Coordinator] 执行组结束: index=%s completed=%s/%s", group_index, completed_count, total_agents)

        # 异步保存子表记录并更新主表状态（不阻塞主流程）
        asyncio.create_task(self.resource_store.persist_all_results(resource_id, final))
        logger.info("[Coordinator] 执行结束: user_id=%s resource_id=%s completed_agents=%s visible_agents=%s", user_id, resource_id, list(final.keys()), resource_plan.visible_agents)
        await self.emitter.emit_done("资源包构建完成")
        visible_final = {
            agent: final[agent]
            for agent in resource_plan.visible_agents
            if agent in final
        }
        return visible_final

    async def _safe_load_profile(self, user_id: int) -> LearnerProfileSnapshot:
        try:
            snapshot = await load_profile_snapshot(user_id)
            profile_markdown = snapshot.profile_markdown or "暂无画像"
            logger.info(
                "[Coordinator] 画像快照加载成功: user_id=%s major=%r version=%s",
                user_id,
                snapshot.major,
                snapshot.version,
            )
            await self.emitter.emit_agent_log("coordinator", f"画像加载成功")
            return snapshot
        except Exception as exc:
            logger.error("[Coordinator] 画像加载失败: %s", exc, exc_info=exc)
            await self.emitter.emit_agent_log("coordinator", f"画像加载失败，将使用默认画像上下文：{exc}")
            return LearnerProfileSnapshot(user_id=user_id)

    async def _safe_build_plan(
        self,
        task: dict,
        snapshot: LearnerProfileSnapshot,
        personalized_context: PersonalizedTaskContext,
        allowed_agents: list[str] | None,
    ) -> ResourcePlan:
        base_plan = build_default_resource_plan(task, allowed_agents)
        logger.info(
            "[Coordinator] 默认资源计划已构建: groups=%s ordered_agents=%s requested=%s execution=%s visible=%s hidden=%s",
            base_plan.execution_groups,
            base_plan.ordered_agents,
            base_plan.requested_agents,
            base_plan.execution_agents,
            base_plan.visible_agents,
            base_plan.hidden_dependency_agents,
        )
        for parameters in base_plan.agent_parameters.values():
            # 这里先补齐画像增强参数，Planner 失败时也能继续执行默认流程。
            parameters["major"] = snapshot.major or parameters.get("major", "")
            parameters["extra"] = self._merge_extra(
                parameters.get("extra", ""),
                personalized_context,
            )

        try:
            planner_plan = await self._plan(
                task=task,
                snapshot=snapshot,
                personalized_context=personalized_context,
                allowed_agents=base_plan.execution_agents,
                requested_agents=base_plan.requested_agents,
                hidden_dependency_agents=base_plan.hidden_dependency_agents,
            )
            logger.info("[Coordinator] Planner 规划成功，开始合并参数")
            return merge_planner_plan_into_default(base_plan, planner_plan)
        except PlanningError as exc:
            logger.error("[Coordinator] 规划失败: %s", exc)
            await self.emitter.emit_agent_log("coordinator", f"规划失败，使用默认资源计划：{exc}")
            return base_plan
        except Exception as exc:
            logger.error("[Coordinator] 规划异常: %s", exc, exc_info=exc)
            await self.emitter.emit_agent_log("coordinator", "规划异常，使用默认资源计划")
            return base_plan

    async def _plan(
        self,
        task: dict,
        snapshot: LearnerProfileSnapshot,
        personalized_context: PersonalizedTaskContext,
        allowed_agents: list[str] | None,
        requested_agents: list[str] | None = None,
        hidden_dependency_agents: list[str] | None = None,
    ) -> ResourcePlan:
        if not PLANNER_PROMPT_PATH.exists():
            raise PlanningError(f"Planner prompt 不存在: {PLANNER_PROMPT_PATH}")

        resource_scope = (
            "未指定，默认生成全部资源类型。"
            if allowed_agents is None
            else (
                f"执行范围(含依赖补全): {', '.join(allowed_agents)}；"
                f"用户请求返回: {', '.join(requested_agents or [])}；"
                f"依赖补全(默认不返回前端): {', '.join(hidden_dependency_agents or []) or '无'}"
            )
        )
        prompt_text = PLANNER_PROMPT_PATH.read_text(encoding="utf-8")
        formatted = prompt_text.format(
            user_input=json.dumps(task, ensure_ascii=False),
            profile=json.dumps(snapshot.as_agent_profile(), ensure_ascii=False),
            personalized_context=json.dumps(personalized_context.as_prompt_context(), ensure_ascii=False),
            resource_scope=resource_scope,
        )
        messages = [
            SystemMessage(content=formatted),
            HumanMessage(content="请根据以上信息生成资源任务规划。"),
        ]
        logger.info(
            "[Coordinator] 正在调用 Planner (json_object): course=%r allowed_agents=%s prompt_path=%s",
            task.get("course", ""),
            allowed_agents or "ALL",
            PLANNER_PROMPT_PATH,
        )
        response = await self.llm_manager.ainvoke_structured(
            "deepseek",
            PlannerPlanOutput,
            messages,
            strict=True,
            model_kwargs=self.planner_model_kwargs,
        )

        agent_parameters = dict(response.agent_parameters)
        for task_item in response.tasks:
            dumped = task_item.model_dump()
            agent = dumped.get("agent")
            if not agent:
                continue
            agent_parameters[agent] = {
                **agent_parameters.get(agent, {}),
                **(dumped.get("parameters") or {}),
            }

        plan = ResourcePlan(
            execution_groups=response.execution_groups,
            dependencies=response.dependencies,
            failure_policy=response.failure_policy,
            visible_agents=response.visible_agents,
            hidden_dependency_agents=response.hidden_dependency_agents,
            execution_agents=response.execution_agents,
            agent_parameters=agent_parameters,
        )

        logger.info(
            "[Coordinator] Planner 返回执行计划: groups=%s visible=%s execution=%s",
            plan.execution_groups,
            plan.visible_agents,
            plan.execution_agents,
        )
        return plan

    async def _skip_agent(
        self,
        agent_name: str,
        dependency_failures: list[str],
        visible_agents: set[str],
    ) -> dict:
        entry = get_agent_registry()[agent_name]
        message = f"上游依赖失败，已跳过：{', '.join(dependency_failures)}"
        await self.emitter.emit_agent_status(
            agent_name,
            "skipped",
            message,
            visible=agent_name in visible_agents,
            dependency_failures=dependency_failures,
            skipped_reason=message,
            failure_policy="skip_on_dependency_failed",
        )
        return {
            "success": False,
            "skipped": True,
            "type": entry.type,
            "title": entry.role,
            "content": "",
            "error": message,
        }

    @staticmethod
    def _dependency_failures(
        agent_name: str,
        plan: ResourcePlan,
        results: dict[str, dict],
    ) -> list[str]:
        failures: list[str] = []
        for dep in plan.dependencies.get(agent_name, []):
            dep_result = results.get(dep)
            if dep_result is not None and not dep_result.get("success"):
                failures.append(dep)
        return failures

    @staticmethod
    def _shared_memory_for_agent(
        agent_name: str,
        plan: ResourcePlan,
        context_bag: dict[str, dict],
    ) -> dict[str, dict]:
        dependencies = plan.dependencies.get(agent_name, [])
        if not dependencies:
            return {}
        return {
            dep: context_bag[dep]
            for dep in dependencies
            if dep in context_bag
        }

    async def _run_agent(
        self,
        agent_name: str,
        params: dict,
        profile: dict,
        personalized_context: PersonalizedTaskContext,
        shared_memory: dict,
        visible_agents: set[str] | None = None,
        user_id: int = 0,
        resource_id: int = 0,
    ) -> dict:
        entry = get_agent_registry()[agent_name]
        is_visible = True if visible_agents is None else (agent_name in visible_agents)
        logger.info(
            "[Coordinator] Agent 启动: agent=%s stage=%s visible=%s params_keys=%s shared_memory_keys=%s",
            agent_name,
            entry.stage,
            is_visible,
            list(params.keys()),
            list(shared_memory.keys()),
        )
        await self.emitter.emit_agent_status(
            agent_name,
            "running",
            f"{entry.role} 正在执行 {entry.desc}",
            visible=is_visible,
            dependency_only=not is_visible,
        )

        profile_markdown = profile.get("profile_markdown") or "暂无画像"
        await self.emitter.emit_agent_log(agent_name, f"已注入学习画像：{profile_markdown[:100]}...")
        if shared_memory:
            await self.emitter.emit_agent_log(agent_name, f"已读取上游成果：{', '.join(shared_memory.keys())}")
        else:
            await self.emitter.emit_agent_log(agent_name, "当前作为首批智能体启动，无上游成果依赖")

        kwargs: dict[str, Any] = {
            "topic": params.get("topic", ""),
            "course": params.get("course", ""),
            "major": params.get("major", ""),
            "gap": params.get("gap", ""),
            "user_profile": profile,
            "shared_memory": shared_memory,
            "user_id": user_id,
            "resource_id": resource_id,
            **entry.extra_kwargs,
        }
        for key in ("target_md_path", "edit_instruction", "output_md_path"):
            if key in params:
                kwargs[key] = params.get(key)
        if agent_name == "ppt":
            for key in ("template_id", "template_source_url", "template_config_url"):
                if key in params:
                    kwargs[key] = params.get(key)
        if agent_name == "mindmap":
            # 导图 Agent 需要额外的学习目标和补充说明来调整导图粒度。
            kwargs["need"] = params.get("need", "review")
            kwargs["extra"] = params.get("extra", "")

        try:
            logger.info("[Coordinator] 调用 Agent 方法: agent=%s method=%s", agent_name, entry.method)
            fn = getattr(entry.agent_loader(), entry.method)
            kwargs = _filter_kwargs_for_callable(fn, kwargs)
            result = await fn(**kwargs)
        except Exception as exc:
            logger.error("[Coordinator] Agent %s 执行失败: %s", agent_name, exc, exc_info=exc)
            message = str(exc)
            await self.emitter.emit_agent_status(agent_name, "failed", message)
            return {
                "success": False,
                "type": entry.type,
                "title": entry.role,
                "content": "",
                "error": message,
            }

        success = bool(result.get("success"))
        if success:
            # PPT 文件保存到 workplace/ppt/，需要复制到 resource 目录
            if agent_name == "ppt":
                result = _relocate_ppt_to_resource_dir(result, user_id, resource_id)
            summary = entry.result_summary(result)
            logger.info("[Coordinator] Agent 执行成功: agent=%s summary=%s", agent_name, summary)
            await self.emitter.emit_agent_status(
                agent_name,
                "success",
                f"生成完成：{summary}",
                visible=is_visible,
                dependency_only=not is_visible,
            )
            if is_visible:
                await self.emitter.emit_artifact_ready(agent_name, _attach_file_url(result, resource_id))
            else:
                await self.emitter.emit_agent_log(
                    agent_name,
                    "该资源属于依赖补全产物，已用于下游执行，默认不对前端返回。",
                    visible=False,
                    dependency_only=True,
                )
        else:
            logger.warning(
                "[Coordinator] Agent 执行完成但未成功: agent=%s error=%r",
                agent_name,
                result.get("error"),
            )
            await self.emitter.emit_agent_status(
                agent_name,
                "failed",
                result.get("error", "生成失败"),
                visible=is_visible,
                dependency_only=not is_visible,
            )
        return result

    async def _run_agent_with_name(
        self,
        agent_name: str,
        params: dict,
        profile: dict,
        personalized_context: PersonalizedTaskContext,
        shared_memory: dict,
        visible_agents: set[str] | None = None,
        user_id: int = 0,
        resource_id: int = 0,
    ) -> tuple[str, dict]:
        result = await self._run_agent(
            agent_name=agent_name,
            params=params,
            profile=profile,
            personalized_context=personalized_context,
            shared_memory=shared_memory,
            visible_agents=visible_agents,
            user_id=user_id,
            resource_id=resource_id,
        )
        return agent_name, result

    @staticmethod
    def _merge_extra(existing_extra: str, personalized_context: PersonalizedTaskContext) -> str:
        return merge_extra(existing_extra, personalized_context)

    @staticmethod
    def _normalize_selected_resources(selected_resources: list[str] | None) -> list[str] | None:
        return normalize_selected_resources(selected_resources)

    @staticmethod
    def _core_ready(plan: ResourcePlan, results: dict[str, dict]) -> bool:
        for agent_name in plan.visible_agents:
            if agent_name in ("content", "mindmap", "quiz") and not results.get(agent_name, {}).get("success"):
                return False
        return True
