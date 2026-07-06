"""算法可视化模块 API 路由。

提供 4 个独立端点，不依赖用户认证：
  GET  /algorithm-visualizer/languages
  GET  /algorithm-visualizer/algorithms
  GET  /algorithm-visualizer/templates
  POST /algorithm-visualizer/run
"""

from __future__ import annotations

from fastapi import APIRouter

from app.infra.response import HttpResponse
from app.algorithm_visualizer.schemas import RunRequest
from app.algorithm_visualizer.service import run_visualization_in_sandbox
from app.algorithm_visualizer.template_registry import (
    LANGUAGES,
    get_all_algorithms,
    get_template_code,
    get_algorithm_info,
)

router = APIRouter()


@router.get("/algorithm-visualizer/languages")
async def get_languages():
    """获取支持的代码语言列表。"""
    return HttpResponse.success(data=LANGUAGES)


@router.get("/algorithm-visualizer/algorithms")
async def get_algorithms(domain: str = "data_structure"):
    """获取算法列表。"""
    try:
        raw_algorithms = get_all_algorithms(domain)
        algorithms = []
        for alg in raw_algorithms:
            algorithms.append({
                "key": alg["key"],
                "name": alg["name"],
                "domain": alg["domain"],
                "visualizerType": alg["visualizer_type"],
                "difficulty": alg["difficulty"],
                "supportedLanguages": alg["supported_languages"],
            })
        return HttpResponse.success(data=algorithms)
    except Exception as e:
        return HttpResponse.error(code=400, message=str(e))


@router.get("/algorithm-visualizer/templates")
async def get_templates(algorithm: str, language: str):
    """获取指定算法和语言的代码模板。"""
    try:
        code = get_template_code(algorithm, language)
        info = get_algorithm_info(algorithm)

        # 定义各类算法的默认初始数据结构
        default_data = {}
        if algorithm in ("bubble_sort", "selection_sort", "insertion_sort"):
            default_data = {"arr": [5, 3, 8, 1, 2]}
        elif algorithm == "binary_search":
            default_data = {"arr": [1, 2, 3, 5, 8], "target": 5}
        elif algorithm == "bracket_match":
            default_data = {"string": "({[]})"}
        elif algorithm == "queue_simulation":
            default_data = {
                "operations": [
                    ["enqueue", 10], ["enqueue", 20],
                    ["dequeue", None], ["enqueue", 30],
                ],
            }

        payload = {
            "domain": info["domain"],
            "algorithm": algorithm,
            "visualizerType": info["visualizer_type"],
            "language": language,
            "templateCode": code,
            "defaultData": default_data,
        }
        return HttpResponse.success(data=payload)
    except ValueError as ve:
        return HttpResponse.error(code=400, message=str(ve))
    except Exception as e:
        return HttpResponse.error(code=400, message=f"加载模板失败: {str(e)}")


@router.post("/algorithm-visualizer/run")
async def run_visualization(request_data: RunRequest):
    """执行提交的代码，返回可视化步骤 TraceEvent[]。"""
    try:
        vis_type = (
            request_data.visualizerType
            or request_data.visualizer_type
            or "array"
        )
        result = await run_visualization_in_sandbox(
            language=request_data.language,
            code=request_data.code,
            algorithm=request_data.algorithm,
            visualizer_type=vis_type,
            domain=request_data.domain,
        )
        # 兼容前端驼峰命名
        if "visualizer_type" in result:
            result["visualizerType"] = result.pop("visualizer_type")
        return HttpResponse.success(data=result)
    except Exception as e:
        return HttpResponse.error(code=400, message=str(e))
