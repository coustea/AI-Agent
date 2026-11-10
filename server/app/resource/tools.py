"""Resource 模块子智能体工具箱 (app.resource.tools)。

将各类教学资源生产能力统一封装为标准 Tool，供主 Agent 在循环中按需调用。
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any
from pydantic import BaseModel, Field, ValidationError

from app.infra.llm import LLM
from app.infra.logging import get_logger
from app.resource.schemas import (
    DifficultyLevel,
    ProgrammingLanguage,
    QuizPayload,
    ReadingPayload,
    ResourceGenerationRequest,
)
from app.shared.cartoon.tool import build_cartoon_tool
from app.shared.ppt.tool import build_ppt_tool
from app.shared.tools.registry import Tool

logger = get_logger(__name__)

ProgressCallback = Callable[[str, str, int], Awaitable[None]]


def _clean_markdown(text: str) -> str:
    """清理 Markdown 首尾的代码围栏标志。"""
    cleaned = text.strip()
    if cleaned.startswith("```markdown"):
        cleaned = cleaned[len("```markdown") :].strip()
    elif cleaned.startswith("```md"):
        cleaned = cleaned[len("```md") :].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```") :].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
    return cleaned


def _parse_json_payload(raw_text: str, model_cls: type[BaseModel]) -> tuple[Any | None, str | None]:
    """从大模型回复文本中抽取并校验 JSON 结构体。"""
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        data = json.loads(text)
        validated = model_cls.model_validate(data)
        return validated, None
    except (json.JSONDecodeError, ValidationError) as exc:
        return None, str(exc)


# ── 参数定义模型 ────────────────────────────────────────────────────────────


class GenerateLectureContentArgs(BaseModel):
    """课程讲义生成工具参数。"""

    topic: str = Field(description="核心学习主题")
    learning_goal: str = Field(default="", description="教学目标或掌握要点")
    focus_points: list[str] = Field(default_factory=list, description="需要重点讲解的要点列表")


class GenerateMindmapArgs(BaseModel):
    """思维导图生成工具参数（已移除旧版冗余 structure_style）。"""

    topic: str = Field(description="核心学习主题")
    learning_goal: str = Field(default="", description="知识框架目标")


class GenerateQuizArgs(BaseModel):
    """随堂测验生成工具参数（已移除冗余题目数配置，由测评智能体自主把控）。"""

    topic: str = Field(description="核心学习主题")
    learning_goal: str = Field(default="", description="考察目标")
    difficulty: DifficultyLevel = Field(default="intermediate", description="试卷难度：beginner, intermediate, advanced")


class GenerateCodeArgs(BaseModel):
    """实战代码示例生成工具参数（仅对齐用户选定的实操语言，移除冗余 focus 模式）。"""

    topic: str = Field(description="核心学习主题")
    language: ProgrammingLanguage = Field(default="python", description="编程语言（python, cpp, typescript, go, java）")


class GenerateReadingArgs(BaseModel):
    """拓展阅读推荐生成工具参数（仅对齐难度要求，移除冗余篇数选择）。"""

    topic: str = Field(description="核心学习主题")
    difficulty: DifficultyLevel = Field(default="intermediate", description="文献难度要求：beginner, intermediate, advanced")


# ── 工具构造工厂 ────────────────────────────────────────────────────────────


def build_resource_tools(
    *,
    request: ResourceGenerationRequest,
    username: str = "anonymous",
    resource_id: str = "default",
    on_progress: ProgressCallback | None = None,
) -> list[Tool]:
    """依据用户请求中选定的目标智能体清单与偏好，动态装配对应的专属教学工具箱。"""
    llm = LLM(temperature=0.3)
    tools: list[Tool] = []
    selected_agents = set(request.target_resources)

    # 1. 课程讲义 (content)
    if "content" in selected_agents:
        async def _lecture_content(
            topic: str = "",
            learning_goal: str = "",
            focus_points: list[str] | None = None,
        ) -> dict[str, Any]:
            """讲义编写 SubAgent 工具实现，深度结合用户设定的认知难度与核心目标。"""
            effective_topic = topic.strip() or request.topic
            effective_goal = learning_goal.strip() or request.learning_goal or "系统掌握核心原理与工程应用"
            logger.info(
                "[ResourceSubAgent:lecture_content] 开始撰写课程讲义: topic={} goal={} 难度={} 要点数={}",
                effective_topic, effective_goal, request.difficulty, len(focus_points or []),
            )
            if on_progress:
                await on_progress("generate_lecture_content", "讲师 SubAgent 正在梳理知识脉络...", 30)

            focus_text = "\n- ".join(focus_points or [])
            prompt = f"""你是一位深谙教学法的资深课程主讲导师。
