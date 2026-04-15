"""
Coordinator Agent：DAG 任务规划 + 分阶段编排 + SSE 实时推送。

工作流：
1. 从数据库读取用户画像 (Long-Term Memory)
2. Planner 分析需求 → 拆解为子任务
3. 按 DAG 阶段顺序执行各子 Agent（阶段内并行，阶段间串行）
4. 使用"黑板模式"：将当前所有的生成结果 (context_bag) 传递给子 Agent 的 shared_memory
5. 每个 Agent 完成后通过 emitter 推送 SSE 事件
6. 汇总结果，推送 done
"""

import os
import json
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.engine import engine
from app.core.logging import get_logger
from app.runtime.resource.events import AgentEventEmitter
from app.agents.resource.agents.mindmap import mindmap_generator
from app.agents.resource.agents.content import content_writer
from app.agents.resource.agents.quiz import quiz_agent
from app.agents.resource.agents.reading import reading_agent
from app.agents.resource.agents.code import code_agent
from app.agents.resource.agents.ppt import ppt_agent
from app.agents.resource.exceptions import (
    PlanningError,
    AgentExecutionError,
    ValidationError,
)

logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"
PLANNER_PROMPT_PATH = PROMPT_DIR / "planner.md"


from app.services.memory import memory_service

async def _load_profile(user_id: int) -> dict:
    profile = await memory_service.get_user_profile(user_id)
    if not profile:
        return {}
    return {
        "knowledge_level": profile.knowledge_level,
        "learning_goal": profile.learning_goal,
        "cognitive_style": profile.cognitive_style,
        "error_pattern": profile.error_pattern,
        "learning_pace": profile.learning_pace,
        "interest_preference": profile.interest_preference,
        "cognitive_level": profile.cognitive_level,
        "profile_summary": profile.profile_summary,
    }


# ──────────────────────────────────────────────────────────────
# P2：AgentEntry — 统一描述 Agent 元数据与调用方式
# ──────────────────────────────────────────────────────────────

@dataclass
class AgentEntry:
    """描述一个子 Agent 的注册信息。

    Attributes:
        role:           Agent 角色名（日志 / SSE 展示用）
        desc:           Agent 功能描述
        type:           产物类型标识（与数据库字段对应）
        agent:          Agent 实例，必须有 ``method`` 对应的异步方法
        method:         调用的异步方法名（如 "generate_mindmap"）
        result_summary: 从 result 字典提取摘要信息的函数，用于 SSE 日志
        extra_kwargs:   调用时额外传入的固定参数（可覆盖通用参数）
    """
    role: str
    desc: str
    type: str
    agent: Any
    method: str
    result_summary: Callable[[dict], str] = field(default=lambda r: "")
    extra_kwargs: dict = field(default_factory=dict)


# P2：统一注册表，新增 Agent 只需在此添加一行
AGENT_REGISTRY: dict[str, AgentEntry] = {
    "content": AgentEntry(
        role="Content Agent",
        desc="撰写深度知识精讲",
        type="doc",
        agent=content_writer,
        method="generate_content",
        result_summary=lambda r: f"，文档 {len(r.get('content', ''))} 字",
    ),
    "mindmap": AgentEntry(
        role="Mindmap Agent",
        desc="构建核心知识拓扑图",
        type="mindmap",
        agent=mindmap_generator,
        method="generate_mindmap",
        result_summary=lambda r: f"，拓扑图已生成 → {r.get('file_path')}",
    ),
    "quiz": AgentEntry(
        role="Quiz Agent",
        desc="生成分层练习题库",
        type="quiz",
        agent=quiz_agent,
        method="generate_quiz",
        result_summary=lambda r: f"，共 {len(r.get('questions', []))} 道题",
    ),
    "reading": AgentEntry(
        role="Reading Agent",
        desc="检索拓展阅读与论文",
        type="reading",
        agent=reading_agent,
        method="generate_reading",
        result_summary=lambda r: f"，共 {len(r.get('recommendations', []))} 条推荐",
    ),
    "code": AgentEntry(
        role="Code Agent",
        desc="编写可运行实操案例",
        type="code",
        agent=code_agent,
        method="generate_code",
        result_summary=lambda r: f"，语言: {r.get('detected_language', 'unknown')}",
    ),
    "ppt": AgentEntry(
        role="PPT Agent",
        desc="生成演示文稿大纲",
        type="ppt",
        agent=ppt_agent,
        method="generate_ppt",
        result_summary=lambda r: f"，大纲已生成",
    ),
}

