"""OpenAI 兼容的 LLM 网关模块。

提供统一的异步 LLM 调用接口，支持：
- 普通文本生成（ainvoke / astream）
- 自研工具调用执行器创建
- 结构化 JSON 输出（ainvoke_json），带 self-repair 自修正 + 跨模式降级
- 视觉模型调用（vision）

内部使用 langchain_openai.ChatOpenAI 作为底层实现。
"""

from __future__ import annotations

import copy
import json
import time
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Any, AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import DEFAULT_TEMPERATURE, JSON_TEMPERATURE, STREAM_TEMPERATURE, STRUCTURED_OUTPUT_STRATEGY, VISION_TEMPERATURE, get
from app.infra.logging import get_logger
from app.infra.utils import ServiceError, parse_first_json_object

if TYPE_CHECKING:
    from app.infra.tool_excute import Tool, ToolEventHandler, ToolExcute

logger = get_logger(__name__)


class ChatModelConfig(BaseModel):
    """LLM 模型配置项。"""
    base_url: str
    api_key: str
    model_name: str
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int | None = None
    timeout: float = 300
    max_retries: int = 2
    model_kwargs: dict[str, Any] = Field(default_factory=dict)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    default_headers: dict[str, str] = Field(default_factory=dict)


class ChatModel(ChatOpenAI):
    """带有防御性 tool_calls 规范化的 ChatOpenAI 子类。"""

    def _create_chat_result(self, response: Any, generation_info: Any | None = None) -> Any:
        try:
            for choice in getattr(response, "choices", None) or []:
                message = getattr(choice, "message", None)
                if message is None or not hasattr(message, "tool_calls"):
                    continue
                tool_calls = getattr(message, "tool_calls")
                if tool_calls is None:
                    continue
                # 处理 dict 和 object 两种格式的 tool_calls
                normalized = (
                    [_fix_tool_call(tool_calls)] if isinstance(tool_calls, dict)
                    else [_fix_tool_call(_to_dict(tc)) for tc in tool_calls]
                )
                object.__setattr__(message, "tool_calls", normalized)
        except Exception as exc:
            logger.warning("[LLM] tool_calls normalization failed: %s", exc)
        return super()._create_chat_result(response, generation_info)


def _to_dict(tc: Any) -> dict[str, Any]:
    """将 tool_call 对象转为 dict（兼容 OpenAI SDK 的对象格式）。"""
    if isinstance(tc, dict):
        return tc
    # OpenAI SDK 返回 ChatCompletionMessageToolCall / FunctionToolCall 对象
    d: dict[str, Any] = {}
    for attr in ("id", "type", "function"):
        val = getattr(tc, attr, None)
        if val is not None:
            d[attr] = val
    # function 可能也是对象，需要转 dict
    fn = d.get("function")
    if fn is not None and not isinstance(fn, dict):
        fn_dict: dict[str, Any] = {}
        for attr in ("name", "arguments"):
            val = getattr(fn, attr, None)
            if val is not None:
                fn_dict[attr] = val
        d["function"] = fn_dict
    return d


def _fix_tool_call(tc: dict[str, Any]) -> dict[str, Any]:
    """修复单个 tool_call 的格式：补充缺失 id，序列化 arguments。"""
    if not tc.get("id"):
        tc = {**tc, "id": f"call_{uuid.uuid4().hex[:12]}"}
    fn = tc.get("function")
    if isinstance(fn, dict) and isinstance(fn.get("arguments"), (dict, list)):
        fn = {**fn, "arguments": json.dumps(fn["arguments"], ensure_ascii=False)}
        tc = {**tc, "function": fn}
    return tc


def _normalize_base_url(base_url: str) -> str:
    """规范化 base_url：去除尾部斜杠和 /chat/completions 后缀。"""
    url = (base_url or "").strip().rstrip("/")
    if url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    return url.rstrip("/")


