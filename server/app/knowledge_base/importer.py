"""ChatDoc 知识库批量导入工具。

用于从本地文件夹批量导入文档到 ChatDoc 知识库。
支持增量更新，避免重复上传。

使用方式：
    # 命令行
    python -m app.knowledge_base.chatdoc.importer /path/to/knowledge

    # 代码调用
    from app.knowledge_base.chatdoc.importer import KnowledgeImporter

    importer = KnowledgeImporter()
    result = await importer.import_from_directory("/path/to/knowledge")
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.knowledge_base.client import ChatDocClient
from app.knowledge_base.service import ChatDocService

logger = get_logger(__name__)

# 支持的文档类型
SUPPORTED_EXTENSIONS = {
    # 文档类
    ".pdf", ".txt", ".md", ".doc", ".docx",
    ".ppt", ".pptx", ".xls", ".xlsx",
    ".csv", ".json", ".xml", ".html", ".htm",
}

# 排除的目录
EXCLUDED_DIRS = {
    "__pycache__", ".git", ".svn", ".hg",
    "node_modules", ".venv", "venv", ".env",
    "dist", "build", ".idea", ".vscode",
}


class KnowledgeImporter:
    """知识库批量导入器。

    功能：
    - 遍历文件夹下所有文档
    - 批量上传到 ChatDoc
    - 自动创建/更新全局知识库
    - 支持增量更新（基于文件 hash 去重）
    """

    def __init__(
        self,
        *,
        repo_name: str = "global_knowledge_base",
        repo_desc: str = "全局知识库",
    ):
        self.repo_name = repo_name
        self.repo_desc = repo_desc
        self._client: ChatDocClient | None = None
        self._repo_id: str | None = None
        self._imported_files: dict[str, dict[str, Any]] = {}  # file_path -> {file_id, hash}

    async def _ensure_client(self) -> ChatDocClient:
        """确保客户端可用。"""
        if self._client is None:
            service = ChatDocService.get_shared()
            self._client = await service._ensure_client()
        return self._client

    async def _ensure_repo(self) -> str:
        """确保知识库存在。"""
        if self._repo_id:
            return self._repo_id

        client = await self._ensure_client()

        # 查找现有知识库
        repos = await client.repo.list(name=self.repo_name)
        for repo in repos:
            if repo.repo_name == self.repo_name:
                self._repo_id = repo.repo_id
                logger.info("[Importer] 复用知识库 repo_id=%s", self._repo_id)
                return self._repo_id

        # 创建新知识库
        repo = await client.repo.create(name=self.repo_name, desc=self.repo_desc)
        self._repo_id = repo.repo_id
        logger.info("[Importer] 创建知识库 repo_id=%s", self._repo_id)
        return self._repo_id

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件 MD5 hash。"""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _should_import(self, file_path: Path) -> bool:
        """判断文件是否需要导入。"""
        # 检查扩展名
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return False

        # 检查文件大小（限制 50MB）
        if file_path.stat().st_size > 50 * 1024 * 1024:
            logger.warning("[Importer] 文件过大，跳过: %s", file_path)
            return False

        return True

    def _load_import_record(self, record_file: Path) -> dict[str, dict[str, Any]]:
        """加载导入记录。"""
        if record_file.exists():
            try:
                with open(record_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_import_record(self, record_file: Path, records: dict[str, dict[str, Any]]) -> None:
        """保存导入记录。"""
        record_file.parent.mkdir(parents=True, exist_ok=True)
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    async def import_from_directory(
        self,
        directory: str | Path,
        *,
        incremental: bool = True,
        record_file: str | Path | None = None,
        concurrency: int = 5,
    ) -> dict[str, Any]:
        """从目录批量导入文档。

        Args:
            directory: 文档目录路径
            incremental: 是否增量更新（跳过已导入的文件）
            record_file: 导入记录文件路径（默认为 directory/.chatdoc_import.json）
            concurrency: 并发上传数

        Returns:
            导入结果统计
        """
        directory = Path(directory).resolve()
        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        record_path = Path(record_file) if record_file else directory / ".chatdoc_import.json"

        # 加载历史记录
        imported_records = self._load_import_record(record_path) if incremental else {}

        # 确保知识库
        repo_id = await self._ensure_repo()
        client = await self._ensure_client()

        # 收集待导入文件
        files_to_import: list[tuple[Path, str]] = []  # (file_path, relative_path)
        skipped_count = 0

        for file_path in directory.rglob("*"):
            # 跳过排除目录
            if any(part in EXCLUDED_DIRS for part in file_path.parts):
                continue

            # 跳过记录文件
            if file_path.name == ".chatdoc_import.json":
                continue

            # 检查是否需要导入
            if not file_path.is_file() or not self._should_import(file_path):
                continue

            relative_path = str(file_path.relative_to(directory))

            # 增量更新检查
            if incremental and relative_path in imported_records:
                current_hash = self._calculate_file_hash(file_path)
                stored_hash = imported_records[relative_path].get("hash", "")

                if current_hash == stored_hash:
                    # 文件未变化，跳过
                    self._imported_files[relative_path] = imported_records[relative_path]
                    skipped_count += 1
                    continue

            files_to_import.append((file_path, relative_path))

        logger.info(
            "[Importer] 扫描完成 directory=%s total=%d to_import=%d skipped=%d",
            directory,
            len(files_to_import) + skipped_count,
            len(files_to_import),
            skipped_count,
        )

        # 并发上传
        success_count = 0
        failed_count = 0
        failed_files: list[str] = []
        semaphore = asyncio.Semaphore(concurrency)

        async def upload_file(file_path: Path, relative_path: str) -> tuple[str, dict[str, Any] | None]:
            """上传单个文件。"""
            async with semaphore:
                try:
                    file_hash = self._calculate_file_hash(file_path)

                    with open(file_path, "rb") as f:
                        result = await client.file.upload(
                            file=f,
                            filename=file_path.name,
                            file_type="wiki",
                        )

                    logger.info(
                        "[Importer] 上传成功 file=%s file_id=%s",
                        relative_path,
                        result.file_id,
                    )

                    return relative_path, {
                        "file_id": result.file_id,
                        "hash": file_hash,
                        "filename": file_path.name,
                    }

                except Exception as e:
                    logger.error("[Importer] 上传失败 file=%s error=%s", relative_path, e)
                    return relative_path, None

        # 执行上传
        if files_to_import:
            tasks = [upload_file(fp, rp) for fp, rp in files_to_import]
            results = await asyncio.gather(*tasks)

            for relative_path, record in results:
                if record:
                    self._imported_files[relative_path] = record
                    success_count += 1
                else:
                    failed_count += 1
                    failed_files.append(relative_path)

        # 将新文件加入知识库
        new_file_ids = [
            record["file_id"]
            for record in self._imported_files.values()
            if "file_id" in record
        ]

        if new_file_ids:
            try:
                await client.repo.add_files(repo_id, new_file_ids)
                logger.info("[Importer] 文件已加入知识库 repo_id=%s count=%d", repo_id, len(new_file_ids))
            except Exception as e:
                logger.error("[Importer] 加入知识库失败: %s", e)

        # 保存导入记录
        self._save_import_record(record_path, self._imported_files)

        # 触发文档处理（切分 + 向量化）
        if new_file_ids:
            try:
                await client.file.split(new_file_ids)
                await client.file.embedding(new_file_ids)
                logger.info("[Importer] 文档处理完成 count=%d", len(new_file_ids))
            except Exception as e:
                logger.warning("[Importer] 文档处理失败（可能后台自动处理）: %s", e)

        result = {
            "directory": str(directory),
            "repo_id": repo_id,
            "total_files": len(files_to_import) + skipped_count,
            "imported": success_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "failed_files": failed_files,
            "file_ids": new_file_ids,
        }

        logger.info(
            "[Importer] 导入完成 imported=%d skipped=%d failed=%d",
            success_count,
            skipped_count,
            failed_count,
        )

        return result

    async def get_import_status(self, file_ids: list[str]) -> list[dict[str, Any]]:
        """查询文档处理状态。"""
        client = await self._ensure_client()
        statuses = await client.file.get_status(file_ids)
        return [
            {
                "file_id": s.file_id,
                "file_name": s.file_name,
                "status": s.status,
                "status_desc": s.status_desc,
            }
            for s in statuses
        ]


async def main(directory: str) -> None:
    """命令行入口。"""
    import sys

    service = ChatDocService.get_shared()

    if not service.enabled:
        print("错误: ChatDoc 未启用，请检查配置")
        sys.exit(1)

    importer = KnowledgeImporter()
    result = await importer.import_from_directory(directory)

    print("\n导入结果:")
    print(f"  目录: {result['directory']}")
    print(f"  知识库 ID: {result['repo_id']}")
    print(f"  总文件数: {result['total_files']}")
    print(f"  新导入: {result['imported']}")
    print(f"  跳过(已存在): {result['skipped']}")
    print(f"  失败: {result['failed']}")

    if result['failed_files']:
        print("\n失败文件:")
        for f in result['failed_files']:
            print(f"  - {f}")

    # 查询处理状态
    if result['file_ids']:
        print("\n文档处理状态:")
        statuses = await importer.get_import_status(result['file_ids'])
        for s in statuses:
            status_text = {0: "处理中", 1: "成功", 2: "失败"}.get(s['status'], "未知")
            print(f"  {s['file_name']}: {status_text}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python -m app.knowledge_base.chatdoc.importer <目录路径>")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