请针对主题【{effective_topic}】（认知难度：{request.difficulty}），撰写一份条理严谨、深入浅出的完整教学讲义。

【教学目标】: {effective_goal}
{f"【核心要点】:\n- {focus_text}" if focus_text else ""}

请直接输出高质量的 Markdown 格式讲义正文，包含清晰的章节、核心机理、对比解析与总结。"""

            response = await llm.text(prompt)
            content = _clean_markdown(response)
            logger.info(
                "[ResourceSubAgent:lecture_content] 讲义撰写完成: topic={} 总字数={}",
                effective_topic, len(content),
            )
            if on_progress:
                await on_progress("generate_lecture_content", "讲义已编写完成", 100)
            return {
                "status": "ok",
                "kind": "content",
                "title": f"{effective_topic} 核心知识讲义",
                "file_type": "markdown",
                "content": content,
                "summary": f"针对 {effective_topic} 的深度讲义已完成撰写，共约 {len(content)} 字",
            }

        tools.append(
            Tool(
                name="generate_lecture_content",
                description="编写详细深入的课程核心讲解讲义 Markdown 正文。",
                args_model=GenerateLectureContentArgs,
                handler=_lecture_content,
            )
        )

    # 2. 思维导图 (mindmap)
    if "mindmap" in selected_agents:
        async def _mindmap(topic: str = "", learning_goal: str = "") -> dict[str, Any]:
            """思维导图绘制 SubAgent 工具实现。"""
            effective_topic = topic.strip() or request.topic
            effective_goal = learning_goal.strip() or request.learning_goal
            logger.info(
                "[ResourceSubAgent:mindmap] 开始绘制思维导图: topic={} goal={}",
                effective_topic, effective_goal,
            )
            if on_progress:
                await on_progress("generate_mindmap", "知识架构师 SubAgent 正在构建思维导图...", 30)

            prompt = f"""你是一位精通知识体系可视化的知识图谱架构师。
请针对主题【{effective_topic}】，设计一份结构化知识思维导图。

【教学目标】: {effective_goal}
【认知难度】: {request.difficulty}
【导图形式】: 请使用标准的 Mermaid 脑图格式（`mindmap` 语法）输出，层级清晰。

请直接输出 Mermaid 代码块或 Markdown 结构。"""

            response = await llm.text(prompt)
            content = _clean_markdown(response)
            logger.info(
                "[ResourceSubAgent:mindmap] 思维导图绘制完成: topic={} 内容长度={}",
                effective_topic, len(content),
            )
            if on_progress:
                await on_progress("generate_mindmap", "思维导图已完成", 100)
            return {
                "status": "ok",
                "kind": "mindmap",
                "title": f"{effective_topic} 知识体系思维导图",
                "file_type": "markdown",
                "content": content,
                "summary": f"{effective_topic} 知识结构导图已绘制完成",
            }

        tools.append(
            Tool(
                name="generate_mindmap",
                description="生成包含知识层级与关联关系的 Mermaid 知识结构思维导图。",
                args_model=GenerateMindmapArgs,
                handler=_mindmap,
            )
        )

    # 3. 随堂测试 (quiz)
    if "quiz" in selected_agents:
        async def _quiz(
            topic: str = "",
            learning_goal: str = "",
            difficulty: DifficultyLevel | None = None,
        ) -> dict[str, Any]:
            """随堂测评编制 SubAgent 工具实现，严格注入前端选定的认知难度阶梯。"""
            effective_topic = topic.strip() or request.topic
            effective_goal = learning_goal.strip() or request.learning_goal
            effective_difficulty = difficulty or request.difficulty
            logger.info(
                "[ResourceSubAgent:quiz] 开始命制随堂测验试卷: topic={} goal={} 难度={}",
                effective_topic, effective_goal, effective_difficulty,
            )
            if on_progress:
                await on_progress("generate_quiz", "测评专家 SubAgent 正在命制测验试题...", 30)

            prompt = f"""你是一位命题出题专家。