def _load_config(path: str) -> ChatModelConfig | None:
    """从配置文件加载模型配置，返回 ChatModelConfig 或 None。"""
    raw = get(path, {}) or {}
    if not isinstance(raw, dict) or not raw.get("model_name"):
        return None
    data = {k: v for k, v in raw.items() if k != "vision"}
    if not data.get("base_url") or not data.get("api_key"):
        raise ServiceError(f"{path} 模型配置缺少 base_url 或 api_key")
    return ChatModelConfig(
        base_url=_normalize_base_url(str(data["base_url"])),
        api_key=str(data["api_key"]),
        model_name=str(data["model_name"]),
        temperature=float(data.get("temperature", DEFAULT_TEMPERATURE)),
        max_tokens=data.get("max_tokens"),
        timeout=float(data.get("timeout", 300)),
        max_retries=int(data.get("max_retries", 2)),
        model_kwargs=dict(data.get("model_kwargs") or {}),
        extra_body=dict(data.get("extra_body") or {}),
        default_headers=dict(data.get("default_headers") or {}),
    )


def _create_model(cfg: ChatModelConfig, *, streaming: bool = False) -> ChatModel:
    """根据配置创建 ChatModel 实例。"""
    kw: dict[str, Any] = {
        "model": cfg.model_name,
        "api_key": cfg.api_key,
        "base_url": cfg.base_url,
        "temperature": cfg.temperature,
        "streaming": streaming,
        "timeout": cfg.timeout,
        "max_retries": cfg.max_retries,
        "model_kwargs": cfg.model_kwargs,
    }
    if cfg.max_tokens is not None:
        kw["max_tokens"] = cfg.max_tokens
    if cfg.extra_body:
        kw["extra_body"] = cfg.extra_body
    if cfg.default_headers:
        kw["default_headers"] = cfg.default_headers
    return ChatModel(**kw)


def _bind(model: Any, *, temperature: float | None = None, max_tokens: int | None = None) -> Any:
    """为模型绑定运行时参数（temperature / max_tokens）。"""
    kw: dict[str, Any] = {}
    if temperature is not None:
        kw["temperature"] = temperature
    if max_tokens is not None:
        kw["max_tokens"] = max_tokens
    return model.bind(**kw) if kw else model


def _parse_json(text: str, schema: type[BaseModel]) -> BaseModel:
    """从 LLM 输出文本中严格解析 JSON 并校验为指定 schema。"""
    return schema.model_validate(parse_first_json_object(text))


def _simplify_schema_for_prompt(schema: type[BaseModel]) -> str:
    """构建用于 prompt 的精简 schema 描述，包含枚举值和嵌套字段提示。"""
    full_schema = schema.model_json_schema()
    defs = full_schema.get("$defs", {})
    required = set(full_schema.get("required") or [])
    props = full_schema.get("properties", {})
    lines: list[str] = []
    for name, prop in props.items():
        marker = " (required)" if name in required else ""
        desc = prop.get("description", "")
        type_hint = _describe_property(prop, defs)
        line = f"  {name}: {type_hint}{marker}"
        if desc:
            line += f" — {desc}"
        lines.append(line)
    return schema.__name__ + " {\n" + "\n".join(lines) + "\n}"


