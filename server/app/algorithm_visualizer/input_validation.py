"""Validation for the JSON input contract used by algorithm templates."""

from __future__ import annotations

from typing import Any


class InputValidationError(ValueError):
    """Raised when input data does not match a template schema."""


def validate_input_data(
    value: object,
    schema: dict[str, Any],
    path: str = "inputData",
) -> None:
    schema_type = schema.get("type")
    if schema_type is None:
        return
    if schema_type == "object":
        _validate_object(value, schema, path)
        return
    if schema_type == "array":
        _validate_array(value, schema, path)
        return
    if schema_type == "string":
        _require_type(value, str, path, "字符串")
        return
    if schema_type == "boolean":
        _require_type(value, bool, path, "布尔值")
        return
    if schema_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise InputValidationError(f"{path} 必须是整数")
        _validate_minimum(value, schema, path)
        return
    if schema_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InputValidationError(f"{path} 必须是数字")
        _validate_minimum(value, schema, path)
        return
    if schema_type == "null":
        if value is not None:
            raise InputValidationError(f"{path} 必须是 null")
        return
    raise InputValidationError(f"{path} 使用了不支持的 schema 类型: {schema_type}")


def _validate_object(value: object, schema: dict[str, Any], path: str) -> None:
    if not isinstance(value, dict):
        raise InputValidationError(f"{path} 必须是对象")

    for key in schema.get("required", []):
        if key not in value:
            raise InputValidationError(f"{path}.{key} 为必填字段")

    properties = schema.get("properties", {})
    for key, item in value.items():
        if key in properties:
            validate_input_data(item, properties[key], f"{path}.{key}")


def _validate_array(value: object, schema: dict[str, Any], path: str) -> None:
    if not isinstance(value, list):
        raise InputValidationError(f"{path} 必须是数组")

    min_items = schema.get("minItems")
    if isinstance(min_items, int) and len(value) < min_items:
        raise InputValidationError(f"{path} 至少需要 {min_items} 项")

    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(value):
            validate_input_data(item, item_schema, f"{path}[{index}]")


def _validate_minimum(
    value: int | float,
    schema: dict[str, Any],
    path: str,
) -> None:
    minimum = schema.get("minimum")
    if isinstance(minimum, (int, float)) and value < minimum:
        raise InputValidationError(f"{path} 不能小于 {minimum}")


def _require_type(
    value: object,
    expected: type[object],
    path: str,
    label: str,
) -> None:
    if not isinstance(value, expected):
        raise InputValidationError(f"{path} 必须是{label}")
