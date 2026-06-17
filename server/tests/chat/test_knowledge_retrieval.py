from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


JAVA_SOURCE = "Java从入门到精通"


def test_route_query_sources_routes_java_queries_to_exact_java_book_source() -> None:
    from app.chat.tools import knowledge

    route = knowledge.route_query_sources("Java 多态 和 继承")

    assert route.query == "Java 多态 和 继承"
    assert route.source_filter == (JAVA_SOURCE,)


def test_retrieve_dense_knowledge_forwards_exact_source_filter(monkeypatch) -> None:
    from app.chat.tools import knowledge

    calls: list[dict] = []

    class FakeVectorStore:
        def similarity_search_by_vector_with_relevance_scores(self, embedding, **kwargs):
            calls.append({"embedding": embedding, **kwargs})
            return []

    monkeypatch.setattr(knowledge, "_get_vectorstore", lambda: FakeVectorStore())
    monkeypatch.setattr(knowledge, "_get_cached_embedding", lambda _query: (0.1, 0.2, 0.3))

    knowledge.retrieve_dense_knowledge(
        "Java 集合",
        top_k=2,
        source_filter=(JAVA_SOURCE, "other"),
    )

    assert calls == [
        {
            "embedding": [0.1, 0.2, 0.3],
            "k": knowledge.KB_TOP_K,
            "filter": {"source": {"$in": [JAVA_SOURCE, "other"]}},
        },
        {
            "embedding": [0.1, 0.2, 0.3],
            "k": knowledge.KB_TOP_K,
            "filter": None,
        },
    ]


def test_retrieve_dense_knowledge_falls_back_to_metadata_match_when_source_filter_misses(monkeypatch) -> None:
    from app.chat.tools import knowledge

    calls: list[dict] = []

    class FakeDoc:
        def __init__(self, text: str, metadata: dict) -> None:
            self.page_content = text
            self.metadata = metadata

    class FakeVectorStore:
        def similarity_search_by_vector_with_relevance_scores(self, embedding, **kwargs):
            calls.append({"embedding": embedding, **kwargs})
            if kwargs.get("filter") is not None:
                return []
            return [
                (FakeDoc("Java 集合", {"file_name": "Java从入门到精通-第06章.md", "chunk_index": 1}), 0.2),
                (FakeDoc("Python 列表", {"file_name": "Python Cookbook.md", "chunk_index": 2}), 0.3),
            ]

    monkeypatch.setattr(knowledge, "_get_vectorstore", lambda: FakeVectorStore())
    monkeypatch.setattr(knowledge, "_get_cached_embedding", lambda _query: (0.1, 0.2, 0.3))

    rows = knowledge.retrieve_dense_knowledge(
        "Java 集合",
        top_k=2,
        source_filter=(JAVA_SOURCE,),
    )

    assert [row["metadata"].get("file_name") for row in rows] == ["Java从入门到精通-第06章.md"]
    assert calls == [
        {
            "embedding": [0.1, 0.2, 0.3],
            "k": knowledge.KB_TOP_K,
            "filter": {"source": {"$in": [JAVA_SOURCE]}},
        },
        {
            "embedding": [0.1, 0.2, 0.3],
            "k": knowledge.KB_TOP_K,
            "filter": None,
        },
    ]


def test_retrieve_dense_knowledge_merges_filtered_and_metadata_fallback_candidates(monkeypatch) -> None:
    from app.chat.tools import knowledge

    class FakeDoc:
        def __init__(self, text: str, metadata: dict) -> None:
            self.page_content = text
            self.metadata = metadata

    calls: list[dict] = []

    class FakeVectorStore:
        def similarity_search_by_vector_with_relevance_scores(self, embedding, **kwargs):
            calls.append({"embedding": embedding, **kwargs})
            if kwargs.get("filter") is not None:
                return [
                    (FakeDoc("source-hit", {"source": JAVA_SOURCE, "chunk_index": 1}), 0.2),
                ]
            return [
                (FakeDoc("source-hit", {"source": JAVA_SOURCE, "chunk_index": 1}), 0.2),
                (FakeDoc("file-hit", {"file_name": "Java从入门到精通-第06章.md", "chunk_index": 2}), 0.25),
                (FakeDoc("other-hit", {"file_name": "Python Cookbook.md", "chunk_index": 3}), 0.3),
            ]

    monkeypatch.setattr(knowledge, "_get_vectorstore", lambda: FakeVectorStore())
    monkeypatch.setattr(knowledge, "_get_cached_embedding", lambda _query: (0.1, 0.2, 0.3))

    rows = knowledge.retrieve_dense_knowledge(
        "Java 集合",
        top_k=3,
        source_filter=(JAVA_SOURCE,),
    )

    assert [row["text"] for row in rows] == ["source-hit", "file-hit"]
    assert calls == [
        {
            "embedding": [0.1, 0.2, 0.3],
            "k": knowledge.KB_TOP_K,
            "filter": {"source": {"$in": [JAVA_SOURCE]}},
        },
        {
            "embedding": [0.1, 0.2, 0.3],
            "k": knowledge.KB_TOP_K,
            "filter": None,
        },
    ]


