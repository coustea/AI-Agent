"""算法可视化模块 API 路由。

当前设计只支持已注册的 Python 算法模板：
  GET  /algorithm-visualizer/templates                    — 公开目录
  GET  /algorithm-visualizer/templates/{template_key}     — 需认证详情
  POST /algorithm-visualizer/templates/{template_key}/runs — 需认证运行
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.algorithm_visualizer.events import record_visualizer_run_event
from app.algorithm_visualizer.schemas import (
    RunRequest,
    RunSuccessResponse,
    TemplateDetailResponse,
    TemplateSummaryResponse,
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


# 公开接口：列出受信、可视化的算法模板。
@router.get("/algorithm-visualizer/templates")
async def get_templates():
    """Return the authoritative official-template catalogue."""
    try:
        templates = [
            TemplateSummaryResponse(
                key=spec.key,
                name=spec.name,
                domain=spec.domain,
                visualizer_type=spec.visualizer_type,
                difficulty=spec.difficulty,
            ).model_dump(by_alias=False)
            for spec in get_all_template_specs()
        ]
        return HttpResponse.success(data=templates)

    except Exception as e:
        return HttpResponse.error(code=400, message=str(e))


# 需认证接口：返回一个模板的真实源码及输入契约。
@router.get("/algorithm-visualizer/templates/{template_key}")
async def get_template(
    template_key: str,
    current_user: User = Depends(get_current_user),
):
    """获取官方算法模板源码和其输入契约。"""
    try:
        spec = get_template_spec(template_key)
        payload = TemplateDetailResponse(
            key=spec.key,
            name=spec.name,
            domain=spec.domain,
            visualizer_type=spec.visualizer_type,
            difficulty=spec.difficulty,
            version=spec.version,
            template_code=spec.source_code,
            default_data=spec.default_input,
            input_schema=spec.input_schema,
        )

        return HttpResponse.success(data=payload.model_dump(by_alias=False))

    except TemplateNotFoundError as ve:
        return HttpResponse.error(code=400, message=str(ve))
    except Exception as e:
        return HttpResponse.error(code=400, message=f"加载模板失败: {str(e)}")


# 需认证接口：运行一个注册模板。
@router.post("/algorithm-visualizer/templates/{template_key}/runs")
async def run_visualization(
    template_key: str,
    request_data: RunRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """运行注册的官方模板。"""
    logger.info("[Visualizer] 运行官方模板: user_id=%s template=%s", current_user.id, template_key)

    try:
        result = run_official_visualization(
            template_key=template_key,
            input_data=request_data.inputData,
        )

    # 插装或执行失败，记录失败事件并返回错误
    except VisualizerRunError as e:
        logger.warning("[Visualizer] 运行失败: user_id=%s template=%s error_type=%s", current_user.id, template_key, e.error_type)
        await _safe_record_event(
            session,
            current_user.id,
            template_key,
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
            template_key,
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
        result["templateKey"],
        success=True,
    )

    logger.info("[Visualizer] 运行成功: user_id=%s template=%s", current_user.id, result["templateKey"])
    # 使用 by_alias=False 确保序列化时使用字段名（camelCase）
    return HttpResponse.success(data=RunSuccessResponse(**result).model_dump(by_alias=False))


# 安全地记录可视化运行事件：埋点异常时仅告警，不影响主流程
async def _safe_record_event(
    session: AsyncSession,
    user_id: int,
    template_key: str,
    *,
    success: bool,
    error_message: str | None = None,
) -> None:
    try:
        await record_visualizer_run_event(
            session,
            user_id=user_id,
            template_key=template_key,
            success=success,
            error_message=error_message,
        )
    except Exception as event_exc:
        logger.warning(
            "[Visualizer] event record failed: user_id=%s template=%s err=%s",
            user_id,
            template_key,
            event_exc,
        )
