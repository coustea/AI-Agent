"""
内容创作 Agent：生成个性化专业课程讲解文档。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.modules.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)


class ContentState(BaseAgentState):
    current_step: str
    outline: str
    content: str


_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json(text: str) -> dict:
    match = _FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
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
    "1. 字数检查：文档正文应在 2000-5000 字之间\n"
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
    """个性化课程讲解文档生成 Agent。

    采用分步生成策略：先生成大纲（outline），再根据大纲扩展完整文档，
    最后由 LLM 进行质量审查（字数、结构、案例等）。

    Attributes:
        name:           "ContentAgent"
        agent_dir:      agents/content/，包含 prompt.md
        state_schema:   ContentState，包含 current_step/outline/content
        method:         generate_content() — 对外入口
        output:         {success, content, outline, file_path, error}

    工作流: agent → tools → step_router → (outline→agent 继续生成 / content→validate 审查) → retry/end
    DAG 阶段: core（依赖 mindmap）
    黑板记忆: 读取 mindmap.agent_output（思维导图核心结构）
    """
    def __init__(self) -> None:
        super().__init__(
            name="ContentAgent",
            agent_dir=Path(__file__).parent,
            state_schema=ContentState,
            temperature=0.3,
        )

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        ctx = ""
        if "mindmap" in shared_memory:
            mm = shared_memory["mindmap"].get("agent_output", "")
            if mm: ctx += f"【思维导图核心结构】\n{mm}\n"
        return ctx

    async def _build_graph(self):
        """P1：override 父类默认图拓扑，插入 step_router 节点实现分步生成。"""
        # self._tools 已由 _load_tools() 填充，无需重复初始化
        graph = StateGraph(self.state_schema)

        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
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

    def _custom_tools_condition(self, state: Any) -> str:
        messages = state.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            return "tools"
        return "step_router"

    def _step_router_condition(self, state: Any) -> str:
        step = state.get("current_step", "outline")
        if step == "outline":
            return "agent"
        else:
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
        from .tools import save_to_workplace

        if callable(save_to_workplace):
            return save_to_workplace(sub_dir, topic, content, ext)

        invoke = getattr(save_to_workplace, "invoke", None)
        if callable(invoke):
            return invoke(
                {
                    "sub_dir": sub_dir,
                    "topic": topic,
                    "content": content,
                    "ext": ext,
                }
            )

        run = getattr(save_to_workplace, "run", None)
        if callable(run):
            return run(
                {
                    "sub_dir": sub_dir,
                    "topic": topic,
                    "content": content,
                    "ext": ext,
                }
            )

        raise TypeError("save_to_workplace 既不是可调用函数，也不是支持 invoke/run 的工具对象")

    async def _agent_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        current_step = state.get("current_step", "outline")
        retry_count = state.get("retry_count", 0)
        feedback = state.get("validation_feedback", "")
        outline = state.get("outline", "")

        logger.info(f"[ContentAgent] _agent_node: step={current_step}, retry={retry_count}")

        if current_step == "outline" and not messages:
            sys_prompt = self._build_system_message(state)
            human_text = "请先为这份讲解文档生成一份详细的大纲（列出各章节标题及每节要点的简短描述）。"
            messages = [SystemMessage(content=sys_prompt), HumanMessage(content=human_text)]
        elif current_step == "outline" and retry_count > 0 and feedback and len(messages) < 3:
            messages.append(HumanMessage(
                content=f"上一次文档未通过审查，原因：{feedback}\n请根据上述反馈修正大纲后重新生成。"
            ))
        elif current_step == "content" and retry_count > 0 and feedback:
            messages.append(HumanMessage(
                content=(
                    f"上一次正文未通过审查，原因：{feedback}\n"
                    "请基于现有大纲重新撰写完整的专业讲解文档，不要向用户追问额外信息。\n\n"
                    f"现有大纲：\n{outline or '请沿用你刚刚生成的大纲结构。'}"
                )
            ))
        elif current_step == "content" and not any("撰写完整的专业讲解文档" in str(m.content) for m in messages):
            messages.append(HumanMessage(
                content=(
                    "请根据以上大纲撰写完整的专业讲解文档（2000-5000字），严格遵循大纲结构，每个章节都要有充实的内容。"
                    "不要向用户追问补充信息，直接完成正文写作。"
                )
            ))

        llm_with_tools = self.llm.bind_tools(self._tools) if self._tools else self.llm

        # 规范化结构化 ToolMessage 内容，避免部分模型接口拒绝 list 类型 content
        from langchain_core.messages import ToolMessage
        safe_messages = []
        for msg in messages:
            if getattr(msg, "type", "") == "tool" and isinstance(msg.content, list):
                texts = []
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    else:
                        texts.append(str(block))
                safe_msg = ToolMessage(
                    content="\n".join(texts),
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                    status=getattr(msg, "status", "success")
                )
                safe_messages.append(safe_msg)
            else:
                safe_messages.append(msg)
        
        response = await llm_with_tools.ainvoke(safe_messages)

        return {"messages": [response]}

    async def _step_router_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        current_step = state.get("current_step", "outline")

        last_content = ""
        if messages and isinstance(messages[-1], AIMessage):
            last_content = messages[-1].content.strip()

        if current_step == "outline":
            logger.info(f"[ContentAgent] 大纲生成完成，长度={len(last_content)}")
            return {"outline": last_content, "current_step": "content"}
        else:
            logger.info(f"[ContentAgent] 文档扩展完成，长度={len(last_content)}")
            return {"content": last_content}

    async def _validate_node(self, state: Any) -> dict:
        content = state.get("content", "")
        outline = state.get("outline", "")
        error = state.get("error")

        if error or not content:
            return {
                "is_valid": False,
                "validation_feedback": error or "未生成正文，请基于现有大纲直接补全完整讲解文档，不要追问用户。",
                "retry_count": state.get("retry_count", 0) + 1,
                "current_step": "content" if outline else "outline",
            }

        logger.info("[ContentAgent] _validate_node: 开始质量审查")

        word_count = len(content)
        if word_count < 500:
            return {
                "is_valid": False,
                "validation_feedback": f"文档字数仅 {word_count} 字，远低于 2000 字的最低要求，请大幅扩展。",
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
            logger.error(f"[ContentAgent] 审查失败: {e}")
            return {"is_valid": True, "validation_feedback": ""}

    async def _fallback_generate_content(self, state: ContentState) -> dict[str, Any]:
        prompt = (
            "你是一位高校课程讲解文档作者。请直接生成一份完整的 Markdown 课程讲解文档，"
            "不要追问用户，不要输出额外说明。\n\n"
            f"专业：{state.get('major', '通用')}\n"
            f"课程：{state.get('course', '')}\n"
            f"主题：{state.get('topic', '')}\n"
            f"知识短板：{state.get('gap', '')}\n"
            "要求：\n"
            "1. 必须包含：概述、核心讲解、案例分析、常见误区、总结\n"
            "2. 字数尽量充实，至少 1200 字\n"
            "3. 面向初学者，讲解清晰具体\n"
            "4. 直接输出最终 Markdown 文档\n"
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
            result = await asyncio.wait_for(
                self.graph.ainvoke(initial_state, {"recursion_limit": 20}),
                timeout=90,
            )
        except Exception as e:
            logger.error(f"[ContentAgent] 工作流执行失败: {e}")
            try:
                result = await self._fallback_generate_content(initial_state)
            except Exception as fallback_error:
                return {"success": False, "content": "", "outline": "", "error": str(fallback_error)}

        content = result.get("content", "")
        outline = result.get("outline", "")
        if not content:
            try:
                fallback = await self._fallback_generate_content(initial_state)
                content = fallback.get("content", "")
                outline = fallback.get("outline", outline)
            except Exception as fallback_error:
                logger.error(f"[ContentAgent] 降级生成失败: {fallback_error}")
        success = bool(content)
        file_path = None
        if success:
            file_path = self._save_to_workplace("content", topic, content, "md")

        return {
            "success": success,
            "content": content,
            "outline": outline,
            "file_path": file_path,
            "error": result.get("error") if not success else None,
        }
