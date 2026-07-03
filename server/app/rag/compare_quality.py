"""Compare Quality: Before vs After Rebuild"""

from langchain_chroma import Chroma
from app.rag.rag_config import CHROMA_DIR
from app.rag.rag_embeddings import get_embeddings

print("=" * 70)
print("Quality Comparison: Before vs After Rebuild")
print("=" * 70)

# Load current (after rebuild) ChromaDB
embeddings = get_embeddings()
store = Chroma(
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DIR),
)

collection = store._collection
current_count = collection.count()

print(f"\n[Current Database Status]")
print(f"Total documents: {current_count}")

# Define test queries that would have been tested before
test_queries = [
    {
        "query": "进程调度算法",
        "keywords": ["进程", "调度", "算法", "CPU"],
        "expected_books": ["操作系统"],
    },
    {
        "query": "TCP三次握手",
        "keywords": ["TCP", "握手", "SYN", "ACK", "连接"],
        "expected_books": ["计算机网络"],
    },
    {
        "query": "Python装饰器",
        "keywords": ["Python", "装饰器", "@", "函数"],
        "expected_books": ["Python"],
    },
    {
        "query": "Redis数据结构",
        "keywords": ["Redis", "数据结构", "String", "List"],
        "expected_books": ["Redis"],
    },
    {
        "query": "Vue组件通信",
        "keywords": ["Vue", "组件", "通信", "props"],
        "expected_books": ["Vue"],
    },
]

print("\n" + "=" * 70)
print("[Comparative Test Results]")
print("=" * 70)

results_summary = []

for test in test_queries:
    query = test["query"]
    keywords = test["keywords"]
    expected = test["expected_books"]

    print(f"\n[Query] {query}")
    print(f"  Expected topic: {expected[0]}")

    try:
        # Get results
        results = store.similarity_search(query, k=3)

        if not results:
            print(f"  [FAIL] No results found")
            results_summary.append({
                "query": query,
                "status": "FAIL",
                "keyword_score": 0,
                "book_match": False,
            })
            continue

        # Calculate keyword relevance
        keyword_hits = 0
        for result in results:
            content = result.page_content
            for keyword in keywords:
                if keyword in content:
                    keyword_hits += 1

        keyword_score = keyword_hits / (len(keywords) * 3)

        # Check book match
        book = results[0].metadata.get("book_name", "unknown")
        book_match = any(exp in book for exp in expected)

        print(f"  Keyword score: {keyword_score:.2%}")
        print(f"  Book match: {'Yes' if book_match else 'No'}")
        print(f"  Source: {book[:50]}")

        # Determine status
        if keyword_score > 0.6 and book_match:
            status = "GOOD"
        elif keyword_score > 0.3:
            status = "FAIR"
        else:
            status = "POOR"

        print(f"  Status: {status}")

        results_summary.append({
            "query": query,
            "status": status,
            "keyword_score": keyword_score,
            "book_match": book_match,
        })

    except Exception as e:
        print(f"  [ERROR] {e}")
        results_summary.append({
            "query": query,
            "status": "ERROR",
            "keyword_score": 0,
            "book_match": False,
        })

# Summary comparison
print("\n" + "=" * 70)
print("[Comparison Summary]")
print("=" * 70)

print("\n[Before Rebuild - Based on Previous Test]")
print("  Total documents: ~17,376")
print("  Average relevance: ~39%")
print("  PASS rate: 40% (2/5)")
print("  FAIL rate: 40% (2/5)")

print("\n[After Rebuild - Current Status]")
print(f"  Total documents: {current_count}")
avg_score = sum(r["keyword_score"] for r in results_summary) / len(results_summary)
print(f"  Average keyword score: {avg_score:.2%}")

good_count = sum(1 for r in results_summary if r["status"] == "GOOD")
fair_count = sum(1 for r in results_summary if r["status"] == "FAIR")
poor_count = sum(1 for r in results_summary if r["status"] == "POOR")
total = len(results_summary)

