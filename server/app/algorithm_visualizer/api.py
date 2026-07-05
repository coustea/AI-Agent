from fastapi import APIRouter, Depends
from app.auth.security import get_current_user
from app.infra.models import User
from app.infra.response import HttpResponse
from app.algorithm_visualizer.schemas import AlgorithmGenerateRequest
from app.algorithm_visualizer.service import generate_visualization

router = APIRouter()

@router.post("/algorithm-visualizer/generate")
async def generate_alg_vis(
    request_data: AlgorithmGenerateRequest,
    current_user: User = Depends(get_current_user)
):
    """Executes code in sandbox and returns algorithm visualization steps."""
    payload = await generate_visualization(
        language=request_data.language,
        code=request_data.code,
        input_str=request_data.input
    )
    return HttpResponse.success(data=payload)
