import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from app.core.logging import get_logger

load_dotenv()
logger = get_logger(__name__)

# 获取根目录，假设当前文件在 app/utils/rag.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 从 .env 中读取知识库目录，默认为 "data"
# 注意：.env 中写的是 KONWLEDGE_BASE_DIR（拼写为 KONWLEDGE_BASE_DIR）
KNOWLEDGE_BASE_DIR = os.getenv("KONWLEDGE_BASE_DIR", "data")
DATA_PATH = BASE_DIR / KNOWLEDGE_BASE_DIR

def get_all_files(directory: Path) -> List[Path]:
    """
    遍历指定目录及其子目录下的所有文件。
    """
    file_list = []
    if not directory.exists() or not directory.is_dir():
        logger.warning(f"目录不存在或不是文件夹: {directory}")
        return file_list

    for root, _, files in os.walk(directory):
        for file in files:
            file_list.append(Path(root) / file)

    return file_list

def load_documents(directory: Path = DATA_PATH) -> List[Document]:
    """
    遍历目录，并根据后缀名加载 Markdown 和 PDF 文件。
    """
    all_files = get_all_files(directory)
    documents = []
    
    if not all_files:
        logger.warning(f"未在 {directory} 下找到任何文件。")
        return documents

    logger.info(f"开始扫描 {directory}，共找到 {len(all_files)} 个文件。")
    
    for file_path in all_files:
        suffix = file_path.suffix.lower()
        try:
            # if suffix == '.pdf':
            #     print(f"正在加载 PDF 文件: {file_path}")
            #     logger.info(f"加载 PDF 文件: {file_path}")
            #     loader = PyMuPDFLoader(str(file_path))
            #     documents.extend(loader.load())
            if suffix == '.md':
                print(f"正在加载 Markdown 文件: {file_path}")
                logger.info(f"加载 Markdown 文件: {file_path}")
                loader = UnstructuredMarkdownLoader(str(file_path))
                documents.extend(loader.load())
            else:
                logger.debug(f"跳过不支持的文件格式: {file_path}")
        except Exception as e:
            print(f"❌ 加载文件 {file_path} 失败: {str(e)}")
            logger.error(f"加载文件 {file_path} 失败: {str(e)}")
            
    logger.info(f"所有文件读取完成，共加载了 {len(documents)} 页/块的内容。")
    return documents




# 仅作调试用途
if __name__ == "__main__":
    docs = load_documents()
    for doc in docs[:3]:  # 打印前几个看看
        print(f"[{doc.metadata.get('source')}] \n{doc.page_content[:200]}...\n")
