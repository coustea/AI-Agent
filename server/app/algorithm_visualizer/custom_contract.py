"""Deterministic input contract discovery for user-provided Python code.

The LLM is responsible for inserting visualization snapshots, not for guessing
which user function should be called or what each input field means.  This
module derives that small contract directly from the submitted source.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any


class CustomCodeContractError(ValueError):
    """Raised when a custom program cannot expose a callable entry function."""


@dataclass(frozen=True, slots=True)
class CustomFunction:
    name: str
    parameters: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CustomCodeContract:
    entry_function: str
    functions: tuple[CustomFunction, ...]
    input_schema: dict[str, Any]
    default_input: dict[str, Any]


def inspect_custom_code(
    source_code: str,
    entry_function: str | None = None,
) -> CustomCodeContract:
    """Find eligible top-level functions and make a beginner-friendly form schema."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        raise CustomCodeContractError(f"自定义代码语法错误：第 {exc.lineno} 行 {exc.msg}") from exc

    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    functions = tuple(
        _function_from_node(node)
        for node in definitions
        if not node.name.startswith("_") and _supports_form_inputs(node)
    )
    if not functions:
        raise CustomCodeContractError("未找到可运行的顶层函数，请先定义例如 def bubble_sort(nums): ...")

    selected = _select_function(functions, entry_function)
    selected_node = next(node for node in definitions if node.name == selected.name)
    schema, default_input = _build_input_contract(selected_node)
    return CustomCodeContract(
        entry_function=selected.name,
        functions=functions,
        input_schema=schema,
        default_input=default_input,
    )


def _function_from_node(node: ast.FunctionDef) -> CustomFunction:
    positional = [*node.args.posonlyargs, *node.args.args]
    if node.args.vararg is not None or node.args.kwarg is not None or node.args.kwonlyargs:
        raise CustomCodeContractError(
            f"函数 {node.name} 使用了 *args、**kwargs 或仅关键字参数；请改为普通参数后再可视化。"
        )
    return CustomFunction(name=node.name, parameters=tuple(arg.arg for arg in positional))


def _supports_form_inputs(node: ast.FunctionDef) -> bool:
    return node.args.vararg is None and node.args.kwarg is None and not node.args.kwonlyargs


def _select_function(functions: tuple[CustomFunction, ...], requested: str | None) -> CustomFunction:
    if requested:
        match = next((item for item in functions if item.name == requested), None)
        if match is None:
            raise CustomCodeContractError(f"未找到入口函数 {requested}，请重新选择。")
        return match

    # Prefer a function with actual inputs; when tied, users normally place the
    # public algorithm after its small helper functions.
    return max(enumerate(functions), key=lambda item: (len(item[1].parameters), item[0]))[1]


def _build_input_contract(node: ast.FunctionDef) -> tuple[dict[str, Any], dict[str, Any]]:
    args = [*node.args.posonlyargs, *node.args.args]
    defaults_by_name = _defaults_by_name(node)
    properties: dict[str, dict[str, Any]] = {}
    default_input: dict[str, Any] = {}

    for arg in args:
        schema, fallback = _schema_for_argument(arg)
        properties[arg.arg] = schema
        default_input[arg.arg] = defaults_by_name.get(arg.arg, fallback)

    _align_related_defaults(default_input)
    return {
        "type": "object",
        "required": [arg.arg for arg in args],
        "properties": properties,
    }, default_input


def _defaults_by_name(node: ast.FunctionDef) -> dict[str, Any]:
    args = [*node.args.posonlyargs, *node.args.args]
    defaults = [None] * (len(args) - len(node.args.defaults)) + list(node.args.defaults)
    values: dict[str, Any] = {}
    for arg, default in zip(args, defaults):
        if default is None:
            continue
        try:
            values[arg.arg] = ast.literal_eval(default)
        except (ValueError, TypeError):
            continue
    return values


def _schema_for_argument(arg: ast.arg) -> tuple[dict[str, Any], Any]:
    annotation = _annotation_name(arg.annotation)
    name = arg.arg.lower()
    if annotation in {"str", "string"} or name in {"s", "text", "string", "pattern", "word", "source"}:
        return {"type": "string"}, "({[]})"
    if annotation in {"bool", "boolean"} or name.startswith(("is_", "has_", "use_")):
        return {"type": "boolean"}, False
    if annotation in {"float", "double", "number"}:
        return {"type": "number"}, 1
    if annotation in {"int", "integer"} or name in {
        "n", "k", "target", "start", "end", "left", "right", "capacity", "size", "limit",
    }:
        return {"type": "integer"}, 3 if name == "target" else 5
    if annotation.startswith(("list", "tuple", "set", "sequence", "iterable")) or name in {
        "arr", "array", "nums", "numbers", "values", "items", "data", "weights", "prices",
        "candidates", "edges", "graph", "points", "intervals",
    }:
        return _array_schema(annotation, name)
    return {"type": "integer"}, 5


def _annotation_name(annotation: ast.expr | None) -> str:
    if annotation is None:
        return ""
    if isinstance(annotation, ast.Name):
        return annotation.id.lower()
    if isinstance(annotation, ast.Attribute):
        return annotation.attr.lower()
    if isinstance(annotation, ast.Subscript):
        return _annotation_name(annotation.value)
    return ""


def _array_schema(annotation: str, name: str) -> tuple[dict[str, Any], Any]:
    if name in {"edges", "points", "intervals"}:
        return {
            "type": "array",
            "items": {"type": "array", "items": {"type": "integer"}},
        }, [[0, 1], [1, 2], [2, 3]]
    if annotation in {"list", "tuple", "set"} and name in {"words", "strings"}:
        return {"type": "array", "items": {"type": "string"}}, ["cat", "dog"]
    return {"type": "array", "items": {"type": "integer"}}, [6, 1, 8, 3, 9, 2]


def _align_related_defaults(default_input: dict[str, Any]) -> None:
    for name in ("target", "key", "value"):
        if name not in default_input:
            continue
        source = next(
            (value for value in default_input.values() if isinstance(value, list) and value and isinstance(value[0], (int, float))),
            None,
        )
        if source is not None:
            default_input[name] = source[min(2, len(source) - 1)]
