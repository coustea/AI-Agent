"""检索感知的查询改写模块。

当初始检索置信度较低时，通过 LLM 生成查询变体以提升召回率。
包含质量过滤和效果追踪机制，避免无效改写浪费资源。

改写策略：
  1. 快速路径跳过：独占关键词命中 / 硬编码规则匹配 / 短术语词库命中 → 不触发 LLM 改写
  2. LLM 改写：调用本地 Ollama 模型生成最多 max_variants 个查询变体
  3. 质量过滤：保留与原查询相似度 > threshold 或命中术语词库的变体
  4. 效果追踪：记录改写模式的增益，对持续无效的模式自动跳过
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from typing import Any

import httpx

from app.config import (
    KB_COURSE_ROUTING,
    KB_OLLAMA_BASE_URL,
    KB_REWRITE_BUDGET_MS,
    KB_REWRITE_CONFIDENCE_THRESHOLD,
    KB_REWRITE_EFFECTIVENESS_CACHE_SIZE,
    KB_REWRITE_ENABLED,
    KB_REWRITE_LLM_MODEL,
    KB_REWRITE_MAX_VARIANTS,
    KB_REWRITE_SIMILARITY_THRESHOLD,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)

# CS 领域常见缩写，短查询命中时允许触发改写
_TERMINOLOGY_DB: dict[str, str] = {
    "GC": "Garbage Collection 垃圾回收",
    "JVM": "Java Virtual Machine Java虚拟机",
    "JDK": "Java Development Kit Java开发工具包",
    "JRE": "Java Runtime Environment Java运行环境",
    "ACID": "Atomicity Consistency Isolation Durability 数据库事务特性",
    "CAP": "Consistency Availability Partition tolerance 分布式理论",
    "TCP": "Transmission Control Protocol 传输控制协议",
    "UDP": "User Datagram Protocol 用户数据报协议",
    "HTTP": "HyperText Transfer Protocol 超文本传输协议",
    "DNS": "Domain Name System 域名系统",
    "SQL": "Structured Query Language 结构化查询语言",
    "OS": "Operating System 操作系统",
    "OOM": "Out Of Memory 内存溢出",
    "API": "Application Programming Interface 应用编程接口",
    "ORM": "Object Relational Mapping 对象关系映射",
    "MVC": "Model View Controller 模型视图控制器",
    "B+树": "B+ Tree 多路平衡搜索树",
    "B树": "B Tree 多路平衡搜索树",
    "AVL": "AVL Tree 自平衡二叉搜索树",
}

# 从 KB_COURSE_ROUTING 提取 weight >= 2.0 的独占关键词
# 这些关键词表示查询已经足够精确，无需 LLM 改写
_EXCLUSIVE_WORDS: set[str] = set()
for _course_keywords in KB_COURSE_ROUTING.values():
    if isinstance(_course_keywords, dict):
        for _kw, _w in _course_keywords.items():
            if _w >= 2.0:
                _EXCLUSIVE_WORDS.add(_kw)


def compute_retrieval_confidence(rows: list[dict[str, Any]]) -> float:
    """计算检索置信度：top1 分数 / top5 平均分数。

    置信度越高表示 top1 结果明显领先，改写价值越低。
    返回 0.0 当结果不足 2 条时（无法计算有效比率）。
    """
    if len(rows) < 2:
        return 0.0

    # 取前 5 条的 distance 分数
    top5 = rows[:5]
    scores = [abs(float(r.get("distance", 0.0))) for r in top5]

    if not scores or scores[0] == 0.0:
        return 0.0

    mean_score = sum(scores) / len(scores)
    if mean_score == 0.0:
        return 0.0

    return scores[0] / mean_score


def _count_tokens(text: str) -> int:
    """计算文本的 token 数：中文字符数 + ASCII 单词数。"""
    if not text:
        return 0
    chinese_chars = sum(1 for ch in text if "一" <= ch <= "鿿")
    ascii_words = len(re.findall(r"[A-Za-z0-9+#.-]+", text))
    return chinese_chars + ascii_words


def should_trigger_rewrite(
    query: str,
    exclusive_words: set[str] | None = None,
    hardcoded_rules: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] | None = None,
    terminology_dict: dict[str, str] | None = None,
) -> bool:
    """判断是否需要触发 LLM 查询改写。

    跳过条件（任一满足即不触发）：
    1. 全局开关关闭
    2. 查询命中独占关键词（已足够精确）
    3. 查询命中硬编码改写规则（已有规则覆盖）
    4. 查询 token 数 < 2 且不在术语词库中（过短无改写价值）

    Returns:
        True 表示需要触发 LLM 改写，False 表示跳过
    """
    if not KB_REWRITE_ENABLED:
        return False

    normalized = (query or "").strip()
    if not normalized:
        return False

    ew = exclusive_words if exclusive_words is not None else _EXCLUSIVE_WORDS
    rules = hardcoded_rules if hardcoded_rules is not None else ()
    term_dict = terminology_dict if terminology_dict is not None else _TERMINOLOGY_DB

    # 命中独占关键词 → 查询已足够精确
    lowered = normalized.lower()
    for word in ew:
        if word.lower() in lowered or word in normalized:
            return False

    # 命中硬编码规则 → 已有规则覆盖
    for pattern, _terms in rules:
        if pattern.search(lowered):
            return False

    # 短查询且不在术语词库中 → 无改写价值
    token_count = _count_tokens(normalized)
    if token_count < 2 and not _hits_terminology_db(normalized, term_dict):
        return False

    return True


def _compute_similarity(text1: str, text2: str) -> float:
    """计算两个文本的字符级 Jaccard 相似度（fallback 方案）。

    将文本转为字符集合，计算交集/并集比率。
    """
    set1 = set(text1)
    set2 = set(text2)
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)


def _hits_terminology_db(text: str, terminology_db: dict[str, str] | None = None) -> bool:
    """检查文本是否包含术语词库中的条目。"""
    db = terminology_db if terminology_db is not None else _TERMINOLOGY_DB
    for term in db:
        if term in text:
            return True
    return False


def filter_rewrite_variants(
    original: str,
    variants: list[str],
    terminology_db: dict[str, str] | None = None,
) -> list[str]:
    """过滤 LLM 生成的查询变体，保留高质量结果。

    保留条件（满足任一）：
    1. 与原查询的字符级 Jaccard 相似度 > KB_REWRITE_SIMILARITY_THRESHOLD
    2. 命中术语词库（即使相似度较低也有价值，如缩写扩展）
    """
    if not variants:
        return []

    term_db = terminology_db if terminology_db is not None else _TERMINOLOGY_DB
    kept: list[str] = []

    for variant in variants:
        normalized_variant = (variant or "").strip()
        if not normalized_variant or normalized_variant == original:
            continue

        similarity = _compute_similarity(original, normalized_variant)
        if similarity > KB_REWRITE_SIMILARITY_THRESHOLD or _hits_terminology_db(normalized_variant, term_db):
            kept.append(normalized_variant)

    return kept


def rewrite_query_with_llm(query: str, max_variants: int | None = None) -> list[str]:
    """调用 Ollama LLM 生成查询改写变体。

    使用 JSON 格式输出，300ms 超时防止阻塞。
    失败时静默降级，返回空列表。
    """
    n = max_variants or KB_REWRITE_MAX_VARIANTS
    prompt = (
        f'你是一个查询改写助手。请将以下查询改写为{n}个不同的中文查询变体，'
        f"保持原意但使用不同的表达方式。\n"
        f"原查询：{query}\n"
        f'请以JSON格式回答，格式为：{{"variants": ["变体1", "变体2", ...]}}\n'
        f"只返回JSON，不要其他内容。"
    )

    try:
        response = httpx.post(
            f"{KB_OLLAMA_BASE_URL}/api/generate",
            json={
                "model": KB_REWRITE_LLM_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False,
            },
            timeout=0.3,
        )
        response.raise_for_status()
        data = response.json()
        raw_response = data.get("response", "")
        if not raw_response:
            return []

        parsed = json.loads(raw_response)
        variants = parsed.get("variants", [])
        return [str(v).strip() for v in variants if str(v).strip()]

    except Exception:
        logger.debug("[knowledge_rewrite] LLM rewrite failed, skipping")
        return []


class RewriteEffectivenessCache:
    """查询改写效果追踪缓存。

    记录每种查询模式的改写增益（gain），对持续无效的模式自动跳过。
    使用 LRU 策略管理缓存大小。
    """

    _GAIN_THRESHOLD = 0.05  # 5% 增益阈值

    def __init__(self, max_size: int | None = None) -> None:
        self._max_size = max_size or KB_REWRITE_EFFECTIVENESS_CACHE_SIZE
        self._cache: OrderedDict[str, float] = OrderedDict()

    def record(self, query_pattern: str, gain: float) -> None:
        """记录查询模式的改写增益。"""
        if query_pattern in self._cache:
            self._cache.move_to_end(query_pattern)
            # 保留最近一次的增益值
            self._cache[query_pattern] = gain
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[query_pattern] = gain

    def is_effective(self, query_pattern: str) -> bool:
        """判断查询模式的改写是否有效。

        未知模式返回 True（允许尝试改写）。
        已知但增益低于阈值的模式返回 False。
        """
        if query_pattern not in self._cache:
            return True
        return self._cache[query_pattern] >= self._GAIN_THRESHOLD


_effectiveness_cache: RewriteEffectivenessCache | None = None


def get_effectiveness_cache() -> RewriteEffectivenessCache:
    """获取模块级效果缓存单例。"""
    global _effectiveness_cache
    if _effectiveness_cache is None:
        _effectiveness_cache = RewriteEffectivenessCache()
    return _effectiveness_cache
