from fastapi import APIRouter
from controller.chat_controller import chat, chat_stream
from utils.schemas import ChatResponse

# Create a main router
router = APIRouter(prefix="/api")

# 注册路由
router.add_api_route("/chat", chat, methods=["POST"], tags=["chat"], response_model=ChatResponse)
router.add_api_route("/chat/stream", chat_stream, methods=["POST"], tags=["chat"])
