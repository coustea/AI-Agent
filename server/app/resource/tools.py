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
from app.resource.schemas import DifficultyLevel, ProgrammingLanguage, QuizPayload, ReadingPayload
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
    username: str = "anonymous",
    resource_id: str = "default",
    on_progress: ProgressCallback | None = None,
) -> list[Tool]:
    """装配供主规划 Agent 调度的完整 7 大教学资源生成子智能体工具。"""
    llm = LLM(temperature=0.3)

    async def _lecture_content(topic: str, learning_goal: str = "", focus_points: list[str] | None = None) -> dict[str, Any]:
        """讲义编写 SubAgent 工具实现。"""
        if on_progress:
            await on_progress("generate_lecture_content", "讲师 SubAgent 正在梳理知识脉络...", 30)

        focus_text = "\n- ".join(focus_points or [])
        prompt = f"""你是一位深谙教学法的资深课程主讲导师。
请针对主题【{topic}】，撰写一份条理严谨、深入浅出的完整教学讲义。

【教学目标】: {learning_goal or "系统掌握核心原理与工程应用"}
{f"【核心要点】:\n- {focus_text}" if focus_text else ""}

请直接输出高质量的 Markdown 格式讲义正文，包含清晰的章节、核心机理、对比解析与总结。"""

        response = await llm.text(prompt)
        content = _clean_markdown(response)
        if on_progress:
            await on_progress("generate_lecture_content", "讲义已编写完成", 100)
        return {
            "status": "ok",
            "kind": "content",
            "title": f"{topic} 核心知识讲义",
            "file_type": "markdown",
            "content": content,
            "summary": f"针对 {topic} 的深度讲义已完成撰写，共约 {len(content)} 字",
        }

    async def _mindmap(topic: str, learning_goal: str = "") -> dict[str, Any]:
        """思维导图绘制 SubAgent 工具实现。"""
        if on_progress:
            await on_progress("generate_mindmap", "知识架构师 SubAgent 正在构建思维导图...", 30)

        prompt = f"""你是一位精通知识体系可视化的知识图谱架构师。
请针对主题【{topic}】，设计一份结构化知识思维导图。

【教学目标】: {learning_goal}
【导图形式】: 请使用标准的 Mermaid 脑图格式（`mindmap` 语法）输出，层级清晰。

请直接输出 Mermaid 代码块或 Markdown 结构。"""

        response = await llm.text(prompt)
        content = _clean_markdown(response)
        if on_progress:
            await on_progress("generate_mindmap", "思维导图已完成", 100)
        return {
            "status": "ok",
            "kind": "mindmap",
            "title": f"{topic} 知识体系思维导图",
            "file_type": "markdown",
            "content": content,
            "summary": f"{topic} 知识结构导图已绘制完成",
        }

    async def _quiz(topic: str, learning_goal: str = "", difficulty: DifficultyLevel = "intermediate") -> dict[str, Any]:
        """随堂测评编制 SubAgent 工具实现。"""
        if on_progress:
            await on_progress("generate_quiz", "测评专家 SubAgent 正在命制测验试题...", 30)

        prompt = f"""你是一位命题出题专家。
请为学习主题【{topic}】（难度：{difficulty}）设计 5 道随堂测验题（包含单选、多选、判断题）。

【核心目标】: {learning_goal}

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
            logger.warning("随堂测验 JSON 校验失败，执行自愈重试: %s", error)
            retry_prompt = f"上一次输出的试卷存在格式错误：{error}\n请修正并仅输出合法 JSON 文本：\n{raw_text}"
            retry_text = await llm.text(retry_prompt)
            payload, error = _parse_json_payload(retry_text, QuizPayload)

        if payload is None:
            raise RuntimeError(f"随堂测验题库生成失败: {error}")

        if on_progress:
            await on_progress("generate_quiz", "测验题库已编制完成", 100)

        return {
            "status": "ok",
            "kind": "quiz",
            "title": f"{topic} 随堂自测练习",
            "file_type": "json",
            "content": payload.model_dump(mode="json"),
            "summary": f"编制了 {len(payload.questions)} 道针对性自测题",
        }

    async def _code(topic: str, language: ProgrammingLanguage = "python") -> dict[str, Any]:
        """实战代码编写 SubAgent 工具实现。"""
        if on_progress:
            await on_progress("generate_code", "研发专家 SubAgent 正在编写工程代码与测试用例...", 30)

        prompt = f"""你是一位资深软件架构研发专家。