def _describe_property(prop: dict[str, Any], defs: dict[str, Any], depth: int = 0) -> str:
    """以人类可读形式描述 JSON schema 属性，包含关键约束。"""
    if depth > 3:
        return "..."
    if "enum" in prop:
        return "enum(" + ", ".join(str(v) for v in prop["enum"]) + ")"
    if "const" in prop:
        return f"const({prop['const']})"
    t = prop.get("type", "")
    # String with constraints
    if t == "string":
        parts: list[str] = ["str"]
        if "pattern" in prop:
            parts.append(f"pattern={prop['pattern']}")
        if "minLength" in prop or "maxLength" in prop:
            mn = prop.get("minLength", "")
            mx = prop.get("maxLength", "")
            if mn and mx:
                parts.append(f"len={mn}-{mx}")
            elif mx:
                parts.append(f"max {mx} chars")
            elif mn:
                parts.append(f"min {mn} chars")
        return " (".join(parts) + ")" if len(parts) > 1 else "str"
    if t == "integer":
        parts = ["int"]
        if "minimum" in prop:
            parts.append(f"min={prop['minimum']}")
        if "maximum" in prop:
            parts.append(f"max={prop['maximum']}")
        return " (".join(parts) + ")" if len(parts) > 1 else "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    # Array with item constraints
    if t == "array":
        items = prop.get("items", {})
        item_desc = _describe_property(items, defs, depth + 1)
        parts = [f"list[{item_desc}]"]
        if "minItems" in prop:
            parts.append(f"min={prop['minItems']}")
        if "maxItems" in prop:
            parts.append(f"max={prop['maxItems']}")
        return " (".join(parts) + ")" if len(parts) > 1 else f"list[{item_desc}]"
    if t == "object" and "properties" in prop:
        inner = prop["properties"]
        fields = ", ".join(inner.keys())
        return f"object({fields})"
    # Reference to another type - expand with required fields
    if "$ref" in prop:
        ref_name = prop["$ref"].split("/")[-1]
        ref_def = defs.get(ref_name, {})
        ref_props = ref_def.get("properties", {})
        ref_required = set(ref_def.get("required", []))
        if ref_props:
            # Build field descriptions with required marker
            field_descs: list[str] = []
            for fname in ref_props:
                ftype = _describe_property(ref_props[fname], defs, depth + 1)
                marker = "*" if fname in ref_required else ""
                field_descs.append(f"{fname}{marker}: {ftype}")
            return f"{ref_name}({'; '.join(field_descs)})"
        return ref_name
    if "anyOf" in prop:
        parts = [_describe_property(p, defs, depth + 1) for p in prop["anyOf"] if isinstance(p, dict)]
        return " | ".join(parts) if parts else "Any"
    return t or "Any"


def _inject_json_instruction(input_data: Any, schema: type[BaseModel]) -> list[BaseMessage]:
    """向消息列表注入 JSON 输出格式指令，确保 LLM 返回符合 schema 的 JSON。"""
    if isinstance(input_data, str):
        msgs: list[BaseMessage] = [HumanMessage(content=input_data)]
    elif isinstance(input_data, BaseMessage):
        msgs = [input_data]
    elif isinstance(input_data, list):
        msgs = list(input_data)
    else:
        raise ValueError(f"Unsupported input_data type: {type(input_data)}")

    schema_desc = _simplify_schema_for_prompt(schema)
    required = schema.model_json_schema().get("required", []) or []
    instruction = (
        "\n\n[FORMAT INSTRUCTION]\n"
        "Return exactly one valid JSON object. Do not include markdown fences or explanatory text.\n"
        f"The root object must contain these required fields: {', '.join(required)}.\n"
        f"Schema:\n{schema_desc}\n"
    )
    for i in range(len(msgs) - 1, -1, -1):
        m = msgs[i]
        if isinstance(m, (HumanMessage, SystemMessage)):
            c = copy.copy(m)
            c.content = str(m.content or "") + instruction
            msgs[i] = c
            return msgs
    msgs.insert(0, SystemMessage(content=instruction.strip()))
    return msgs


def _build_repair_prompt(
    schema: type[BaseModel],
    raw_output: str,
    error_msg: str,
) -> list[BaseMessage]:
    """构造 self-repair 修正 prompt：将失败输出和错误原因喂回模型。

    核心思路：不是从零重新生成，而是让模型看到自己哪里错了，在已有输出基础上修正。
    """
    schema_desc = _simplify_schema_for_prompt(schema)
    return [
        SystemMessage(content=(
            "你是一个 JSON 修正助手。上一次生成的 JSON 存在错误，请根据错误信息修正。\n"
            "规则：\n"
            "- 只输出修正后的完整 JSON 对象\n"
            "- 不要包含 markdown 代码围栏或解释文字\n"
            f"- 必须符合以下 schema:\n{schema_desc}"
        )),
        HumanMessage(content=(
            f"上一次输出（有错误）:\n```\n{raw_output}\n```\n\n"
            f"错误信息:\n{error_msg}\n\n"
            "请输出修正后的完整 JSON。"
        )),
    ]