请为学习主题【{effective_topic}】（难度：{effective_difficulty}）设计 5 道随堂测验题（包含单选、多选、判断题）。

【核心目标】: {effective_goal}

请严格按 JSON 格式输出：
{{
  "questions": [
    {{
      "id": 1,
      "type": "single",
      "question": "题干内容...",
      "options": [{{"key": "A", "text": "选项A"}}, {{"key": "B", "text": "选项B"}}],
      "answer": "A",
      "explanation": "答案解析与考核点",
      "knowledge_point": "考查知识点"
    }}
  ]
}}
"""
            raw_text = await llm.text(prompt)
            payload, error = _parse_json_payload(raw_text, QuizPayload)
            if error:
                logger.warning("[ResourceSubAgent:quiz] 试卷 JSON 校验失败，执行自愈重试: {}", error)
                retry_prompt = f"上一次输出的试卷存在格式错误：{error}\n请修正并仅输出合法 JSON 文本：\n{raw_text}"
                retry_text = await llm.text(retry_prompt)
                payload, error = _parse_json_payload(retry_text, QuizPayload)

            if payload is None:
                logger.error("[ResourceSubAgent:quiz] 随堂测验题库生成彻底失败: {}", error)
                raise RuntimeError(f"随堂测验题库生成失败: {error}")

            logger.info(
                "[ResourceSubAgent:quiz] 随堂测验试卷命制完成: topic={} 题数={} 难度={}",
                effective_topic, len(payload.questions), effective_difficulty,
            )
            if on_progress:
                await on_progress("generate_quiz", "测验题库已编制完成", 100)

            return {
                "status": "ok",
                "kind": "quiz",
                "title": f"{effective_topic} 随堂自测练习",
                "file_type": "json",
                "content": payload.model_dump(mode="json"),
                "summary": f"编制了 {len(payload.questions)} 道针对性自测题（难度：{effective_difficulty}）",
            }

        tools.append(
            Tool(
                name="generate_quiz",
                description="编制包含单选、多选与判断题的随堂自测练习试题库。",
                args_model=GenerateQuizArgs,
                handler=_quiz,
            )
        )

    # 4. 代码实操 (code)
    if "code" in selected_agents:
        pref_lang = request.preferences.programming_language

        async def _code(
            topic: str = "",
            language: ProgrammingLanguage | None = None,
        ) -> dict[str, Any]:
            """实战代码编写 SubAgent 工具实现，严格注入前端选定的编程语言与难度。"""
            effective_topic = topic.strip() or request.topic
            effective_lang = language or pref_lang
            logger.info(
                "[ResourceSubAgent:code] 开始编写实战工程代码: topic={} lang={} 难度={}",
                effective_topic, effective_lang, request.difficulty,
            )
            if on_progress:
                await on_progress("generate_code", f"研发专家 SubAgent 正在编写 {effective_lang} 工程代码...", 30)

            prompt = f"""你是一位资深软件架构研发专家。
请针对主题【{effective_topic}】，使用【{effective_lang}】编写一份规范、高质量、可直接运行的实战代码范例（认知难度：{request.difficulty}）。

