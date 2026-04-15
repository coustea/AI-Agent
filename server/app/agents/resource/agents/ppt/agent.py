"""
PPT 演示文稿生成 Agent（骨架）。
基于 BaseResourceAgent 实现，通过本地工具生成结构化 PPT 文件。
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import AIMessage, ToolMessage

from app.core.logging import get_logger
from app.agents.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)


class PptState(BaseAgentState):
    """PPT 生成的专属状态字段"""
    # PPT 特有的输出字段
    slide_count: int
    outline: str
    speaker_notes: str
    file_path: Optional[str]


class PptAgent(BaseResourceAgent):
    """PPT 演示文稿生成 Agent。

    优先使用百度 AI PPT API 生成带模板的演示文稿；
    当 BAIDU_API_KEY 不可用时，回退到本地 LLM 生成 + save_ppt_file。

    Attributes:
        name:           "PptAgent"
        agent_dir:      agents/ppt/，包含 prompt.md
        state_schema:   PptState，包含 slide_count/outline/speaker_notes/file_path
        method:         generate_ppt() — 对外入口
        output:         {success, content, file_path, slide_count, outline, speaker_notes, error}

    工作流: agent → tools(baidu_generate_ppt / save_ppt_file) → validate → retry/end
    DAG 阶段: presentation（最后执行，依赖所有前置 Agent）
    黑板记忆: 读取 content.outline（内容大纲）和 mindmap.file_path（思维导图）
    用户画像: 读取 cognitive_style（认知风格）
    """
    def __init__(self) -> None:
        super().__init__(
            name="PptAgent",
            agent_dir=Path(__file__).parent,
            state_schema=PptState,
            temperature=0.3,
        )
        self._baidu_available = bool(os.getenv("BAIDU_API_KEY"))

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        """黑板记忆：从前置 Agent 输出中提取关键上下文"""
        ctx = ""
        if "content" in shared_memory:
            content_data = shared_memory["content"]
            outline = content_data.get("outline", "")
            if outline:
                ctx += f"【参考内容大纲】\n{outline}\n"
        if "mindmap" in shared_memory:
            mindmap_data = shared_memory["mindmap"]
            file_path = mindmap_data.get("file_path", "")
            if file_path:
                ctx += f"【知识拓扑图】\n已生成思维导图: {file_path}\n"
        return ctx

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        if not profile: return ""
        parts = []
        if profile.get("cognitive_style"):
            parts.append(f"- 认知风格: {profile['cognitive_style']}")
        return "\n".join(parts)

    def _build_system_message(self, state: Any) -> str:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            cognitive_style=user_profile.get("cognitive_style", "通用"),
        )
        return self._append_context_to_prompt(system_prompt, state)

    def _build_initial_human_message(self, state: Any) -> str:
        topic = state.get("topic", "")
        if self._baidu_available:
            return (
                f"请为主题 '{topic}' 生成一份 PPT 演示文稿。\n"
                f"请直接调用 baidu_generate_ppt 工具，传入 topic 参数。"
            )
        return (
            f"请为主题 '{topic}' 生成一份 PPT 演示文稿，并在大纲完成后调用 save_ppt_file 保存。"
        )

    async def _validate_node(self, state: Any) -> dict:
        """校验节点：提取本地工具返回的文件路径。"""
        messages = state.get("messages", [])
        content = ""
        file_path = None
        slide_count = 0

        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content.strip()

        for msg in messages:
            if not isinstance(msg, ToolMessage) or msg.name not in ("save_ppt_file", "baidu_generate_ppt"):
                continue

            payload = msg.content
            try:
                if isinstance(payload, str):
                    data = json.loads(payload)
                elif isinstance(payload, list):
                    data = None
                    for item in payload:
                        if isinstance(item, dict) and "text" in item:
                            data = json.loads(item["text"])
                            break
                    if data is None:
                        continue
                else:
                    data = payload
            except (json.JSONDecodeError, TypeError):
                continue

            if isinstance(data, dict):
                file_path = data.get("file_path") or data.get("filePath")
                slide_count = int(data.get("slide_count", 0) or 0)
                break

        if not file_path and content:
            path_match = re.search(r'file_path[：:]\s*(.+?)(?:\n|$)', content)
            if path_match:
                file_path = path_match.group(1).strip()

        logger.info(f"[PptAgent] 校验 PPT 内容，文件路径: {file_path}")
        is_valid = bool(file_path)

        # 构造校验反馈
        if is_valid:
            feedback = ""
        elif self._baidu_available:
            feedback = (
                "未检测到 PPT 文件路径。"
                "请调用 baidu_generate_ppt 工具（传入 topic 参数）生成 PPT。"
            )
        else:
            feedback = (
                "未检测到 PPT 文件路径。"
                "请调用 save_ppt_file 工具生成并保存 PPT。"
            )

        return {
            "is_valid": is_valid,
            "validation_feedback": feedback,
            "file_path": file_path,
            "slide_count": slide_count,
        }

    async def generate_ppt(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[PptAgent] 收到生成请求: topic={topic}")
        await self._ensure_graph()

        initial_state: PptState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "is_valid": False,
            "validation_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[PptAgent] 工作流执行失败: {e}")
            return {
                "success": False,
                "content": "",
                "file_path": None,
                "slide_count": 0,
                "outline": "",
                "speaker_notes": "",
                "error": str(e)
            }

        messages = result.get("messages", [])
        final_content = messages[-1].content if messages else ""

        # 提取校验节点设置的文件路径
        file_path = result.get("file_path")

        return {
            "success": bool(file_path),
            "content": final_content,
            "file_path": file_path,
            "slide_count": result.get("slide_count", final_content.count("##") if final_content else 0),
            "outline": final_content,
            "speaker_notes": "",
            "error": result.get("error") if file_path else result.get("error"),
        }


if __name__ == '__main__':
    import asyncio

    agent = PptAgent()

    async def main():
        await agent._ensure_graph()

        result = await agent.generate_ppt(
            topic="操作系统进程管理",
            course="操作系统",
            major="计算机科学",
            gap="对进程调度算法理解不清晰",
            user_profile={
                "cognitive_style": "偏逻辑推理"
            },
            shared_memory={
                "content": {
                    "outline": "进程定义、PCB、调度算法（FCFS、SJF、RR）、同步与互斥"
                },
                "mindmap": {
                    "file_path": "/tmp/mindmap.png"
                }
            }
        )

        print("=" * 50)
        print("[PPT 生成结果]")
        print("=" * 50)

        print(f"success: {result['success']}")
        print(f"file_path: {result['file_path']}")
        print(f"slide_count: {result['slide_count']}")

        print("\n[PPT 内容]\n")
        print(result["content"])

        if result.get("error"):
            print("\n[错误信息]")
            print(result["error"])

    asyncio.run(main())
