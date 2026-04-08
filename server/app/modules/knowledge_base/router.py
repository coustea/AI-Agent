"""
知识库管理 API 路由
"""
from fastapi import APIRouter, Depends, BackgroundTasks

from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.modules.knowledge_base.schemas import (
    KnowledgeImportRequest,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    SearchResult,
)
from app.modules.knowledge_base.service import KnowledgeBaseService

router = APIRouter()


@router.post("/import")
async def import_knowledge_base(
    req: KnowledgeImportRequest,
    background_tasks: BackgroundTasks,
    _user=Depends(get_current_user),
):
    """导入知识库到向量数据库（异步后台任务）"""

    def import_task():
        service = KnowledgeBaseService()
        result = service.import_knowledge_base(
            directory_path=req.directory_path,
            collection_name=req.collection_name,
        )
        # 这里可以添加任务完成后的通知逻辑
        return result

    # 添加到后台任务
    background_tasks.add_task(import_task)

    return HttpResponse.success(
        message="知识库导入任务已启动，正在后台处理",
        data={
            "directory_path": req.directory_path,
            "collection_name": req.collection_name,
        },
    )


@router.post("/import/sync")
async def import_knowledge_base_sync(
    req: KnowledgeImportRequest,
    _user=Depends(get_current_user),
):
    """同步导入知识库（阻塞式，适合小规模数据）"""
    service = KnowledgeBaseService()
    result = service.import_knowledge_base(
        directory_path=req.directory_path,
        collection_name=req.collection_name,
    )

    if result["success"]:
        return HttpResponse.success(message=result["message"], data=result["stats"])
    else:
        return HttpResponse.error(message=result["message"], code=500)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    req: KnowledgeSearchRequest,
    _user=Depends(get_current_user),
):
    """检索知识库"""
    service = KnowledgeBaseService()

    try:
        results = service.search_with_score(
            query=req.query,
            collection_name=req.collection_name,
            k=req.top_k,
        )

        search_results = [
            SearchResult(
                content=doc.page_content,
                metadata=doc.metadata,
                score=float(score),
            )
            for doc, score in results
        ]

        return KnowledgeSearchResponse(
            query=req.query,
            results=search_results,
            total=len(search_results),
        )

    except Exception as e:
        return HttpResponse.error(message=f"检索失败: {str(e)}", code=500)


@router.get("/collections")
async def list_collections(_user=Depends(get_current_user)):
    """列出所有知识库集合"""
    # 这里可以扩展为列出所有 Chroma 集合
    return HttpResponse.success(
        data={
            "collections": ["knowledge_base"],
            "default": "knowledge_base",
        }
    )