def test_retrieve_dense_knowledge_keeps_best_similarity_order_after_merge(monkeypatch) -> None:
    from app.chat.tools import knowledge

    class FakeDoc:
        def __init__(self, text: str, metadata: dict) -> None:
            self.page_content = text
            self.metadata = metadata

    class FakeVectorStore:
        def similarity_search_by_vector_with_relevance_scores(self, embedding, **kwargs):
            if kwargs.get("filter") is not None:
                return [
                    (FakeDoc("source-hit", {"source": JAVA_SOURCE, "chunk_index": 1}), 0.30),
                ]
            return [
                (FakeDoc("source-hit", {"source": JAVA_SOURCE, "chunk_index": 1}), 0.30),
                (FakeDoc("file-hit", {"file_name": "Java从入门到精通-第06章.md", "chunk_index": 2}), 0.10),
            ]

    monkeypatch.setattr(knowledge, "_get_vectorstore", lambda: FakeVectorStore())
    monkeypatch.setattr(knowledge, "_get_cached_embedding", lambda _query: (0.1, 0.2, 0.3))

    rows = knowledge.retrieve_dense_knowledge(
        "Java 集合",
        top_k=2,
        source_filter=(JAVA_SOURCE,),
    )

    assert [row["text"] for row in rows] == ["file-hit", "source-hit"]
    assert [row["rank"] for row in rows] == [1, 2]


def test_retrieve_dense_knowledge_respects_top_k_after_merge(monkeypatch) -> None:
    from app.chat.tools import knowledge

    class FakeDoc:
        def __init__(self, text: str, metadata: dict) -> None:
            self.page_content = text
            self.metadata = metadata

    class FakeVectorStore:
        def similarity_search_by_vector_with_relevance_scores(self, embedding, **kwargs):
            if kwargs.get("filter") is not None:
                return [
                    (FakeDoc("source-hit", {"source": JAVA_SOURCE, "chunk_index": 1}), 0.30),
                ]
            return [
                (FakeDoc("source-hit", {"source": JAVA_SOURCE, "chunk_index": 1}), 0.30),
                (FakeDoc("file-hit-1", {"file_name": "Java从入门到精通-第06章.md", "chunk_index": 2}), 0.10),
                (FakeDoc("file-hit-2", {"file_name": "Java从入门到精通-第07章.md", "chunk_index": 3}), 0.20),
            ]

    monkeypatch.setattr(knowledge, "_get_vectorstore", lambda: FakeVectorStore())
    monkeypatch.setattr(knowledge, "_get_cached_embedding", lambda _query: (0.1, 0.2, 0.3))

    rows = knowledge.retrieve_dense_knowledge(
        "Java 集合",
        top_k=2,
        source_filter=(JAVA_SOURCE,),
    )

    assert len(rows) == 2
    assert [row["text"] for row in rows] == ["file-hit-1", "file-hit-2"]


def test_rank_with_bm25_applies_source_filter_with_metadata_fallbacks() -> None:
    from app.chat.tools import knowledge

    corpus = [
        {
            "text": "Java 集合 与 List 接口",
            "metadata": {"file_name": "Java从入门到精通-第06章.md", "chunk_index": 1},
            "search_text": "java 集合 与 list 接口\njava从入门到精通-第06章.md",
        },
        {
            "text": "Java 线程 与 synchronized",
            "metadata": {"book_title": "《Java从入门到精通》", "chunk_index": 2},
            "search_text": "java 线程 与 synchronized\n《java从入门到精通》",
        },
        {
            "text": "Python 列表 与 字典",
            "metadata": {"source": "Python Cookbook", "chunk_index": 3},
            "search_text": "python 列表 与 字典\npython cookbook",
        },
    ]

    index = knowledge.build_bm25_index(corpus)
    rows = knowledge.rank_with_bm25(
        "Java 集合 线程",
        index,
        top_k=5,
        source_filter=(JAVA_SOURCE,),
    )

    assert len(rows) == 2
    metadata_rows = [row["metadata"] for row in rows]
    assert any(meta.get("file_name") == "Java从入门到精通-第06章.md" for meta in metadata_rows)
    assert any(meta.get("book_title") == "《Java从入门到精通》" for meta in metadata_rows)


