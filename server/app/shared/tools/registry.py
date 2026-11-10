"""模型工具的定义、注册与执行分派。

``Tool`` 同时承载 JSON Schema 来源与执行入口，``ToolRegistry`` 按名称分派调用。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any

from pydantic import BaseModel

ToolHandler = Callable[..., Awaitable[Any]]


def summarize_tool_args(name: str, args: Mapping[str, Any] | str) -> str:
    """提取并格式化工具入参为人性化可读的紧凑单行字符串。"""
    payload: dict[str, Any] = {}
    if isinstance(args, str):
        try:
            payload = json.loads(args) if args.strip() else {}
        except Exception:
            return f"raw='{args.strip()[:100]}'"
    elif isinstance(args, Mapping):
        payload = dict(args)

    if not payload:
        return "无参数"

    if name == "load_skill":
        skill_name = payload.get("name", "unknown")
        ref = payload.get("reference", "")
        return f"skill='{skill_name}'" + (f" (ref='{ref}')" if ref else "")

    if name == "bash":
        cmd = str(payload.get("command", "")).strip()
        cmd_preview = cmd if len(cmd) <= 120 else f"{cmd[:117]}..."
        return f"command={cmd_preview!r}"

    if name == "synthesize_speech":
        out = payload.get("output_path", "")
        text = str(payload.get("text", "")).strip()
        text_preview = text if len(text) <= 40 else f"{text[:37]}..."
        return f"output={out!r}, text={text_preview!r} (共 {len(text)} 字)"

    if name in {"write", "edit"}:
        path = payload.get("path", "")
        content = str(payload.get("content", ""))
        return f"path={path!r}, length={len(content)}"

    if name in {"read", "view_image"}:
        path = payload.get("path", "")
        return f"path={path!r}"

    if name == "generate_lecture_content":
        return f"topic={payload.get('topic', '')!r}, goal={payload.get('learning_goal', '')!r}"

    if name == "generate_quiz":
        return f"topic={payload.get('topic', '')!r}, difficulty={payload.get('difficulty', '')!r}"

    if name == "generate_code":
        return f"topic={payload.get('topic', '')!r}, lang={payload.get('language', '')!r}"

    if name == "generate_mindmap":
        return f"topic={payload.get('topic', '')!r}"

    if name == "generate_reading":
        return f"topic={payload.get('topic', '')!r}, difficulty={payload.get('difficulty', '')!r}"

    # 通用参数缩减
    items = []
    for k, v in payload.items():
        val_str = str(v).replace("\n", " ")
        if len(val_str) > 50:
            val_str = f"{val_str[:47]}..."
        items.append(f"{k}={val_str}")
    preview = ", ".join(items)
    return preview if len(preview) <= 180 else f"{preview[:177]}..."


def summarize_tool_result(name: str, raw: Any, max_len: int = 150) -> str:
    """提取并格式化工具执行结果的关键摘要信息。"""
    if raw is None:
        return "无返回结果 (None)"

    if isinstance(raw, Mapping):
        status = raw.get("status", "ok")
        if name == "bash":
            exit_code = raw.get("exit_code", 0)
            stdout = str(raw.get("stdout", "")).strip().replace("\n", " ")
            stderr = str(raw.get("stderr", "")).strip().replace("\n", " ")
            std_part = f"stdout={stdout[:80]!r}" if stdout else ""
            err_part = f"stderr={stderr[:80]!r}" if stderr else ""
            parts = [f"exit={exit_code}"]
            if std_part:
                parts.append(std_part)
            if err_part:
                parts.append(err_part)
            return ", ".join(parts)

        if name == "synthesize_speech":
            return f"audio={raw.get('audio_path')!r}, duration={raw.get('duration_ms')}ms"

        if name == "load_skill":
            text = str(raw.get("text", "")).strip().replace("\n", " ")
            preview = text if len(text) <= 80 else f"{text[:77]}..."
            return f"status={status}, preview={preview!r} (共 {len(str(raw.get('text', '')))} 字符)"

        if "title" in raw:
            title = raw.get("title", "")
            summary = raw.get("summary", "")
            return f"status={status}, title={title!r}, summary={summary!r}"

        # 通用 dict
        filtered = {k: v for k, v in raw.items() if k not in {"text", "content"}}
        if filtered:
            raw_preview = json.dumps(filtered, ensure_ascii=False)
            if len(raw_preview) > max_len:
                raw_preview = f"{raw_preview[:max_len - 3]}..."
            return f"status={status}, data={raw_preview}"

    text_rep = str(raw).strip().replace("\n", " ")
    if len(text_rep) > max_len:
        text_rep = f"{text_rep[:max_len - 3]}..."
    return text_rep


def format_tool_output(raw: Any) -> str:
    """将工具返回的任意结构（dict / str / BaseModel）归一化为回灌给 LLM 的文本。"""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, BaseModel):
        return raw.model_dump_json(indent=2)
    if isinstance(raw, Mapping):
        if set(raw.keys()) <= {"text", "status", "total_lines", "count", "path"} and "text" in raw:
            prefix = "[Error] " if raw.get("status") == "failed" else ""
            return f"{prefix}{raw['text']}"
        return json.dumps(dict(raw), ensure_ascii=False, indent=2)
    return str(raw)


@dataclass(frozen=True, slots=True)
class Tool:
    """一个可供模型选择并由应用执行的工具。"""

    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler

    def __post_init__(self) -> None:
        """校验工具名、描述与处理函数非空。"""
        if not self.name.strip():
            raise ValueError("Tool name cannot be empty")
        if not self.description.strip():
            raise ValueError(f"Tool description cannot be empty: {self.name}")
        if self.handler is None:
            raise ValueError(f"Tool handler cannot be None: {self.name}")

    def to_openai_schema(self) -> dict[str, Any]:
        """生成 OpenAI function-calling schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }


def tool(
    name: str | None = None,
    description: str | None = None,
    args_model: type[BaseModel] | None = None,
) -> Callable[[ToolHandler], Tool]:
    """装饰器：将异步函数转换为统一的 Tool 实例。"""
    def decorator(fn: ToolHandler) -> Tool:
        tool_name = (name or fn.__name__).strip()
        tool_desc = (description or fn.__doc__ or "").strip()
        if not tool_desc:
            tool_desc = f"Tool {tool_name}"
        return Tool(
            name=tool_name,
            description=tool_desc,
            args_model=args_model,
            handler=fn,
        )
    return decorator


class ToolRegistry:
    """工具注册与执行分派器。"""

    def __init__(self, tools: Sequence[Tool] | None = None) -> None:
        """按名称建立工具索引，重名直接报错。"""
        self._tools: dict[str, Tool] = {}
        for item in tools or ():
            if item.name in self._tools:
                raise ValueError(f"Tool already registered: {item.name}")
            self._tools[item.name] = item

    def openai_schemas(self) -> list[dict[str, Any]]:
        """返回全部工具的 OpenAI function-calling schema 列表。"""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, args: Mapping[str, Any] | str = "") -> Any:
        """按名称执行工具：参数先经 args_model 校验再调用 handler。"""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        if isinstance(args, str):
            payload = json.loads(args) if args.strip() else {}
        else:
            payload = dict(args)
        return await tool.handler(**tool.args_model.model_validate(payload).model_dump())
