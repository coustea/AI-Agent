"""元数据推断 — 从文件路径和内容推断 title/course/section。

公共接口：
  enrich_metadata()   批量为 Document 填充元数据

Called by: app/rag/indexing/build.py.
User instruction: "需要设计好rag系统的文件加载，切割文档，以及嵌入向量和存入向量数据库，
每个模块要划分开，不要耦合"
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from langchain_core.documents import Document

from app.infra.logging import get_logger

logger = get_logger(__name__)

# 路径片段 → 课程名映射（新版扁平化目录结构）
# 新结构：source/课程名/章节名/文件.md（无编号前缀）
_COURSE_DIR_MAP: dict[str, str] = {
    # 计算机基础课程
    "操作系统": "操作系统",
    "计算机网络": "计算机网络",
    "数据结构与算法": "数据结构与算法",
    "计算机组成原理": "计算机组成原理",
    "数据库系统": "数据库系统",
    # 编程语言
    "Java": "Java",
    "Python": "Python",
    "C-CPP": "C/C++",
    # AI 相关
    "机器学习": "机器学习",
    "深度学习": "深度学习",
    "AI入门": "AI入门",
    "生成式AI": "生成式AI",
    "AI-Agents": "AI-Agents",
    "AI工程": "AI工程",
    # Web 开发
    "前端全栈": "前端全栈",
    "Web安全": "Web安全",
    # 系统与架构
    "系统架构": "系统架构",
    "分布式系统": "分布式系统",
    # 数学基础
    "数学": "数学",
    "高等数学": "高等数学",
    "统计学": "统计学",
    "概率论与数理统计": "概率论与数理统计",
    # 其他
    "面试": "面试",
    "通识": "通识",
}

# 标题关键词 → 课程名映射（回退推断）
_COURSE_KEYWORDS: dict[str, str] = {
    "计算机网络": "计算机网络",
    "操作系统": "操作系统",
    "数据结构": "数据结构",
    "计算机组成原理": "计算机组成原理",
    "数据库": "数据库系统",
    "Java": "程序设计基础",
    "Python": "程序设计基础",
    "Redis": "数据库系统",
    "算法": "算法设计与分析",
    "高等数学": "高等数学",
    "线性代数": "线性代数",
    "概率论": "概率论与数理统计",
    "软件工程": "软件工程",
    "设计模式": "软件工程",
    "排序": "算法设计与分析",
    "搜索": "算法设计与分析",
    "回溯": "算法设计与分析",
    "动态规划": "算法设计与分析",
    "贪心": "算法设计与分析",
    "分治": "算法设计与分析",
    "图": "数据结构",
    "树": "数据结构",
    "哈希": "数据结构",
    "堆": "数据结构",
    "栈": "数据结构",
    "队列": "数据结构",
    "链表": "数据结构",
}


# 从相对路径推断教材标题（章节目录名优先，其次文件名）
def infer_title(source: str) -> str:
    """从相对路径推断教材标题。

    优先使用课程分类目录下的子目录名（如 hello-algo 章节目录），
    其次使用文件名（去除 .final.md / .md 后缀）。
    """
    parts = Path(source).parts
    for part in parts:
        if part.startswith("chapter_"):
            return part.replace("chapter_", "").replace("_", " ")

    name = Path(source).name
    for suffix in (".final.md", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name


# 从路径课程目录或标题关键词推断课程名
def infer_course(source: str, title: str = "") -> str:
    """从相对路径推断课程名。

    新版扁平化目录结构：source/课程名/章节名/文件.md
    直接从第一级目录名匹配课程。
    """
    parts = Path(source).parts
    # 新结构：第一级目录即为课程名
    if parts:
        first_dir = parts[0]
        if first_dir in _COURSE_DIR_MAP:
            return _COURSE_DIR_MAP[first_dir]

    # 回退：用标题关键词匹配课程
    text = title.lower()
    for keyword, course in _COURSE_KEYWORDS.items():
        if keyword.lower() in text:
            return course

    return ""


# 取首个 Markdown 标题行作为章节信息
def infer_section(text: str) -> str:
    """提取第一行标题作为章节信息。"""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") and " " in stripped:
            return stripped.lstrip("# ").strip()
    return ""


# 批量为文档填充 title/course/section/parent_id 等元数据
def enrich_metadata(docs: list[Document]) -> list[Document]:
    """批量为 Document 填充 title/course/section/heading_path/parent_id。

    遍历每个 Document，从其 metadata["source"] 和内容推断元数据，
    写入 metadata 字典。原地修改并返回。

    Args:
        docs: LangChain Document 列表。

    Returns:
        元数据已填充的 Document 列表。
    """
    for doc in docs:
        source = doc.metadata.get("source", "")
        title = infer_title(source)
        course = infer_course(source, title)
        section = infer_section(doc.page_content)
        # 用源路径 MD5 生成稳定父文档 ID
        parent_id = hashlib.md5(source.encode("utf-8")).hexdigest()[:16]

        doc.metadata["title"] = title
        doc.metadata["course"] = course
        doc.metadata["section"] = section
        doc.metadata["parent_id"] = parent_id
        doc.metadata.setdefault("heading_path", "")

    logger.info("[metadata] enriched %d documents", len(docs))
    return docs
