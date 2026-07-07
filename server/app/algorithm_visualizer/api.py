"""算法可视化模块 API 路由。

提供 4 个独立端点：
  GET  /algorithm-visualizer/languages   — 公开
  GET  /algorithm-visualizer/algorithms  — 公开
  GET  /algorithm-visualizer/templates   — 需认证
  POST /algorithm-visualizer/run         — 需认证，成功/失败均记录 visualizer_run 事件
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.algorithm_visualizer.events import record_visualizer_run_event
from app.algorithm_visualizer.schemas import RunRequest
from app.algorithm_visualizer.service import run_visualization_in_sandbox
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
    return HttpResponse.success(data=LANGUAGES)


@router.get("/algorithm-visualizer/algorithms")
async def get_algorithms(domain: str = "data_structure"):
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
async def get_templates(
    algorithm: str,
    language: str,
    current_user: User = Depends(get_current_user),
):
    try:
        code = get_template_code(algorithm, language)
        info = get_algorithm_info(algorithm)

        default_data = {}
        # Sorting
        if algorithm in ("bubble_sort", "selection_sort", "insertion_sort", "shell_sort", "merge_sort", "heap_sort", "counting_sort", "bucket_sort", "radix_sort", "array_base", "double_pointers", "quick_partition", "merge_divide"):
            default_data = {"arr": [5, 3, 8, 1, 2]}
        # Searching & binary divide
        elif algorithm in ("binary_search", "sequential_search", "interpolation_search", "fibonacci_search", "binary_divide"):
            default_data = {"arr": [1, 2, 3, 5, 8], "target": 5}
        # Hash lookup
        elif algorithm in ("hash_search", "hash_table_base"):
            default_data = {"arr": [5, 3, 8, 1, 2], "target": 8}
        # Bracket matching / Palindrome
        elif algorithm in ("bracket_match", "palindrome_check", "interval_dp"):
            default_data = {"string": "({[]})"}
        # Queue / Stack Base / Monotonic stack/queue
        elif algorithm in ("queue_simulation", "queue_base", "stack_base", "monotonic_stack", "monotonic_queue"):
            default_data = {
                "operations": [
                    ["enqueue", 10], ["enqueue", 20],
                    ["dequeue", None], ["enqueue", 30],
                ],
            }
        # Linked List
        elif algorithm in ("linked_list_reverse", "linked_list_base"):
            default_data = {"arr": [1, 2, 3, 4, 5]}
        # Trees
        elif algorithm in ("binary_tree_traverse", "binary_tree_recursion", "bst", "heap_tree", "segment_tree", "fenwick_tree", "heap_base"):
            default_data = {"arr": [1, 2, 3, 4, 5, 6, 7]}
        # Graph / DFS / BFS / Shortest path / Topological sort / MST / DSU
        elif algorithm in ("graph_dfs", "graph_bfs", "graph_representation", "shortest_path", "topological_sort", "mst_kruskal", "dsu_union"):
            default_data = {"num_nodes": 6}
        # DP Fibonacci / Recursion fib / One d dp / Quick power / Prime sieve / Paschal triangle
        elif algorithm in ("dp_fibonacci", "recursion_fib", "one_d_dp", "basic_bit", "prime_sieve", "combination_num"):
            default_data = {"n": 6}
        # String match
        elif algorithm in ("string_match_naive", "kmp_match", "rabin_karp"):
            default_data = {"text": "abacaabadcabacaba", "pattern": "abacaba"}
        # Trie/Words
        elif algorithm in ("trie_tree", "trie_string_search"):
            default_data = {"words": ["cat", "car"]}
        # Permutations, subsets, combinations, subset_enum
        elif algorithm in ("permutations", "subsets", "combinations", "subset_enum", "xor_trick"):
            default_data = {"arr": [1, 2, 3]}
        # N-Queens / Maze
        elif algorithm == "n_queens":
            default_data = {"n": 4}
        elif algorithm == "maze_search":
            default_data = {"maze": [[0, 1, 0, 0], [0, 0, 0, 1], [1, 0, 1, 0], [0, 0, 0, 0]]}
        # Two D DP / Knapsack / TSP
        elif algorithm == "two_d_dp":
            default_data = {"grid": [[1, 3, 1], [1, 5, 1], [4, 2, 1]]}
        elif algorithm == "knapsack_dp":
            default_data = {"weights": [2, 3, 4, 5], "values": [3, 4, 5, 6], "capacity": 5}
        elif algorithm == "state_compress_dp":
            default_data = {"dist": [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]}
        # Sliding window
        elif algorithm == "sliding_window":
            default_data = {"arr": [1, 4, 2, 10, 2, 3, 1, 0, 20], "k": 4}
        # Difference array
        elif algorithm == "difference_array":
            default_data = {"arr": [1, 2, 3, 4, 5], "updates": [[1, 3, 2], [2, 4, 1]]}
        # Greedy
        elif algorithm == "interval_greedy":
            default_data = {"intervals": [[1, 2], [2, 3], [3, 4], [1, 3]]}
        elif algorithm == "stock_problem":
            default_data = {"prices": [7, 1, 5, 3, 6, 4]}
        elif algorithm == "jump_game":
            default_data = {"arr": [2, 3, 1, 1, 4]}
        elif algorithm == "huffman_coding":
            default_data = {"char_freqs": {"a": 5, "b": 9, "c": 12, "d": 13, "e": 16, "f": 45}}
        elif algorithm == "covering_problem":
            default_data = {"states_needed": ["mt", "wa", "or"], "stations": {"kone": ["id", "nv"], "ktwo": ["wa", "id"]}}
        # Hanoi
        elif algorithm == "recursive_divide":
            default_data = {"n": 3}
        # Bit mask
        elif algorithm == "bit_mask":
            default_data = {"state": 5, "mask": 2, "action": "set"}
        # Math
        elif algorithm == "gcd_euclidean":
            default_data = {"a": 48, "b": 18}
        elif algorithm == "quick_power":
            default_data = {"x": 2, "n": 10}
        elif algorithm == "mod_arithmetic":
            default_data = {"base": 2, "exp": 10, "mod": 1000}

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
async def run_visualization(
    request_data: RunRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """执行提交的代码，返回可视化步骤 TraceEvent[]。

    无论成功或失败都记录 ``visualizer_run`` 事件，失败时 error_message 写入 metadata。
    """
    vis_type = (
        request_data.visualizerType
        or request_data.visualizer_type
        or "array"
    )
    try:
        result = await run_visualization_in_sandbox(
            language=request_data.language,
            code=request_data.code,
            algorithm=request_data.algorithm,
            visualizer_type=vis_type,
            domain=request_data.domain,
        )
        if "visualizer_type" in result:
            result["visualizerType"] = result.pop("visualizer_type")
    except Exception as e:
        await _safe_record_event(
            session,
            current_user.id,
            request_data.algorithm,
            request_data.language,
            success=False,
            error_message=str(e),
        )
        return HttpResponse.error(code=400, message=str(e))

    await _safe_record_event(
        session,
        current_user.id,
        request_data.algorithm,
        request_data.language,
        success=True,
    )
    return HttpResponse.success(data=result)


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
