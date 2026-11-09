"""执行智能体 (SubAgent) — 负责执行单项任务节点并调度工具 (app.resource.agents.subagent)。

在 Plan-and-Execute 架构中作为标准的 Worker 执行者，根据 TaskNode 的规划指示，
或调用多模态生成工具 (PPT/Cartoon)，或利用大模型完成高防御性的文本/结构化资源产出。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError

from app.infra.llm import LLM
from app.resource.schemas import (
    AgentResult,
    QuizPayload,
    ReadingPayload,
    TaskNode,
)
from app.resource.tools import execute_tool_for_task
from app.shared.tools.registry import Tool

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int], Awaitable[None]]


class SubAgent:
    """通用执行智能体：在 Plan-and-Execute 体系中接收单一 TaskNode 并完成执行交付。"""

    def __init__(self, role: str = "学科专家") -> None:
        """初始化 SubAgent 并创建推理 LLM 实例与课件生成器。"""
        self.role = role
        self.llm = LLM(temperature=0.3)
        from app.shared.ppt.agent import PPTAgent as _SharedPPTAgent

        self._generator: Any = _SharedPPTAgent()

    async def execute_task(
        self,
        task: TaskNode,
        *,
        topic: str,
        learning_goal: str = "",
        difficulty: str = "intermediate",
        upstream_results: dict[str, AgentResult] | None = None,
        preferences: dict[str, Any] | None = None,
        toolbox: dict[str, Tool] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> AgentResult:
        """核心执行入口：根据任务类型（工具驱动或文本生成）派发执行。"""
        upstream_results = upstream_results or {}
        preferences = preferences or {}
        toolbox = toolbox or {}

        logger.info(
            "SubAgent[%s] 开始执行任务 task_id=%s type=%s tool=%s",
            self.role,
            task.task_id,
            task.task_type,
            task.tool_name,
        )

        if progress_callback:
            await progress_callback(f"{self.role} 开始推进任务", 10)

        # 1. 工具调用分支（如 PPT 课件、教学动画）
        if task.task_type == "tool" and task.tool_name:
            return await self._execute_tool_task(
                task=task,
                topic=topic,
                learning_goal=learning_goal,
                upstream_results=upstream_results,
                preferences=preferences,
                toolbox=toolbox,
                progress_callback=progress_callback,
            )

        # 2. 文本与结构化生成分支（讲义、导图、习题、代码、拓展阅读）
        return await self._execute_text_task(
            task=task,
            topic=topic,
            learning_goal=learning_goal,
            difficulty=difficulty,
            upstream_results=upstream_results,
            preferences=preferences,
            progress_callback=progress_callback,
        )

    async def _execute_tool_task(
        self,
        *,
        task: TaskNode,
        topic: str,
        learning_goal: str,
        upstream_results: dict[str, AgentResult],
        preferences: dict[str, Any],
        toolbox: dict[str, Tool],
        progress_callback: ProgressCallback | None,
    ) -> AgentResult:
        """调用已绑定的外部工具生成多模态资源产物。"""
        tool_name = task.tool_name or ""
        if progress_callback:
            await progress_callback(f"正在调用 {tool_name} 工具生成多模态教学产物...", 30)

        source_materials: list[str] = []
        content_res = upstream_results.get("content")
        if content_res and content_res.content:
            raw_text = str(content_res.content)
            lines = [line.strip("# -*").strip() for line in raw_text.splitlines() if len(line.strip()) > 6]
            source_materials = lines[:8]
        if not source_materials:
            source_materials = [learning_goal or topic]

        if tool_name in ("generate_ppt_deck", "ppt"):
            tool_args = {
                "topic": topic,
                "learning_goal": learning_goal or f"全面系统讲授 {topic}",
                "source_points": source_materials,
            }
        elif tool_name in ("generate_teaching_video", "cartoon"):
            voice = str(preferences.get("voice") or "teacher")
            tool_args = {
                "topic": topic,
                "learning_goal": learning_goal or f"用生动的动画演示讲解 {topic}",
                "source_materials": source_materials,
                "voice": "coach" if voice == "coach" else "teacher",
            }
        else:
            tool_args = {
                "topic": topic,
                "learning_goal": learning_goal,
                "source_materials": source_materials,
            }

        result = await execute_tool_for_task(tool_name, tool_args, toolbox)
        if progress_callback:
            await progress_callback("工具调用完成并产出成果", 100)
        return result

    async def _execute_text_task(
        self,
        *,
        task: TaskNode,
        topic: str,
        learning_goal: str,
        difficulty: str,
        upstream_results: dict[str, AgentResult],
        preferences: dict[str, Any],
        progress_callback: ProgressCallback | None,
    ) -> AgentResult:
        """执行大模型文本生成任务，包含讲义、思维导图、测验题与示例代码。"""
        res_type = task.resource_type
        if progress_callback:
            await progress_callback(f"正在进行 {task.title} 深度推理与内容构建...", 40)

        upstream_context = ""
        if upstream_results:
            ctx_snippets: list[str] = []
            for tid, u_res in upstream_results.items():
                if u_res.success and u_res.content:
                    content_preview = str(u_res.content)[:1200]
                    ctx_snippets.append(f"【上游 {tid} 产物参考】:\n{content_preview}")
            upstream_context = "\n\n".join(ctx_snippets)

        if res_type == "quiz":
            return await self._generate_quiz(
                topic=topic,
                learning_goal=learning_goal,
                difficulty=difficulty,
                upstream_context=upstream_context,
                task_prompt=task.task_prompt,
                progress_callback=progress_callback,
            )
        elif res_type == "reading":
            return await self._generate_reading(
                topic=topic,
                learning_goal=learning_goal,
                difficulty=difficulty,
                task_prompt=task.task_prompt,
                progress_callback=progress_callback,
            )
        else:
            return await self._generate_markdown(
                res_type=res_type,
                title=task.title,
                topic=topic,
                learning_goal=learning_goal,
                difficulty=difficulty,
                upstream_context=upstream_context,
                task_prompt=task.task_prompt,
                preferences=preferences,
                progress_callback=progress_callback,
            )

    async def _generate_markdown(
        self,
        *,
        res_type: str,
        title: str,
        topic: str,
        learning_goal: str,
        difficulty: str,
        upstream_context: str,
        task_prompt: str,
        preferences: dict[str, Any],
        progress_callback: ProgressCallback | None,
    ) -> AgentResult:
        """生成 Markdown 格式的基础教学资源。"""
        prompt = f"""你是一位高水准的{self.role}。
