"""
思维导图生成 Agent。
使用本地工具生成 HTML 思维导图文件。
"""

import os
import re
import json
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import AIMessage, ToolMessage

from app.infra.logging import get_logger
from app.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)


class MindmapState(BaseAgentState):
    need: str
    extra: str
    file_path: Optional[str]
    html_content: Optional[str]
    agent_output: Optional[str]


NEED_MAP = {
    "exam": "考前突击 (侧重考点与易错题)",
    "review": "课后复习 (侧重知识梳理与图解)",
    "deep": "深度探究 (侧重底层原理与拓展)",
    "practice": "实践应用 (侧重代码或实操案例)",
}


class MindmapGenerator(BaseResourceAgent):
    """思维导图生成 Agent。

    使用本地工具将 Markdown 转换为交互式 HTML 思维导图。

    Attributes:
        name:           "MindmapAgent"
        agent_dir:      agents/mindmap/，包含 prompt.md、tools/、skills/
        state_schema:   MindmapState，包含 need/extra/file_path/html_content/agent_output
        method:         generate_mindmap() — 对外入口
        output:         {success, file_path, html_content, agent_output, error}

    工作流: agent → tools(markdown_to_mindmap) → validate → retry/end
    DAG 阶段: foundation（首个执行，产物供后续 Agent 参考）
    黑板记忆: 无读取（作为首阶段，无前置依赖）
    """
    def __init__(self) -> None:
        super().__init__(
            name="MindmapAgent",
            agent_dir=Path(__file__).parent,
            state_schema=MindmapState,
            temperature=0.1,
        )
        self._mindmap_skill_tool_name: str | None = None
        self._mindmap_skill_description: str = ""
        self._mindmap_skill_instructions: str = ""

    async def _load_tools(self) -> None:
        """加载本地工具和 Skills，并记录详细日志。"""
        await super()._load_tools()

        local_tools = self.plugin_manager.list_local_tools()
        logger.info(f"[MindmapAgent] 已加载本地工具: {local_tools}")

        skills = self.plugin_manager.list_skills()
        skill_names = [s["name"] for s in skills]
        logger.info(f"[MindmapAgent] 已加载 Skills: {skill_names}")

        summary = self.plugin_manager.summary()
        logger.info(
            f"[MindmapAgent] 工具加载完成 — "
            f"本地: {len(summary['local_tools'])}, "
            f"Skills: {len(summary['skills'])}"
        )
        self._cache_mindmap_skill()

    def _cache_mindmap_skill(self) -> None:
        """缓存 create-mindmap 技能的元数据与正文，确保生成前可直接使用。"""
        self._mindmap_skill_tool_name = None
        self._mindmap_skill_description = ""
        self._mindmap_skill_instructions = ""

        for skill in self.plugin_manager.list_skills():
            if skill.get("name") != "create-mindmap":
                continue

            self._mindmap_skill_tool_name = skill.get("tool_name")
            self._mindmap_skill_description = skill.get("description", "")

            reader = getattr(self.plugin_manager, "_read_skill_instructions", None)
            if callable(reader):
                try:
                    self._mindmap_skill_instructions = str(reader("create-mindmap")).strip()
                except Exception as exc:
                    logger.warning(f"[MindmapAgent] 读取 create-mindmap 技能正文失败: {exc}")

            logger.info(
                "[MindmapAgent] 已缓存 create-mindmap 技能: "
                f"tool={self._mindmap_skill_tool_name or 'N/A'}"
            )
            return

        logger.warning("[MindmapAgent] 未找到 create-mindmap 技能，导图生成将退回 prompt 驱动模式")

    def _build_system_message(self, state: Any) -> str:
        need_key = state.get("need", "review")
        need_text = NEED_MAP.get(need_key, need_key)

        prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", "待定"),
            topic=state.get("topic", "未知知识点"),
            gap=state.get("gap", "无"),
            need=need_text,
            extra=state.get("extra", "无"),
        )

        prompt += (
            "\n\n【执行指南】\n"
            "1. 先按 create-mindmap 技能的规则组织 Markdown 思维导图。\n"
            "2. 再使用 `markdown_to_mindmap` 工具生成 HTML 思维导图。\n"
            "3. 生成成功后，向用户反馈生成的 HTML 文件路径即可。\n"
            "注意：不要直接输出 Markdown 源码，必须调用工具生成 HTML。"
        )

        if self._mindmap_skill_description:
            prompt += (
                "\n\n【可用技能】\n"
                f"- create-mindmap: {self._mindmap_skill_description}\n"
            )
            if self._mindmap_skill_tool_name:
                prompt += (
                    f"如需查看技能原文，可调用 `{self._mindmap_skill_tool_name}`；"
                    "但即使不显式调用，也必须遵循下方已加载的技能规则。\n"
                )

        if self._mindmap_skill_instructions:
            prompt += (
                "\n\n## [create-mindmap 技能指令]\n"
                f"{self._mindmap_skill_instructions}"
            )

        return self._append_context_to_prompt(prompt, state)

    def _build_initial_human_message(self, state: Any) -> str:
        topic = state.get('topic')
        gap = state.get('gap')
        need = state.get("need", "review")
        extra = state.get("extra", "")

        msg = f"请为知识点 '{topic}' 生成思维导图，并严格遵循 create-mindmap 技能的结构与格式要求。"
        if gap and gap != "无":
            msg += f" 特别注意学生在 '{gap}' 方面存在薄弱环节，请在图中重点体现。"
        if need:
            msg += f" 本次导图目标为：{need}。"
        if extra:
            msg += f" 额外要求：{extra}。"
        msg += " 请完成 Markdown 结构设计后立即调用 markdown_to_mindmap 生成 HTML。"
        return msg

    async def _validate_node(self, state: Any) -> dict:
        """从工具调用结果中提取 file_path 和 html_content。"""
        messages = state.get("messages", [])
        file_path = None
        html_content = None

        # 获取最后的 AI 消息作为 agent_output
        agent_output = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                agent_output = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        # 从 ToolMessage 中提取 markmap 工具返回的文件路径
        for msg in messages:
            if isinstance(msg, ToolMessage) and msg.name == "markdown_to_mindmap":
                content = msg.content

                # 统一转为可解析的对象
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            try:
                                inner = json.loads(item["text"]) if isinstance(item["text"], str) else item["text"]
                                if isinstance(inner, dict):
                                    file_path = inner.get("file_path") or inner.get("filePath")
                                    break
                            except (json.JSONDecodeError, TypeError):
                                continue
                        elif isinstance(item, str):
                            try:
                                inner = json.loads(item)
                                if isinstance(inner, dict):
                                    file_path = inner.get("file_path") or inner.get("filePath")
                                    break
                            except (json.JSONDecodeError, TypeError):
                                continue
                elif isinstance(content, dict):
                    file_path = content.get("file_path") or content.get("filePath")
                elif isinstance(content, str):
                    try:
                        res = json.loads(content)
                        if isinstance(res, dict):
                            file_path = res.get("file_path") or res.get("filePath")
                        elif isinstance(res, list) and res and isinstance(res[0], dict) and "text" in res[0]:
                            inner = json.loads(res[0]["text"]) if isinstance(res[0]["text"], str) else res[0]["text"]
                            if isinstance(inner, dict):
                                file_path = inner.get("file_path") or inner.get("filePath")
                    except json.JSONDecodeError:
                        pass

                    if not file_path:
                        m = re.search(r"(/.*\.html)", content)
                        if m:
                            file_path = m.group(1)

        # 读取 HTML 内容
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
            except Exception as e:
                logger.warning(f"[MindmapAgent] 无法读取 HTML 文件 {file_path}: {e}")

        is_valid = bool(file_path)
        retry_count = state.get("retry_count", 0) + 1

        if not is_valid:
            logger.warning(
                f"[MindmapAgent] 校验未通过 (retry={retry_count}): "
                f"未找到 file_path，已有 {len(messages)} 条消息"
            )

        return {
            "file_path": file_path,
            "html_content": html_content,
            "agent_output": agent_output,
            "is_valid": is_valid,
            "retry_count": retry_count,
            "validation_feedback": "" if is_valid else "未检测到思维导图文件路径。请确保调用了 markdown_to_mindmap 工具并正确生成了 HTML 文件。",
        }

    async def generate_mindmap(
        self,
        topic: str = "",
        gap: str = "",
        course: str = "",
        major: str = "通用",
        need: str = "review",
        extra: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[MindmapAgent] 收到生成请求: topic={topic}, gap={gap}")
        await self._ensure_graph()

        initial_state: MindmapState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "need": need,
            "extra": extra,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "file_path": None,
            "html_content": None,
            "agent_output": None,
            "is_valid": False,
            "validation_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 25})
        except Exception as e:
            logger.error(f"[MindmapAgent] 工作流执行失败: {e}")
            return {"success": False, "file_path": None, "html_content": None, "agent_output": "", "error": str(e)}

        return {
            "success": result.get("is_valid", False),
            "file_path": result.get("file_path"),
            "html_content": result.get("html_content"),
            "agent_output": result.get("agent_output", ""),
            "error": result.get("error") if not result.get("is_valid") else None,
        }

if __name__ == '__main__':
    import asyncio

    _gen = MindmapGenerator()
    result = asyncio.run(
        _gen.generate_mindmap(
            topic="Python 面向对象编程",
            gap="类与继承的理解",
            course="Python程序设计",
            major="计算机科学",
            need="review",
            extra="请包含 UML 类图示例",
        )
    )

    if result["success"]:
        print(f"思维导图生成成功: {result['file_path']}")
    else:
        print(f"生成失败: {result.get('error', '未知错误')}")
