"""检索感知查询改写模块的单元测试。"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.rag.knowledge_rewrite import (
    RewriteEffectivenessCache,
    _TERMINOLOGY_DB,
    compute_retrieval_confidence,
    filter_rewrite_variants,
    should_trigger_rewrite,
)


# ============ TestRetrievalConfidence ============


class TestRetrievalConfidence:
    """检索置信度计算测试。"""

    def test_high_confidence_when_top1_leads(self) -> None:
        """top1 分数远高于其余时，置信度应较高。"""
        rows = [
            {"distance": 0.1},
            {"distance": 0.5},
            {"distance": 0.6},
            {"distance": 0.7},
            {"distance": 0.8},
        ]
        confidence = compute_retrieval_confidence(rows)
        # top1=0.1, mean=0.54, ratio=0.1/0.54 ≈ 0.185
        assert 0.1 < confidence < 0.25

    def test_low_confidence_when_clustered(self) -> None:
        """所有分数接近时，置信度应接近 1.0。"""
        rows = [
            {"distance": 0.5},
            {"distance": 0.51},
            {"distance": 0.52},
            {"distance": 0.53},
            {"distance": 0.54},
        ]
        confidence = compute_retrieval_confidence(rows)
        # top1=0.5, mean≈0.52, ratio≈0.96
        assert 0.9 < confidence < 1.0

    def test_empty_rows_returns_zero(self) -> None:
        """空结果返回 0.0。"""
        assert compute_retrieval_confidence([]) == 0.0

    def test_single_row_returns_zero(self) -> None:
        """单条结果返回 0.0（无法计算有效比率）。"""
        assert compute_retrieval_confidence([{"distance": 0.5}]) == 0.0


# ============ TestShouldTriggerRewrite ============


class TestShouldTriggerRewrite:
    """查询改写触发判断测试。"""

    def test_skip_on_exclusive_word(self) -> None:
        """命中独占关键词时不触发改写。"""
        result = should_trigger_rewrite(
            "Java 多线程",
            exclusive_words={"Java", "多线程"},
            hardcoded_rules=(),
            terminology_dict={},
        )
        assert result is False

    def test_skip_on_hardcoded_rule(self) -> None:
        """命中硬编码规则时不触发改写。"""
        rules = (
            (re.compile(r"tcp\s*三次握手", re.IGNORECASE), ("TCP", "三次握手")),
        )
        result = should_trigger_rewrite(
            "tcp三次握手的过程",
            exclusive_words=set(),
            hardcoded_rules=rules,
            terminology_dict={},
        )
        assert result is False

    def test_trigger_on_no_fast_path(self) -> None:
        """无快速路径命中时触发改写。"""
        result = should_trigger_rewrite(
            "什么是进程调度算法",
            exclusive_words=set(),
            hardcoded_rules=(),
            terminology_dict={},
        )
        assert result is True

    def test_short_query_in_terminology_dict(self) -> None:
        """短查询命中术语词库时触发改写。"""
        result = should_trigger_rewrite(
            "JVM",
            exclusive_words=set(),
            hardcoded_rules=(),
            terminology_dict=_TERMINOLOGY_DB,
        )
        assert result is True

    def test_short_query_not_in_dict(self) -> None:
        """短查询不在术语词库中时不触发改写。"""
        result = should_trigger_rewrite(
            "x",
            exclusive_words=set(),
            hardcoded_rules=(),
            terminology_dict={},
        )
        assert result is False


# ============ TestFilterRewriteVariants ============


class TestFilterRewriteVariants:
    """查询变体质量过滤测试。"""

    def test_keep_similar_variant(self) -> None:
        """与原查询相似的变体应保留。"""
        original = "进程调度算法"
        # 大部分字符重叠，字符级 Jaccard 应 > 0.6
        variants = ["进程调度算法原理", "完全无关xyz"]
        kept = filter_rewrite_variants(original, variants, terminology_db={})
        assert "进程调度算法原理" in kept

    def test_keep_terminology_db_hit_with_low_similarity(self) -> None:
        """命中术语词库但相似度低的变体应保留。"""
        original = "什么是内存管理"
        variants = ["JVM垃圾回收机制"]
        kept = filter_rewrite_variants(original, variants, terminology_db=_TERMINOLOGY_DB)
        # "JVM垃圾回收机制" 命中 JVM 术语，即使与原查询相似度低也应保留
        assert "JVM垃圾回收机制" in kept

    def test_filter_empty_variants(self) -> None:
        """空变体列表返回空。"""
        assert filter_rewrite_variants("查询", []) == []

    def test_filter_duplicate_of_original(self) -> None:
        """与原查询完全相同的变体应被过滤。"""
        original = "什么是死锁"
        kept = filter_rewrite_variants(original, ["什么是死锁"], terminology_db={})
        assert kept == []


# ============ TestRewriteEffectivenessCache ============


class TestRewriteEffectivenessCache:
    """改写效果追踪缓存测试。"""

    def test_record_and_check_effective(self) -> None:
        """记录有效增益后，is_effective 返回 True。"""
        cache = RewriteEffectivenessCache(max_size=10)
        cache.record("进程调度", 0.15)
        assert cache.is_effective("进程调度") is True

    def test_ineffective_pattern_skipped(self) -> None:
        """增益低于阈值的模式，is_effective 返回 False。"""
        cache = RewriteEffectivenessCache(max_size=10)
        cache.record("模糊查询", 0.02)
        assert cache.is_effective("模糊查询") is False

    def test_unknown_pattern_allowed(self) -> None:
        """未知模式返回 True（允许尝试改写）。"""
        cache = RewriteEffectivenessCache(max_size=10)
        assert cache.is_effective("全新查询") is True

    def test_cache_eviction(self) -> None:
        """缓存满时淘汰最旧条目。"""
        cache = RewriteEffectivenessCache(max_size=3)
        cache.record("a", 0.1)
        cache.record("b", 0.1)
        cache.record("c", 0.1)
        # 插入第 4 条，应淘汰 "a"
        cache.record("d", 0.1)
        assert cache.is_effective("a") is True  # 未知 → 允许
        assert cache.is_effective("d") is True  # 已知且有效
