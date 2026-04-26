"""
Resource service — 资源生成全流程：持久化 + 编排 + SSE 推送。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine
from app.infra.models import (
    GeneratedResource,
    ResourceMindmap,
    ResourceContent,
    ResourceQuiz,
    ResourceReading,
    ResourceCode,
    ResourceMedia,
)
from app.infra.logging import get_logger
from app.resource.coordinator import CoordinatorAgent
from app.resource.events import AgentEventEmitter
from app.resource.utils import get_agent_registry

logger = get_logger(__name__)


def _file_url_from_result(result: dict | None, resource_id: int) -> str | None:
    """Convert an internal generated file path to the public resource file URL."""
    if not result:
        return None
    file_url = result.get("file_url")
    if isinstance(file_url, str) and file_url.strip():
        return file_url
    file_path = result.get("file_path")
    if not file_path:
        return None
    filename = Path(str(file_path)).name
    if not filename:
        return None
    return f"/api/v1/ai/resources/{resource_id}/files/{filename}"


class ResourceService:
    """GeneratedResource 持久化 CRUD。"""

    async def create_resource(
        self,
        user_id: int,
        course: str,
        gap: str,
        need: str = "review",
        request_extra: str | None = None,
    ) -> GeneratedResource:
        """创建资源主表记录，返回带有 id 的记录。"""
        async with AsyncSession(engine) as session:
            resource = GeneratedResource(
                user_id=user_id,
                course=course,
                gap=gap,
                need=need,
                request_extra=request_extra,
                status="pending",
            )
            session.add(resource)
            await session.commit()
            await session.refresh(resource)
            logger.info("[ResourceService] 主表记录已创建: user_id=%s resource_id=%s", user_id, resource.id)
            return resource

    async def update_resource_status(
        self,
        resource_id: int,
        status: str,
        plan_result: str | None = None,
    ) -> None:
        """更新资源主表状态。"""
        async with AsyncSession(engine) as session:
            resource = await session.get(GeneratedResource, resource_id)
            if resource:
                resource.status = status
                if plan_result:
                    resource.plan_result = plan_result
                await session.commit()
                logger.info("[ResourceService] 状态已更新: resource_id=%s status=%s", resource_id, status)

    async def save_mindmap(
        self,
        resource_id: int,
        file_path: str | None,
        content: str | None,
        status: str = "success",
        error: str | None = None,
    ) -> ResourceMindmap:
        """保存思维导图子表记录。"""
        async with AsyncSession(engine) as session:
            record = ResourceMindmap(
                resource_id=resource_id,
                file_path=file_path,
                content=content,
                status=status,
                error=error,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("[ResourceService] 思维导图已保存: resource_id=%s file=%s", resource_id, file_path)
            return record

    async def save_content(
        self,
        resource_id: int,
        file_path: str | None,
        content: str | None,
        status: str = "success",
        error: str | None = None,
    ) -> ResourceContent:
        """保存内容讲解子表记录。"""
        async with AsyncSession(engine) as session:
            record = ResourceContent(
                resource_id=resource_id,
                file_path=file_path,
                content=content,
                status=status,
                error=error,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("[ResourceService] 内容讲解已保存: resource_id=%s", resource_id)
            return record

    async def save_quiz(
        self,
        resource_id: int,
        file_path: str | None,
        content: str | None,
        status: str = "success",
        error: str | None = None,
    ) -> ResourceQuiz:
        """保存练习题子表记录。"""
        async with AsyncSession(engine) as session:
            record = ResourceQuiz(
                resource_id=resource_id,
                file_path=file_path,
                content=content,
                status=status,
                error=error,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("[ResourceService] 练习题已保存: resource_id=%s", resource_id)
            return record

    async def save_reading(
        self,
        resource_id: int,
        file_path: str | None,
        content: str | None,
        status: str = "success",
        error: str | None = None,
    ) -> ResourceReading:
        """保存延伸阅读子表记录。"""
        async with AsyncSession(engine) as session:
            record = ResourceReading(
                resource_id=resource_id,
                file_path=file_path,
                content=content,
                status=status,
                error=error,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("[ResourceService] 延伸阅读已保存: resource_id=%s", resource_id)
            return record

    async def save_code(
        self,
        resource_id: int,
        file_path: str | None,
        content: str | None,
        full_code: str | None = None,
        language: str | None = None,
        status: str = "success",
        error: str | None = None,
    ) -> ResourceCode:
        """保存代码实操子表记录。"""
        async with AsyncSession(engine) as session:
            record = ResourceCode(
                resource_id=resource_id,
                file_path=file_path,
                content=content,
                full_code=full_code,
                language=language,
                status=status,
                error=error,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("[ResourceService] 代码实操已保存: resource_id=%s language=%s", resource_id, language)
            return record

    async def save_media(
        self,
        resource_id: int,
        media_type: str,
        file_path: str | None,
        status: str = "success",
        error: str | None = None,
    ) -> ResourceMedia:
        """保存多模态资源子表记录。"""
        async with AsyncSession(engine) as session:
            record = ResourceMedia(
                resource_id=resource_id,
                media_type=media_type,
                file_path=file_path,
                status=status,
                error=error,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("[ResourceService] 多模态资源已保存: resource_id=%s type=%s file=%s", resource_id, media_type, file_path)
            return record

    async def persist_all_results(
        self,
        resource_id: int,
        results: dict,
    ) -> str:
        """异步保存所有 agent 结果到数据库，返回最终状态。"""
        def _get_content(result: dict | None) -> str | None:
            if not result:
                return None
            return result.get("markdown_content") or result.get("content") or json.dumps(result, ensure_ascii=False)

        # 文本类资源
        if "mindmap" in results:
            r = results["mindmap"]
            await self.save_mindmap(
                resource_id=resource_id,
                file_path=_file_url_from_result(r, resource_id),
                content=_get_content(r),
                status="success" if r.get("success") else "failed",
                error=r.get("error"),
            )

        if "content" in results:
            r = results["content"]
            await self.save_content(
                resource_id=resource_id,
                file_path=_file_url_from_result(r, resource_id),
                content=_get_content(r),
                status="success" if r.get("success") else "failed",
                error=r.get("error"),
            )

        if "quiz" in results:
            r = results["quiz"]
            await self.save_quiz(
                resource_id=resource_id,
                file_path=_file_url_from_result(r, resource_id),
                content=_get_content(r),
                status="success" if r.get("success") else "failed",
                error=r.get("error"),
            )

        if "reading" in results:
            r = results["reading"]
            await self.save_reading(
                resource_id=resource_id,
                file_path=_file_url_from_result(r, resource_id),
                content=_get_content(r),
                status="success" if r.get("success") else "failed",
                error=r.get("error"),
            )

        if "code" in results:
            r = results["code"]
            await self.save_code(
                resource_id=resource_id,
                file_path=_file_url_from_result(r, resource_id),
                content=_get_content(r),
                full_code=r.get("full_code"),
                language=r.get("detected_language"),
                status="success" if r.get("success") else "failed",
                error=r.get("error"),
            )

        # 多模态资源
        for media_type in ("ppt", "image", "video"):
            if media_type in results:
                r = results[media_type]
                await self.save_media(
                    resource_id=resource_id,
                    media_type=media_type,
                    file_path=_file_url_from_result(r, resource_id),
                    status="success" if r.get("success") else "failed",
                    error=r.get("error"),
                )

        # 计算最终状态
        successful_agents = [name for name, value in results.items() if value.get("success")]
        failed_agents = [name for name, value in results.items() if not value.get("success")]
        if failed_agents and successful_agents:
            status = "partial_success"
        elif failed_agents:
            status = "failed"
        else:
            status = "completed"

        await self.update_resource_status(resource_id, status)
        logger.info("[ResourceService] 资源包已入库: resource_id=%s status=%s agents=%s", resource_id, status, list(results.keys()))
        return status

    async def list_user_resources(
        self,
        session: AsyncSession,
        user_id: int,
        limit: int = 20,
    ) -> list[GeneratedResource]:
        """获取用户的资源列表。"""
        stmt = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(GeneratedResource.created_at.desc())
            .limit(limit)
        )
        result = await session.exec(stmt)
        return list(result.all())

    async def get_user_resource(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int,
    ) -> GeneratedResource | None:
        """获取单个资源记录。"""
        resource = await session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            return None
        return resource


class ResourceGenerationRuntime:
    """资源生成运行时：DAG 编排 + SSE 推送。"""

    def __init__(self, resource_svc: ResourceService) -> None:
        self.resource_svc = resource_svc

    def list_agents(self) -> list[dict]:
        """获取 agent 注册表。"""
        registry = get_agent_registry()
        return [
            {"id": name, "role": info.role, "desc": info.desc, "type": info.type}
            for name, info in registry.items()
        ]

    async def stream_bundle(
        self,
        *,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式生成资源包。"""
        logger.info(
            "[ResourceRuntime] 开始流式生成: user_id=%s course=%r selected_resources=%s",
            user_id,
            task.get("course", ""),
            selected_resources,
        )
        emitter = AgentEventEmitter()
        coordinator = CoordinatorAgent(emitter, self.resource_svc)

        async def run_and_cleanup() -> None:
            try:
                await coordinator.run(
                    user_id=user_id,
                    task=task,
                    selected_resources=selected_resources,
                )
            except Exception as exc:
                logger.error("[ResourceRuntime] 协调器执行异常: %s", exc, exc_info=exc)
                await emitter.emit_agent_status("system", "failed", str(exc))
                await emitter.emit_done("资源生成异常终止")
            finally:
                logger.info("[ResourceRuntime] 开始执行插件清理")
                await self._cleanup_plugins()

        runner = asyncio.create_task(run_and_cleanup())
        try:
            async for chunk in emitter.stream():
                yield chunk
        finally:
            logger.info("[ResourceRuntime] 等待后台协调任务收尾")
            await runner
            logger.info("[ResourceRuntime] 流式生成结束: user_id=%s", user_id)

    async def _cleanup_plugins(self) -> None:
        """清理插件资源。"""
        logger.info("[ResourceRuntime] 资源清理完成（统一注册表模式，无需关闭插件连接）")

    async def aclose(self) -> None:
        """关闭运行时。"""
        await self._cleanup_plugins()


class ResourceUseCases:
    """资源相关用例。"""

    def __init__(self, resource_svc: ResourceService, runtime: ResourceGenerationRuntime) -> None:
        self.resource_svc = resource_svc
        self.runtime = runtime

    async def stream_bundle(
        self,
        *,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ):
        """流式生成资源包。"""
        async for chunk in self.runtime.stream_bundle(
            user_id=user_id,
            task=task,
            selected_resources=selected_resources,
        ):
            yield chunk

    def list_agents(self) -> list[dict]:
        """获取 agent 列表。"""
        return self.runtime.list_agents()

    async def list_resources(self, session: AsyncSession, user_id: int, limit: int = 20):
        """获取用户资源列表。"""
        return await self.resource_svc.list_user_resources(session, user_id, limit)

    async def get_resource(self, session: AsyncSession, user_id: int, resource_id: int):
        """获取单个资源。"""
        return await self.resource_svc.get_user_resource(session, user_id, resource_id)


# 模块级单例
resource_service = ResourceService()
resource_runtime = ResourceGenerationRuntime(resource_service)
resource_usecases = ResourceUseCases(resource_service, resource_runtime)