请针对主题【{topic}】，使用【{language}】编写一份规范、高质量、可直接运行的实战代码范例。

包含详细注释、典型应用场景实现及自测用例。请直接输出 Markdown 代码块。"""

        response = await llm.text(prompt)
        content = _clean_markdown(response)
        if on_progress:
            await on_progress("generate_code", "实战代码工程已交付", 100)
        return {
            "status": "ok",
            "kind": "code",
            "title": f"{topic} {str(language).upper()} 工程实战代码",
            "file_type": "markdown",
            "content": content,
            "summary": f"完成 {topic} 的 {language} 实战案例编写",
        }

    async def _reading(topic: str, difficulty: DifficultyLevel = "intermediate") -> dict[str, Any]:
        """拓展阅读策展 SubAgent 工具实现。"""
        if on_progress:
            await on_progress("generate_reading", "学术文献策展 SubAgent 正在整理推荐阅读...", 30)

        prompt = f"""你是一位技术与学术文献策展人。
请为学习主题【{topic}】（难度：{difficulty}）推荐 3-5 篇经典高质量的拓展文献与技术文档。

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
            data = {"recommendations": [{"title": f"{topic} 官方权威文档", "author": "官方文档", "url": "https://docs.python.org", "difficulty": difficulty, "description": "系统掌握底层实现", "reading_time": "20 分钟"}]}

        if on_progress:
            await on_progress("generate_reading", "推荐文献列表已完成", 100)
        return {
            "status": "ok",
            "kind": "reading",
            "title": f"{topic} 精选延伸阅读",
            "file_type": "json",
            "content": data,
            "summary": f"推荐了 {len(data.get('recommendations', []))} 篇精选阅读材料",
        }

    # 多模态子智能体进度转发桥接
    async def _ppt_progress(msg: str, pct: int) -> None:
        """转发演示文稿生成的实时进度与消息。"""
        if on_progress:
            await on_progress("generate_ppt_deck", msg, pct)

    async def _cartoon_progress(msg: str, pct: int) -> None:
        """转发动画讲解视频生成的实时进度与消息。"""
        if on_progress:
            await on_progress("generate_teaching_video", msg, pct)

    return [
        Tool(
            name="generate_lecture_content",
            description="编写详细深入的课程核心讲解讲义 Markdown 正文。",
            args_model=GenerateLectureContentArgs,
            handler=_lecture_content,
        ),
        Tool(
            name="generate_mindmap",
            description="生成包含知识层级与关联关系的 Mermaid 知识结构思维导图。",
            args_model=GenerateMindmapArgs,
            handler=_mindmap,
        ),
        Tool(
            name="generate_quiz",
            description="编制包含单选、多选与判断题的随堂自测练习试题库。",
            args_model=GenerateQuizArgs,
            handler=_quiz,
        ),
        Tool(
            name="generate_code",
            description="生成符合工程规范、带详细注释与用例的实战代码案例。",
            args_model=GenerateCodeArgs,
            handler=_code,
        ),
        Tool(
            name="generate_reading",
            description="整理推荐经典文献、官方文档与精选拓展阅读资料清单。",
            args_model=GenerateReadingArgs,
            handler=_reading,
        ),
        build_ppt_tool(
            username=username,
            session_id=resource_id,
            progress=_ppt_progress if on_progress else None,
        ),
        build_cartoon_tool(
            username=username,
            resource_id=resource_id,
            progress=_cartoon_progress if on_progress else None,
        ),
    ]