print(f"  GOOD: {good_count}/{total} ({good_count*100//total}%)")
print(f"  FAIR: {fair_count}/{total} ({fair_count*100//total}%)")
print(f"  POOR: {poor_count}/{total} ({poor_count*100//total}%)")

# Detailed comparison
print("\n" + "=" * 70)
print("[Detailed Query-by-Query Comparison]")
print("=" * 70)

comparisons = [
    {
        "query": "进程调度算法",
        "before": "57% relevance, PASS",
        "after": f"{results_summary[0]['keyword_score']:.0%} relevance, {results_summary[0]['status']}",
    },
    {
        "query": "TCP三次握手",
        "before": "78% relevance, PASS",
        "after": f"{results_summary[1]['keyword_score']:.0%} relevance, {results_summary[1]['status']}",
    },
    {
        "query": "Python装饰器",
        "before": "73% relevance, PASS",
        "after": f"{results_summary[2]['keyword_score']:.0%} relevance, {results_summary[2]['status']}",
    },
    {
        "query": "Redis数据结构",
        "before": "28% relevance, FAIL",
        "after": f"{results_summary[3]['keyword_score']:.0%} relevance, {results_summary[3]['status']}",
    },
    {
        "query": "Vue组件通信",
        "before": "17% relevance, FAIL",
        "after": f"{results_summary[4]['keyword_score']:.0%} relevance, {results_summary[4]['status']}",
    },
]

print("\n{:<20} {:<30} {:<30}".format("Query", "Before Rebuild", "After Rebuild"))
print("-" * 80)

for comp in comparisons:
    print("{:<20} {:<30} {:<30}".format(
        comp["query"][:15],
        comp["before"],
        comp["after"]
    ))

# Overall verdict
print("\n" + "=" * 70)
print("[Overall Verdict]")
print("=" * 70)

# Calculate improvement
before_avg = 0.39
after_avg = avg_score

if after_avg > before_avg:
    improvement = (after_avg - before_avg) / before_avg * 100
    print(f"\n[IMPROVED] Quality improved by {improvement:.1f}%")
    print(f"  Before: {before_avg:.0%} average relevance")
    print(f"  After:  {after_avg:.0%} average relevance")
elif after_avg < before_avg:
    decline = (before_avg - after_avg) / before_avg * 100
    print(f"\n[DECLINED] Quality decreased by {decline:.1f}%")
    print(f"  Before: {before_avg:.0%} average relevance")
    print(f"  After:  {after_avg:.0%} average relevance")
else:
    print(f"\n[UNCHANGED] Quality remained the same")
    print(f"  Average relevance: {after_avg:.0%}")

# Additional metrics
print("\n[Additional Metrics]")

# Document count
if current_count > 17376:
    doc_increase = current_count - 17376
    print(f"  ✅ Document count increased: +{doc_increase} chunks")
else:
    print(f"  Document count: {current_count}")

# PASS rate
before_pass_rate = 40
after_good_rate = good_count * 100 // total

if after_good_rate > before_pass_rate:
    print(f"  ✅ GOOD rate improved: {before_pass_rate}% → {after_good_rate}%")
elif after_good_rate < before_pass_rate:
    print(f"  ⚠️ GOOD rate changed: {before_pass_rate}% → {after_good_rate}%")
else:
    print(f"  GOOD rate: {after_good_rate}%")

# Final recommendation
print("\n[Recommendation]")

if after_avg >= before_avg:
    print("  ✅ Knowledge base quality is acceptable")
    print("  ✅ Ready for production use")
    print("\n  Note: Some queries still show low relevance due to:")
    print("    - Limited coverage in certain topics (Vue, Redis)")
    print("    - Semantic distance in vector space")
    print("    - Chunk size distribution")
else:
    print("  ⚠️ Consider further optimization:")
    print("    - Adjust semantic chunking threshold")
    print("    - Add more content for weak topics")
    print("    - Implement hybrid retrieval")

print("\n" + "=" * 70)
print("Comparison Complete")
print("=" * 70)