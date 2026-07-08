"""LLM 自动插装引擎 — 将干净算法代码转为带 tracer 调用的可视化代码。

核心流程：
1. 检查缓存（hash → 插装结果）
2. 调用 LLM 插装
3. 校验插装质量（语法、tracer 导入、required_events）
4. 校验失败 → 单次重试（带错误反馈）
5. 存入缓存

Phase 1 仅支持 Python。
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm
from app.infra.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Tracer SDK API 文档（供 LLM prompt 使用）
# ---------------------------------------------------------------------------

_PYTHON_TRACER_API = """\
# Python Tracer SDK API 参考

## 导入方式
from visual_tracer import ArrayTracer, StackTracer, QueueTracer, LinkedListTracer, TreeTracer, GraphTracer, DpTableTracer

## ArrayTracer（数组可视化，用于排序/查找/贪心等）
tracer = ArrayTracer()
tracer.init_array(array, line=N)       # 初始化数组，array 是 list
tracer.compare(i, j, line=N)           # 比较位置 i 和 j
tracer.swap(i, j, line=N)              # 交换位置 i 和 j
tracer.assign(index, value, line=N)    # 赋值 array[index] = value
tracer.mark_sorted(index, line=N)      # 标记位置已归位
tracer.move_pointer({"i": i, "j": j}, line=N)  # 移动指针
tracer.finish(line=N)                  # 排序/操作完成

## StackTracer（栈可视化）
tracer = StackTracer()
tracer.init_stack(line=N)
tracer.push(value, line=N)
tracer.pop(line=N)                     # 返回弹出的值
tracer.highlight_input(input_index, line=N)
tracer.finish(line=N)

## QueueTracer（队列可视化）
tracer = QueueTracer()
tracer.init_queue(line=N)
tracer.enqueue(value, line=N)
tracer.dequeue(line=N)                 # 返回出队的值
tracer.finish(line=N)

## LinkedListTracer（链表可视化）
tracer = LinkedListTracer()
tracer.init_list(nodes, pointers, line=N)  # nodes: [{"id":"node-0","label":"1"}], pointers: [{"label":"head","nodeIndex":0}]
tracer.set_visited(node_index, visited=True, line=N)
tracer.move_pointer(label, node_index, tone="accent", line=N)
tracer.add_node(label, tone="default", line=N)  # 返回 node_index
tracer.remove_node(node_index, line=N)
tracer.finish(line=N)

## TreeTracer（树可视化）
tracer = TreeTracer()
tracer.init_tree(nodes, line=N)        # nodes: [{"id":"node-0","label":"1","children":["node-1","node-2"]}]
tracer.visit_node(node_id, visited=True, line=N)
tracer.finish(line=N)

## GraphTracer（图可视化）
tracer = GraphTracer()
tracer.init_graph(nodes, line=N)       # nodes: [{"id":"0","label":"0","edges":[{"to":"1"},{"to":"2"}]}]
tracer.visit_node(node_id, visited=True, line=N)
tracer.finish(line=N)

## DpTableTracer（DP 表格可视化）
tracer = DpTableTracer()
tracer.init_table(headers, rows, cols, fill_value=0, line=N)
tracer.set_value(row, col, value, line=N)
tracer.highlight(row, col, tone="active", line=N)
tracer.clear_highlights(line=N)
tracer.finish(line=N)

## 通用规则
- 每个 tracer 调用必须带 line=N 参数，N 是原始代码中该操作的行号（1-based）
- tracer 实例必须在**模块级**（函数外）创建，不要在函数内部创建
- 算法结束时必须调用 tracer.finish()
- 在所有代码末尾（模块级）调用 tracer.dump() 来输出 trace.json
- 示例结构：
  ```python
  from visual_tracer import ArrayTracer
  tracer = ArrayTracer()

  def bubble_sort(arr):
      tracer.init_array(arr, line=1)
      ...
      tracer.finish(line=10)

  bubble_sort([5, 3, 8, 1, 2])
  tracer.dump()
  ```
"""

# ---------------------------------------------------------------------------
# 插装 Prompt 模板
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是一个算法可视化插装专家。你的任务是在干净的算法代码中插入 tracer 调用，
使其运行时能产生可视化事件流。

## 核心规则
1. **保持原有算法逻辑完全不变** — 不修改任何计算、比较、赋值的语义
2. **每个 tracer 调用必须带 line=N** — N 是原始代码中该操作所在行号（1-based）
3. **覆盖所有 required_events** — 根据算法的 visualizer_type 插入必需的 tracer 调用
4. **代码必须可执行** — 无语法错误，import 正确
5. **tracer 必须在模块级创建** — 不要在函数内部创建 tracer 实例
6. **代码末尾必须调用 tracer.dump()** — 输出 trace.json

## 输出格式
将插装后的完整代码放在 markdown 代码块中：
```python
# 插装后的代码
```

不要输出任何其他内容（不要解释、不要注释说明修改了什么）。
"""

