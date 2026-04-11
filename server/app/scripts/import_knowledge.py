"""
知识库导入执行脚本。
用法: 
    cd server
    python -m app.scripts.import_knowledge
"""

import sys
from pathlib import Path

# 确保能导入 app 模块
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.modules.knowledge_base.service import KnowledgeBaseService

def main():
    print("=" * 60)
    print("开始执行知识库导入流水线")
    print("=" * 60)
    
    # 获取项目根目录 (server 文件夹)
    project_root = Path(__file__).parent.parent.parent
    # 拼装知识库所在目录绝对路径
    doc_dir = str(project_root / "doc") 
    
    if not Path(doc_dir).exists():
        print(f"❌ 目录不存在: {doc_dir}，请确保在 server 目录下执行或创建该目录")
        return

    # 初始化知识库服务
    # 默认使用本地 Ollama 的 bge-m3:latest 和 MarkdownHeaderTextSplitter
    kb_service = KnowledgeBaseService()
    
    print(f"📁 源文档目录: {doc_dir}")
    print("🚀 正在扫描并处理 .md 文件...")
    
    # 执行导入
    result = kb_service.import_knowledge_base(directory_path=doc_dir)
    
    if result["success"]:
        print("\n✅ 知识库导入成功！")
        print(f"📊 统计信息:")
        print(f"  - 处理文档数: {result['stats'].get('total_docs', 0)}")
        print(f"  - 生成向量块: {result['stats'].get('total_chunks', 0)}")
        print(f"  - 集合名称: {result['stats'].get('collection_name', 'knowledge_base')}")
        print(f"  - 存储位置: {result['stats'].get('persist_directory', './data')}")
        
        # 可选：进行一次简单的检索测试验证
        print("\n🔍 进行连通性测试检索...")
        try:
            test_query = "什么是" # 随便测一个词
            search_res = kb_service.search_similar(test_query, k=1)
            if search_res:
                print(f"   [成功] 测试检索返回了结果: {search_res[0].page_content[:50]}...")
            else:
                print("   [提示] 测试检索未返回结果，但服务正常。")
        except Exception as e:
            print(f"   [警告] 测试检索失败: {e}")
            
    else:
        print(f"\n❌ 知识库导入失败: {result['message']}")

if __name__ == "__main__":
    main()
