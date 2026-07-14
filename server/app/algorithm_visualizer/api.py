"""算法可视化模块 API 路由。 

当前设计：
  GET  /algorithm-visualizer/languages   — 公开
  GET  /algorithm-visualizer/algorithms  — 公开
  GET  /algorithm-visualizer/templates   — 需认证，返回干净模板代码（无 tracer）
  POST /algorithm-visualizer/run         — 需认证，运行代码（自动插装 + 沙箱执行）

运行流程：
  1. 前端获取干净模板代码展示在编辑器
  2. 用户点击运行，提交代码
  3. 后端检测代码是否包含 tracer 调用
  4. 若无 tracer → LLM 自动插装 → 沙箱执行
  5. 若已有 tracer → 直接沙箱执行
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.algorithm_visualizer.events import record_visualizer_run_event
from app.algorithm_visualizer.schemas import (
    AlgorithmResponse,
    LanguageResponse,
    RunErrorResponse,
    RunRequest,
    RunSuccessResponse,
    TemplateResponse,
)
from app.algorithm_visualizer.service import (
    VisualizerRunError,
    run_visualization_in_sandbox,
)
from app.algorithm_visualizer.template_registry import (
    LANGUAGES,
    get_all_algorithms,
    get_algorithm_info,
    get_template_code,
    build_default_data,
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
    return HttpResponse.success(data=[LanguageResponse(**lang) for lang in LANGUAGES])


# 公开接口：按 domain / language 过滤并列出算法模板
@router.get("/algorithm-visualizer/algorithms")
async def get_algorithms(domain: str = "all", language: str | None = None):
    """获取算法模板列表。

    domain 默认 all。
    language 可选，用于前端在已选语言后过滤算法。
    """
    try:
        raw_algorithms = get_all_algorithms(domain)

        algorithms = []
        for alg in raw_algorithms:
            supported_languages = alg["supported_languages"]

            # 仅保留当前所选语言支持的算法
            if language and language not in supported_languages:
                continue

            alg_response = AlgorithmResponse(**alg)
            # 使用 by_alias=False 确保序列化时使用字段名（camelCase）
            algorithms.append(alg_response.model_dump(by_alias=False))

        return HttpResponse.success(data=algorithms)

    except Exception as e:
        return HttpResponse.error(code=400, message=str(e))


# 需认证接口：返回干净的模板代码及前端默认输入数据（不含 tracer 调用）
@router.get("/algorithm-visualizer/templates")
async def get_templates(
    algorithm: str,
    language: str,
    current_user: User = Depends(get_current_user),
):
    """获取算法可视化模板代码（干净代码，无 tracer 调用）。

    返回的代码是纯算法实现，不包含任何 tracer 调用。
    用户点击运行时，后端会自动插装 tracer 调用。
    """
    try:
        info = get_algorithm_info(algorithm)

        # 校验该算法是否支持请求的语言
        if language not in info["supported_languages"]:
            return HttpResponse.error(
                code=400,
                message=f"算法 {algorithm} 不支持语言 {language}",
            )

        code = get_template_code(algorithm, language)
        default_data = build_default_data(algorithm)

        payload = TemplateResponse(
            algorithm=algorithm,
            domain=info["domain"],
            visualizer_type=info["visualizer_type"],
            required_events=info.get("required_events", []),
            supported_languages=info["supported_languages"],
            language=language,
            template_code=code,
            default_data=default_data,
        )

        # 使用 by_alias=False 确保序列化时使用字段名（camelCase）而不是别名（snake_case）
        return HttpResponse.success(data=payload.model_dump(by_alias=False))

    except ValueError as ve:
        return HttpResponse.error(code=400, message=str(ve))
    except Exception as e:
        return HttpResponse.error(code=400, message=f"加载模板失败: {str(e)}")


# 需认证接口：运行提交的可视化代码（自动插装 tracer + 沙箱执行）
@router.post("/algorithm-visualizer/run")
async def run_visualization(
    request_data: RunRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """执行提交的可视化代码，返回 TraceEvent[]。

    如果代码不包含 tracer 调用，后端自动进行 LLM 插装。
    如果代码已包含 tracer 调用，直接执行。
    """
    algorithm = request_data.algorithm or ""
    language = request_data.language or ""

    vis_type = request_data.visualizerType or ""

    # 将 inputData dict 转换为 JSON 字符串传递给沙箱
    input_data_str = json.dumps(request_data.inputData) if request_data.inputData else None

    # 在沙箱中运行用户代码（缺失 tracer 时自动插装）
    try:
        result = await run_visualization_in_sandbox(
            language=language,
            code=request_data.code,
            algorithm=algorithm,
            visualizer_type=vis_type,
            domain=request_data.domain,
            input_data=input_data_str,
        )

    # 插装或执行失败，记录失败事件并返回错误
    except VisualizerRunError as e:
        await _safe_record_event(
            session,
            current_user.id,
            algorithm or "__missing_algorithm__",
            language or "__missing_language__",
            success=False,
            error_message=f"{e.error_type}: {e.message}",
        )

        return HttpResponse.error(
            code=400,
            message=e.message,
        )

    # 未预期异常，同样记录失败事件
    except Exception as e:
        await _safe_record_event(
            session,
            current_user.id,
            algorithm or "__missing_algorithm__",
            language or "__missing_language__",
            success=False,
            error_message=str(e),
        )

        return HttpResponse.error(
            code=400,
            message=str(e),
        )

    # 运行成功，记录成功事件
    await _safe_record_event(
        session,
        current_user.id,
        result["algorithm"],
        result["language"],
        success=True,
    )

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


# build_default_data 移至 template_registry.py

    return {}