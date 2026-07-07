"""算法可视化模块 API 路由。

当前设计：
  GET  /algorithm-visualizer/languages   — 公开
  GET  /algorithm-visualizer/algorithms  — 公开
  GET  /algorithm-visualizer/templates   — 需认证，返回可视化模板代码
  POST /algorithm-visualizer/run         — 需认证，运行已包含 tracer 的代码

当前阶段不接入 LLM，不自动插装普通代码。
"""

from __future__ import annotations

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
)
from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


@router.get("/algorithm-visualizer/languages")
async def get_languages():
    return HttpResponse.success(data=[LanguageResponse(**lang) for lang in LANGUAGES])


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

            if language and language not in supported_languages:
                continue

            algorithms.append(AlgorithmResponse(**alg))

        return HttpResponse.success(data=algorithms)

    except Exception as e:
        return HttpResponse.error(code=400, message=str(e))


@router.get("/algorithm-visualizer/templates")
async def get_templates(
    algorithm: str,
    language: str,
    current_user: User = Depends(get_current_user),
):
    """获取算法可视化模板代码。

    注意：
    当前阶段要求用户基于该模板修改代码和数据。
    后端不会用 LLM 自动把普通代码转换为可视化代码。
    """
    try:
        info = get_algorithm_info(algorithm)

        if language not in info["supported_languages"]:
            return HttpResponse.error(
                code=400,
                message=f"算法 {algorithm} 不支持语言 {language}",
            )

        code = get_template_code(algorithm, language)
        default_data = build_default_data(algorithm)

        payload = TemplateResponse(
            **info,
            language=language,
            template_code=code,
            default_data=default_data,
        )

        return HttpResponse.success(data=payload)

    except ValueError as ve:
        return HttpResponse.error(code=400, message=str(ve))
    except Exception as e:
        return HttpResponse.error(code=400, message=f"加载模板失败: {str(e)}")