def test_retrieve_knowledge_forwards_course_name_and_routed_source_filter(monkeypatch) -> None:
    from app.chat.tools import knowledge

    route_calls: list[dict] = []
    dense_calls: list[dict] = []
    sparse_calls: list[dict] = []

    def fake_route(query: str, course_name: str | None = None):
        route_calls.append({"query": query, "course_name": course_name})
        return knowledge.QueryRouteResult(query=query, source_filter=(JAVA_SOURCE,))

    def fake_dense(query: str, *, top_k: int | None = None, source_filter=None):
        dense_calls.append({"query": query, "top_k": top_k, "source_filter": source_filter})
        return [
            {
                "rank": 1,
                "distance": 0.1,
                "metadata": {"source": JAVA_SOURCE, "chunk_index": 1},
                "text": "Java 线程基础",
                "retrieval_mode": "dense",
            }
        ]

    def fake_sparse(query: str, *, top_k: int | None = None, source_filter=None):
        sparse_calls.append({"query": query, "top_k": top_k, "source_filter": source_filter})
        return []

    monkeypatch.setattr(knowledge, "route_query_sources", fake_route)
    monkeypatch.setattr(knowledge, "retrieve_dense_knowledge", fake_dense)
    monkeypatch.setattr(knowledge, "retrieve_sparse_knowledge", fake_sparse)

    rows = knowledge.retrieve_knowledge("Java 线程", course_name="Java程序设计", top_k=3)

    assert rows[0]["metadata"]["source"] == JAVA_SOURCE
    assert route_calls == [{"query": "Java 线程", "course_name": "Java程序设计"}]
    assert dense_calls == [
        {
            "query": "Java 线程",
            "top_k": max(3 * 2, knowledge.KB_TOP_K),
            "source_filter": (JAVA_SOURCE,),
        }
    ]
    assert sparse_calls == [
        {
            "query": "Java 线程",
            "top_k": max(3 * 2, knowledge.KB_TOP_K),
            "source_filter": (JAVA_SOURCE,),
        }
    ]


def test_make_search_knowledge_base_passes_course_name_structurally(monkeypatch) -> None:
    from app.chat.tools import knowledge

    calls: list[dict] = []

    async def fake_aformat(query: str, *, course_name: str | None = None, top_k: int | None = None):
        calls.append({"query": query, "course_name": course_name, "top_k": top_k})
        return "context", [{"rank": 1}]

    monkeypatch.setattr(knowledge, "aformat_knowledge_context", fake_aformat)

    tool = knowledge.make_search_knowledge_base()
    result = asyncio.run(tool("集合", course_name="Java程序设计", top_k=2))

    assert result == "context"
    assert calls == [{"query": "集合", "course_name": "Java程序设计", "top_k": 2}]


def test_search_knowledge_base_tool_accepts_structured_arguments(monkeypatch) -> None:
    from app.chat.tools import knowledge

    calls: list[dict] = []

    async def fake_aformat(query: str, *, course_name: str | None = None, top_k: int | None = None):
        calls.append({"query": query, "course_name": course_name, "top_k": top_k})
        return "tool-context", [{"rank": 1}]

    monkeypatch.setattr(knowledge, "aformat_knowledge_context", fake_aformat)

    result = asyncio.run(
        knowledge.search_knowledge_base.ainvoke(
            {"query": "集合", "course_name": "Java程序设计", "top_k": 2}
        )
    )

    assert result == "tool-context"
    assert calls == [{"query": "集合", "course_name": "Java程序设计", "top_k": 2}]


