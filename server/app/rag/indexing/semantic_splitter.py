"""语义分块器 - 基于语义相似度进行文档切分。

语义分块不依赖固定的字符数或预设的分隔符，而是根据文本的语义内涵来切分。
核心思想：在语义主题发生显著变化的地方进行切分，使每个分块都具有高度的内部语义一致性。

实现原理：
1. 句子分割：将文本拆分成句子列表
2. 上下文感知嵌入：为每个句子及其上下文生成嵌入向量
3. 计算语义距离：计算相邻句子之间的余弦距离
4. 识别断点：根据统计方法识别语义断点
5. 合并成块：根据断点位置合并句子形成分块

断点识别方法：
- percentile（百分位法）：第95百分位的差异值作为阈值
- standard_deviation（标准差法）：平均值 + N × 标准差
- interquartile（四分位距法）：Q3 + N × IQR
- gradient（梯度法）：计算差异值的变化率，适合紧密文本

使用示例：
    from app.rag.indexing.semantic_splitter import SemanticSplitter

    splitter = SemanticSplitter(
        embedding_model="BAAI/bge-small-zh-v1.5",
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=95,
    )
    chunks = splitter.split_documents(documents)
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

try:
    from langchain_experimental.text_splitter import SemanticChunker
except ImportError:
    raise ImportError(
        "langchain-experimental is required for semantic chunking. "
        "Install it with: pip install langchain-experimental"
    )

from app.infra.logging import get_logger
# Import from new locations within the RAG package
from app.rag.indexing.embeddings import create_ollama_embeddings, get_embeddings as get_rag_embeddings
from app.rag.config import EMBEDDING_MODEL, OLLAMA_BASE_URL

logger = get_logger(__name__)


class SemanticSplitter:
    """语义分块器：基于语义相似度进行文档切分。

    相比传统的固定大小分块，语义分块能够：
    - 保持主题完整性：每个分块聚焦于单一语义主题
    - 避免语义切断：在语义变化处切分，而非固定位置
    - 提升检索精度：语义一致的分块检索更准确

    注意事项：
    - 计算成本较高：需要为每个句子生成嵌入向量
    - 不保护代码块：代码建议使用 MarkdownSplitter 或混合策略
    - 适合场景：理论性文档、学术论文、技术文档正文
    """

    def __init__(
        self,
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: float = 95,
        buffer_size: int = 1,
        device: str = "cpu",
    ):
        """初始化语义分块器。

        Args:
            embedding_model: 嵌入模型名称，推荐使用中文模型如 bge-small-zh-v1.5。
            breakpoint_threshold_type: 断点识别方法，可选：
                - percentile: 百分位法（默认，适合通用场景）
                - standard_deviation: 标准差法（适合语义跳跃明显的文本）
                - interquartile: 四分位距法（适合噪声较多的文本）
                - gradient: 梯度法（适合语义紧密的文本，如法律、医疗文档）
            breakpoint_threshold_amount: 断点阈值参数：
                - percentile: 第N百分位（默认95，表示最显著的5%作为断点）
                - standard_deviation: N倍标准差（默认3）
                - interquartile: N倍IQR（默认1.5）
                - gradient: 第N百分位（默认95）
            buffer_size: 上下文窗口大小（前后各N个句子），默认1。
            device: 计算设备，"cpu" 或 "cuda"。
        """
        self.embedding_model_name = embedding_model
        self.breakpoint_threshold_type = breakpoint_threshold_type
        self.breakpoint_threshold_amount = breakpoint_threshold_amount
        self.buffer_size = buffer_size
        self.device = device

        # 延迟加载嵌入模型
        self._embeddings = None
        self._semantic_chunker = None

    def _get_embeddings(self):
        """延迟加载嵌入模型。支持两种来源：

        1. HuggingFace 格式（如 BAAI/bge-m3, BAAI/bge-small-zh-v1.5）
        2. Ollama 格式（如 bge-m3，通过 langchain-ollama）
        """
        if self._embeddings is None:
            # 判断模型来源：如果包含 "/" 则为 HuggingFace，否则为 Ollama
            if "/" in self.embedding_model_name:
                # HuggingFace 格式
                try:
                    from langchain_community.embeddings import HuggingFaceEmbeddings

                    logger.info(
                        "[SemanticSplitter] Loading HuggingFace embedding model: %s",
                        self.embedding_model_name
                    )
                    self._embeddings = HuggingFaceEmbeddings(
                        model_name=self.embedding_model_name,
                        model_kwargs={"device": self.device},
                        encode_kwargs={"normalize_embeddings": True},
                    )
                    logger.info("[SemanticSplitter] Embedding model loaded successfully")
                except Exception as e:
                    logger.exception("[SemanticSplitter] Failed to load HuggingFace embedding model")
                    raise RuntimeError(
                        f"Failed to load HuggingFace embedding model {self.embedding_model_name}: {e}"
                    ) from e
            else:
                # Ollama 格式
                try:
                    logger.info(
                        "[SemanticSplitter] Loading Ollama embedding model: %s",
                        self.embedding_model_name
                    )
                    if self.embedding_model_name == EMBEDDING_MODEL:
                        self._embeddings = get_rag_embeddings()
                    else:
                        self._embeddings = create_ollama_embeddings(
                            self.embedding_model_name,
                            OLLAMA_BASE_URL,
                        )
                    logger.info("[SemanticSplitter] Embedding model loaded successfully")
                except Exception as e:
                    logger.exception("[SemanticSplitter] Failed to load Ollama embedding model")
                    raise RuntimeError(
                        f"Failed to load Ollama embedding model {self.embedding_model_name}: {e}"
                    ) from e
        return self._embeddings

    def _get_semantic_chunker(self) -> SemanticChunker:
        """获取语义分块器实例。"""
        if self._semantic_chunker is None:
            embeddings = self._get_embeddings()
            self._semantic_chunker = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type=self.breakpoint_threshold_type,
                breakpoint_threshold_amount=self.breakpoint_threshold_amount,
                buffer_size=self.buffer_size,
            )
        return self._semantic_chunker

    def split_text(self, text: str) -> list[str]:
        """切分单个文本。

        Args:
            text: 待切分的文本内容。

        Returns:
            切分后的文本块列表。
        """
        if not text or not text.strip():
            return []

        chunker = self._get_semantic_chunker()
        return chunker.split_text(text)

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """切分文档列表。

        Args:
            documents: 待切分的文档列表。

        Returns:
            切分后的文档块列表。
        """
        if not documents:
            return []

        chunker = self._get_semantic_chunker()

        logger.info(
            "[SemanticSplitter] Splitting %d documents with semantic chunking",
            len(documents)
        )

        try:
            chunks = chunker.split_documents(documents)

            # 为每个分块添加元数据
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = i
                chunk.metadata["splitter_type"] = "semantic"
                chunk.metadata["breakpoint_threshold_type"] = self.breakpoint_threshold_type

            logger.info(
                "[SemanticSplitter] Split into %d chunks",
                len(chunks)
            )

            return chunks

        except Exception as e:
            logger.exception("[SemanticSplitter] Failed to split documents")
            raise RuntimeError(f"Semantic chunking failed: {e}") from e


class HybridSplitter:
    """混合分块器：结构切分 + 语义优化。

    两阶段策略：
    1. 结构切分：使用 MarkdownSplitter 保护代码块和表格，按标题层级切分
    2. 语义优化：对过长的分块进行语义二次切分

    这种策略结合了两种方法的优势：
    - 保护代码块和表格的完整性（来自 MarkdownSplitter）
    - 在语义边界切分，保持主题完整性（来自 SemanticSplitter）

    适用场景：
    - 包含大量代码的技术文档
    - 需要精确控制分块大小的场景
    - 对语义完整性要求高的应用
    """

    def __init__(
        self,
        # 结构切分参数
        primary_heading: str = "##",
        secondary_heading: str = "###",
        max_size: int = 800,
        min_size: int = 100,
        overlap: int = 150,
        heading_in_body: bool = True,
        # 语义切分参数
        embedding_model: str = "bge-m3",  # 默认使用 bge-m3（与知识库一致）
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: float = 95,
        # 混合策略参数
        semantic_threshold: float = 1.5,  # 超过 max_size * threshold 才进行语义切分
    ):
        """初始化混合分块器。

        Args:
            primary_heading: 一级切分标题，默认 "##"。
            secondary_heading: 二级切分标题，默认 "###"。
            max_size: 最大分块大小，默认 800 字符。
            min_size: 最小分块大小（孤儿块阈值），默认 100 字符。
            overlap: 分块重叠字符数，默认 150。
            heading_in_body: 是否在分块中添加章节上下文，默认 True。
            embedding_model: 语义切分使用的嵌入模型。
                - "bge-m3" 或其他 Ollama 模型名称（使用本地 Ollama）
                - "BAAI/bge-m3" 或其他 HuggingFace 模型路径（自动下载）
            breakpoint_threshold_type: 语义断点识别方法。
            breakpoint_threshold_amount: 语义断点阈值。
            semantic_threshold: 语义切分阈值，超过 max_size * threshold 才进行语义切分。
        """
        # 延迟导入避免循环依赖
        from app.rag.indexing.markdown_splitter import MarkdownSplitter

        self.markdown_splitter = MarkdownSplitter(
            max_size=max_size,
            min_size=min_size,
            overlap=overlap,
            heading_in_body=heading_in_body,
            primary_heading=primary_heading,
            secondary_heading=secondary_heading,
        )

        self.semantic_splitter = SemanticSplitter(
            embedding_model=embedding_model,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )

        self.max_size = max_size
        self.semantic_threshold = semantic_threshold

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """混合切分文档列表。

        流程：
        1. 使用 MarkdownSplitter 进行结构切分
        2. 对过长的分块进行语义二次切分

        Args:
            documents: 待切分的文档列表。

        Returns:
            切分后的文档块列表。
        """
        if not documents:
            return []

        logger.info(
            "[HybridSplitter] Starting hybrid splitting for %d documents",
            len(documents)
        )

        # Step 1: 结构切分
        logger.info("[HybridSplitter] Stage 1: Structural splitting")
        structural_chunks = self.markdown_splitter.split_documents(documents)
        logger.info(
            "[HybridSplitter] Stage 1 completed: %d chunks",
            len(structural_chunks)
        )

        # Step 2: 语义优化（仅对超长块）
        semantic_threshold_size = int(self.max_size * self.semantic_threshold)
        long_chunks = [
            chunk for chunk in structural_chunks
            if len(chunk.page_content) > semantic_threshold_size
        ]

        if not long_chunks:
            logger.info(
                "[HybridSplitter] No chunks exceed threshold size (%d), skipping semantic splitting",
                semantic_threshold_size
            )
            return structural_chunks

        logger.info(
            "[HybridSplitter] Stage 2: Semantic splitting for %d long chunks (>%d chars)",
            len(long_chunks),
            semantic_threshold_size
        )

        final_chunks = []
        for chunk in structural_chunks:
            if len(chunk.page_content) > semantic_threshold_size:
                # 对超长块进行语义二次切分
                try:
                    semantic_subchunks = self.semantic_splitter.split_documents([chunk])

                    # 继承原始元数据
                    for subchunk in semantic_subchunks:
                        # 保留原始元数据（如 source, heading_path 等）
                        original_metadata = dict(chunk.metadata)
                        original_metadata["semantic_split"] = True
                        subchunk.metadata.update(original_metadata)

                    final_chunks.extend(semantic_subchunks)
                    logger.debug(
                        "[HybridSplitter] Split long chunk (%d chars) into %d semantic chunks",
                        len(chunk.page_content),
                        len(semantic_subchunks)
                    )
                except Exception as e:
                    logger.warning(
                        "[HybridSplitter] Semantic splitting failed, keeping original chunk: %s",
                        e
                    )
                    final_chunks.append(chunk)
            else:
                # 正常大小的块直接保留
                final_chunks.append(chunk)

        # 重新编号
        for i, chunk in enumerate(final_chunks):
            chunk.metadata["chunk_index"] = i

        logger.info(
            "[HybridSplitter] Completed: %d final chunks",
            len(final_chunks)
        )

        return final_chunks


def create_splitter(
    strategy: str = "hybrid",
    **kwargs,
) -> SemanticSplitter | HybridSplitter:
    """工厂函数：创建分块器实例。

    Args:
        strategy: 分块策略，可选：
            - "semantic": 纯语义分块
            - "hybrid": 混合分块（结构切分 + 语义优化）
            - "markdown": 纯结构分块（使用现有的 MarkdownSplitter）
        **kwargs: 传递给分块器的参数。

    Returns:
        分块器实例。

    Raises:
        ValueError: 未知的分块策略。
    """
    if strategy == "semantic":
        return SemanticSplitter(**kwargs)
    elif strategy == "hybrid":
        return HybridSplitter(**kwargs)
    elif strategy == "markdown":
        from app.rag.indexing.markdown_splitter import MarkdownSplitter
        return MarkdownSplitter(**kwargs)
    else:
        raise ValueError(
            f"Unknown splitting strategy: {strategy}. "
            f"Supported strategies: semantic, hybrid, markdown"
        )