请围绕主题【{topic}】，针对【{difficulty}】水平的学习者，撰写专业、详尽且严谨的教学资源：{title}。

【教学目标】
{learning_goal or "构建系统认知，掌握核心机理与工程实践规范"}

【定制指示】
{task_prompt}

{f"【偏好设置】: {preferences}" if preferences else ""}
{upstream_context}

请直接输出 Markdown 格式的完整内容。不要输出无用的前言套话。
"""
        response = await self.llm.text(prompt)
        cleaned = self._clean_markdown(response)
        if progress_callback:
            await progress_callback("内容生成完成", 100)

        return AgentResult(
            success=True,
            title=title,
            file_type="markdown",
            content=cleaned,
            summary=f"完成 {topic} 的 {res_type} 教学资源制作",
            metrics={"char_count": len(cleaned)},
            metadata={"resource_type": res_type},
        )

    async def _generate_quiz(
        self,
        *,
        topic: str,
        learning_goal: str,
        difficulty: str,
        upstream_context: str,
        task_prompt: str,
        progress_callback: ProgressCallback | None,
    ) -> AgentResult:
        """生成结构化测试习题，采用 Pydantic 校验与自愈重试机制。"""
        prompt = f"""你是一位顶尖的教学测评出题专家。
请为学习主题【{topic}】（难度：{difficulty}）设计一套随堂练习题（含单选、多选、判断题）。

【核心目标】: {learning_goal}
【任务说明】: {task_prompt}
{upstream_context}

请严格按 JSON 格式输出，满足以下 Schema：
{{
  "questions": [
    {{
      "id": 1,
      "type": "single",
      "question": "题干内容...",
      "options": [{{"key": "A", "text": "选项A"}}, {{"key": "B", "text": "选项B"}}],
      "answer": "A",
      "explanation": "答案解析...",
      "knowledge_point": "考查知识点"
    }}
  ]
}}
"""
        raw_text = await self.llm.text(prompt)
        payload, error = self._parse_json_payload(raw_text, QuizPayload)
        if error:
            logger.warning("习题 JSON 解析失败，执行自愈重试: %s", error)
            retry_prompt = f"上一次输出的 JSON 存在格式校验错误：{error}\n请修正并仅输出合法的 JSON 文本：\n{raw_text}"
            retry_text = await self.llm.text(retry_prompt)
            payload, error = self._parse_json_payload(retry_text, QuizPayload)

        if payload is not None:
            if progress_callback:
                await progress_callback("习题库编制完成", 100)
            return AgentResult(
                success=True,
                title=f"{topic} 随堂自测练习",
                file_type="json",
                content=payload.model_dump(mode="json"),
                summary=f"生成 {len(payload.questions)} 道针对性测验题",
                metrics={"question_count": len(payload.questions)},
                metadata={"resource_type": "quiz"},
            )
        else:
            return AgentResult(
                success=False,
                title=f"{topic} 测验生成失败",
                file_type="json",
                error=f"JSON 校验失败: {error}",
                metadata={"resource_type": "quiz"},
            )

    async def _generate_reading(
        self,
        *,
        topic: str,
        learning_goal: str,
        difficulty: str,
        task_prompt: str,
        progress_callback: ProgressCallback | None,
    ) -> AgentResult:
        """生成精选延伸阅读材料列表。"""
        prompt = f"""你是一位学术文献与工程实践资料策展专家。