@router.post("/algorithm-visualizer/run")
async def run_visualization(
    request_data: RunRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """执行提交的可视化代码，返回 TraceEvent[]。

    当前阶段不接入 LLM。
    code 必须包含 tracer 调用，并生成 trace.json。
    """
    algorithm = request_data.algorithm or ""
    language = request_data.language or ""

    vis_type = request_data.visualizerType or ""

    try:
        result = await run_visualization_in_sandbox(
            language=language,
            code=request_data.code,
            algorithm=algorithm,
            visualizer_type=vis_type,
            domain=request_data.domain,
            input_data=request_data.inputData,
        )

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

    await _safe_record_event(
        session,
        current_user.id,
        result["algorithm"],
        result["language"],
        success=True,
    )

    return HttpResponse.success(data=RunSuccessResponse(**result))


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


def build_default_data(algorithm: str) -> dict:
    """根据算法模板返回前端默认数据。

    只用于前端展示或填充模板，不参与后端自动插装。
    """
    if algorithm in (
        "bubble_sort",
        "selection_sort",
        "insertion_sort",
        "shell_sort",
        "quick_sort",
        "merge_sort",
        "heap_sort",
        "counting_sort",
        "bucket_sort",
        "radix_sort",
        "array_base",
        "double_pointers",
        "quick_partition",
        "merge_divide",
    ):
        return {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]}

    if algorithm in (
        "binary_search",
        "sequential_search",
        "interpolation_search",
        "fibonacci_search",
        "binary_divide",
    ):
        return {"arr": [1, 2, 3, 5, 8], "target": 5}

    if algorithm in ("hash_search", "hash_table_base"):
        return {"arr": [5, 3, 8, 1, 2], "target": 8}

    if algorithm in ("bracket_match", "palindrome_check", "interval_dp"):
        return {"string": "({[]})"}

    if algorithm in (
        "queue_simulation",
        "queue_base",
        "stack_base",
        "monotonic_stack",
        "monotonic_queue",
    ):
        return {
            "operations": [
                ["enqueue", 10],
                ["enqueue", 20],
                ["dequeue", None],
                ["enqueue", 30],
            ],
        }

    if algorithm in ("linked_list_reverse", "linked_list_base"):
        return {"arr": [1, 2, 3, 4, 5]}

    if algorithm in (
        "binary_tree_traverse",
        "binary_tree_recursion",
        "bst",
        "heap_tree",
        "segment_tree",
        "fenwick_tree",
        "heap_base",
    ):
        return {"arr": [1, 2, 3, 4, 5, 6, 7]}

    if algorithm in (
        "graph_dfs",
        "graph_bfs",
        "graph_representation",
        "shortest_path",
        "topological_sort",
        "mst_kruskal",
        "dsu_union",
    ):
        return {
            "num_nodes": 6,
            "edges": [
                [0, 1],
                [0, 2],
                [1, 3],
                [1, 4],
                [2, 5],
            ],
            "start": 0,
        }

    if algorithm in (
        "dp_fibonacci",
        "recursion_fib",
        "one_d_dp",
        "basic_bit",
        "prime_sieve",
        "combination_num",
    ):
        return {"n": 6}

    if algorithm in ("string_match_naive", "kmp_match", "rabin_karp"):
        return {"text": "abacaabadcabacaba", "pattern": "abacaba"}

    if algorithm in ("trie_tree", "trie_string_search"):
        return {"words": ["cat", "car"]}

    if algorithm in (
        "permutations",
        "subsets",
        "combinations",
        "subset_enum",
        "xor_trick",
    ):
        return {"arr": [1, 2, 3]}

    if algorithm == "n_queens":
        return {"n": 4}

    if algorithm == "maze_search":
        return {
            "maze": [
                [0, 1, 0, 0],
                [0, 0, 0, 1],
                [1, 0, 1, 0],
                [0, 0, 0, 0],
            ],
        }

    if algorithm == "two_d_dp":
        return {"grid": [[1, 3, 1], [1, 5, 1], [4, 2, 1]]}

    if algorithm == "knapsack_dp":
        return {
            "weights": [2, 3, 4, 5],
            "values": [3, 4, 5, 6],
            "capacity": 5,
        }

    if algorithm == "state_compress_dp":
        return {
            "dist": [
                [0, 10, 15, 20],
                [10, 0, 35, 25],
                [15, 35, 0, 30],
                [20, 25, 30, 0],
            ],
        }

    if algorithm == "sliding_window":
        return {"arr": [1, 4, 2, 10, 2, 3, 1, 0, 20], "k": 4}

    if algorithm == "difference_array":
        return {"arr": [1, 2, 3, 4, 5], "updates": [[1, 3, 2], [2, 4, 1]]}

    if algorithm == "interval_greedy":
        return {"intervals": [[1, 2], [2, 3], [3, 4], [1, 3]]}

    if algorithm == "stock_problem":
        return {"prices": [7, 1, 5, 3, 6, 4]}

    if algorithm == "jump_game":
        return {"arr": [2, 3, 1, 1, 4]}

    if algorithm == "huffman_coding":
        return {
            "char_freqs": {
                "a": 5,
                "b": 9,
                "c": 12,
                "d": 13,
                "e": 16,
                "f": 45,
            },
        }

    if algorithm == "covering_problem":
        return {
            "states_needed": ["mt", "wa", "or"],
            "stations": {
                "kone": ["id", "nv"],
                "ktwo": ["wa", "id"],
            },
        }

    if algorithm == "recursive_divide":
        return {"n": 3}

    if algorithm == "bit_mask":
        return {"state": 5, "mask": 2, "action": "set"}

    if algorithm == "gcd_euclidean":
        return {"a": 48, "b": 18}

    if algorithm == "quick_power":
        return {"x": 2, "n": 10}

    if algorithm == "mod_arithmetic":
        return {"base": 2, "exp": 10, "mod": 1000}

    return {}
