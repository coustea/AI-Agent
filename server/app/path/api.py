from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import bg_apply_profile_update_from_learning_event
from app.infra.database import get_session
from app.infra.models import PathNode, PathNodeResource, User
from app.infra.response import HttpResponse
from app.path.schemas import (
    AuxiliaryResourceRequest,
    CreateLearningPathRequest,
    LearningPathResourceDTO,
    PathQuizSubmitRequest,
)
from app.path.service import PathService, build_learning_event_item

router = APIRouter(prefix="/path-plan", tags=["AI Path Planning"])


@router.post("")
async def create_path(
    request: CreateLearningPathRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    path_id = await service.init_path_task(current_user.id, request)
    background_tasks.add_task(
        _run_generation_bg,
        user_id=current_user.id,
        path_id=path_id,
        request=request,
    )
    return HttpResponse.success(data={"id": path_id, "status": "generating"}, status_code=201)


@router.get("/{path_id}/events")
async def stream_path_events(
    path_id: int,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    from fastapi.responses import StreamingResponse
    from app.path.events import path_event_bus
    import asyncio

    service = PathService(session)
    try:
        await service.get_path_by_id(current_user.id, path_id)
    except ValueError as exc:
        return HttpResponse.error(code=404, message=str(exc))

    async def event_stream():
        queue = path_event_bus.subscribe(path_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield f": heartbeat\n\n"
                    continue
                data = event.model_dump_json()
                yield f"event: {event.event_type}\ndata: {data}\n\n"
                if event.event_type == "path.done":
                    break
        finally:
            path_event_bus.unsubscribe(path_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/active")
async def get_active_path(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    response = await service.get_active_path_overview(current_user.id, module)
    return HttpResponse.success(data=response.model_dump(mode="json") if response else None)


@router.get("/history")
async def get_path_history(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    items = await service.list_path_history(current_user.id, module)
    return HttpResponse.success(data=[item.model_dump(mode="json") for item in items])


@router.post("/{path_id}/activate")
async def activate_history_path(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
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
    service = PathService(session)
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
    service = PathService(session)
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
    service = PathService(session)
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
    service = PathService(session)
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
    stmt = (
        select(PathNodeResource)
        .where(PathNodeResource.user_id == current_user.id)
        .order_by(col(PathNodeResource.created_at).desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list((await session.exec(stmt)).all())
    node_map: dict[int, PathNode] = {}
    if rows:
        node_ids = {row.node_id for row in rows}
        node_rows = list((await session.exec(select(PathNode).where(PathNode.id.in_(node_ids)))).all())
        node_map = {node.id: node for node in node_rows if node.id is not None}
    total_stmt = select(PathNodeResource).where(PathNodeResource.user_id == current_user.id)
    total = len(list((await session.exec(total_stmt)).all()))
    return HttpResponse.success(data={
        "items": [
            {
                "id": row.id,
                "learning_need": row.title,
                "status": "completed",
                "resource_types": [row.resource_type],
                "resource_type": row.resource_type,
                "title": row.title,
                "path_id": row.path_id,
                "path_node_id": row.node_id,
                "node_id": node_map.get(row.node_id).node_id if node_map.get(row.node_id) else None,
                "node_title": node_map.get(row.node_id).title if node_map.get(row.node_id) else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ],
        "total": total,
    })


@router.get("/resources/{resource_id}")
async def get_path_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    resource = await session.get(PathNodeResource, resource_id)
    if resource is None or resource.user_id != current_user.id:
        return HttpResponse.error(code=404, message="路径资源不存在")
    return HttpResponse.success(data=LearningPathResourceDTO.from_model(resource).model_dump(mode="json"))


@router.get("/{path_id}")
async def get_path_by_id(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
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
    service = PathService(session)
    try:
        event, profile_payload = await service.record_learning_event(current_user.id, path_id, payload)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    background_tasks.add_task(
        bg_apply_profile_update_from_learning_event,
        current_user.id,
        profile_payload,
    )
    return HttpResponse.success(data=build_learning_event_item(event).model_dump(mode="json"))


@router.get("/{path_id}/evaluation")
async def get_path_learning_evaluation(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        evaluation = await service.get_learning_evaluation(current_user.id, path_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=evaluation.model_dump(mode="json") if evaluation else None)


# ── Background task wrapper ──────────────────────────────────────────────────

async def _run_generation_bg(user_id: int, path_id: int, request: CreateLearningPathRequest):
    from app.path.service import run_generation_bg
    await run_generation_bg(user_id, path_id, request)
