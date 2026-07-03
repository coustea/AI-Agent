"""Check ChromaDB status"""

import sys

from langchain_chroma import Chroma
from app.rag.rag_config import CHROMA_DIR
from app.rag.rag_embeddings import get_embeddings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=" * 70)
print("ChromaDB Status Check")
print("=" * 70)

print(f"\nChroma directory: {CHROMA_DIR}")
print(f"Directory exists: {CHROMA_DIR.exists()}")

try:
    # Load existing ChromaDB
    embeddings = get_embeddings()
    store = Chroma(
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    # Get collection info
    collection = store._collection
    print(f"\nCollection name: {collection.name}")
    print(f"Total documents: {collection.count()}")

    # Sample query
    print("\n[Test Query]")
    results = store.similarity_search("什么是进程调度", k=3)
    print(f"Query results: {len(results)}")
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        book = doc.metadata.get("book_name", "unknown")
        print(f"\n  Result {i}:")
        print(f"    Source: {source}")
        print(f"    Book: {book}")
        print(f"    Content preview: {doc.page_content[:100]}...")

    print("\n" + "=" * 70)
    print("[SUCCESS] ChromaDB is functional!")
    print("=" * 70)

except Exception as e:
    print(f"\n[ERROR] Failed to load ChromaDB: {e}")
    import traceback
    traceback.print_exc()
