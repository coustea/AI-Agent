"""PPTAgent & PPTService — 基于无状态流 + python-pptx 的课件生成智能体。

工作流（全流程基于 output_dir 文件系统流转，无内存 state 闭包）：
1. 主规划智能体 (PPTAgent) 按需加载 ``pptx`` skill，规划 60-30-10 配色与 ``DESIGN_PLAN.json``。
2. ``init_deck_plan`` 从物理技能目录 ``server/skills/pptx/templates/`` 复制 ``ppt_helpers.py``、``build_deck.py`` 与 ``slide_skeleton.py`` 到工作区。
3. 调用共享无状态 ``subagent(prompts=[...])`` 工具并行派生子智能体，每个子智能体在全新 ``messages=[]`` 上下文中编写 ``slides/sXX.py`` 并调用 ``test_slide`` 通过单页 OOXML 几何校验。
4. 调用 ``build_and_audit_deck`` 编译 ``deck.pptx``、执行整套 OOXML 几何审计、渲染 ``thumbnails/grid.png`` 并发布交互式 ``slides.html`` 与 ``AUDIT_REPORT.json``。
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from app.config import path_node_ppt_url, static_url, user_path_node_ppt_dir
from app.infra.llm import get_llm_client
from app.infra.logging import get_logger
from app.shared.ppt.schemas import (
    DeckDesignPlan,
    PPTArtifact,
    PPTGenerationError,
    PPTPreferences,
    PathPPT,
    ResourcePPT,
)
from app.shared.ppt.tool import (
    _compile_and_audit_workspace,
    _test_single_slide_script,
    build_ppt_planner_tools,
)
from app.shared.tools import ToolRegistry, get_skill_loader

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest
    from app.resource.schemas import AgentResult

logger = get_logger(__name__)

ProgressCallback = Callable[[str, int], Awaitable[None]]


def ppt_pipeline_metadata() -> dict[str, Any]:
    """返回 PPT 引擎元数据标记。"""
    return {
        "engine": "python-pptx-harness-v2",
        "architecture": "stateless-subagents",
        "skill": "pptx",
    }


class PPTAgent:
    """无状态流 python-pptx 教学课件生成智能体。"""

    async def generate(
        self,
        request: ResourcePPT | PathPPT | BaseModel,
        output_dir: Path,
        *,
        progress: ProgressCallback | None = None,
    ) -> PPTArtifact:
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "slides").mkdir(exist_ok=True)

        topic, prompt_context = self._format_request_context(request)
        skill_loader = get_skill_loader()
        skill_catalog = skill_loader.describe_skills(only=["pptx"])

        if progress:
            await progress("PPT 首席架构师正在基于 pptx 技能规划幻灯片全书设计蓝图...", 10)

        planner_tools = build_ppt_planner_tools(
            output_dir=output_dir,
            skill_loader=skill_loader,
            topic=topic,
            progress=progress,
        )

        system_prompt = (
            "你是 PPT 首席架构师智能体 (PPTAgent)，采用无状态子智能体架构生成专业级 PowerPoint (.pptx) 教学课件。\n\n"
            "可用技能 (Skills):\n"
            f"{skill_catalog}\n\n"
            "必须严格遵循以下执行流程：\n"
            "1. 先调用 `load_skill(name='pptx')` 学习 60-30-10 配色法则、深浅三明治结构与不重复版式规范。\n"
            "2. 调用 `init_deck_plan` 规划 6~9 页教学幻灯片，并从 `skills/pptx/templates/` 复制物理脚手架：\n"
            "   - `s01` 必须使用 `hero_cover`\n"
            "   - `s02` 必须使用 `roadmap_grid`\n"
            "   - 中间教学页在 `split_concept`、`three_columns`、`process_flow`、`comparison_matrix`、`bento_quad`、`code_or_formula_spotlight` 之间轮换，相邻两页绝不重复！\n"
            "   - 最后一页必须使用 `summary_takeaways`\n"
            "   - 每页的 `key_points` 必须包含 3 条高信息密度的教学干货，格式为 `'小标题：具体阐述'`。\n"
            "3. 调用 `subagent(prompts=[...])`（每页一条包含 slide_id、layout、title、key_points 的子任务提示词），并行让无状态子智能体定制每页 `slides/sXX.py` 代码并通过 `test_slide` 校验。\n"
            "4. 调用 `build_and_audit_deck` 编译 `deck.pptx`、生成 `thumbnails/grid.png` 与 `slides.html`。\n"
            "5. 若 `build_and_audit_deck` 报错，调用 `subagent(prompts=[...])` 修复问题页并重新 `build_and_audit_deck`。"
        )

        plan_file = output_dir / "DESIGN_PLAN.json"
        audit_file = output_dir / "AUDIT_REPORT.json"

        def _verify_planner_done() -> str | None:
            if not plan_file.is_file():
                return "You have not called `init_deck_plan` yet."
            if not audit_file.is_file():
                passed, report = _compile_and_audit_workspace(output_dir, title=topic)
                if not passed:
                    return f"OOXML Audit failed: {json.dumps(report.get('errors') or report, ensure_ascii=False)}"
                return None

            audit_data = json.loads(audit_file.read_text(encoding="utf-8"))
            if not audit_data.get("passed"):
                return f"OOXML Audit has unresolved errors: {json.dumps(audit_data.get('errors') or audit_data, ensure_ascii=False)}"
            return None

        client, spec = get_llm_client("text")
        registry = ToolRegistry(planner_tools)
        tool_schemas = registry.get_tools_description()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_context},
        ]

        try:
            async with asyncio.timeout(360.0):
                for step in range(1, 15):
                    response = await client.chat.completions.create(
                        model=spec.model_name,
                        messages=messages,
                        temperature=0.1,
                        tools=tool_schemas,
                        tool_choice="auto",
                    )
                    msg = response.choices[0].message
                    raw_tool_calls = msg.tool_calls or []
                    assistant_dict: dict[str, Any] = {
                        "role": "assistant",
                        "content": msg.content or "",
                    }
                    if raw_tool_calls:
                        assistant_dict["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments or "{}",
                                },
                            }
                            for tc in raw_tool_calls
                        ]
                    messages.append(assistant_dict)

                    if not raw_tool_calls:
                        gate_error = _verify_planner_done()
                        if gate_error:
                            messages.append({
                                "role": "user",
                                "content": f"[Quality Gate Failed]\n{gate_error}\n请立即调用工具修复。",
                            })
                            continue
                        break

                    async def _exec_tc(tc: Any, current_step: int = step) -> dict[str, Any]:
                        t_name = tc.function.name
                        if progress and registry.has_tool(t_name):
                            try:
                                await progress(f"[PPT] 执行工具 {t_name}...", min(90, 15 + current_step * 5))
                            except Exception:
                                pass
                        output = await registry.execute_as_text(t_name, tc.function.arguments or "{}", call_id=tc.id)
                        return {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": output[:40_000],
                        }

                    tool_msgs = await asyncio.gather(*(_exec_tc(tc) for tc in raw_tool_calls))
                    messages.extend(tool_msgs)
        except TimeoutError:
            raise PPTGenerationError("PPT 规划与生成超时 (>360s)", stage="planning")
        except Exception as exc:
            if isinstance(exc, PPTGenerationError):
                raise
            raise PPTGenerationError(f"PPT 规划异常: {exc}", stage="planning") from exc

        if not plan_file.is_file():
            raise PPTGenerationError("PPT 主规划循环未完成幻灯片蓝图规划", stage="planning")

        plan_obj = DeckDesignPlan.model_validate_json(plan_file.read_text(encoding="utf-8"))
        audit_obj: dict[str, Any] = (
            json.loads(audit_file.read_text(encoding="utf-8")) if audit_file.is_file() else {}
        )
        if not audit_obj.get("passed"):
            passed, audit_obj = _compile_and_audit_workspace(output_dir, title=plan_obj.title)
            if not passed:
                raise PPTGenerationError(
                    f"PPT OOXML 审计未通过: {audit_obj.get('errors') or audit_obj.get('error')}",
                    stage="ooxml-audit",
                )

        if progress:
            await progress("PPTX 与交互预览课件生成完成！", 100)

        html_path = output_dir / "slides.html"
        pptx_path = output_dir / "deck.pptx"

        return PPTArtifact(
            title=plan_obj.title,
            path=html_path,
            pptx_path=pptx_path,
            generated_at=datetime.now(timezone.utc),
            slide_count=int(audit_obj.get("slide_count") or len(plan_obj.slides)),
        )

    @staticmethod
    def _format_request_context(request: Any) -> tuple[str, str]:
        """将 ResourcePPT 或 PathPPT 转换为清晰的规划提示词。"""
        if isinstance(request, PathPPT):
            topic = request.node_title or request.tutorial_title
            kp_str = "、".join(request.knowledge_points[:12]) or "核心概念与机制"
            weak_str = "、".join(request.weak_knowledge_points[:8]) or "无"
            context = (
                f"【学习路径课件任务】\n"
                f"- 路径名称: {request.path_title}\n"
                f"- 节点主题: {topic}\n"
                f"- 教学目标: {request.path_goal}\n"
                f"- 核心知识点: {kp_str}\n"
                f"- 薄弱点强化: {weak_str}\n"
                f"- 教程摘要: {request.tutorial_summary}\n\n"
                f"【源教程内容】\n{request.tutorial_core_content[:12_000]}"
            )
            return topic, context

        if isinstance(request, ResourcePPT):
            plan_dict = request.resource_plan or {}
            topic = str(plan_dict.get("topic") or request.learning_need[:48]).strip()
            goal = str(plan_dict.get("learner_goal") or request.learning_need).strip()
            artifact_blocks: list[str] = []
            for art in request.artifacts[:8]:
                mat_lines = "\n".join(f"  * {m}" for m in art.materials[:6])
                artifact_blocks.append(f"### [{art.agent_id}] {art.title}\n{art.summary}\n{mat_lines}")
            materials_text = "\n\n".join(artifact_blocks) or "请围绕主题系统展开核心概念、原理、流程与案例对比。"
            context = (
                f"【多智能体资源课件任务】\n"
                f"- 课程主题: {topic}\n"
                f"- 学习目标: {goal}\n"
                f"- 学习场景: {request.learning_scenario}\n"
                f"- 偏好风格: narrative={request.preferences.narrative_style}, density={request.preferences.density}\n\n"
                f"【上游资源交接素材】\n{materials_text[:12_000]}"
            )
            return topic, context

        raw_topic = str(getattr(request, "title", None) or getattr(request, "learning_need", "核心课程专题"))[:48]
        return raw_topic, f"请围绕主题《{raw_topic}》设计一套结构化教学 PPTX 课件。"


class PPTService:
    """PPT 生成服务 — 统一封装 ResourcePPT 与 PathPPT 的生成入口。"""

    def __init__(self, *, generator: PPTAgent | None = None) -> None:
        self._generator = generator or PPTAgent()

    async def generate(
        self,
        request: ResourcePPT | PathPPT,
        output_dir: Path,
        *,
        progress: ProgressCallback | None = None,
    ) -> PPTArtifact:
        return await self._generator.generate(
            request,
            output_dir=output_dir,
            progress=progress,
        )

    async def generate_for_path(
        self,
        request: "PathResourceRequest",
    ) -> "AgentResult":
        from app.resource.schemas import AgentResult

        logger.info(
            "[PPTService] 开始路径节点 PPTX 生成: node_id=%s node_title=%s",
            request.node_id,
            request.node_title,
        )

        tutorial = request.tutorial
        if tutorial is None or not tutorial.content_markdown.strip():
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error="缺少教程正文内容，无法生成 PPT",
            )

        ppt_request = PathPPT(
            username=request.username,
            profile=request.profile,
            preferences=PPTPreferences(),
            path_title=request.path_title,
            path_goal=request.path_goal,
            node_title=request.node_title,
            node_key=request.node_key,
            difficulty=request.difficulty,
            knowledge_points=list(tutorial.knowledge_points or []),
            weak_knowledge_points=list(tutorial.weak_knowledge_points or []),
            tutorial_title=tutorial.title,
            tutorial_summary=tutorial.summary or "",
            tutorial_knowledge_points=list(tutorial.knowledge_points or []),
            tutorial_core_content=tutorial.content_markdown.strip(),
        )

        output_dir = user_path_node_ppt_dir(
            request.username,
            str(request.path_id),
            str(request.node_id),
        )
        try:
            artifact = await self.generate(ppt_request, output_dir)
        except PPTGenerationError as exc:
            logger.exception("[PPTService] 路径 PPT 生成失败: stage=%s error=%s", exc.stage, exc)
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error=str(exc),
                metadata={"generation_stage": exc.stage},
            )

        artifact.html_url = path_node_ppt_url(
            request.username,
            str(request.path_id),
            str(request.node_id),
        )
        if artifact.pptx_path and artifact.pptx_path.is_file():
            artifact.pptx_url = static_url(artifact.pptx_path)

        return AgentResult(
            success=True,
            title=f"{artifact.title} - 教学课件",
            file_type="html",
            content="",
            summary=f"生成 {artifact.slide_count} 页 PPTX 教学课件",
            metrics={"slide_count": artifact.slide_count},
            metadata={
                "agent_id": "ppt",
                "html_file_path": str(artifact.path),
                "html_url": artifact.html_url,
                "pptx_file_path": str(artifact.pptx_path or ""),
                "pptx_url": artifact.pptx_url,
                "slide_count": artifact.slide_count,
                "file_size": artifact.path.stat().st_size if artifact.path.is_file() else 0,
                "ppt_pipeline": ppt_pipeline_metadata(),
            },
        )


__all__ = [
    "PPTAgent",
    "PPTService",
    "ProgressCallback",
    "_compile_and_audit_workspace",
    "_test_single_slide_script",
    "ppt_pipeline_metadata",
]
