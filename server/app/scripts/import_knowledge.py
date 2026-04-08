"""
知识库导入脚本 - 独立运行版本
用法: cd server && python app/scripts/import_knowledge.py

使用本地 HuggingFace Embeddings 模型，无需 API Key
"""
import os
from pathlib import Path

try:
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    
    print("=" * 60)
    print("开始导入知识库到向量数据库")
    print("=" * 60)
    
    # 配置
    knowledge_dir = r"E:\coding"
    persist_dir = "./data/chroma_db"
    collection_name = "coding_knowledge"
    
    print(f"\n📁 源目录: {knowledge_dir}")
    print(f"💾 存储路径: {persist_dir}")
    print(f"📦 集合名称: {collection_name}\n")
    
    # 检查目录是否存在
    if not Path(knowledge_dir).exists():
        print(f"❌ 错误: 目录不存在 {knowledge_dir}")
        exit(1)
    
    # 1. 加载文档
    print("📖 步骤 1/3: 加载文档...")
    
    documents = []
    
    # 手动遍历文件，跳过损坏的文件/目录
    def load_files_safely(directory, extensions, encoding="utf-8"):
        """安全地加载文件，跳过损坏的文件和目录"""
        from langchain.schema import Document
        loaded_docs = []
        skipped = []
        
        def safe_walk(path):
            """安全地遍历目录，跳过损坏的子目录"""
            try:
                for item in Path(path).iterdir():
                    try:
                        if item.is_file() and item.suffix in extensions:
                            try:
                                with open(item, "r", encoding=encoding, errors="ignore") as f:
                                    content = f.read()
                                
                                # 只添加非空文件
                                if content.strip():
                                    doc = Document(
                                        page_content=content,
                                        metadata={"source": str(item)}
                                    )
                                    loaded_docs.append(doc)
                            except Exception as e:
                                skipped.append((str(item), f"读取失败: {str(e)}"))
                        elif item.is_dir():
                            safe_walk(item)  # 递归遍历子目录
                    except OSError as e:
                        skipped.append((str(item), f"访问失败: {str(e)}"))
                        continue
            except OSError as e:
                skipped.append((str(path), f"目录访问失败: {str(e)}"))
        
        safe_walk(directory)
        return loaded_docs, skipped
    
    # 加载 .txt 文件
    print("  正在加载 .txt 文件...")
    txt_docs, txt_skipped = load_files_safely(knowledge_dir, [".txt"])
    documents.extend(txt_docs)
    print(f"  ✓ 加载 .txt 文件: {len(txt_docs)} 个")
    if txt_skipped:
        print(f"  ⚠ 跳过文件/目录: {len(txt_skipped)} 个")
        # 显示前3个跳过的原因
        for path, reason in txt_skipped[:3]:
            print(f"    - {Path(path).name}: {reason}")
    
    # 加载 .md 文件
    print("  正在加载 .md 文件...")
    md_docs, md_skipped = load_files_safely(knowledge_dir, [".md"])
    documents.extend(md_docs)
    print(f"  ✓ 加载 .md 文件: {len(md_docs)} 个")
    if md_skipped:
        print(f"  ⚠ 跳过文件/目录: {len(md_skipped)} 个")
        for path, reason in md_skipped[:3]:
            print(f"    - {Path(path).name}: {reason}")
    
    # 加载 .py 文件
    print("  正在加载 .py 文件...")
    py_docs, py_skipped = load_files_safely(knowledge_dir, [".py"])
    documents.extend(py_docs)
    print(f"  ✓ 加载 .py 文件: {len(py_docs)} 个")
    if py_skipped:
        print(f"  ⚠ 跳过文件/目录: {len(py_skipped)} 个")
        for path, reason in py_skipped[:3]:
            print(f"    - {Path(path).name}: {reason}")
    
    if not documents:
        print("\n❌ 未找到任何文档，请检查目录路径")
        exit(1)
    
    print(f"\n✅ 总共加载: {len(documents)} 个文档")
    
    # 2. 切分文档
    print("\n✂️  步骤 2/3: 切分文档...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✅ 切分完成: {len(chunks)} 个文本块")
    
    # 3. 创建向量数据库
    print("\n🔮 步骤 3/3: 创建向量数据库...")
    print("  (使用本地 HuggingFace 模型，首次运行会自动下载...)")
    
    # 使用本地 HuggingFace Embeddings（不需要 API Key）
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
    )
    
    print(f"✅ 向量数据库创建完成！")
    
    # 4. 测试检索
    print("\n" + "=" * 60)
    print("🔍 测试检索功能")
    print("=" * 60)
    
    test_query = "docsify"
    print(f"\n查询: '{test_query}'")
    
    results = vectorstore.similarity_search_with_score(test_query, k=3)
    
    print(f"\n找到 {len(results)} 个相关结果:\n")
    for i, (doc, score) in enumerate(results, 1):
        print(f"结果 {i} (相似度分数: {score:.4f})")
        print(f"来源: {doc.metadata.get('source', 'Unknown')}")
        print(f"内容预览: {doc.page_content[:150]}...")
        print("-" * 60)
    
    print("\n" + "=" * 60)
    print("✅ 知识库导入完成！")
    print("=" * 60)
    print(f"\n📊 统计信息:")
    print(f"  - 文档总数: {len(documents)}")
    print(f"  - 文本块数: {len(chunks)}")
    print(f"  - 集合名称: {collection_name}")
    print(f"  - 存储位置: {persist_dir}")
    print("\n💡 提示: 现在可以通过 API 接口进行知识检索了！")
    
except ImportError as e:
    print(f"❌ 缺少依赖包: {e}")
    print("\n请先安装依赖:")
    print("  uv add langchain langchain-community langchain-chroma chromadb sentence-transformers")
except Exception as e:
    print(f"\n❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