包含详细注释、典型应用场景实现及自测用例。请直接输出 Markdown 代码块。"""

            response = await llm.text(prompt)
            content = _clean_markdown(response)
            logger.info(
                "[ResourceSubAgent:code] 实战工程代码交付: topic={} lang={} 代码字符数={}",
                effective_topic, effective_lang, len(content),
            )
            if on_progress:
                await on_progress("generate_code", "实战代码工程已交付", 100)
            return {
                "status": "ok",
                "kind": "code",
                "title": f"{effective_topic} {str(effective_lang).upper()} 工程实战代码",
                "file_type": "markdown",
                "content": content,
                "summary": f"完成 {effective_topic} 的 {effective_lang} 实战案例编写",
            }

        tools.append(
            Tool(
                name="generate_code",
                description="生成符合工程规范、带详细注释与用例的实战代码案例。",
                args_model=GenerateCodeArgs,
                handler=_code,
            )
        )

    # 5. 拓展阅读 (reading)
    if "reading" in selected_agents:
        async def _reading(
            topic: str = "",
            difficulty: DifficultyLevel | None = None,
        ) -> dict[str, Any]:
            """拓展阅读策展 SubAgent 工具实现，严格结合前端选定的文献难度。"""
            effective_topic = topic.strip() or request.topic
            effective_difficulty = difficulty or request.difficulty
            logger.info(
                "[ResourceSubAgent:reading] 开始策展精选阅读材料: topic={} 难度={}",
                effective_topic, effective_difficulty,
            )
            if on_progress:
                await on_progress("generate_reading", "学术文献策展 SubAgent 正在整理推荐阅读...", 30)

            prompt = f"""你是一位技术与学术文献策展人。
请为学习主题【{effective_topic}】（难度：{effective_difficulty}）推荐 3-5 篇经典高质量的拓展文献与技术文档。

请严格按 JSON 格式输出：
{{
  "recommendations": [
    {{
      "title": "材料标题",
      "author": "作者或团队",
      "url": "在线参考链接",
      "difficulty": "introductory",
      "description": "推荐理由与核心摘要",
      "reading_time": "15 分钟"
    }}
  ]
}}
"""
            raw_text = await llm.text(prompt)
            payload, _ = _parse_json_payload(raw_text, ReadingPayload)
            if payload is not None:
                data = payload.model_dump(mode="json")
            else:
                data = {
                    "recommendations": [
                        {
                            "title": f"{effective_topic} 官方权威文档",
                            "author": "官方文档",
                            "url": "https://docs.python.org",
                            "difficulty": effective_difficulty,
                            "description": "系统掌握底层实现",
                            "reading_time": "20 分钟",
                        }
                    ]
                }

            recs_count = len(data.get("recommendations", []))
            logger.info(
                "[ResourceSubAgent:reading] 精选拓展阅读策展完成: topic={} 篇数={} 难度={}",
                effective_topic, recs_count, effective_difficulty,
            )
            if on_progress:
                await on_progress("generate_reading", "推荐文献列表已完成", 100)
            return {
                "status": "ok",
                "kind": "reading",
                "title": f"{effective_topic} 精选延伸阅读",
                "file_type": "json",
                "content": data,
                "summary": f"推荐了 {recs_count} 篇精选阅读材料（难度：{effective_difficulty}）",
            }

        tools.append(
            Tool(
                name="generate_reading",
                description="整理推荐经典文献、官方文档与精选拓展阅读资料清单。",
                args_model=GenerateReadingArgs,
                handler=_reading,
            )
        )

    # 6. 演示课件 (ppt)
    if "ppt" in selected_agents:
        async def _ppt_progress(msg: str, pct: int) -> None:
            """转发演示文稿生成的实时进度与消息。"""
            if on_progress:
                await on_progress("generate_ppt_deck", msg, pct)

        tools.append(
            build_ppt_tool(
                username=username,
                session_id=resource_id,
                progress=_ppt_progress if on_progress else None,
            )
        )

    # 7. 动画讲解 (cartoon)
    if "cartoon" in selected_agents:
        async def _cartoon_progress(msg: str, pct: int) -> None:
            """转发动画讲解视频生成的实时进度与消息。"""
            if on_progress:
                await on_progress("generate_teaching_video", msg, pct)

        tools.append(
            build_cartoon_tool(
                username=username,
                resource_id=resource_id,
                progress=_cartoon_progress if on_progress else None,
            )
        )

    return tools
