from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.evaluation.response import LearningEventItem
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import bg_apply_profile_update_from_learning_event
from app.infra.database import get_session
from app.infra.models import LearningEvent, User
from app.infra.response import HttpResponse
from app.path.schemas import (
    AuxiliaryResourceRequest,
    CreateLearningPathRequest,
    PathQuizSubmitRequest,
)
from app.path.service import LearningPathService

router = APIRouter(prefix="/path-plan", tags=["AI Path Planning"])


def _build_learning_event_item(event: LearningEvent) -> LearningEventItem:
    return LearningEventItem(
        id=event.id or 0,
        event_type=event.event_type,
        resource_id=event.resource_id,
        resource_item_id=event.resource_item_id,
        path_id=event.path_id,
        path_node_id=event.path_node_id,
        node_id=event.node_id,
        course=event.course,
        topic=event.topic,
        score=event.score,
        feedback=event.feedback,
        created_at=event.created_at,
    )


@router.post("")
async def create_path(
    request: CreateLearningPathRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    result = await service.create_path(current_user.id, request)
    return HttpResponse.success(data=result.model_dump(mode="json"), status_code=201)


@router.get("/active")
async def get_active_path(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    response = await service.get_active_path_overview(current_user.id, module)
    return HttpResponse.success(data=response.model_dump(mode="json") if response else None)


@router.get("/history")
async def get_path_history(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    items = await service.list_path_history(current_user.id, module)
    return HttpResponse.success(data=[item.model_dump(mode="json") for item in items])


@router.post("/{path_id}/activate")
async def activate_history_path(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    try:
        result = await service.activate_history_path(current_user.id, path_id)
    except ValueError as exc:
        return HttpResponse.error(code=404, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.get("/nodes/{node_id}/workspace")
async def get_node_workspace(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    try:
        result = await service.get_node_workspace(current_user.id, node_id)
    except ValueError as exc:
        return HttpResponse.error(code=404, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.post("/nodes/{node_id}/questions")
async def generate_node_questions(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    try:
        result = await service.generate_node_questions(current_user.id, node_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.post("/nodes/{node_id}/quiz-submit")
async def submit_node_quiz(
    node_id: int,
    payload: PathQuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    try:
        result = await service.submit_node_quiz(current_user.id, node_id, payload)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.post("/nodes/{node_id}/resources")
async def generate_node_resource(
    node_id: int,
    payload: AuxiliaryResourceRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    try:
        result = await service.generate_node_resource(current_user.id, node_id, payload)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.get("/resources")
async def list_path_resources(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await LearningPathService(session).list_path_resources(current_user.id, limit, offset)
    return HttpResponse.success(data=result)


@router.get("/resources/{resource_id}")
async def get_path_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await LearningPathService(session).get_path_resource_bundle(current_user.id, resource_id)
    if result is None:
        return HttpResponse.error(code=404, message="路径资源不存在")
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.get("/{path_id}")
async def get_path_by_id(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    try:
        response = await service.get_path_by_id(current_user.id, path_id)
    except ValueError as exc:
        return HttpResponse.error(code=404, message=str(exc))
    return HttpResponse.success(data=response.model_dump(mode="json"))


@router.post("/{path_id}/events")
async def record_path_learning_event(
    path_id: int,
    payload: LearningEventCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    try:
        event = await service.record_learning_event(current_user.id, path_id, payload)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    background_tasks.add_task(
        bg_apply_profile_update_from_learning_event,
        current_user.id,
        {
            "event_type": event.event_type,
            "session_id": event.session_id,
            "resource_id": event.resource_id,
            "resource_item_id": event.resource_item_id,
            "path_id": event.path_id,
            "path_node_id": event.path_node_id,
            "node_id": event.node_id,
            "course": event.course,
            "topic": event.topic,
            "score": event.score,
            "feedback": event.feedback,
            "metadata": event.metadata_json or {},
        },
    )
    return HttpResponse.success(data=_build_learning_event_item(event).model_dump(mode="json"))


@router.get("/{path_id}/evaluation")
async def get_path_learning_evaluation(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = LearningPathService(session)
    try:
        evaluation = await service.get_learning_evaluation(current_user.id, path_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=evaluation.model_dump(mode="json") if evaluation else None)
