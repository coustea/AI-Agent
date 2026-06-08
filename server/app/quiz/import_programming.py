"""编程题数据导入服务。

从 quiz/datasets/ 目录下的开源数据集将力扣和洛谷的编程题
导入到 programming_problems 表。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from app.infra.logging import get_logger
from app.infra.models import ProgrammingProblem

logger = get_logger(__name__)

DATASETS_DIR = Path(__file__).parent.parent.parent / "quiz" / "datasets"

BATCH_SIZE = 200

# 力扣英文 topic → 中文算法分类映射
_TOPIC_TO_CATEGORY = {
    "Array": "数组",
    "Hash Table": "哈希表",
    "Linked List": "链表",
    "String": "字符串",
    "Stack": "栈",
    "Queue": "队列",
    "Tree": "树",
    "Binary Tree": "树",
    "Binary Search Tree": "树",
    "Heap": "堆",
    "Graph": "图论",
    "Dynamic Programming": "动态规划",
    "Backtracking": "回溯",
    "Greedy": "贪心",
    "Divide and Conquer": "分治",
    "Binary Search": "二分查找",
    "Sort": "排序",
    "Two Pointers": "双指针",
    "Sliding Window": "滑动窗口",
    "Recursion": "递归",
    "Math": "数学",
    "Bit Manipulation": "位运算",
    "Union Find": "并查集",
    "Trie": "字典树",
    "Monotonic Stack": "单调栈",
    "Topological Sort": "拓扑排序",
    "Breadth-First Search": "广度优先搜索",
    "Depth-First Search": "深度优先搜索",
    "Matrix": "矩阵",
    "Combinatorics": "组合数学",
    "Number Theory": "数论",
    "Probability and Statistics": "概率统计",
    "Design": "设计",
    "Simulation": "模拟",
    "Prefix Sum": "前缀和",
    "Counting": "计数",
    "Enumeration": "枚举",
}


# ---------------------------------------------------------------------------
# 力扣数据转换
# ---------------------------------------------------------------------------

def _load_leetcode_merged() -> list[dict]:
    """加载 neenza/leetcode-problems 的 merged_problems.json。"""
    merged_path = DATASETS_DIR / "leetcode-problems" / "merged_problems.json"
    if not merged_path.exists():
        logger.warning("[ProgImport] 力扣 merged_problems.json 不存在")
        return []

    data = json.load(open(merged_path, encoding="utf-8"))
    questions = data.get("questions", [])
    logger.info("[ProgImport] 力扣 merged_problems.json: %d 题", len(questions))
    return questions


def _load_leetcode_cn_slugs() -> dict[str, str]:
    """加载力扣中文题面，返回 {slug: html_content} 映射。"""
    cn_dir = DATASETS_DIR / "leetcode-problemset-cn" / "leetcode-cn"
    cn_problem_dir = cn_dir / "problem (Chinese)"
    if not cn_problem_dir.exists():
        logger.warning("[ProgImport] 力扣中文题面目录不存在")
        return {}

    slug_map: dict[str, str] = {}
    for fname in os.listdir(cn_problem_dir):
        # 文件名格式: "两数之和 [two-sum].html" 或 "两数之和 [two-sum].md"
        match = re.search(r"\[([^\]]+)\]\.(?:html|md)$", fname)
        if not match:
            continue
        slug = match.group(1)
        filepath = cn_problem_dir / fname
        try:
            content = filepath.read_text(encoding="utf-8")
            slug_map[slug] = content
        except Exception:
            pass

    logger.info("[ProgImport] 力扣中文题面: %d 题", len(slug_map))
    return slug_map


def _difficulty_cn(difficulty: str) -> str:
    """将英文难度映射为中文。"""
    mapping = {"Easy": "简单", "Medium": "中等", "Hard": "困难"}
    return mapping.get(difficulty, difficulty)


def _extract_cn_title(html_content: str) -> str:
    """从力扣中文 HTML 片段中提取题目标题。"""
    # 中文题面通常没有标题，使用第一段文字的前30字
    text = re.sub(r"<[^>]+>", "", html_content).strip()
    return text[:30] + "..." if len(text) > 30 else text


def _leetcode_to_model(
    item: dict, cn_map: dict[str, str]
) -> ProgrammingProblem | None:
    """将力扣 JSON 记录转换为 ProgrammingProblem ORM 对象。"""
    slug = item.get("problem_slug", "")
    if not slug:
        return None

    frontend_id = item.get("frontend_id", "")
    title_en = item.get("title", "")
    if not title_en:
        return None

    cn_content = cn_map.get(slug, "")
    description = cn_content if cn_content else item.get("description", "")

    examples_raw = item.get("examples", [])
    examples = []
    for ex in examples_raw:
        examples.append({
            "explanation": ex.get("example_text", ""),
        })

    difficulty = _difficulty_cn(item.get("difficulty", ""))
    tags = item.get("topics", [])
    category = _TOPIC_TO_CATEGORY.get(tags[0], None) if tags else None
    title = _extract_cn_title(cn_content) if cn_content else title_en

    return ProgrammingProblem(
        problem_slug=f"lc-{frontend_id}-{slug}",
        title=title,
        difficulty=difficulty,
        category=category,
        description=description,
        examples=examples,
        hints=item.get("hints"),
        code_snippets=item.get("code_snippets"),
        tags=tags,
    )


# ---------------------------------------------------------------------------
# 洛谷数据转换
# ---------------------------------------------------------------------------

def _load_luogu_problems() -> list[tuple[str, str]]:
    """扫描洛谷题面 Markdown 文件，返回 (pid, content) 列表。"""
    luogu_dir = DATASETS_DIR / "luogu-problems" / "problem"
    if not luogu_dir.exists():
        logger.warning("[ProgImport] 洛谷题面目录不存在")
        return []

    results: list[tuple[str, str]] = []
    for fname in sorted(os.listdir(luogu_dir)):
        if not re.match(r"^P\d+\.md$", fname):
            continue
        pid = fname.replace(".md", "")
        filepath = luogu_dir / fname
        try:
            content = filepath.read_text(encoding="utf-8")
            if content.strip():
                results.append((pid, content))
        except Exception:
            pass

    logger.info("[ProgImport] 洛谷题面: %d 题", len(results))
    return results


def _parse_luogu_markdown(pid: str, content: str) -> ProgrammingProblem:
    """将洛谷 Markdown 题面解析为 ProgrammingProblem。"""
    lines = content.split("\n")

    # 解析标题 (第一行 "# 标题")
    title = pid
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            # 去掉开头的编号如 "1 " 或 "P1001 "
            title = re.sub(r"^\d+\s+", "", line[2:].strip())
            break

    # 解析各段
    description = ""
    input_format = ""
    output_format = ""
    examples: list[dict] = []
    current_section = ""
    section_buffer: list[str] = []

    def flush_section():
        nonlocal description, input_format, output_format
        text = "\n".join(section_buffer).strip()
        if current_section == "题目描述":
            description = text
        elif current_section == "输入格式":
            input_format = text
        elif current_section == "输出格式":
            output_format = text

    in_sample_input = False
    in_sample_output = False
    sample_input_buf: list[str] = []
    sample_output_buf: list[str] = []

    for line in lines:
        # 样例输入
        if re.match(r"^###\s*样例输入\s*#", line):
            # 保存上一个样例
            if in_sample_output and sample_output_buf:
                examples.append({
                    "input": "\n".join(sample_input_buf).strip(),
                    "output": "\n".join(sample_output_buf).strip(),
                    "explanation": "",
                })
            in_sample_input = True
            in_sample_output = False
            sample_input_buf = []
            sample_output_buf = []
            continue
        # 样例输出
        if re.match(r"^###\s*样例输出\s*#", line):
            in_sample_input = False
            in_sample_output = True
            continue

        if in_sample_input:
            if line.strip() in ("```", "```cpp", "```c", "```python"):
                continue
            sample_input_buf.append(line)
            continue
        if in_sample_output:
            if line.strip() in ("```", "```cpp", "```c", "```python"):
                continue
            sample_output_buf.append(line)
            continue

        # 章节标题
        if line.startswith("## "):
            flush_section()
            section_name = line[3:].strip()
            if section_name in ("题目描述", "输入格式", "输出格式", "提示"):
                current_section = section_name
            else:
                current_section = ""
            section_buffer = []
            continue

        if current_section:
            section_buffer.append(line)

    flush_section()
    # 保存最后一个样例
    if sample_output_buf:
        examples.append({
            "input": "\n".join(sample_input_buf).strip(),
            "output": "\n".join(sample_output_buf).strip(),
            "explanation": "",
        })

    lg_url = f"https://www.luogu.com.cn/problem/{pid}"

    return ProgrammingProblem(
        problem_slug=f"lg-{pid}",
        title=title,
        description=description or content,
        input_format=input_format,
        output_format=output_format,
        examples=examples,
        tags=[],
    )


# ---------------------------------------------------------------------------
# 导入主流程
# ---------------------------------------------------------------------------

async def import_programming_problems(session) -> int:
    """导入编程题到数据库。

    Args:
        session: 数据库会话

    Returns:
        新增题目数量
    """
    from sqlalchemy import select, func

    count = (await session.exec(
        select(func.count()).select_from(ProgrammingProblem)
    )).scalar() or 0

    if count > 0:
        logger.info("[ProgImport] 编程题已有 %d 条，跳过导入", count)
        return 0

    # 力扣
    lc_questions = _load_leetcode_merged()
    cn_map = _load_leetcode_cn_slugs()
    lc_models = []
    for item in lc_questions:
        model = _leetcode_to_model(item, cn_map)
        if model:
            lc_models.append(model)
    logger.info("[ProgImport] 力扣转换完成: %d 题", len(lc_models))

    # 洛谷
    luogu_raw = _load_luogu_problems()
    luogu_models = [_parse_luogu_markdown(pid, content) for pid, content in luogu_raw]
    logger.info("[ProgImport] 洛谷转换完成: %d 题", len(luogu_models))

    all_models = lc_models + luogu_models
    if not all_models:
        logger.info("[ProgImport] 无编程题数据")
        return 0

    imported = 0
    batch: list[ProgrammingProblem] = []

    for model in all_models:
        batch.append(model)
        if len(batch) >= BATCH_SIZE:
            session.add_all(batch)
            await session.commit()
            imported += len(batch)
            batch = []

    if batch:
        session.add_all(batch)
        await session.commit()
        imported += len(batch)

    logger.info("[ProgImport] 导入完成: 力扣 %d + 洛谷 %d = %d 题",
                len(lc_models), len(luogu_models), imported)
    return imported