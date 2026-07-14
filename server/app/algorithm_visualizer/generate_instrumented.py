"""批量生成 python_instrumented.py 文件。

从 instrumentation_cache.json 提取已插装的代码，
为每个算法模板目录创建预插装版本。
"""

import json
import hashlib
from pathlib import Path

# 缓存文件路径
CACHE_FILE = Path(__file__).parent / "instrumentation_cache.json"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Tracer 导入模板
TRACER_IMPORTS = {
    "array": "from visual_tracer import ArrayTracer\ntracer = ArrayTracer()\n",
    "stack-queue": "from visual_tracer import StackTracer, QueueTracer\ntracer = StackTracer()  # 或 QueueTracer()\n",
    "linked-list": "from visual_tracer import LinkedListTracer\ntracer = LinkedListTracer()\n",
    "tree": "from visual_tracer import TreeTracer\ntracer = TreeTracer()\n",
    "graph": "from visual_tracer import GraphTracer\ntracer = GraphTracer()\n",
    "dp-table": "from visual_tracer import DpTableTracer\ntracer = DpTableTracer()\n",
}


def compute_hash(code: str, visualizer_type: str, required_events: list) -> str:
    raw = f"{code}\0{visualizer_type}\0{','.join(sorted(required_events))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_cache() -> dict:
    """加载插装缓存。"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def extract_algorithm_from_code(code: str) -> str | None:
    """从插装代码中提取算法名。"""
    import re
    # 查找 "# xxx 算法实现" 注释
    match = re.search(r"#\s*(\w+)\s+算法实现", code)
    if match:
        return match.group(1)
    return None


def save_instrumented_file(domain: str, algorithm: str, code: str) -> None:
    """保存预插装文件。"""
    output_dir = TEMPLATES_DIR / domain / algorithm
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "python_instrumented.py"

    # 移除末尾的运行代码（tracer.dump() 和函数调用）
    lines = code.strip().split("\n")
    clean_lines = []
    for line in lines:
        # 跳过模块级的运行代码
        if line.strip().startswith("tracer.dump()"):
            continue
        if line.strip().startswith("bubble_sort([") or "tracer.dump()" in line:
            continue
        clean_lines.append(line)

    final_code = "\n".join(clean_lines).strip()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_code)

    print(f"✓ Created: {output_file}")


def main():
    """主函数。"""
    # 加载缓存
    cache = load_cache()
    print(f"Loaded {len(cache)} entries from cache")

    # 从缓存中提取成功的插装代码
    from app.algorithm_visualizer.template_registry import ALGORITHMS, get_template_code

    saved_count = 0

    for hash_key, entry in cache.items():
        if entry.get("error"):
            continue

        code = entry["code"]

        # 尝试匹配算法
        for algo_key, algo_info in ALGORITHMS.items():
            try:
                clean_code = get_template_code(algo_key, "python")
                expected_hash = compute_hash(
                    clean_code,
                    algo_info["visualizer_type"],
                    algo_info.get("required_events", [])
                )

                if hash_key == expected_hash:
                    domain = algo_info["domain"]
                    save_instrumented_file(domain, algo_key, code)
                    saved_count += 1
                    break
            except Exception as e:
                continue

    print(f"\nTotal saved: {saved_count} instrumented templates")


if __name__ == "__main__":
    main()