"""LLM transformation contract for user-provided algorithm code.

Official templates never enter this module.  User code is transformed into one
small, explicit entry point which the custom runtime can validate and execute.
"""

from __future__ import annotations

import ast
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm


class CustomInstrumentationError(ValueError):
    """Raised when LLM output is not an executable visualization program."""


_SYSTEM_PROMPT = """你负责把用户给出的 Python 算法代码改写为可视化程序。
只输出 Python 代码，不要 Markdown，不要解释。

输出必须定义唯一入口：def visualize(input_data, tracer):
- 将 input_data 作为算法输入，不要硬编码测试数据，不要读取 stdin。
- 保持用户算法的计算语义；可以把原函数放在 visualize 内或在模块级定义。
- 用 tracer.snapshot(event_type, structure, line=N, message=...) 记录状态。
- line 如提供，必须对应用户原始代码的行号；无法准确对应时省略 line。
- 第一条 snapshot 的 event_type 必须是对应类型的初始化事件，最后一条必须是 finish。
- structure 必须匹配类型：array={"array": list}；stack-queue={"mode":"stack"或"queue","items":list,"pointers":list}；linked-list={"nodes":list,"pointers":list}；tree/graph={"nodes":list}；dp-table={"headers":list,"values":二维list,"highlighted":list}。
- 只能使用 Python 的基础语法和内置函数；禁止 import、文件/网络/进程操作、eval、exec、open、globals、locals、dunder 名称或属性。
- 返回 JSON 可序列化的算法结果。
"""


async def instrument_custom_code(
    *,
    source_code: str,
    visualizer_type: str,
    entry_function: str,
    input_schema: dict[str, object],
) -> str:
    field_names = list(input_schema.get("properties", {}))
    required_fields = list(input_schema.get("required", field_names))
    bindings = "\n".join(f'- {name} = input_data["{name}"]' for name in field_names)
    prompt = f"""可视化类型：{visualizer_type}
必须调用的用户入口函数：{entry_function}
输入字段（必须逐一从 input_data 读取，不能改名或猜测）：
{bindings or '- 此函数没有参数'}

请保留用户给出的所有必要函数，并在 visualize 中用上述字段按原函数参数顺序调用 {entry_function}。
不得改用其他函数、硬编码示例数据，或忽略任一输入字段。

用户代码：
```python
{source_code}
```
"""
    try:
        response = await get_llm().ainvoke(
            [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=prompt)],
            temperature=0,
            max_tokens=6000,
        )
    except Exception as exc:
        raise CustomInstrumentationError(f"AI 插装服务不可用：{exc}") from exc

    code = _extract_code(str(getattr(response, "content", response)))
    _validate_instrumented_code(code, required_fields)
    return code


def _extract_code(content: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else content).strip()


def _validate_instrumented_code(code: str, required_input_fields: list[str]) -> None:
    if not code:
        raise CustomInstrumentationError("AI 未返回可执行的插装代码。")
    if len(code) > 48_000:
        raise CustomInstrumentationError("AI 生成的插装代码过大。")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise CustomInstrumentationError(f"AI 生成的代码语法错误：{exc.msg}") from exc

    if any(not isinstance(node, (ast.FunctionDef, ast.Pass)) for node in tree.body):
        raise CustomInstrumentationError("AI 生成的代码只能包含函数定义，不能在模块级执行语句。")

    entry = next((node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "visualize"), None)
    if entry is None or [arg.arg for arg in entry.args.args[:2]] != ["input_data", "tracer"]:
        raise CustomInstrumentationError("AI 生成的代码必须定义 visualize(input_data, tracer)。")
    if any(isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef)) for node in ast.walk(tree)):
        raise CustomInstrumentationError("AI 生成的代码包含不允许的导入、类或异步定义。")

    forbidden_names = {"eval", "exec", "open", "compile", "input", "globals", "locals", "vars", "getattr", "setattr", "delattr", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and (node.id in forbidden_names or node.id.startswith("__")):
            raise CustomInstrumentationError(f"AI 生成的代码使用了受限名称：{node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise CustomInstrumentationError("AI 生成的代码包含受限属性访问。")

    accessed_fields = {
        node.slice.value
        for node in ast.walk(entry)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "input_data"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }
    missing_fields = [field for field in required_input_fields if field not in accessed_fields]
    if missing_fields:
        raise CustomInstrumentationError(
            f"AI 插装结果没有读取输入字段：{', '.join(missing_fields)}，请重新运行。"
        )
