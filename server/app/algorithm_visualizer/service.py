"""Official algorithm-visualization execution service."""

from __future__ import annotations

from typing import Any

from app.algorithm_visualizer.input_validation import InputValidationError
from app.algorithm_visualizer.official_runtime import OfficialRuntimeError, execute_official_template
from app.algorithm_visualizer.template_registry import TemplateNotFoundError, get_template_spec
from app.algorithm_visualizer.trace_validation import InvalidTraceError, validate_trace_events

_MAX_COLLECTION_SIZE = 128
_MAX_TEXT_LENGTH = 4096


class VisualizerRunError(Exception):
    """Raised when a registered algorithm cannot produce a renderable trace."""

    def __init__(self, message: str, error_type: str = "VISUALIZER_RUN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type


def run_official_visualization(
    *,
    algorithm: str,
    language: str,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Run one registered template and return its validated render contract.

    Templates are trusted, versioned source files. The client can only supply
    input data, so no user code, LLM instrumentation, or process sandbox is
    part of the visualization path.
    """

    if language != "python":
        raise VisualizerRunError("当前仅支持 Python 算法模板。", "UNSUPPORTED_LANGUAGE")

    try:
        spec = get_template_spec(algorithm)
    except TemplateNotFoundError as exc:
        raise VisualizerRunError(str(exc), "MISSING_ALGORITHM") from exc

    # Validate input against the registered input_model.
    try:
        validated = spec.input_model.model_validate(input_data)
        input_data = validated.model_dump(mode="json")
    except Exception as exc:
        raise VisualizerRunError(str(exc), "INPUT_INVALID") from exc

    try:
        _validate_runtime_limits(spec.key, input_data)
    except InputValidationError as exc:
        raise VisualizerRunError(str(exc), "INPUT_INVALID") from exc

    try:
        execution = execute_official_template(spec, input_data)
        dict_events = _trace_events_to_dicts(execution.events)
        validate_trace_events(
            dict_events,
            spec.visualizer_type,
            source_line_count=len(spec.source_code.splitlines()),
        )
    except (OfficialRuntimeError, InvalidTraceError, TypeError, ValueError) as exc:
        raise VisualizerRunError(str(exc), "RUNTIME_ERROR") from exc

    return {
        "domain": spec.domain,
        "algorithm": spec.key,
        "visualizerType": spec.visualizer_type,
        "language": "python",
        "executionMode": "official",
        "events": dict_events,
        "result": execution.result,
        "summary": execution.summary,
    }


def _trace_events_to_dicts(events: list[Any]) -> list[dict[str, Any]]:
    """Convert TraceEvent dataclass instances to JSON-compatible dicts."""
    result: list[dict[str, Any]] = []
    for event in events:
        entry: dict[str, Any] = {
            "id": event.id,
            "step": event.step,
            "type": event.type,
            "visualizerType": event.visualizer_type,
            "state": {"structure": _to_jsonable(event.state)},
            "targets": _to_jsonable(event.targets),
        }
        if event.line is not None:
            entry["line"] = event.line
        if event.message is not None:
            entry["message"] = event.message
        result.append(entry)
    return result


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-compatible representation."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "val"):
        return getattr(value, "val")
    return str(value)


def _validate_runtime_limits(algorithm: str, input_data: dict[str, Any]) -> None:
    """Keep trusted template execution bounded for interactive requests."""

    def validate(value: Any, path: str) -> None:
        if isinstance(value, str) and len(value) > _MAX_TEXT_LENGTH:
            raise InputValidationError(f"{path} 不能超过 {_MAX_TEXT_LENGTH} 个字符")
        if isinstance(value, list):
            if len(value) > _MAX_COLLECTION_SIZE:
                raise InputValidationError(f"{path} 不能超过 {_MAX_COLLECTION_SIZE} 项")
            for index, item in enumerate(value):
                validate(item, f"{path}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                validate(item, f"{path}.{key}")

    validate(input_data, "inputData")