DAG_PHASES = [
    {"name": "foundation", "label": "知识框架构建", "agents": ["mindmap"]},
    {"name": "core",       "label": "核心资源生成", "agents": ["content", "code"]},
    {"name": "enrichment", "label": "拓展资源丰富", "agents": ["quiz", "reading"]},
    {"name": "presentation", "label": "演示资源生成", "agents": ["ppt"]},
]

DEFAULT_RESOURCE_ORDER = [
    agent_name
    for phase in DAG_PHASES
    for agent_name in phase["agents"]
]


class CoordinatorAgent:
    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = ChatOpenAI(
            model=os.getenv("FAST_LLM_MODEL", "general"),
            api_key=os.getenv("FAST_LLM_API_KEY", os.getenv("OPENAI_API_KEY")),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0,
        )

    async def run(
        self,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ) -> dict:
        await self.emitter.emit_coordinator("parsing", "正在读取学习者画像...")
        profile = await self._safe_load_profile(user_id)
        allowed_agents = self._normalize_selected_resources(selected_resources)
        if allowed_agents is None:
            await self.emitter.emit_agent_log("coordinator", "未指定资源范围，按赛题要求执行全量资源生成")
        else:
            await self.emitter.emit_agent_log(
                "coordinator",
                f"已指定资源范围，仅生成: {', '.join(allowed_agents)}",
            )

        tasks = await self._safe_plan(task, profile, allowed_agents)
        await self.emitter.emit_coordinator(
            "dispatching", f"任务拆解完成，共 {len(tasks)} 个子任务，开始 DAG 分阶段调度..."
        )

        task_by_agent: dict[str, dict] = {t["agent"]: t for t in tasks}
        context_bag: dict[str, dict] = {}
        final: dict[str, dict] = {}

        for phase in DAG_PHASES:
            phase_agents = phase["agents"]
            active_in_phase = [a for a in phase_agents if a in task_by_agent]

            if not active_in_phase:
                continue

            await self.emitter.emit_coordinator(
                f"phase_{phase['name']}",
                f"阶段 [{phase['label']}]：调度 {', '.join(active_in_phase)}..."
            )

            coroutines = [
                self._run_agent(
                    agent_name,
                    task_by_agent[agent_name].get("parameters", {}),
                    profile,
                    shared_memory=context_bag,
                )
                for agent_name in active_in_phase
            ]

            phase_results = await asyncio.gather(*coroutines, return_exceptions=True)

            for agent_name, result in zip(active_in_phase, phase_results):
                if isinstance(result, Exception):
                    error_msg = f"{type(result).__name__}: {result}"
                    logger.error(f"[Coordinator] Agent {agent_name} 阶段异常: {error_msg}", exc_info=result)
                    await self.emitter.emit_agent_error(agent_name, error_msg)
                    final[agent_name] = {"error": error_msg, "success": False}
                else:
                    final[agent_name] = result
                    if result:
                        context_bag[agent_name] = result
                        logger.info(f"[Coordinator] Agent {agent_name} 已写入黑板，当前黑板 keys: {list(context_bag.keys())}")

        await self.emitter.emit_coordinator("integrating", "正在组装学习资源包并持久化...")
        try:
            await self._save_resource(user_id, task, final)
            success_count = sum(1 for v in final.values() if v.get("success"))
            await self.emitter.emit_agent_log(
                "coordinator", f"资源包入库完成: {success_count}/{len(final)} 个 Agent 成功产出"
            )
        except Exception as e:
            logger.error(f"[Coordinator] 保存资源记录失败: {e}", exc_info=True)
            await self.emitter.emit_agent_log("coordinator", f"⚠ 资源持久化失败: {e}")

        await self.emitter.emit_done("资源包构建完成")
        return final

    async def _safe_load_profile(self, user_id: int) -> dict:
        """安全加载用户画像，包含错误处理"""
        try:
            profile = await _load_profile(user_id)
            if profile:
                await self.emitter.emit_agent_log(
                    "coordinator",
                    f"画像加载成功: level={profile.get('knowledge_level', 'N/A')}, "
                    f"style={profile.get('cognitive_style', 'N/A')}"
                )
                logger.info(f"[Coordinator] 用户 {user_id} 画像加载完成")
            else:
                await self.emitter.emit_agent_log("coordinator", "未找到用户画像，将以默认配置运行")
            return profile or {}
        except Exception as e:
            logger.error(f"[Coordinator] 画像加载失败: {e}", exc_info=True)
            await self.emitter.emit_agent_log("coordinator", f"⚠ 画像加载异常: {e}，将跳过个性化")
            return {}

    async def _safe_plan(
        self,
        task: dict,
        profile: dict,
        allowed_agents: list[str] | None,
    ) -> list[dict]:
        """安全执行任务规划，包含错误处理和回退策略"""
        try:
            return await self._plan(task, profile, allowed_agents)
        except PlanningError as e:
            logger.error(f"[Coordinator] 规划失败: {e}")
            await self.emitter.emit_agent_log(
                "coordinator", f"⚠ 使用默认任务规划: {str(e)}"
            )
            return self._default_tasks(task, allowed_agents)
        except Exception as e:
            logger.error(f"[Coordinator] 规划异常: {e}", exc_info=True)
            await self.emitter.emit_agent_log(
                "coordinator", f"⚠ 规划异常，使用默认任务规划"
            )
            return self._default_tasks(task, allowed_agents)

    async def _plan(
        self,
        task: dict,
        profile: dict,
        allowed_agents: list[str] | None,
    ) -> list[dict]:
        await self.emitter.emit_coordinator("parsing", "正在分析学习需求，拆解任务...")
        await self.emitter.emit_agent_log("coordinator", "调用 LLM Planner 进行 DAG 任务规划...")
        prompt_text = PLANNER_PROMPT_PATH.read_text(encoding="utf-8")
        resource_scope = (
            "未指定，默认按赛题要求生成全部资源类型。"
            if allowed_agents is None
            else f"仅允许以下资源类型: {', '.join(allowed_agents)}"
        )
        formatted = prompt_text.format(
            user_input=json.dumps(task, ensure_ascii=False),
            profile=json.dumps(profile, ensure_ascii=False),
            resource_scope=resource_scope,
        )
        messages = [
            SystemMessage(content=formatted),
            HumanMessage(content="请根据以上信息进行任务拆解。"),
        ]
        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                content = "\n".join(lines).strip()
            plan = json.loads(content)
            tasks = plan.get("tasks", [])
            tasks = self._filter_tasks_by_selection(tasks, allowed_agents)
            logger.info(f"[Coordinator] 规划完成，共 {len(tasks)} 个子任务")
            await self.emitter.emit_agent_log(
                "coordinator", f"Planner 返回 {len(tasks)} 个子任务: {', '.join(t.get('agent', '?') for t in tasks)}"
            )
            return tasks
        except json.JSONDecodeError as e:
            logger.error(f"[Coordinator] Planner 返回非法 JSON: {e}")
            await self.emitter.emit_agent_log(
                "coordinator", f"⚠ Planner 输出解析失败 (JSONDecodeError)，回退到默认任务模板"
            )
            return self._default_tasks(task, allowed_agents)
        except Exception as e:
            logger.error(f"[Coordinator] 规划失败: {e}", exc_info=True)
            await self.emitter.emit_agent_log(
                "coordinator", f"⚠ Planner 调用异常 ({type(e).__name__}: {e})，回退到默认任务模板"
            )
            return self._default_tasks(task, allowed_agents)

    @staticmethod
    def _default_tasks(task: dict, allowed_agents: list[str] | None = None) -> list[dict]:
        agents = allowed_agents or DEFAULT_RESOURCE_ORDER
        return [
            {
                "agent": a,
                "description": f"为 {task.get('course', '')} 生成{AGENT_REGISTRY[a].desc}",
                "parameters": {
                    "topic": task.get("course", ""),
                    "major": "",
                    "course": task.get("course", ""),
                    "gap": task.get("gap", ""),
                    "need": task.get("need", "review"),
                    "extra": task.get("extra", ""),
                },
            }
            for a in agents
        ]

    @staticmethod
    def _normalize_selected_resources(selected_resources: list[str] | None) -> list[str] | None:
        if not selected_resources:
            return None

        normalized: list[str] = []
        seen: set[str] = set()
        for raw_name in selected_resources:
            name = str(raw_name).strip().lower()
            if not name:
                continue
            if name not in AGENT_REGISTRY or name in seen:
                continue
            normalized.append(name)
            seen.add(name)

        if not normalized:
            return None

        order_index = {name: idx for idx, name in enumerate(DEFAULT_RESOURCE_ORDER)}
        normalized.sort(key=lambda name: order_index[name])
        return normalized

    @staticmethod
    def _filter_tasks_by_selection(
        tasks: list[dict],
        allowed_agents: list[str] | None,
    ) -> list[dict]:
        if allowed_agents is None:
            return tasks
        allowed_set = set(allowed_agents)
        return [task for task in tasks if task.get("agent") in allowed_set]

    async def _run_agent(
        self,
        agent_name: str,
        params: dict,
        profile: dict,
        shared_memory: dict,
    ) -> dict:
        # P2：统一从注册表获取 Agent 信息，不再 if/elif
        entry = AGENT_REGISTRY.get(agent_name)
        if entry is None:
            await self.emitter.emit_agent_error(agent_name, f"未知智能体: {agent_name}")
            return {}

        agent_id = agent_name
        await self.emitter.emit_agent_start(agent_id)
        await self.emitter.emit_agent_log(agent_id, f"[{entry.role}] 已唤醒，任务: {entry.desc}")

        # ── 阶段 1：注入用户画像与黑板记忆 ──
        profile_summary = ""
        if profile:
            level = profile.get("knowledge_level", "")
            style = profile.get("cognitive_style", "")
            parts = [p for p in [level, style] if p]
            profile_summary = f"（{', '.join(parts)}）" if parts else ""
        await self.emitter.emit_agent_log(
            agent_id, f"加载学习者画像 {profile_summary}，注入长时记忆上下文..."
        )

        # ── 阶段 2：构建 Prompt ──
        blackboard_agents = list(shared_memory.keys()) if shared_memory else []
        if blackboard_agents:
            await self.emitter.emit_agent_log(
                agent_id, f"读取黑板共享记忆: {', '.join(blackboard_agents)}，构建协作 Prompt..."
            )
        else:
            await self.emitter.emit_agent_log(agent_id, "构建 System Prompt，初始化工作流...")

        try:
            # ── 阶段 3：P2 统一调用——从注册表取 method，动态 getattr 调用 ──
            kwargs: dict[str, Any] = {
                "topic": params.get("topic", ""),
                "course": params.get("course", ""),
                "major": params.get("major", ""),
                "gap": params.get("gap", ""),
                "user_profile": profile,
                "shared_memory": shared_memory,
                **entry.extra_kwargs,   # AgentEntry 可携带额外固定参数
            }
            # mindmap 需要额外的 need / extra 参数
            if agent_name == "mindmap":
                kwargs["need"] = params.get("need", "review")
                kwargs["extra"] = params.get("extra", "")

            await self.emitter.emit_agent_log(agent_id, "初始化 LangGraph 工作流，准备调用 LLM...")
            fn = getattr(entry.agent, entry.method)
            result = await fn(**kwargs)

            # ── 阶段 4：结果校验 ──
            success = result.get("success", False)
            if success:
                extra_info = entry.result_summary(result)
                await self.emitter.emit_agent_log(agent_id, f"校验通过 ✓{extra_info}")
            else:
                error_msg = result.get("error", "未知原因")
                await self.emitter.emit_agent_log(
                    agent_id, f"校验未通过或生成失败: {error_msg}"
                )

            logger.info(f"[Coordinator] Agent {agent_name} 完成: success={success}")
            await self.emitter.emit_agent_done(agent_id, data=result)
            return result

        except Exception as e:
            logger.error(f"[Coordinator] Agent {agent_name} 异常: {e}", exc_info=True)
            await self.emitter.emit_agent_error(agent_id, str(e))
            return {}

    @staticmethod
    async def _save_resource(user_id: int, task: dict, results: dict) -> None:
        import json
        from sqlmodel.ext.asyncio.session import AsyncSession
        from app.models.resource import GeneratedResource

        async with AsyncSession(engine) as session:
            def _serialize(data: dict | None) -> str | None:
                if not data:
                    return None
                return json.dumps(data, ensure_ascii=False)

            resource = GeneratedResource(
                user_id=user_id,
                course=task.get("course", ""),
                gap=task.get("gap", ""),
                need=task.get("need", "review"),
                extra=task.get("extra", ""),
                mindmap_result=_serialize(results.get("mindmap")),
                content_result=_serialize(results.get("content")),
                code_result=_serialize(results.get("code")),
                quiz_result=_serialize(results.get("quiz")),
                reading_result=_serialize(results.get("reading")),
                ppt_result=_serialize(results.get("ppt")),
            )
            session.add(resource)
            await session.commit()
            logger.info(f"[Coordinator] 资源记录已保存: user={user_id}, id={resource.id}")
