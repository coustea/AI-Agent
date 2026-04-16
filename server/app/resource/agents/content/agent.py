"""
内容创作 Agent：生成个性化专业课程讲解文档。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode


from app.infra.logging import get_logger
from app.resource.base_agent import BaseResourceAgent, BaseAgentState
from app.tools.file_operator import save_to_workplace

logger = get_logger(__name__)


class ContentState(BaseAgentState):
    current_step: str
    outline: str
    content: str


_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json(text: str) -> dict:
    # 先尝试解析标准 ```json ... ``` 代码块，兼容审查模型常见输出格式。
    match = _FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 如果模型前后夹杂解释文字，这里再退一步抽取最外层 JSON 对象。
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {"passed": False, "feedback": "无法解析审查结果"}


_REVIEW_PROMPT = (
    "你是一位教学文档质量审查专家。请审查以下课程讲解文档的质量。\n\n"
    "## 审查标准\n"
    "1. 字数检查：文档正文应在 1500-3000 字之间\n"
    "2. 结构完整性：是否包含 概述、核心讲解、案例分析、常见误区、总结 等主要章节\n"
    "3. 内容针对性：是否围绕主题 {topic} 深入展开，而非泛泛而谈\n"
    "4. 个性化匹配：是否考虑了用户画像中描述的学习特点\n"
    "5. 案例质量：是否包含至少一个完整的实际案例\n\n"
    "## 待审查文档\n"
    "{content}\n\n"
    "## 大纲\n"
    "{outline}\n\n"
    "## 输出要求\n"
    "请严格按以下 JSON 格式输出审查结论，不要包含代码围栏：\n"
    '{{"passed": true/false, "feedback": "如果不通过，说明具体原因和改进建议"}}'
)


class ContentWriter(BaseResourceAgent):
    """个性化课程讲解文档生成 Agent。"""

    tool_names = [
        "save_to_workplace", "read_file_safe",
        "write_file", "edit_file", "append_file", "read_file_lines",
        "list_directory", "file_tree", "find_files", "get_file_info",
        "save_docx_file", "extract_pdf_text",
    ]
    skill_names = ["docx", "pdf"]
    def __init__(self) -> None:
        super().__init__(
            name="ContentAgent",
            agent_dir=Path(__file__).parent,
            state_schema=ContentState,
            temperature=0.3,
        )

    @staticmethod
    def _workflow_timeout_seconds() -> int:
        """Allow enough time for outline + content + review, while staying configurable."""
        # 内容 Agent 需要经历“大纲 -> 正文 -> 审查”三轮，因此超时阈值单独拉高。
        return int(os.getenv("CONTENT_AGENT_TIMEOUT_SECONDS", "360"))

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        ctx = ""
        # 把思维导图的骨架提前注入正文 Agent，减少正文结构跑偏。
        if "mindmap" in shared_memory:
            mm = shared_memory["mindmap"].get("agent_output", "")
            if mm: ctx += f"【思维导图核心结构】\n{mm}\n"
        return ctx

    async def _build_graph(self):
        """P1：override 父类默认图拓扑，插入 step_router 节点实现分步生成。"""
        # self._tools 已由 _load_tools() 填充，无需重复初始化
        graph = StateGraph(self.state_schema)

        # agent 负责与 LLM 交互，tools 执行工具，step_router 在“大纲/正文”之间切换，
        # validate 做最终质量审查。
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", self._tools_node)
        graph.add_node("step_router", self._step_router_node)
        graph.add_node("validate", self._validate_node)

        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", self._custom_tools_condition)
        graph.add_edge("tools", "agent")

        graph.add_conditional_edges(
            "step_router",
            self._step_router_condition,
            {"agent": "agent", "validate": "validate"}
        )
        graph.add_conditional_edges(
            "validate",
            self._should_retry,
            path_map={"end": END, "retry": "agent"},
        )
        compiled = graph.compile()
        logger.info(f"[{self.name}] StateGraph 构建完成 (含 step_router, 工具数: {len(self._tools)})")
        return compiled

    async def _tools_node(self, state: Any) -> dict:
        """Wrap ToolNode so ContentAgent can log tool calls and outputs explicitly."""
        messages = state.get("messages", [])
        last_ai = messages[-1] if messages and isinstance(messages[-1], AIMessage) else None
        pending_calls = list(getattr(last_ai, "tool_calls", []) or [])
        if pending_calls:
            logger.info(
                "[ContentAgent] 即将执行工具: names=%s args=%s",
                [call.get("name", "unknown") for call in pending_calls],
                [call.get("args", {}) for call in pending_calls],
            )

        tool_node = ToolNode(self._tools)
        result = await tool_node.ainvoke(state)

        output_messages = result.get("messages", []) if isinstance(result, dict) else []
        for msg in output_messages:
            if isinstance(msg, ToolMessage):
                logger.info(
                    "[ContentAgent] 工具执行完成: name=%s tool_call_id=%s output_preview=%r",
                    getattr(msg, "name", "unknown"),
                    getattr(msg, "tool_call_id", ""),
                    str(msg.content)[:300],
                )
        return result

    def _custom_tools_condition(self, state: Any) -> str:
        messages = state.get("messages", [])
        # 只要最后一条 AI 消息声明了 tool_calls，就先进入 tools 节点消费工具调用。
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            return "tools"
        return "step_router"

    def _step_router_condition(self, state: Any) -> str:
        step = state.get("current_step", "outline")
        # 第一步先拿到大纲；拿到大纲但还没有正文时，再回到 agent 继续扩写正文。
        if step == "outline":
            return "agent"
        if step == "content" and state.get("outline") and not state.get("content"):
            return "agent"
        return "validate"

    def _build_system_message(self, state: Any) -> str:
        """构建 System Prompt（返回字符串）。"""
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            user_profile="",
        )
        return self._append_context_to_prompt(system_prompt, state)

    def _build_initial_human_message(self, state: Any) -> str:
        """ContentWriter 使用分步生成，此方法由 _agent_node 动态调用。"""
        return ""

    def _save_to_workplace(self, sub_dir: str, topic: str, content: str, ext: str = "md") -> str:
        # 统一走共享 save_to_workplace，保持所有资源文件的命名和保存位置一致。
        return save_to_workplace(
            sub_dir=sub_dir,
            topic=topic,
            content=content,
            ext=ext,
        )

    @staticmethod
    def _build_content_request(outline: str) -> str:
        outline_text = outline.strip() or "请沿用你刚刚生成的大纲结构。"
        # 第二轮提示词只做一件事：强制模型沿着已有大纲写完整正文。
        return (
            "请根据以下大纲撰写完整的专业讲解文档（1500-3000字），严格遵循大纲结构，每个章节都要有充实的内容。"
            "不要向用户追问补充信息，直接完成正文写作。\n\n"
            f"现有大纲：\n{outline_text}"
        )

    @staticmethod
    def _looks_like_refusal(content: str) -> bool:
        text = (content or "").strip()
        if not text:
            return True
        refusal_markers = (
            "无法按照要求完成",
            "无法完成",
            "请补充",
            "请您补充",
            "未提供具体的大纲",
            "未提供大纲",
            "请提供大纲",
            "需要更多信息",
        )
        return any(marker in text for marker in refusal_markers)

    @classmethod
    def _needs_content_recovery(cls, content: str) -> bool:
        text = (content or "").strip()
        if cls._looks_like_refusal(text):
            return True
        return len(text) < 500

    async def _agent_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        current_step = state.get("current_step", "outline")
        retry_count = state.get("retry_count", 0)
        feedback = state.get("validation_feedback", "")
        outline = state.get("outline", "")

        logger.info(f"[ContentAgent] _agent_node: step={current_step}, retry={retry_count}")

        if current_step == "outline" and not messages:
            # 首轮只要求模型先产出大纲，降低一次性直接写长文失败的概率。
            sys_prompt = self._build_system_message(state)
            human_text = "请先为这份讲解文档生成一份详细的大纲（列出各章节标题及每节要点的简短描述）。"
            messages = [SystemMessage(content=sys_prompt), HumanMessage(content=human_text)]
        elif current_step == "outline" and retry_count > 0 and feedback and len(messages) < 3:
            # 如果大纲阶段就被打回，这里把审查反馈显式喂回去，要求重写大纲。
            messages.append(HumanMessage(
                content=f"上一次文档未通过审查，原因：{feedback}\n请根据上述反馈修正大纲后重新生成。"
            ))
        elif current_step == "content" and retry_count > 0 and feedback:
            # 正文阶段重试时，保留已有大纲，只让模型根据反馈修正文案。
            messages.append(HumanMessage(
                content=(
                    f"上一次正文未通过审查，原因：{feedback}\n"
                    "请基于现有大纲重新撰写完整的专业讲解文档，不要向用户追问额外信息。\n\n"
                    f"现有大纲：\n{outline or '请沿用你刚刚生成的大纲结构。'}"
                )
            ))
        elif current_step == "content" and not any("撰写完整的专业讲解文档" in str(m.content) for m in messages):
            # 第一次进入正文阶段时，补一条“按大纲扩写”的 HumanMessage。
            messages.append(HumanMessage(content=self._build_content_request(outline)))

        llm_with_tools = self.llm.bind_tools(self._tools) if self._tools else self.llm

        # 规范化结构化 ToolMessage 内容，避免部分模型接口拒绝 list 类型 content
        from app.shared.sanitizers import sanitize_tool_messages
        messages = sanitize_tool_messages(messages)

        logger.info(
            "[ContentAgent] 调用 LLM: step=%s message_count=%d outline_len=%d feedback=%r",
            current_step,
            len(messages),
            len(outline),
            feedback[:200],
        )
        llm_timeout = int(os.getenv("CONTENT_LLM_TIMEOUT", "180"))
        try:
            response = await asyncio.wait_for(
                llm_with_tools.ainvoke(messages),
                timeout=llm_timeout,
            )
        except asyncio.TimeoutError:
            logger.error("[ContentAgent] LLM 调用超时: step=%s timeout=%ds", current_step, llm_timeout)
            return {"error": f"LLM 调用超时 ({llm_timeout}s)", "is_valid": False}
        if isinstance(response, AIMessage) and getattr(response, "tool_calls", None):
            logger.info(
                "[ContentAgent] LLM 选择工具: names=%s args=%s",
                [call.get("name", "unknown") for call in response.tool_calls],
                [call.get("args", {}) for call in response.tool_calls],
            )
        logger.info(
            "[ContentAgent] LLM 返回: step=%s tool_calls=%s content_preview=%r",
            current_step,
            bool(getattr(response, "tool_calls", None)),
            (response.content or "")[:300] if isinstance(response.content, str) else str(response.content)[:300],
        )

        return {"messages": [response]}

    async def _step_router_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        current_step = state.get("current_step", "outline")

        last_content = ""
        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content
            if isinstance(content, str):
                last_content = content.strip()
            else:
                last_content = str(content).strip()

        if current_step == "outline":
            # 大纲阶段结束后，把大纲落回状态，并切换到正文阶段。
            logger.info(f"[ContentAgent] 大纲生成完成，长度={len(last_content)}, 预览={last_content[:200]!r}")
            return {"outline": last_content, "current_step": "content"}
        else:
            # 正文阶段结束后，只回填 content，后续交给 validate 做质量判定。
            logger.info(f"[ContentAgent] 文档扩展完成，长度={len(last_content)}, 预览={last_content[:200]!r}")
            return {"content": last_content}

    async def _validate_node(self, state: Any) -> dict:
        content = state.get("content", "")
        outline = state.get("outline", "")
        error = state.get("error")

        if error or not content:
            logger.warning(
                "[ContentAgent] 校验未通过: error=%r content_len=%d outline_len=%d",
                error,
                len(content),
                len(outline),
            )
            return {
                "is_valid": False,
                "validation_feedback": error or "未生成正文，请基于现有大纲直接补全完整讲解文档，不要追问用户。",
                "retry_count": state.get("retry_count", 0) + 1,
                "current_step": "content" if outline else "outline",
            }

        logger.info("[ContentAgent] _validate_node: 开始质量审查")

        word_count = len(content)
        # 先做本地快速校验，避免每次都再额外调用一次评审模型。
        if word_count < 800:
            logger.warning("[ContentAgent] 正文字数不足: %d", word_count)
            return {
                "is_valid": False,
                "validation_feedback": f"文档字数仅 {word_count} 字，远低于 1500 字的最低要求，请大幅扩展。",
                "retry_count": state.get("retry_count", 0) + 1,
                "current_step": "content",
            }

        prompt = _REVIEW_PROMPT.format(
            topic=state.get("topic", ""),
            content=content[:3000],
            outline=outline[:1000],
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            review = _extract_json(response.content)
            passed = review.get("passed", False)
            feedback = review.get("feedback", "")

            logger.info(f"[ContentAgent] 审查结果: passed={passed}, feedback={feedback}")
            return {
                "is_valid": passed,
                "validation_feedback": feedback,
                "retry_count": state.get("retry_count", 0) + 1 if not passed else state.get("retry_count", 0),
                "current_step": "content",
            }
        except Exception as e:
            logger.exception("[ContentAgent] 审查失败")
            return {"is_valid": True, "validation_feedback": ""}

    async def _fallback_generate_content(self, state: ContentState) -> dict[str, Any]:
        # 当图工作流超时或审查链路异常时，降级为一次性长文生成，保证至少给用户返回可读内容。
        prompt = (
            "你是一位高校课程讲解文档作者。请直接生成一份完整的 Markdown 课程讲解文档，"
            "不要追问用户，不要输出额外说明。\n\n"
            f"专业：{state.get('major', '通用')}\n"
            f"课程：{state.get('course', '')}\n"
            f"主题：{state.get('topic', '')}\n"
            f"知识短板：{state.get('gap', '')}\n"
            f"参考大纲：\n{state.get('outline', '') or '请按标准教学文档结构自行组织'}\n"
            "要求：\n"
            "1. 必须包含：概述、核心讲解、案例分析、常见误区、总结\n"
            "2. 字数尽量充实，至少 1200 字\n"
            "3. 面向初学者，讲解清晰具体\n"
            "4. 直接输出最终 Markdown 文档\n"
            "5. 严禁向用户索要补充信息，必须直接完成全文\n"
            "6. 控制在 1500-3000 字之间，不要过长\n"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip() if isinstance(response.content, str) else str(response.content)
        outline = "1. 概述\n2. 核心讲解\n3. 案例分析\n4. 常见误区\n5. 总结"
        return {"content": content, "outline": outline, "error": None}

    async def generate_content(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[ContentAgent] 收到生成请求: topic={topic}")
        await self._ensure_graph()
        start_time = time.perf_counter()
        timeout_seconds = self._workflow_timeout_seconds()

        initial_state: ContentState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "current_step": "outline",
            "outline": "",
            "content": "",
            "is_valid": False,
            "validation_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            logger.info("[ContentAgent] 开始执行工作流: timeout=%ss topic=%r", timeout_seconds, topic)
            result = await asyncio.wait_for(
                self.graph.ainvoke(initial_state, {"recursion_limit": 20}),
                timeout=timeout_seconds,
            )
            logger.info(
                "[ContentAgent] 工作流执行完成: elapsed=%.2fs keys=%s content_len=%d outline_len=%d",
                time.perf_counter() - start_time,
                sorted(result.keys()),
                len(result.get("content", "") or ""),
                len(result.get("outline", "") or ""),
            )
        except asyncio.TimeoutError:
            logger.exception(
                "[ContentAgent] 工作流执行超时: timeout=%ss elapsed=%.2fs topic=%r",
                timeout_seconds,
                time.perf_counter() - start_time,
                topic,
            )
            try:
                logger.info("[ContentAgent] 尝试降级生成正文")
                result = await self._fallback_generate_content(initial_state)
            except Exception as fallback_error:
                logger.exception("[ContentAgent] 超时后的降级生成失败")
                return {
                    "success": False,
                    "content": "",
                    "file_path": None,
                    "outline": "",
                    "error": str(fallback_error),
                }
        except Exception:
            logger.exception(
                "[ContentAgent] 工作流执行失败: elapsed=%.2fs topic=%r",
                time.perf_counter() - start_time,
                topic,
            )
            try:
                logger.info("[ContentAgent] 尝试降级生成正文")
                result = await self._fallback_generate_content(initial_state)
            except Exception as fallback_error:
                logger.exception("[ContentAgent] 异常后的降级生成失败")
                return {
                    "success": False,
                    "content": "",
                    "file_path": None,
                    "outline": "",
                    "error": str(fallback_error),
                }

        content = result.get("content", "")
        outline = result.get("outline", "")
        if self._needs_content_recovery(content):
            try:
                logger.warning(
                    "[ContentAgent] 正文需要补救: content_len=%d refusal=%s，尝试降级补全",
                    len(content or ""),
                    self._looks_like_refusal(content),
                )
                # 这里复用已有 outline，尽量让降级内容仍然贴合前面已经规划出的结构。
                initial_state["outline"] = outline
                fallback = await self._fallback_generate_content(initial_state)
                content = fallback.get("content", "")
                outline = fallback.get("outline", outline)
            except Exception as fallback_error:
                logger.exception("[ContentAgent] 降级生成失败")
        if self._needs_content_recovery(content):
            logger.error("[ContentAgent] 补救后正文仍不可用，判定生成失败")
            content = ""

        success = bool(content)
        file_path = None
        if success:
            file_path = self._save_to_workplace("content", topic, content, "md")
            try:
                saved_content = Path(file_path).read_text(encoding="utf-8")
                if saved_content.strip():
                    content = saved_content
            except Exception:
                logger.exception("[ContentAgent] 文档已保存，但回读文件失败: %s", file_path)
            logger.info(
                "[ContentAgent] 文档生成成功: file_path=%s content_len=%d outline_len=%d elapsed=%.2fs",
                file_path,
                len(content),
                len(outline),
                time.perf_counter() - start_time,
            )
        else:
            logger.error(
                "[ContentAgent] 文档生成失败: outline_len=%d error=%r elapsed=%.2fs",
                len(outline),
                result.get("error"),
                time.perf_counter() - start_time,
            )

        return {
            "success": success,
            "content": content,
            "outline": outline,
            "file_path": file_path,
            "error": result.get("error") if not success else None,
        }
