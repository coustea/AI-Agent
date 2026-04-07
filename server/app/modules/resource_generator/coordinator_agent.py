"""
Coordinator Agent：任务规划 + 并发调度子智能体 + SSE 实时推送。

工作流：
1. 从数据库读取用户画像
2. Planner 分析需求 → 拆解为子任务
3. asyncio.gather 并发执行各子 Agent
4. 每个 Agent 完成后通过 emitter 推送 SSE 事件
5. 汇总结果，推送 done
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
from app.models.profile_builder import UserProfile
from app.modules.resource_generator.sse import AgentEventEmitter
from app.modules.resource_generator.mindmap_agent import mindmap_generator
from app.modules.resource_generator.content_writer_agent import content_writer
from app.modules.resource_generator.quiz_agent import quiz_agent
from app.modules.resource_generator.reading_agent import reading_agent
from app.modules.resource_generator.code_agent import code_agent
from app.modules.resource_generator.media_agent import media_agent

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
# Coordinator Agent
# ==========================================
class CoordinatorAgent:
    """调度中心：规划任务 → 并发执行 → 实时推送。"""

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
        agents = ["content", "mindmap", "quiz", "reading", "media", "code"]
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
    # 2. 执行单个子智能体（调度到 Agent 单例）
    # ------------------------------------------
    async def _run_agent(self, agent_name: str, params: dict, profile: dict) -> dict:
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
                )

            elif agent_name == "content":
                result = await content_writer.generate_content(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    user_profile=json.dumps(profile, ensure_ascii=False),
                )

            elif agent_name == "quiz":
                result = await quiz_agent.generate_quiz(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    gap=params.get("gap", ""),
                    knowledge_level=profile.get("knowledge_level", "中等") or "中等",
                    error_pattern=profile.get("error_pattern", "") or "",
                )

            elif agent_name == "reading":
                result = await reading_agent.generate_reading(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    interest_preference=profile.get("interest_preference", "") or "",
                    cognitive_style=profile.get("cognitive_style", "") or "",
                )

            elif agent_name == "code":
                result = await code_agent.generate_code(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    gap=params.get("gap", ""),
                    knowledge_level=profile.get("knowledge_level", "中等") or "中等",
                    learning_pace=profile.get("learning_pace", "中等") or "中等",
                )

            elif agent_name == "media":
                result = await media_agent.generate_media(
                    topic=params.get("topic", ""),
                    major=params.get("major", ""),
                    course=params.get("course", ""),
                    gap=params.get("gap", ""),
                    cognitive_style=profile.get("cognitive_style", "通用") or "通用",
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
    # 3. 主入口：规划 → 并发执行 → 汇总
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
            "dispatching", f"任务拆解完成，共 {len(tasks)} 个子任务，开始并发调度..."
        )

        # 3. 并发执行所有子智能体
        coroutines = [
            self._run_agent(t["agent"], t.get("parameters", {}), profile)
            for t in tasks
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # 4. 汇总
        await self.emitter.emit_coordinator("integrating", "正在组装学习资源包...")

        final = {}
        for t, r in zip(tasks, results):
            agent_name = t["agent"]
            if isinstance(r, Exception):
                final[agent_name] = {"error": str(r)}
            else:
                final[agent_name] = r

        await self.emitter.emit_done("资源包构建完成")
        return final
