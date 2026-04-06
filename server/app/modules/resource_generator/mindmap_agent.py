"""
数据结构思维导图生成 Agent
基于 LangChain + MCP 插件化架构（markmap 服务）
"""

import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.logging import get_logger
from app.utils.mcp_manager import mcp_manager

load_dotenv()
logger = get_logger(__name__)

# ==========================================
# 1. 加载 Prompt 模板
# ==========================================
PROMPT_DIR = Path(__file__).parent / "prompt"
MINDMAP_PROMPT_PATH = PROMPT_DIR / "mindmap.md"

with open(MINDMAP_PROMPT_PATH, "r", encoding="utf-8") as f:
    MINDMAP_GENERATOR_PROMPT = f.read()


# ==========================================
# 2. 思维导图生成 Agent
# ==========================================
class MindmapGenerator:
    """思维导图生成器

    通过 mcp_manager 调用 "markmap" MCP 服务。
    """

    def __init__(self):
        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.3,
        )

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", MINDMAP_GENERATOR_PROMPT)
        ])

    async def generate_mindmap(
        self,
        topic: str,
        major: str = "",
        course: str = "",
    ) -> Dict[str, Any]:
        """
        根据学生的专业和课程生成知识体系思维导图。

        Args:
            topic: 知识点主题，如 "二叉树"、"神经网络"
            major: 专业，"计算机" 或 "人工智能"
            course: 课程/科目，如 "数据结构"、"深度学习"

        Returns:
            dict: 包含 HTML 思维导图内容及文件路径
        """
        logger.info(
            f"[MindmapGenerator] 开始生成思维导图: "
            f"topic={topic}, major={major}, course={course}"
        )

        # 1. 调用 LLM 生成 Markdown 思维导图
        try:
            prompt = self.prompt_template.invoke({
                "topic": topic,
                "major": major,
                "course": course,
            })
            response = await self.llm.ainvoke(prompt)
            markdown_content = response.content.strip()

            # 清理包裹的 markdown 标签
            if markdown_content.startswith("```markdown"):
                markdown_content = markdown_content[11:]
            if markdown_content.startswith("```"):
                markdown_content = markdown_content[3:]
            if markdown_content.endswith("```"):
                markdown_content = markdown_content[:-3]

            markdown_content = markdown_content.strip()
            logger.info(f"[MindmapGenerator] Markdown 内容已生成")

        except Exception as e:
            logger.error(f"[MindmapGenerator] LLM 生成失败: {e}")
            return {
                "success": False,
                "error": f"LLM 生成失败: {str(e)}"
            }

        # 2. 通过 mcp_manager 调用 markmap 服务
        file_path = None
        html_content = None

        try:
            result_data = await mcp_manager.call_tool_json(
                "markmap",
                "markdown_to_mindmap",
                markdown=markdown_content,
                open=False,
            )

            if "error" in result_data:
                logger.warning(f"MCP 工具生成出错: {result_data.get('message')}")
                return {
                    "success": False,
                    "error": f"MCP 工具生成出错: {result_data.get('message')}"
                }

            file_path = result_data.get("filePath")
            logger.info(f"[MindmapGenerator] 思维导图已生成: {file_path}")

            # 读取生成的 HTML 内容以便直接返回给前端
            if file_path and os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()

        except Exception as e:
            logger.error(f"[MindmapGenerator] MCP 调用失败: {e}")
            return {
                "success": False,
                "error": f"MCP 调用失败: {str(e)}"
            }

        # 3. 返回结果
        return {
            "success": True,
            "file_path": file_path,
            "html_content": html_content
        }


# 全局实例
mindmap_generator = MindmapGenerator()


if __name__ == "__main__":
    import asyncio
    from app.utils.mcp_manager import mcp_manager as _mgr

    _mgr.load_from_settings()

    result = asyncio.run(mindmap_generator.generate_mindmap("操作系统进程之间的调度","计算机科学与技术","操作系统"))
    if result["success"]:
        print(f"Success! File: {result['file_path']}")
        print(f"HTML length: {len(result['html_content'])} chars")
    else:
        print(f"Failed: {result['error']}")
