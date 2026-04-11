"""
知识库管理服务 - RAG 向量数据库导入
"""
import asyncio
import os
from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import (
    DirectoryLoader,
    UnstructuredMarkdownLoader,
)
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.logging import get_logger

logger = get_logger(__name__)


class KnowledgeBaseService:
    """知识库服务：负责文档加载、切分、向量化存储"""

    def __init__(
        self,
        persist_directory: str = "./data",
        embedding_model: str = "bge-m3:latest",
    ):
        self.persist_directory = persist_directory
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        self.text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
        )

    def load_documents_from_directory(self, directory_path: str) -> List[Document]:
        """从目录加载所有支持的文档类型"""
        documents = []
        dir_path = Path(directory_path)

        if not dir_path.exists():
            logger.error(f"Directory not found: {directory_path}")
            raise FileNotFoundError(f"目录不存在: {directory_path}")

        logger.info(f"开始扫描目录: {directory_path}")

        # 支持的文件类型及对应的加载器
        loaders_config = [
            ("**/*.md", UnstructuredMarkdownLoader, {}),
        ]

        for pattern, loader_cls, loader_kwargs in loaders_config:
            try:
                loader = DirectoryLoader(
                    directory_path,
                    glob=pattern,
                    loader_cls=loader_cls,
                    loader_kwargs=loader_kwargs,
                    show_progress=True,
                    use_multithreading=True,
                )
                docs = loader.load()
                documents.extend(docs)
                logger.info(f"加载 {pattern} 文件: {len(docs)} 个文档")
            except Exception as e:
                logger.warning(f"加载 {pattern} 文件时出错: {str(e)}")

        logger.info(f"总共加载文档数: {len(documents)}")
        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """将文档切分为小块"""
        logger.info(f"开始切分 {len(documents)} 个文档")
        chunks = []
        for doc in documents:
            splits = self.text_splitter.split_text(doc.page_content)
            for split in splits:
                merged_metadata = {**doc.metadata, **split.metadata}
                chunks.append(Document(page_content=split.page_content, metadata=merged_metadata))
        logger.info(f"切分后得到 {len(chunks)} 个文本块")
        return chunks

    def create_vector_store(
        self, documents: List[Document], collection_name: str = "knowledge_base"
    ) -> Chroma:
        """创建向量数据库"""
        logger.info(f"开始创建向量数据库，集合名: {collection_name}")

        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=self.persist_directory,
        )

        logger.info(f"向量数据库创建完成，存储路径: {self.persist_directory}")
        return vectorstore

    def load_vector_store(self, collection_name: str = "knowledge_base") -> Chroma:
        """加载已存在的向量数据库"""
        logger.info(f"加载向量数据库，集合名: {collection_name}")

        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )

        return vectorstore

    def import_knowledge_base(
        self, directory_path: str = "doc", collection_name: str = "knowledge_base"
    ) -> dict:
        """完整的知识库导入流程"""
        try:
            # 1. 加载文档
            documents = self.load_documents_from_directory(directory_path)

            if not documents:
                return {
                    "success": False,
                    "message": "未找到任何可加载的文档",
                    "stats": {"total_docs": 0, "total_chunks": 0},
                }

            # 2. 切分文档
            chunks = self.split_documents(documents)

            # 3. 创建向量数据库
            vectorstore = self.create_vector_store(chunks, collection_name)

            return {
                "success": True,
                "message": "知识库导入成功",
                "stats": {
                    "total_docs": len(documents),
                    "total_chunks": len(chunks),
                    "collection_name": collection_name,
                    "persist_directory": self.persist_directory,
                },
            }

        except Exception as e:
            logger.error(f"知识库导入失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"导入失败: {str(e)}",
                "stats": {},
            }

    def search_similar(
        self,
        query: str,
        collection_name: str = "knowledge_base",
        k: int = 5,
    ) -> List[Document]:
        """相似度搜索"""
        vectorstore = self.load_vector_store(collection_name)
        results = vectorstore.similarity_search(query, k=k)
        return results

    def search_with_score(
        self,
        query: str,
        collection_name: str = "knowledge_base",
        k: int = 5,
    ) -> List[tuple[Document, float]]:
        """带相似度分数的搜索"""
        vectorstore = self.load_vector_store(collection_name)
        results = vectorstore.similarity_search_with_score(query, k=k)
        return results

    async def search_similar_async(
        self,
        query: str,
        collection_name: str = "knowledge_base",
        k: int = 5,
    ) -> List[Document]:
        """异步相似度搜索"""
        return await asyncio.to_thread(
            self.search_similar,
            query,
            collection_name,
            k,
        )

    async def search_with_score_async(
        self,
        query: str,
        collection_name: str = "knowledge_base",
        k: int = 5,
    ) -> List[tuple[Document, float]]:
        """异步带相似度分数的搜索"""
        return await asyncio.to_thread(
            self.search_with_score,
            query,
            collection_name,
            k,
        )