def test_sparse_search_text_excludes_mirror_site_noise() -> None:
    from app.chat.tools.knowledge import build_sparse_search_text

    text = build_sparse_search_text(
        "HashMap 是基于哈希表的实现",
        {
            "source": "Java从入门到精通（第5版） (明日科技) (z-library.sk, 1lib.sk, z-lib.sk).final.md",
            "heading_path": "第10章 集合框架",
        },
    )

    assert "hashmap" in text
    assert "第10章 集合框架" in text
    assert "z-library.sk" not in text
    assert "1lib.sk" not in text
    assert "z-lib.sk" not in text


def test_get_sparse_corpus_uses_cleaned_search_text(monkeypatch) -> None:
    from app.chat.tools import knowledge

    class FakeCollection:
        def get(self, include=None, limit=None):
            return {
                "documents": ["HashMap 是基于哈希表的实现"],
                "metadatas": [
                    {
                        "source": "Java从入门到精通（第5版） (明日科技) (z-library.sk, 1lib.sk, z-lib.sk).final.md",
                        "heading_path": "第10章 集合框架",
                    }
                ],
            }

    class FakeVectorStore:
        _collection = FakeCollection()

    monkeypatch.setattr(knowledge, "_get_vectorstore", lambda: FakeVectorStore())
    knowledge._get_sparse_corpus.cache_clear()

    corpus = knowledge._get_sparse_corpus()

    assert corpus
    assert "z-library.sk" not in corpus[0]["search_text"]


def test_merge_ranked_results_uses_rrf_ordering() -> None:
    from app.chat.tools.knowledge import merge_ranked_results

    dense_rows = [
        {"rank": 1, "distance": 0.2, "metadata": {"source": "java.md", "chunk_index": 1}, "text": "dense-a", "retrieval_mode": "dense"},
        {"rank": 2, "distance": 0.3, "metadata": {"source": "db.md", "chunk_index": 2}, "text": "dense-b", "retrieval_mode": "dense"},
    ]
    sparse_rows = [
        {"rank": 1, "distance": -4.0, "metadata": {"source": "db.md", "chunk_index": 2}, "text": "sparse-b", "retrieval_mode": "sparse"},
        {"rank": 2, "distance": -3.0, "metadata": {"source": "java.md", "chunk_index": 1}, "text": "sparse-a", "retrieval_mode": "dense"},
    ]

    merged = merge_ranked_results("query", dense_rows=dense_rows, sparse_rows=sparse_rows, top_k=2)

    # RRF scoring:
    # java.md: 1/(60+1) + 1/(60+2) = 0.0164 + 0.0159 = 0.0323
    # db.md: 1/(60+2) + 1/(60+1) = 0.0159 + 0.0164 = 0.0323
    # Both have same score, so order should preserve dense rank order (java.md first)
    assert [item["metadata"]["source"] for item in merged] == ["java.md", "db.md"]


def test_compute_source_metrics_counts_top1_accuracy_and_pollution() -> None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval" / "knowledge_retrieval"))
    from evaluate import compute_source_metrics

    results = [
        {
            "expected_sources": ["Java从入门到精通"],
            "result_sources": ["Java从入门到精通", "数据库系统概念"],
        }
    ]

    metrics = compute_source_metrics(results)

    assert metrics["top1_source_accuracy"] == 1.0
    assert metrics["cross_book_pollution_rate"] == 0.5


def test_extract_canonical_source_identity_prefers_book_title_then_source_then_file_name() -> None:
    from app.chat.tools.knowledge import extract_canonical_source_identity

    assert (
        extract_canonical_source_identity(
            {
                "book_title": "《Java从入门到精通》",
                "source": "ignored-source.md",
                "file_name": "ignored-file.md",
            }
        )
        == "java从入门到精通"
    )
    assert (
        extract_canonical_source_identity(
            {
                "source": "Java从入门到精通（第2版）.final.md",
                "file_name": "ignored-file.md",
            }
        )
        == "java从入门到精通第2版finalmd"
    )
    assert (
        extract_canonical_source_identity(
            {
                "file_name": "Java从入门到精通-第06章.md",
            }
        )
        == "java从入门到精通第06章md"
    )


def test_extract_canonical_source_identity_strips_known_noise() -> None:
    from app.chat.tools.knowledge import extract_canonical_source_identity

    assert (
        extract_canonical_source_identity(
            {
                "source": "Java从入门到精通（第2版） (z-library.sk, 1lib.sk, z-lib.sk).final.md",
            }
        )
        == "java从入门到精通第2版finalmd"
    )