_INSTRUMENT_PROMPT = """\
## 算法信息
- 算法名称：{algorithm_name}
- 可视化类型：{visualizer_type}
- 必需事件：{required_events}

## Tracer SDK API
{tracer_api}

## 原始干净代码
```python
{clean_code}
```

请在上述代码中插入 tracer 调用，使其产生可视化事件流。
记住：保持算法逻辑不变，每个 tracer 调用带 line=N（原始行号），覆盖所有必需事件。
"""

_RETRY_PROMPT = """\
上一次插装结果存在问题，请修正。

## 错误信息
{errors}

## 上一次插装结果
```python
{last_code}
```

## 原始干净代码
```python
{clean_code}
```

## 算法信息
- 可视化类型：{visualizer_type}
- 必需事件：{required_events}

请重新生成插装代码，修正上述错误。保持算法逻辑不变，每个 tracer 调用带 line=N。
"""


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class InstrumentationResult:
    """插装结果。"""

    code: str
    error: str | None = None
    cached: bool = False


# ---------------------------------------------------------------------------
# 插装引擎
# ---------------------------------------------------------------------------

class CodeInstrumenter:
    """LLM 自动插装引擎，带缓存和重试。

    所有 LLM 调用均为异步，需在 async 上下文中使用。
    """

    def __init__(self) -> None:
        self._cache: dict[str, InstrumentationResult] = {}

    async def instrument(
        self,
        clean_code: str,
        *,
        algorithm_name: str,
        visualizer_type: str,
        required_events: list[str],
        language: str = "python",
    ) -> InstrumentationResult:
        """对干净代码进行插装，返回插装结果。

        Args:
            clean_code: 干净的算法代码（无 tracer 调用）
            algorithm_name: 算法名称（如 "bubble_sort"）
            visualizer_type: 可视化类型（如 "array", "tree", "graph"）
            required_events: 必需事件列表
            language: 编程语言，当前仅支持 python

        Returns:
            InstrumentationResult 包含插装后代码或错误信息
        """
        if language != "python":
            return InstrumentationResult(
                code=clean_code,
                error=f"插装引擎暂不支持 {language}，仅支持 Python",
            )

        # 1. 计算缓存键
        cache_key = self._compute_hash(clean_code, visualizer_type, required_events)

        # 2. 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.info("[Instrumenter] 缓存命中: algorithm=%s", algorithm_name)
            return InstrumentationResult(
                code=cached.code,
                error=cached.error,
                cached=True,
            )

        # 3. 第一次 LLM 插装
        instrumented_code = await self._call_llm(
            clean_code=clean_code,
            algorithm_name=algorithm_name,
            visualizer_type=visualizer_type,
            required_events=required_events,
        )

        if instrumented_code is None:
            result = InstrumentationResult(
                code=clean_code,
                error="LLM 插装失败：无法从响应中提取代码",
            )
            self._cache[cache_key] = result
            return result

        # 4. 校验
        errors = self._validate(instrumented_code, visualizer_type, required_events)
        if not errors:
            result = InstrumentationResult(code=instrumented_code)
            self._cache[cache_key] = result
            logger.info("[Instrumenter] 插装成功: algorithm=%s", algorithm_name)
            return result

        # 5. 单次重试（带错误反馈）
        logger.warning(
            "[Instrumenter] 首次插装校验失败: algorithm=%s errors=%s",
            algorithm_name,
            "; ".join(errors),
        )

        retry_code = await self._call_llm_retry(
            clean_code=clean_code,
            last_code=instrumented_code,
            visualizer_type=visualizer_type,
            required_events=required_events,
            errors=errors,
        )

        if retry_code is not None:
            retry_errors = self._validate(retry_code, visualizer_type, required_events)
            if not retry_errors:
                result = InstrumentationResult(code=retry_code)
                self._cache[cache_key] = result
                logger.info("[Instrumenter] 重试插装成功: algorithm=%s", algorithm_name)
                return result

        # 两次都失败
        result = InstrumentationResult(
            code=clean_code,
            error=f"插装失败（重试后仍不通过）: {'; '.join(errors)}",
        )
        self._cache[cache_key] = result
        logger.error("[Instrumenter] 插装最终失败: algorithm=%s", algorithm_name)
        return result

    # ------------------------------------------------------------------
    # 缓存
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_hash(
        code: str,
        visualizer_type: str,
        required_events: list[str],
    ) -> str:
        raw = f"{code}\0{visualizer_type}\0{','.join(sorted(required_events))}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # LLM 调用
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        clean_code: str,
        algorithm_name: str,
        visualizer_type: str,
        required_events: list[str],
    ) -> str | None:
        """调用 LLM 进行插装，返回插装后代码或 None。"""
        prompt = _INSTRUMENT_PROMPT.format(
            algorithm_name=algorithm_name,
            visualizer_type=visualizer_type,
            required_events=", ".join(required_events),
            tracer_api=_PYTHON_TRACER_API,
            clean_code=clean_code,
        )

        try:
            llm = get_llm()
            response = await llm.ainvoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ],
                temperature=0.1,
            )
            return self._extract_code(response)
        except Exception as e:
            logger.error("[Instrumenter] LLM 调用失败: %s", e)
            return None

    async def _call_llm_retry(
        self,
        clean_code: str,
        last_code: str,
        visualizer_type: str,
        required_events: list[str],
        errors: list[str],
    ) -> str | None:
        """带错误反馈的重试调用。"""
        prompt = _RETRY_PROMPT.format(
            errors="; ".join(errors),
            last_code=last_code,
            clean_code=clean_code,
            visualizer_type=visualizer_type,
            required_events=", ".join(required_events),
        )

        try:
            llm = get_llm()
            response = await llm.ainvoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ],
                temperature=0.1,
            )
            return self._extract_code(response)
        except Exception as e:
            logger.error("[Instrumenter] LLM 重试调用失败: %s", e)
            return None

    # ------------------------------------------------------------------
    # 代码提取
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_code(response: Any) -> str | None:
        """从 LLM 响应中提取 markdown 代码块内的 Python 代码。"""
        content = getattr(response, "content", "") or ""
        content = str(content).strip()

        if not content:
            return None

        # 尝试提取 ```python ... ``` 代码块
        pattern = r"```python\s*\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            return matches[0].strip()

        # 尝试提取 ``` ... ``` 代码块（无语言标记）
        pattern = r"```\s*\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            return matches[0].strip()

        # 如果整个响应看起来就是代码（以 def/class/import/from 开头）
        lines = content.split("\n")
        non_empty = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        if non_empty and any(
            non_empty[0].strip().startswith(kw)
            for kw in ("def ", "class ", "import ", "from ")
        ):
            return content

        return None

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------

    def _validate(
        self,
        code: str,
        visualizer_type: str,
        required_events: list[str],
    ) -> list[str]:
        """校验插装结果，返回错误列表（空列表表示通过）。"""
        errors: list[str] = []

        # 1. 语法检查
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"语法错误: 第{e.lineno}行 - {e.msg}")
            return errors  # 语法错误直接返回，后续检查无意义

        # 2. Tracer 导入检查
        tracer_classes = self._get_tracer_classes(visualizer_type)
        has_import = any(
            f"from visual_tracer import {cls}" in code or "import visual_tracer" in code
            for cls in tracer_classes
        )
        if not has_import and "visual_tracer" not in code:
            errors.append(
                f"缺少 tracer 导入: 需要 from visual_tracer import {tracer_classes[0]}"
            )

        # 3. Tracer 实例化检查
        tracer_var = self._find_tracer_variable(code, tracer_classes)
        if not tracer_var:
            errors.append(f"未找到 tracer 实例化: 需要 {tracer_classes[0]}()")

        # 4. Required events 检查
        for event in required_events:
            if event not in code:
                errors.append(f"缺少必需事件调用: {event}()")

        # 5. line 参数检查（至少有一个 tracer 调用带 line=）
        if tracer_var and not re.search(rf"{tracer_var}\.\w+\(.*line\s*=", code):
            errors.append("tracer 调用缺少 line 参数（需要 line=N 标注原始行号）")

        return errors

    @staticmethod
    def _get_tracer_classes(visualizer_type: str) -> list[str]:
        """根据 visualizer_type 返回对应的 tracer 类名列表。"""
        mapping: dict[str, list[str]] = {
            "array": ["ArrayTracer"],
            "stack-queue": ["StackTracer", "QueueTracer"],
            "linked-list": ["LinkedListTracer"],
            "tree": ["TreeTracer"],
            "graph": ["GraphTracer"],
            "dp-table": ["DpTableTracer"],
        }
        return mapping.get(visualizer_type, [])

    @staticmethod
    def _find_tracer_variable(code: str, tracer_classes: list[str]) -> str | None:
        """从代码中找到 tracer 变量名。"""
        for cls in tracer_classes:
            match = re.search(rf"(\w+)\s*=\s*{cls}\s*\(", code)
            if match:
                return match.group(1)
        return None


# ---------------------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------------------

_instrumenter: CodeInstrumenter | None = None


def get_instrumenter() -> CodeInstrumenter:
    """获取插装引擎单例。"""
    global _instrumenter
    if _instrumenter is None:
        _instrumenter = CodeInstrumenter()
    return _instrumenter