# 不可重试的错误关键词 — 认证、权限、连接等基础性问题
_UNREPAIRABLE_KEYWORDS = (
    "authorization",
    "PermissionDenied",
    "AuthenticationError",
    "APIConnectionError",
    "RateLimitError",
    "NotFound",
    "401",
    "403",
    "404",
    "429",
)


def _is_repairable_error(error_msg: str) -> bool:
    """判断错误是否值得 self-repair。

    校验类错误（ValidationError、字段缺失、类型不匹配等）是模型输出的问题，
    喂回模型让它在已有输出上修正是有效的。
    认证/权限/连接类错误是基础设施问题，repair 无意义，直接降级。
    """
    msg = error_msg.lower()
    return not any(kw.lower() in msg for kw in _UNREPAIRABLE_KEYWORDS)


class Llm:
    """统一异步 LLM 网关。

    结构化输出策略由 config.yaml 的 models.structured_output_strategy 控制：
    - function_calling_first：优先 function_calling，失败后先 self-repair 修正，
      仍失败再降级 json_mode → prompt
    - json_mode_first：跳过 function_calling，直接 json_mode，同上降级逻辑
    - prompt_first：仅 prompt 注入 + 手动解析
    """

    def __init__(self) -> None:
        self.text_config = _load_config("models")
        self.vision_config = _load_config("models.vision")
        self._text_model = _create_model(self.text_config) if self.text_config else None
        self._vision_model = _create_model(self.vision_config) if self.vision_config else None
        self._strategy = STRUCTURED_OUTPUT_STRATEGY

    @property
    def model(self) -> Any:
        if self._text_model is None:
            raise ServiceError("文本模型配置缺失")
        return self._text_model

    async def ainvoke(self, input_data: Any, *, model: Any | None = None, temperature: float | None = None, max_tokens: int | None = None) -> Any:
        temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
        return await _bind(model or self.model, temperature=temp, max_tokens=max_tokens).ainvoke(input_data)

    async def astream(self, input_data: Any, *, model: Any | None = None, temperature: float | None = None, max_tokens: int | None = None) -> AsyncIterator[Any]:
        temp = temperature if temperature is not None else STREAM_TEMPERATURE
        async for chunk in _bind(model or self.model, temperature=temp, max_tokens=max_tokens).astream(input_data):
            yield chunk

    def create_tool_excute(
        self,
        tools: list[Tool] | None = None,
        event_handler: ToolEventHandler | None = None,
    ) -> ToolExcute:
        from app.infra.tool_excute import ToolExcute

        return ToolExcute(tools, event_handler=event_handler)

    # ------------------------------------------------------------------ #
    #  结构化输出：self-repair 自修正 + 跨模式降级
    # ------------------------------------------------------------------ #

    async def ainvoke_json(
        self,
        schema: type[BaseModel],
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> BaseModel:
        """结构化 JSON 输出：1次生成 → 1次修正 → 降级下一模式。

        流程（每种模式）：
        1. 用首选模式生成 JSON（1 次）
        2. 如果失败，携带真实原文 + 校验错误喂回模型修正（1 次）
        3. 修正仍失败，降级到下一模式，重复 1-2
        4. 所有模式都失败则抛出 ServiceError

        Args:
            schema: Pydantic 模型类，定义输出结构
            input_data: 输入消息（字符串、BaseMessage 或消息列表）
            temperature: 采样温度，默认 0.1（低温度确保结构化输出稳定）
            max_tokens: 最大输出长度

        Returns:
            校验后的 Pydantic 模型实例

        Raises:
            ServiceError: 所有模式 + 修正都失败时抛出
        """
        # 将输入转换为消息列表
        if isinstance(input_data, str):
            messages: list[BaseMessage] = [HumanMessage(content=input_data)]
        elif isinstance(input_data, BaseMessage):
            messages = [input_data]
        elif isinstance(input_data, list):
            messages = list(input_data)
        else:
            raise ValueError(f"Unsupported input_data type: {type(input_data)}")

        # JSON 结构化输出使用低温度确保稳定性和确定性
        json_temp = temperature if temperature is not None else JSON_TEMPERATURE
        model = _bind(self.model, temperature=json_temp, max_tokens=max_tokens)
        errors: list[str] = []
        strategy = self._strategy

        # 按策略确定模式优先级
        if strategy == "function_calling_first":
            tiers = ["function_calling", "json_mode", "prompt"]
        elif strategy == "json_mode_first":
            tiers = ["json_mode", "prompt"]
        else:  # prompt_first
            tiers = ["prompt"]

        for tier in tiers:
            # ── 第1步：生成 1 次 ──
            raw_output = ""
            error_msg = ""
            t0 = time.perf_counter()
            try:
                result, raw_output = await self._invoke_tier(model, tier, schema, messages)
                if not isinstance(result, schema):
                    raise ValueError(f"expected {schema.__name__}, got {type(result).__name__}")
                logger.info(
                    "[LLM] ainvoke_json ok schema=%s tier=%s %dms",
                    schema.__name__, tier,
                    round((time.perf_counter() - t0) * 1000),
                )
                return result
            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                raw_output = raw_output or str(exc)[:500]
                errors.append(f"{tier}(generate)={error_msg}")
                logger.warning(
                    "[LLM] ainvoke_json fail schema=%s tier=%s error=%s",
                    schema.__name__, tier, exc,
                )

            # ── 第2步：携带原文 + 错误修正 1 次 ──
            # 只有校验类错误才值得修正，认证/连接等基础错误直接降级
            if raw_output and _is_repairable_error(error_msg):
                t0 = time.perf_counter()
                repair_content = ""
                try:
                    repair_msgs = _build_repair_prompt(schema, raw_output, error_msg)
                    resp = await model.ainvoke(repair_msgs)
                    repair_content = getattr(resp, "content", "") or ""
                    if not repair_content.strip():
                        raise ValueError("repair: empty response")
                    parsed = _parse_json(repair_content, schema)
                    logger.info(
                        "[LLM] ainvoke_json ok schema=%s tier=%s repair %dms",
                        schema.__name__, tier,
                        round((time.perf_counter() - t0) * 1000),
                    )
                    return parsed
                except Exception as exc:
                    errors.append(f"{tier}(repair)={type(exc).__name__}: {exc}")
                    logger.warning(
                        "[LLM] ainvoke_json fail schema=%s tier=%s repair error=%s",
                        schema.__name__, tier, exc,
                    )

        raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {'; '.join(errors)}")

    async def _invoke_tier(
        self,
        model: Any,
        tier: str,
        schema: type[BaseModel],
        messages: list[BaseMessage],
    ) -> tuple[BaseModel | None, str]:
        """调用单个 tier 模式，返回 (result, raw_output)。

        result 为 None 表示该模式无法产出可解析的结果。
        raw_output 为原始输出文本，用于 self-repair 修正。
        """
        if tier == "function_calling":
            runnable = model.with_structured_output(schema, method="function_calling")
            result = await runnable.ainvoke(messages)
            # function_calling 返回的直接是 Pydantic 实例，序列化为 raw
            raw = result.model_dump_json() if isinstance(result, BaseModel) else str(result)
            return result, raw

        if tier == "json_mode":
            runnable = model.with_structured_output(schema, method="json_mode")
            result = await runnable.ainvoke(messages)
            raw = result.model_dump_json() if isinstance(result, BaseModel) else str(result)
            return result, raw

        # tier == "prompt"
        injected = _inject_json_instruction(messages, schema)
        resp = await model.ainvoke(injected)
        raw = getattr(resp, "content", "") or ""
        if not raw.strip():
            raise ValueError("empty response")
        result = _parse_json(raw, schema)
        return result, raw

    async def vision(self, input_data: Any, *, temperature: float | None = None, max_tokens: int | None = None) -> Any:
        if self._vision_model is None:
            raise ServiceError("图片理解模型配置缺失")
        temp = temperature if temperature is not None else VISION_TEMPERATURE
        return await _bind(self._vision_model, temperature=temp, max_tokens=max_tokens).ainvoke(input_data)


@lru_cache(maxsize=1)
def get_llm() -> Llm:
    return Llm()