请为学习主题【{topic}】（难度：{difficulty}）推荐 3-5 篇精选拓展阅读材料。

【目标】: {learning_goal}
【要求】: {task_prompt}

请严格按 JSON 格式输出：
{{
  "recommendations": [
    {{
      "title": "阅读材料标题",
      "author": "作者或团队",
      "url": "在线参考链接或官方文档地址",
      "difficulty": "introductory",
      "description": "核心推荐理由与摘要",
      "reading_time": "15 分钟"
    }}
  ]
}}
"""
        raw_text = await self.llm.text(prompt)
        payload, _ = self._parse_json_payload(raw_text, ReadingPayload)
        if payload is not None:
            if progress_callback:
                await progress_callback("推荐文献整理完毕", 100)
            return AgentResult(
                success=True,
                title=f"{topic} 延伸阅读推荐",
                file_type="json",
                content=payload.model_dump(mode="json"),
                summary=f"推荐 {len(payload.recommendations)} 篇专业文献与实操文档",
                metrics={"item_count": len(payload.recommendations)},
                metadata={"resource_type": "reading"},
            )
        return AgentResult(
            success=True,
            title=f"{topic} 延伸阅读材料",
            file_type="markdown",
            content=self._clean_markdown(raw_text),
            summary="生成延伸阅读推荐材料",
            metadata={"resource_type": "reading"},
        )

    def _clean_markdown(self, text: str) -> str:
        """剥离代码块围栏与首尾杂质字符。"""
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

    def _parse_json_payload(
        self,
        raw_text: str,
        model_cls: type[BaseModel],
    ) -> tuple[Any | None, str | None]:
        """从模型回复中提取并校验 JSON 数据结构。"""
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

    async def generate_for_path(self, request: Any) -> AgentResult:
        """为学习路径 (Path) 节点生成辅助资源，保证系统间完全解耦。"""
        tutorial = getattr(request, "tutorial", None)
        node_title = getattr(request, "node_title", "学习节点")
        context_text = getattr(tutorial, "content_markdown", "") if tutorial else ""
        prompt = f"围绕节点【{node_title}】，基于以下教程内容生成高质量教学辅助内容：\n{context_text[:1500]}"
        response = await self.llm.text(prompt)
        cleaned = self._clean_markdown(response)
        return AgentResult(
            success=True,
            title=f"{node_title} 辅助材料",
            file_type="markdown",
            content=cleaned,
            summary=f"成功为路径节点 {node_title} 生成辅助资源",
            metadata={"node_id": getattr(request, "node_id", None)},
        )

    async def generate_resource(self, input: Any, **kwargs: Any) -> AgentResult:
        """执行资源生成入口，自适应 TaskNode 或 ResourceInput。"""
        if hasattr(input, "learning_need") or hasattr(input, "teaching_plan"):
            from uuid import uuid4
            from app.config import user_resource_ppt_dir
            from app.shared.ppt.schemas import PPTBrief, PPTGenerationError

            target_dir = user_resource_ppt_dir(getattr(input, "username", "alice"), uuid4().hex)
            brief = PPTBrief(
                title=getattr(input, "learning_need", "教学课件"),
                context=getattr(input, "learning_need", ""),
            )
            try:
                artifact = await self._generator.generate(brief, target_dir)
                return AgentResult(
                    success=True,
                    title=artifact.title,
                    file_type="pptx",
                    content="",
                    summary=f"成功生成课件 {artifact.title}",
                    metadata=artifact.metadata(),
                )
            except PPTGenerationError as exc:
                return AgentResult(
                    success=False,
                    title="课件制作失败",
                    file_type="pptx",
                    error=str(exc),
                    metadata={"generation_stage": getattr(exc, "stage", "failed")},
                )
            except Exception as exc:
                return AgentResult(
                    success=False,
                    title="课件制作失败",
                    file_type="pptx",
                    error=str(exc),
                    metadata={"generation_stage": "failed"},
                )
        return await self.execute_task(input, **kwargs)
