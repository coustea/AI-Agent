"""
百度 AI PPT 生成工具。

通过百度千帆 AI PPT API 生成带模板的演示文稿，下载 .pptx 文件到本地。
当 BAIDU_API_KEY 环境变量可用时，优先使用此工具（比 save_ppt_file 效果更好）。
"""

import json
import os
import time
from pathlib import Path

import requests
from langchain.tools import tool

from app.core.logging import get_logger
from app.utils.paths import WORKPLACE_DIR

logger = get_logger(__name__)

URL_PREFIX = "https://qianfan.baidubce.com/v2/tools/ai_ppt/"


def _get_api_key() -> str | None:
    return os.getenv("BAIDU_API_KEY")


def _fetch_theme(api_key: str, query: str) -> tuple[int, int]:
    """根据查询主题智能选择 PPT 模板，返回 (style_id, tpl_id)。"""
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.post(URL_PREFIX + "get_ppt_theme", headers=headers, timeout=30)
    result = resp.json()
    if result.get("errno", 0) != 0:
        raise RuntimeError(f"获取主题失败: {result.get('errmsg', 'unknown')}")

    themes = result["data"]["ppt_themes"]
    if not themes:
        raise RuntimeError("无可用 PPT 模板")

    # 按主题关键词匹配分类
    category_keywords: dict[str, list[str]] = {
        "未来科技": ["科技", "人工智能", "ai", "数据", "算法", "系统", "程序", "计算机",
                   "技术", "机器学习", "深度学习", "网络", "软件", "数字化"],
        "企业商务": ["企业", "公司", "商务", "管理", "战略", "营销", "财务", "报告", "总结", "规划"],
        "卡通手绘": ["儿童", "小学", "幼儿", "教育", "课件", "趣味", "游戏"],
        "扁平简约": ["简约", "设计", "现代", "信息", "图表"],
        "中国风": ["中国", "传统", "古典", "历史", "文化", "国学"],
    }

    # 为每个主题计算匹配分数
    query_lower = query.lower()
    best_theme = None
    best_score = -1

    for theme in themes:
        style_names = theme.get("style_name_list", [])
        score = 0
        for cat, keywords in category_keywords.items():
            if cat in style_names:
                score += sum(1 for kw in keywords if kw in query_lower)
        if score > best_score:
            best_score = score
            best_theme = theme

    if best_theme is None or best_score == 0:
        import random
        best_theme = random.choice(themes)

    return best_theme["style_id"], best_theme["tpl_id"]


def _generate_outline(api_key: str, query: str) -> dict:
    """调用百度 API 生成 PPT 大纲。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Appbuilder-From": "openclaw",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    params = {"query": query}

    title = ""
    outline = ""
    chat_id = ""
    query_id = ""

    with requests.post(
        URL_PREFIX + "generate_outline",
        headers=headers,
        json=params,
        stream=True,
        timeout=120,
    ) as resp:
        for line in resp.iter_lines():
            line = line.decode("utf-8")
            if line and line.startswith("data:"):
                delta = json.loads(line[5:].strip())
                if not title:
                    title = delta.get("title", "")
                    chat_id = delta.get("chat_id", "")
                    query_id = delta.get("query_id", "")
                outline += delta.get("outline", "")

    return {"chat_id": chat_id, "query_id": query_id, "title": title, "outline": outline}


def _generate_ppt(api_key: str, query: str, outline_data: dict,
                  style_id: int, tpl_id: int) -> str:
    """调用百度 API 生成 PPT 并下载，返回本地文件路径。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Appbuilder-From": "openclaw",
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    params = {
        "query_id": int(outline_data["query_id"]),
        "chat_id": int(outline_data["chat_id"]),
        "query": query,
        "outline": outline_data["outline"],
        "title": outline_data["title"],
        "style_id": style_id,
        "tpl_id": tpl_id,
        "web_content": None,
        "enable_save_bos": True,
    }

    ppt_url = None
    with requests.post(
        URL_PREFIX + "generate_ppt_by_outline",
        headers=headers,
        json=params,
        stream=True,
        timeout=300,
    ) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"PPT 生成请求失败: HTTP {resp.status_code}")
        for line in resp.iter_lines():
            line = line.decode("utf-8")
            if line and line.startswith("data:"):
                data = json.loads(line[5:].strip())
                if data.get("is_end"):
                    ppt_url = data.get("data", {}).get("ppt_url")

    if not ppt_url:
        raise RuntimeError("PPT 生成完成但未获取到下载链接")

    # 下载 PPT 文件
    download_resp = requests.get(ppt_url, timeout=120)
    download_resp.raise_for_status()

    target_dir = WORKPLACE_DIR / "ppt"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in query[:50] if c.isalnum() or c in "一二三四五六七八九十百千万亿")
    if not safe_name:
        safe_name = "ppt"
    file_path = target_dir / f"{safe_name}_{int(time.time())}.pptx"
    file_path.write_bytes(download_resp.content)

    logger.info(f"[BaiduPPT] 文件已下载: {file_path}")
    return str(file_path)


@tool("baidu_generate_ppt")
def baidu_generate_ppt(topic: str, query: str | None = None) -> str:
    """使用百度 AI PPT API 生成带模板的演示文稿。

    Args:
        topic: PPT 主题名称（用于文件命名）。
        query: PPT 生成提示词（默认等于 topic）。
    """
    api_key = _get_api_key()
    if not api_key:
        return json.dumps(
            {"error": "BAIDU_API_KEY 未配置，无法使用百度 AI PPT。请改用 save_ppt_file。"},
            ensure_ascii=False,
        )

    query = query or topic

    try:
        logger.info(f"[BaiduPPT] 开始生成: topic={topic}")

        # 1. 选择模板
        style_id, tpl_id = _fetch_theme(api_key, query)
        logger.info(f"[BaiduPPT] 选择模板: style_id={style_id}, tpl_id={tpl_id}")

        # 2. 生成大纲
        outline_data = _generate_outline(api_key, query)
        logger.info(f"[BaiduPPT] 大纲生成完成: title={outline_data['title']}")

        # 3. 生成 PPT 并下载
        file_path = _generate_ppt(api_key, query, outline_data, style_id, tpl_id)

        return json.dumps(
            {
                "file_path": file_path,
                "slide_count": 0,
                "title": outline_data["title"],
                "source": "baidu_ai_ppt",
            },
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"[BaiduPPT] 生成失败: {e}")
        return json.dumps(
            {"error": f"百度 AI PPT 生成失败: {e}"},
            ensure_ascii=False,
        )