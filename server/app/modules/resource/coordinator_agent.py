"""
Coordinator Agent：DAG 任务规划 + 分阶段编排 + SSE 实时推送。

工作流：
1. 从数据库读取用户画像
2. Planner 分析需求 → 拆解为子任务
3. 按 DAG 阶段顺序执行各子 Agent（阶段内并行，阶段间串行）
4. 后续阶段的 Agent 可获取前置阶段的输出作为上下文
5. 每个 Agent 完成后通过 emitter 推送 SSE 事件
6. 汇总结果，推送 done
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sqlmodel import Session

from app.core.engine import engine
from app.core.logging import get_logger
from app.models.profile import UserProfile
from app.modules.resource.sse import AgentEventEmitter
from app.modules.resource.mindmap_agent import mindmap_generator
from app.modules.resource.content_writer_agent import content_writer
from app.modules.resource.quiz_agent import quiz_agent
from app.modules.resource.reading_agent import reading_agent
from app.modules.resource.code_agent import code_agent
from app.modules.resource.media_agent import media_agent

load_dotenv()
logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"
PLANNER_PROMPT_PATH = PROMPT_DIR / "planner.md"


# ==========================================
# 辅助：读取用户画像
# ==========================================
def _load_profile(user_id: int) -> dict:
    """从数据库读取用户画像，返回 dict。"""
    with Session(engine) as session:
        profile = session.get(UserProfile, user_id)
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


# ==========================================
# 子智能体注册表
# ==========================================
AGENT_REGISTRY = {
    "content": {
        "role": "Content Agent",
        "desc": "撰写深度知识精讲",
        "type": "doc",
    },
    "mindmap": {
        "role": "Mindmap Agent",
        "desc": "构建核心知识拓扑图",
        "type": "mindmap",
    },
    "quiz": {
        "role": "Quiz Agent",
        "desc": "生成分层练习题库",
        "type": "quiz",
    },
    "reading": {
        "role": "Reading Agent",
        "desc": "检索拓展阅读与论文",
        "type": "reading",
    },
    "media": {
        "role": "Media Agent",
        "desc": "生成多媒体教学脚本",
        "type": "media",
    },
    "code": {
        "role": "Code Agent",
        "desc": "编写可运行实操案例",
        "type": "code",
    },
}

# ==========================================
# DAG 阶段配置
# ==========================================
DAG_PHASES = [
    {"name": "foundation", "label": "知识框架构建", "agents": ["mindmap"]},
    {"name": "core", "label": "核心资源生成", "agents": ["content", "code"]},
    {"name": "enrichment", "label": "拓展资源丰富", "agents": ["quiz", "reading", "media"]},
]

# 每个 Agent 依赖哪些上游 Agent 的输出
AGENT_CONTEXT_DEPS: dict[str, list[str]] = {
    "mindmap": [],
    "content": ["mindmap"],
    "code": ["mindmap"],
    "quiz": ["content"],
    "reading": ["content"],
    "media": ["content", "mindmap"],
}


# ==========================================
# Coordinator Agent
# ==========================================
class CoordinatorAgent:
    """调度中心：规划任务 → DAG 分阶段执行 → 实时推送。"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0,
        )

    # ------------------------------------------
    # 1. 规划：LLM 拆解任务
    # ------------------------------------------
    async def _plan(self, task: dict, profile: dict) -> list[dict]:
        """调用 LLM 将学习任务拆解为子任务列表。"""
        await self.emitter.emit_coordinator("parsing", "正在分析学习需求，拆解任务...")

        prompt_text = PLANNER_PROMPT_PATH.read_text(encoding="utf-8")
        formatted = prompt_text.format(
            user_input=json.dumps(task, ensure_ascii=False),
            profile=json.dumps(profile, ensure_ascii=False),
        )
        messages = [
            SystemMessage(content=formatted),
            HumanMessage(content="请根据以上信息进行任务拆解。"),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()

            # 去除可能的代码围栏
            if content.startswith("```"):
                lines = content.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                content = "\n".join(lines).strip()

            plan = json.loads(content)
            tasks = plan.get("tasks", [])
            logger.info(f"[Coordinator] 规划完成，共 {len(tasks)} 个子任务")
            return tasks
        except Exception as e:
            logger.error(f"[Coordinator] 规划失败: {e}")
            # 降级：返回默认的6个任务
            return self._default_tasks(task)

    @staticmethod
    def _default_tasks(task: dict) -> list[dict]:
        """规划失败时的降级默认任务。"""
        agents = ["mindmap", "content", "code", "quiz", "reading", "media"]
        return [
            {
                "agent": a,
                "description": f"为 {task.get('course', '')} 生成{AGENT_REGISTRY[a]['desc']}",
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

    # ------------------------------------------
    # 2. 构建上游上下文
    # ------------------------------------------
    @staticmethod
    def _build_upstream_context(agent_name: str, context_bag: dict) -> str:
        """从已完成的 Agent 结果中提取上下文，供下游 Agent 参考。"""
        deps = AGENT_CONTEXT_DEPS.get(agent_name, [])
        if not deps:
            return ""

        parts: list[str] = []
        for dep in deps:
            dep_result = context_bag.get(dep)
            if not dep_result:
                continue

            dep_label = AGENT_REGISTRY.get(dep, {}).get("desc", dep)
            # 截取关键内容，避免 token 过长
            summary = json.dumps(dep_result, ensure_ascii=False, indent=2)
            if len(summary) > 3000:
                summary = summary[:3000] + "\n... (内容已截断)"
            parts.append(f"## [{dep_label} 输出]\n{summary}")

        return "\n\n".join(parts) if parts else ""

    # ------------------------------------------
    # 3. 执行单个子智能体
    # ------------------------------------------
    async def _run_agent(
        self,
        agent_name: str,
        params: dict,
        profile: dict,
        upstream_context: str = "",
    ) -> dict:
        """执行一个子智能体，推送 SSE 事件。"""
        agent_id = AGENT_REGISTRY.get(agent_name, {}).get("type", agent_name)

        await self.emitter.emit_agent_start(agent_id)
        await self.emitter.emit_agent_log(agent_id, "已分配计算资源，开始处理...")

        try:
            if agent_name == "mindmap":
                result = await mindmap_generator.generate_mindmap(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    upstream_context=upstream_context,
                )

            elif agent_name == "content":
                result = await content_writer.generate_content(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    user_profile=json.dumps(profile, ensure_ascii=False),
                    upstream_context=upstream_context,
                )

            elif agent_name == "quiz":
                result = await quiz_agent.generate_quiz(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    gap=params.get("gap", ""),
                    knowledge_level=profile.get("knowledge_level", "中等") or "中等",
                    error_pattern=profile.get("error_pattern", "") or "",
                    upstream_context=upstream_context,
                )

            elif agent_name == "reading":
                result = await reading_agent.generate_reading(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    interest_preference=profile.get("interest_preference", "") or "",
                    cognitive_style=profile.get("cognitive_style", "") or "",
                    upstream_context=upstream_context,
                )

            elif agent_name == "code":
                result = await code_agent.generate_code(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    gap=params.get("gap", ""),
                    knowledge_level=profile.get("knowledge_level", "中等") or "中等",
                    learning_pace=profile.get("learning_pace", "中等") or "中等",
                    upstream_context=upstream_context,
                )

            elif agent_name == "media":
                result = await media_agent.generate_media(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    gap=params.get("gap", ""),
                    cognitive_style=profile.get("cognitive_style", "通用") or "通用",
                    upstream_context=upstream_context,
                )

            else:
                await self.emitter.emit_agent_error(agent_id, f"未知智能体: {agent_name}")
                return {}

            await self.emitter.emit_agent_done(agent_id, data=result)
            return result

        except Exception as e:
            logger.error(f"[Coordinator] Agent {agent_name} 失败: {e}")
            await self.emitter.emit_agent_error(agent_id, str(e))
            return {}

    # ------------------------------------------
    # 4. 主入口：规划 → DAG 分阶段执行 → 汇总
    # ------------------------------------------
    async def run(self, user_id: int, task: dict) -> dict:
        """
        Args:
            user_id: 用户 ID，用于从数据库读取画像
            task: 学习任务 { course, gap, need, extra }
        Returns:
            汇总结果 dict
        """
        # 1. 读取画像
        await self.emitter.emit_coordinator("parsing", "正在读取学习者画像...")
        profile = _load_profile(user_id)
        logger.info(f"[Coordinator] 用户 {user_id} 画像加载完成")

        # 2. 规划
        tasks = await self._plan(task, profile)
        await self.emitter.emit_coordinator(
            "dispatching", f"任务拆解完成，共 {len(tasks)} 个子任务，开始 DAG 分阶段调度..."
        )

        # 3. 构建按 agent 名索引的任务查找表
        task_by_agent: dict[str, dict] = {t["agent"]: t for t in tasks}

        # 4. 按 DAG 阶段顺序执行
        context_bag: dict[str, dict] = {}
        final: dict[str, dict] = {}

        for phase in DAG_PHASES:
            phase_agents = phase["agents"]
            # 只执行规划器选中的 Agent
            active_in_phase = [a for a in phase_agents if a in task_by_agent]

            if not active_in_phase:
                continue

            await self.emitter.emit_coordinator(
                f"phase_{phase['name']}",
                f"阶段 [{phase['label']}]：正在执行 {', '.join(active_in_phase)}...",
            )

            coroutines = []
            for agent_name in active_in_phase:
                upstream_ctx = self._build_upstream_context(agent_name, context_bag)
                coroutines.append(
                    self._run_agent(
                        agent_name,
                        task_by_agent[agent_name].get("parameters", {}),
                        profile,
                        upstream_context=upstream_ctx,
                    )
                )

            phase_results = await asyncio.gather(*coroutines, return_exceptions=True)

            # 收集结果到 context_bag 和 final
            for agent_name, result in zip(active_in_phase, phase_results):
                if isinstance(result, Exception):
                    final[agent_name] = {"error": str(result)}
                else:
                    final[agent_name] = result
                    # 只有成功的非空结果才放入 context_bag 供下游参考
                    if result:
                        context_bag[agent_name] = result

        # 5. 汇总
        await self.emitter.emit_coordinator("integrating", "正在组装学习资源包...")

        # 6. 持久化到数据库
        try:
            await self._save_resource(user_id, task, final)
        except Exception as e:
            logger.error(f"[Coordinator] 保存资源记录失败: {e}")

        await self.emitter.emit_done("资源包构建完成")
        return final

    @staticmethod
    async def _save_resource(user_id: int, task: dict, results: dict) -> None:
        """将生成结果保存到 generated_resources 表"""
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
                media_result=_serialize(results.get("media")),
            )
            session.add(resource)
            await session.commit()
            logger.info(f"[Coordinator] 资源记录已保存: user={user_id}, id={resource.id}")
