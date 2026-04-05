import asyncio  # ⭐ 引入 asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.core.security import get_current_user
from app.models.user import User
from app.modules.profile_builder.chat_agent import ChatAgent
from app.modules.profile_builder.profile_agent import ProfileBuilderAgent
from app.modules.memory.service import memory_service
from app.modules.profile_builder.schema import ChatRequest

router = APIRouter()


@router.post("/chat/stream")
async def chat_stream_endpoint(
        req: ChatRequest,
        current_user: User = Depends(get_current_user)
):
    chat_agent = ChatAgent()
    generator = chat_agent.chat_stream(user_id=current_user.id, user_message=req.message)

    msg_count = memory_service.get_message_count(
        user_id=current_user.id,
        session_id=chat_agent.global_session_id,
        module=chat_agent.module_name
    )

    THRESHOLD = 20
    if msg_count > 0 and msg_count % THRESHOLD == 0:
        profile_agent = ProfileBuilderAgent()
        asyncio.create_task(profile_agent.build_profile(user_id=current_user.id))

    return StreamingResponse(generator, media_type="text/event-stream")