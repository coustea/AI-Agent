"""Chat HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.bootstrap.container import AppContainer
from app.core.response import HttpResponse
from app.interface.http.dependencies import get_app_container, get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/chat/stream")
async def mentor_chat_stream(
    message: str = Form(...),
    session_id: str | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    container: AppContainer = Depends(get_app_container),
):
    effective_session = session_id or container.chat_usecases.default_session_id(current_user.id)
    image_urls: list[str] = []
    file_urls: list[str] = []

    for upload in files:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        content = await upload.read()
        try:
            saved = await container.chat_usecases.save_upload(
                filename=upload.filename,
                content=content,
                user_id=current_user.id,
                session_id=effective_session,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if saved["file_type"] == "image":
            image_urls.append(saved["url"])
        else:
            file_urls.append(saved["url"])

    return StreamingResponse(
        container.chat_usecases.stream_chat(
            user_id=current_user.id,
            user_message=message,
            session_id=effective_session,
            image_urls=image_urls or None,
            file_urls=file_urls or None,
        ),
        media_type="text/event-stream",
    )


@router.post("/chat/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    container: AppContainer = Depends(get_app_container),
):
    if not file.filename:
        return HttpResponse.error(code=400, message="文件名不能为空")
    content = await file.read()
    try:
        saved = await container.chat_usecases.save_upload(
            filename=file.filename,
            content=content,
            user_id=current_user.id,
            session_id=session_id,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=saved)


@router.get("/chat/uploads/{owner_id}/{session_id}/{filename}")
async def get_uploaded_file(
    owner_id: int,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    container: AppContainer = Depends(get_app_container),
):
    try:
        file_path = container.chat_usecases.resolve_uploaded_file(
            current_user_id=current_user.id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/sessions")
async def get_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    container: AppContainer = Depends(get_app_container),
):
    return HttpResponse.success(data=await container.chat_usecases.list_sessions(current_user.id, limit))


@router.post("/chat/sessions")
async def create_session(
    current_user: User = Depends(get_current_user),
    container: AppContainer = Depends(get_app_container),
):
    return HttpResponse.success(data=await container.chat_usecases.create_session(current_user.id))


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    container: AppContainer = Depends(get_app_container),
):
    success = await container.chat_usecases.archive_session(current_user.id, session_id)
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="会话已归档")


@router.get("/chat/history")
async def chat_history(
    session_id: str | None = Query(default=None, description="指定会话ID（不传则取最近会话）"),
    limit: int = Query(default=50, ge=1, le=200, description="返回的消息条数"),
    current_user: User = Depends(get_current_user),
    container: AppContainer = Depends(get_app_container),
):
    items = await container.chat_usecases.get_history(
        user_id=current_user.id,
        session_id=session_id,
        limit=limit,
    )
    return HttpResponse.success(data=[item.model_dump() for item in items])
