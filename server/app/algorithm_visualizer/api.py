"""算法可视化模块 API 路由。

当前设计：
  GET  /algorithm-visualizer/languages   — 公开
  GET  /algorithm-visualizer/algorithms  — 公开
  GET  /algorithm-visualizer/templates   — 需认证，返回官方模板源码与默认输入
  POST /algorithm-visualizer/run         — 需认证，运行官方模板
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.algorithm_visualizer.events import record_visualizer_run_event
from app.algorithm_visualizer.schemas import (
    AlgorithmResponse,
    LanguageResponse,
    RunRequest,
    RunSuccessResponse,
    TemplateResponse,
)
from app.algorithm_visualizer.service import (
    VisualizerRunError,
    run_official_visualization,
)
from app.algorithm_visualizer.template_registry import (
    TemplateNotFoundError,
    get_all_template_specs,
    get_template_spec,
)
from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse

# 算法可视化模块的 API 路由与日志实例
router = APIRouter()
logger = get_logger(__name__)


# 公开接口：返回所有支持的可视化编程语言列表
@router.get("/algorithm-visualizer/languages")
async def get_languages():
    return HttpResponse.success(data=[LanguageResponse(key="python", label="Python", extension="py")])


# 公开接口：按 domain / language 过滤并列出算法模板
@router.get("/algorithm-visualizer/algorithms")
async def get_algorithms(domain: str = "all", language: str | None = None):
    """获取算法模板列表。

    domain 默认 all。
    language 可选，用于前端在已选语言后过滤算法。
    """
    try:
        specs = get_all_template_specs()
        algorithms = []
        for spec in specs:
            if domain != "all" and spec.domain != domain:
                continue
            # Only Python is supported now.
            if language and language != "python":
                continue

            alg_response = AlgorithmResponse(
                key=spec.key,
                name=spec.name,
                domain=spec.domain,
                visualizer_type=spec.visualizer_type,
                difficulty=spec.difficulty,
                supported_languages=["python"],
            )
            algorithms.append(alg_response.model_dump(by_alias=False))

        return HttpResponse.success(data=algorithms)

    except Exception as e:
        return HttpResponse.error(code=400, message=str(e))


# 需认证接口：返回官方模板源码及前端默认输入数据
@router.get("/algorithm-visualizer/templates")
async def get_templates(
    algorithm: str,
    language: str,
    current_user: User = Depends(get_current_user),
):
    """获取官方算法模板源码和其输入契约。"""
    try:
        spec = get_template_spec(algorithm)

        if language != "python":
            return HttpResponse.error(
                code=400,
                message=f"算法 {algorithm} 不支持语言 {language}",
            )

        payload = TemplateResponse(
            algorithm=algorithm,
            domain=spec.domain,
            visualizer_type=spec.visualizer_type,
            language="python",
            template_code=spec.source_code,
            default_data=spec.default_input,
            input_schema=spec.input_schema,
        )

        return HttpResponse.success(data=payload.model_dump(by_alias=False))

    except TemplateNotFoundError as ve:
        return HttpResponse.error(code=400, message=str(ve))
    except Exception as e:
        return HttpResponse.error(code=400, message=f"加载模板失败: {str(e)}")


# 需认证接口：运行注册算法模板
@router.post("/algorithm-visualizer/run")
async def run_visualization(
    request_data: RunRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """运行注册的官方模板。"""
    algorithm = request_data.algorithm
    language = request_data.language
    logger.info("[Visualizer] 运行官方模板: user_id=%s algorithm=%s", current_user.id, algorithm)

    try:
        result = run_official_visualization(
            algorithm=algorithm,
            language=language,
            input_data=request_data.inputData,
        )

    # 插装或执行失败，记录失败事件并返回错误
    except VisualizerRunError as e:
        logger.warning("[Visualizer] 运行失败: user_id=%s algorithm=%s error_type=%s", current_user.id, algorithm, e.error_type)
        await _safe_record_event(
            session,
            current_user.id,
            algorithm,
            language,
            success=False,
            error_message=f"{e.error_type}: {e.message}",
        )

        return HttpResponse.error(
            code=400,
            message=e.message,
            data={"errorType": e.error_type},
        )

    # 未预期异常，同样记录失败事件
    except Exception as e:
        await _safe_record_event(
            session,
            current_user.id,
            algorithm,
            language,
            success=False,
            error_message=str(e),
        )

        return HttpResponse.error(
            code=400,
            message=str(e),
            data={"errorType": "VISUALIZER_RUN_ERROR"},
        )

    # 运行成功，记录成功事件
    await _safe_record_event(
        session,
        current_user.id,
        result["algorithm"],
        result["language"],
        success=True,
    )

    logger.info("[Visualizer] 运行成功: user_id=%s algorithm=%s", current_user.id, result["algorithm"])
    # 使用 by_alias=False 确保序列化时使用字段名（camelCase）
    return HttpResponse.success(data=RunSuccessResponse(**result).model_dump(by_alias=False))


# 安全地记录可视化运行事件：埋点异常时仅告警，不影响主流程
async def _safe_record_event(
    session: AsyncSession,
    user_id: int,
    algorithm: str,
    language: str,
    *,
    success: bool,
    error_message: str | None = None,
) -> None:
    try:
        await record_visualizer_run_event(
            session,
            user_id=user_id,
            algorithm=algorithm,
            language=language,
            success=success,
            error_message=error_message,
        )
    except Exception as event_exc:
        logger.warning(
            "[Visualizer] event record failed: user_id=%s algorithm=%s err=%s",
            user_id,
            algorithm,
            event_exc,
        )
