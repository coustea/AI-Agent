"""LLM 管理器。

职责：
- 从 config.yaml 加载模型配置
- 提供统一的文本生成、流式生成、工具调用、结构化 JSON 输出和图片理解接口
- 重试：使用 ChatOpenAI 自带 max_retries

使用方式：
    llm = get_llm()

    # 文本生成
    response = await llm.ainvoke(messages)

    # 使用 LangChain 原生工具绑定
    tool_model = llm.model.bind_tools(tools)
    response = await llm.ainvoke(messages, model=tool_model)

    # 或使用封装后的工具调用
    response = await llm.ainvoke_tools(messages, tools)

    # 结构化 JSON 输出（prompt 规范输出 → 正则解析，tool_calling 保底）
    result = await llm.ainvoke_json(MySchema, messages)

    # 流式输出
    async for chunk in llm.astream(messages):
        ...

    # 图片理解
    response = await llm.vision(messages)
"""

from __future__ import annotations

import copy
import json
import time
from functools import lru_cache
from typing import Any, AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import INFERENCE_TEMPERATURE, VISION_TEMPERATURE, get
from app.infra.logging import get_logger
from app.infra.utils import (
    ServiceError,
    parse_first_json_object,
    parse_first_json_value,
    strip_markdown_code_fences,
)

logger = get_logger(__name__)


import uuid

class SparkCompatibleChatOpenAI(ChatOpenAI):
    """讯飞星火 OpenAI 兼容接口定制客户端。
    
    拦截并规范化不符合规范的 tool_calls 格式（如字典格式、缺失 id 等）。
    """
    def _create_chat_result(self, response: Any, generation_info: Any | None = None) -> Any:
        try:
            if hasattr(response, "choices") and response.choices:
                for choice in response.choices:
                    if hasattr(choice, "message") and choice.message:
                        msg = choice.message
                        if hasattr(msg, "tool_calls") and msg.tool_calls is not None:
                            tool_calls = msg.tool_calls
                            if isinstance(tool_calls, dict):
                                if "id" not in tool_calls or not tool_calls["id"]:
                                    tool_calls["id"] = f"call_{uuid.uuid4().hex[:12]}"
                                object.__setattr__(msg, "tool_calls", [tool_calls])
                            elif isinstance(tool_calls, list):
                                for tc in tool_calls:
                                    if isinstance(tc, dict) and ("id" not in tc or not tc["id"]):
                                        tc["id"] = f"call_{uuid.uuid4().hex[:12]}"
        except Exception as exc:
            logger.warning("[LLM] 规范化星火 tool_calls 失败: %s", exc)
        return super()._create_chat_result(response, generation_info)


# ── URL 工具 ──────────────────────────────────────────────────────────────────


def _normalize_base_url(url: str) -> str:
    """规范化 OpenAI 兼容接口 base_url。

    不能用 rstrip("/chat/completions")，rstrip 按字符集合删除会误删正常字符。
    """
    normalized = (url or "").strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        normalized = normalized.removesuffix("/chat/completions")
    return normalized.rstrip("/")


# ── JSON Schema 兼容处理 ──────────────────────────────────────────────────────


def _simplify_anyof_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """将 anyOf: [{"$ref": "..."}, {"type": "null"}] 简化为直接 $ref。

    Pydantic v2 对 Optional[X] 生成 anyOf + $ref，星火/GLM 等模型
    的 function calling 不兼容这种结构。简化后用 default 值兜底 null。
    """
    result = copy.deepcopy(schema)

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if "anyOf" in obj and isinstance(obj["anyOf"], list) and len(obj["anyOf"]) == 2:
                items = obj["anyOf"]
                ref_item = next((it for it in items if isinstance(it, dict) and "$ref" in it), None)
                null_item = next(
                    (it for it in items if isinstance(it, dict) and it.get("type") == "null"),
                    None,
                )
                if ref_item and null_item:
                    new_obj = {k: v for k, v in obj.items() if k != "anyOf"}
                    new_obj.update(ref_item)
                    obj.clear()
                    obj.update(new_obj)

            for value in list(obj.values()):
                _walk(value)

        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(result)
    return result


# ── JSON 提取 ─────────────────────────────────────────────────────────────────


def _deduplicate_json_objects(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 JSON 序列化结果去重，避免同一个对象被重复验证。"""
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:
        try:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        except TypeError:
            key = str(item)
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def _extract_json_objects(text: str) -> list[dict[str, Any]]:
    """从混杂文本中提取所有顶层 JSON 对象。

    从每个 ``{`` 或 ``[`` 位置尝试 raw_decode，
    顶层对象或数组内的对象均加入候选集。
    """
    decoder = json.JSONDecoder()
    s = strip_markdown_code_fences(text or "").strip()
    candidates: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            candidates.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    candidates.append(item)

    for i, char in enumerate(s):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(s[i:])
            collect(value)
        except json.JSONDecodeError:
            pass

    return _deduplicate_json_objects(candidates)


def _extract_root_candidates(text: str, schema: type) -> list[dict[str, Any]]:
    """提取与 schema 根对象结构匹配的 JSON 候选。

    模型经常在 JSON 前后附加说明文字，或嵌套输出子对象。
    此方法递归扫描所有可解析 JSON，只保留包含 schema 必填字段的候选，
    避免把内部子对象误判为根对象。
    """
    decoder = json.JSONDecoder()
    s = strip_markdown_code_fences(text or "").strip()
    required = _schema_required_keys(schema)
    candidates: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            if required and required.issubset(value.keys()):
                candidates.append(value)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    for i, char in enumerate(s):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(s[i:])
            collect(value)
        except json.JSONDecodeError:
            pass

    return _deduplicate_json_objects(candidates)


# ── JSON 修复 ─────────────────────────────────────────────────────────────────


def _flatten_nested_config(data: dict[str, Any], schema: type) -> dict[str, Any]:
    """如果 LLM 输出了嵌套的 config 对象但 schema 期望扁平字段，自动提升到顶层。

    典型场景：PptPayload schema 已扁平化（template_id/topic 是顶层字段），
    但 LLM 仍输出 {"config": {"template_id": ...}, "slides": [...]}。
    """
    if not isinstance(data, dict) or "config" not in data:
        return data

    config = data.get("config")
    if not isinstance(config, dict):
        return data

    schema_fields = set(getattr(schema, "model_fields", {}).keys())
    keys_to_lift = [k for k in config if k in schema_fields and k not in data]

    if not keys_to_lift:
        return data

    flattened = dict(data)
    for k in keys_to_lift:
        flattened[k] = config[k]
    del flattened["config"]

    logger.info("[LLM] 自动扁平化嵌套 config: 提升字段 %s 到顶层", keys_to_lift)
    return flattened


def _clean_nested_json(data: Any) -> Any:
    """递归清理嵌套的 JSON 字符串。

    部分模型在 Tool Calling 时把复杂嵌套对象输出成格式化字符串。
    """
    if isinstance(data, dict):
        return {k: _clean_nested_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_clean_nested_json(item) for item in data]
    if isinstance(data, str):
        s = data.strip()
        if "{" in s or "[" in s:
            try:
                parsed = parse_first_json_value(s)
                if isinstance(parsed, (dict, list)):
                    return _clean_nested_json(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
    return data


# ── Schema 辅助 ───────────────────────────────────────────────────────────────


def _schema_required_keys(schema: type) -> set[str]:
    """获取 schema 顶层必填字段。Pydantic Schema 缺失 required 时退回 model_fields。"""
    try:
        required = set(schema.model_json_schema().get("required", []) or [])
    except Exception:
        required = set()
    return required or set(getattr(schema, "model_fields", {}).keys())


def _score_json_candidate(candidate: dict[str, Any], schema: type) -> int:
    """根据 schema 字段对 JSON 候选打分，分数越高越像根对象。"""
    required = _schema_required_keys(schema)
    fields = set(getattr(schema, "model_fields", {}).keys())
    keys = set(candidate.keys())
    return len(required & keys) * 10 + len(fields & keys)


# ── LLM 管理器 ────────────────────────────────────────────────────────────────


class Llm:
    """统一 LLM 管理器。

    提供五种核心方法：
    - ainvoke(): 异步文本生成
    - astream(): 异步流式输出
    - ainvoke_tools(): 异步工具调用
    - ainvoke_json(): 异步结构化 JSON 输出（prompt 规范输出 → 正则解析，tool_calling 保底）
    - vision(): 图片理解
    """

    def __init__(self) -> None:
        self._text_model: ChatOpenAI | None = None
        self._vision_model: ChatOpenAI | None = None
        self._text_base_url: str = ""
        self._text_model_name: str = ""
        self._init()

    @property
    def model(self) -> Any:
        """默认文本模型，供调用方使用 LangChain 原生 bind/bind_tools。"""
        if not self._text_model:
            raise ServiceError("文本模型配置缺失")
        return self._text_model

    # ── 初始化 ────────────────────────────────────────────────────────────────

    def _init(self) -> None:
        self._init_text_model()
        self._init_vision_model()

    def _init_text_model(self) -> None:
        text_cfg = get("models", {})
        text_cfg = {k: v for k, v in text_cfg.items() if k != "vision"}

        if not text_cfg or "model_name" not in text_cfg:
            return

        self._text_base_url = _normalize_base_url(text_cfg["base_url"])
        self._text_model_name = text_cfg["model_name"]

        self._text_model = ChatOpenAI(
            model=text_cfg["model_name"],
            api_key=text_cfg["api_key"],
            base_url=self._text_base_url,
            temperature=INFERENCE_TEMPERATURE,
            streaming=False,
            max_retries=text_cfg.get("max_retries", 2),
            timeout=text_cfg.get("timeout", 300),
            max_tokens=text_cfg.get("max_tokens"),
        )

        logger.info(
            "[LLM] 文本模型初始化: model=%s base_url=%s",
            text_cfg["model_name"],
            self._text_base_url,
        )

    def _init_vision_model(self) -> None:
        vision_cfg = get("models.vision", {})
        if not vision_cfg or "model_name" not in vision_cfg:
            return

        self._vision_model = ChatOpenAI(
            model=vision_cfg["model_name"],
            api_key=vision_cfg["api_key"],
            base_url=_normalize_base_url(vision_cfg["base_url"]),
            temperature=vision_cfg.get("temperature", VISION_TEMPERATURE),
            streaming=False,
            max_retries=vision_cfg.get("max_retries", 2),
            timeout=vision_cfg.get("timeout", 300),
        )

        logger.info("[LLM] 视觉模型初始化: model=%s", vision_cfg["model_name"])

    # ── 模型绑定 ──────────────────────────────────────────────────────────────

    def _bind_text_model(
        self,
        *,
        model: Any | None = None,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> Any:
        """按调用参数绑定文本模型。"""
        runnable = model or self.model
        bind_kwargs: dict[str, Any] = {}
        if temperature != INFERENCE_TEMPERATURE:
            bind_kwargs["temperature"] = temperature
        if max_tokens is not None:
            bind_kwargs["max_tokens"] = max_tokens
        return runnable.bind(**bind_kwargs) if bind_kwargs else runnable

    # ── 普通文本 / 流式 / 工具调用 ────────────────────────────────────────────

    async def ainvoke(
        self,
        input_data: Any,
        *,
        model: Any | None = None,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> Any:
        """异步文本生成。"""
        runnable = self._bind_text_model(model=model, temperature=temperature, max_tokens=max_tokens)
        return await runnable.ainvoke(input_data)

    async def astream(
        self,
        input_data: Any,
        *,
        model: Any | None = None,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Any]:
        """异步流式生成。"""
        runnable = self._bind_text_model(model=model, temperature=temperature, max_tokens=max_tokens)
        async for chunk in runnable.astream(input_data, stream=True):
            yield chunk

    async def ainvoke_tools(
        self,
        input_data: Any,
        tools: list[Any],
        *,
        tool_choice: Any | None = None,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> Any:
        """异步工具调用（LangChain bind_tools 的轻量封装）。"""
        model = self._bind_text_model(temperature=temperature, max_tokens=max_tokens)
        runnable = model.bind_tools(tools) if tool_choice is None else model.bind_tools(tools, tool_choice=tool_choice)
        return await runnable.ainvoke(input_data)

    # ── JSON 输出：消息准备 ───────────────────────────────────────────────────

    def _inject_format_instruction(self, input_data: Any, schema: type) -> list[BaseMessage]:
        """将输入转换为 BaseMessage 列表，并在最后一条消息中注入 JSON 格式指令。

        直接字符串拼接会破坏多轮对话历史，此方法只在最后一条
        HumanMessage / SystemMessage 末尾追加指令。
        """
        if isinstance(input_data, str):
            messages: list[BaseMessage] = [HumanMessage(content=input_data)]
        elif isinstance(input_data, BaseMessage):
            messages = [input_data]
        elif isinstance(input_data, list):
            messages = list(input_data)
        else:
            raise ValueError(f"Unsupported input_data type: {type(input_data)}")

        instruction = self._build_format_instruction(schema)

        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if isinstance(msg, (HumanMessage, SystemMessage)):
                new_msg = copy.copy(msg)
                new_msg.content = str(msg.content or "") + instruction
                messages[i] = new_msg
                return messages

        messages.insert(0, SystemMessage(content=instruction.strip()))
        return messages

    @staticmethod
    def _build_format_instruction(schema: type) -> str:
        """构建注入到消息末尾的 JSON 格式指令。"""
        json_schema = schema.model_json_schema()
        schema_hint = json.dumps(json_schema, ensure_ascii=False, indent=2)

        parts = [
            "\n\n[FORMAT INSTRUCTION]",
            "You must return the response as a valid JSON object matching the JSON Schema below.",
            "Do not include any explanation, markdown code fence blocks (like ```json), "
            "or extra text outside the JSON object.",
        ]

        required_fields = json_schema.get("required", [])
        if required_fields:
            parts.append(
                f"CRITICAL: The root JSON object MUST contain these required fields: "
                f"{', '.join(required_fields)}. "
                "Do NOT return a nested sub-object — return the complete root object."
            )

        min_length_hints: list[str] = []
        for field_name, field_info in schema.model_fields.items():
            min_len = getattr(field_info, "min_length", None)
            if min_len and min_len > 0:
                min_length_hints.append(f"  - {field_name}: at least {min_len} items")

        if min_length_hints:
            parts.append(
                "CRITICAL: The following list fields MUST NOT be empty or shorter than their minimum:\n"
                + "\n".join(min_length_hints)
            )

        parts.append(f"JSON Schema:\n{schema_hint}")
        return "\n".join(parts) + "\n"

    # ── JSON 输出：从文本解析 ─────────────────────────────────────────────────

    def _parse_json_from_text(self, content: str, schema: type) -> Any:
        """从模型文本输出中提取并验证 JSON 对象。

        提取策略：
        1. 优先提取包含 schema 必填字段的根对象候选
        2. 回退到通用提取器
        3. 最终尝试 parse_first_json_object

        每个候选按 schema 字段匹配度评分，从高到低尝试 Pydantic 校验。
        """
        # 精确提取：只保留包含所有必填字段的候选
        candidates = _extract_root_candidates(content, schema)
        # 回退：通用提取
        if not candidates:
            candidates = _extract_json_objects(content)

        logger.info("[LLM] JSON 候选对象数量=%d", len(candidates))

        # 无候选时直接暴力解析
        if not candidates:
            parsed = parse_first_json_object(content)
            parsed = _flatten_nested_config(parsed, schema)
            return schema.model_validate(parsed)

        # 按字段匹配度评分，从高到低验证
        scored = sorted(candidates, key=lambda c: _score_json_candidate(c, schema), reverse=True)

        last_error: Exception | None = None
        for i, candidate in enumerate(scored):
            score = _score_json_candidate(candidate, schema)
            logger.debug(
                "[LLM] 验证候选[%d/%d]: score=%d keys=%s",
                i + 1, len(scored), score, sorted(candidate.keys())[:10],
            )
            try:
                candidate = _flatten_nested_config(candidate, schema)
                return schema.model_validate(candidate)
            except Exception as exc:
                last_error = exc
                logger.debug("[LLM] 候选[%d/%d] 验证失败: %s", i + 1, len(scored), exc)

        raise ValueError(f"未找到符合 {schema.__name__} 的 JSON 对象") from last_error

    # ── JSON 输出：Tool Calling 解析 ──────────────────────────────────────────

    def _parse_tool_call_args(self, tool_call: Any, function_name: str, schema: type) -> Any | None:
        """解析单个 tool_call 的 args，尝试 Pydantic 校验。不匹配则返回 None。"""
        call_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)

        if call_name and call_name != function_name:
            return None

        args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)

        if not args:
            logger.warning("[LLM] tool_call args 为空, call_name=%s", call_name)
            return None

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as exc:
                logger.warning("[LLM] tool_call args JSON 解析失败: %s", exc)
                return None

        cleaned = _clean_nested_json(args)
        cleaned = _flatten_nested_config(cleaned, schema)

        try:
            return schema.model_validate(cleaned)
        except Exception as exc:
            logger.warning("[LLM] tool_call Pydantic 验证失败: %s", exc)
            return None

    # ── JSON 输出：两层 Fallback ──────────────────────────────────────────────

    async def _invoke_via_prompt(self, model: Any, messages: list[BaseMessage], schema: type) -> Any:
        """第一层：prompt 规范输出 + 正则解析。"""
        t0 = time.perf_counter()

        logger.info("[LLM] prompt 解析层开始: schema=%s", schema.__name__)

        resp = await model.ainvoke(messages)
        content = getattr(resp, "content", "") or ""

        logger.info(
            "[LLM] prompt 解析层响应: content_len=%d preview='%s'",
            len(content), content[:200],
        )

        if not content.strip():
            raise ValueError("模型返回空内容")

        result = self._parse_json_from_text(content, schema)

        logger.info(
            "[LLM] prompt 解析层成功: schema=%s duration_ms=%d",
            schema.__name__, _elapsed_ms(t0),
        )
        return result

    async def _invoke_via_tool_calling(
        self,
        model: Any,
        messages: list[BaseMessage],
        schema: type,
        function_name: str,
        function_description: str,
    ) -> Any:
        """第二层：Tool Calling 保底。"""
        t0 = time.perf_counter()

        logger.info("[LLM] tool_calling 层开始: schema=%s tool_name=%s", schema.__name__, function_name)

        raw_schema = schema.model_json_schema()
        simplified_schema = _simplify_anyof_refs(raw_schema)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": function_name,
                    "description": function_description,
                    "parameters": simplified_schema,
                },
            }
        ]

        runnable = model.bind_tools(
            tools,
            tool_choice={"type": "function", "function": {"name": function_name}},
        )
        resp = await runnable.ainvoke(messages)

        tool_calls = getattr(resp, "tool_calls", []) or []
        logger.info("[LLM] tool_calling 层响应: tool_calls=%d", len(tool_calls))

        # 尝试从 tool_calls 中解析
        for i, tc in enumerate(tool_calls):
            result = self._parse_tool_call_args(tc, function_name, schema)
            if result is not None:
                logger.info(
                    "[LLM] tool_calling 层成功: schema=%s duration_ms=%d",
                    schema.__name__, _elapsed_ms(t0),
                )
                return result

        # tool_calls 为空时，尝试从 content 解析 JSON（部分模型不返回 tool_calls 而是输出在 content）
        content = getattr(resp, "content", "") or ""
        if content.strip():
            logger.info("[LLM] tool_calling 层无 tool_calls，尝试从 content 解析: content_len=%d", len(content))
            result = self._parse_json_from_text(content, schema)
            logger.info(
                "[LLM] tool_calling 层(content 回退)成功: schema=%s duration_ms=%d",
                schema.__name__, _elapsed_ms(t0),
            )
            return result

        raise ValueError("模型未返回可用 tool_calls 或 JSON content")

    # ── JSON 输出：调度入口 ───────────────────────────────────────────────────

    async def ainvoke_json(
        self,
        schema: type,
        input_data: Any,
        *,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
        function_name: str | None = None,
        function_description: str | None = None,
    ) -> Any:
        """异步结构化 JSON 输出。

        两层 fallback：
        1. prompt 规范输出 + 正则解析（快、稳定、适配所有模型）
        2. tool_calling 保底（当 prompt 层解析失败时兜底）
        """
        model = self._bind_text_model(temperature=temperature, max_tokens=max_tokens)
        fn_name = function_name or schema.__name__
        fn_desc = function_description or f"Return {schema.__name__}"
        messages = self._inject_format_instruction(input_data, schema)

        logger.info(
            "[LLM] ainvoke_json 开始: schema=%s messages=%d preview='%s'",
            schema.__name__, len(messages), _messages_preview(messages),
        )

        errors: list[str] = []

        # 第一层：prompt 规范输出 + 正则解析
        try:
            return await self._invoke_via_prompt(model, messages, schema)
        except Exception as exc:
            errors.append(f"prompt={type(exc).__name__}: {exc}")
            logger.warning("[LLM] prompt 层失败: schema=%s error=%s", schema.__name__, exc)

        # 第二层：tool_calling 保底
        try:
            return await self._invoke_via_tool_calling(model, messages, schema, fn_name, fn_desc)
        except Exception as exc:
            errors.append(f"tool_calling={type(exc).__name__}: {exc}")
            logger.warning("[LLM] tool_calling 层失败: schema=%s error=%s", schema.__name__, exc)

        raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {'; '.join(errors)}")

    # ── 图片理解 ───────────────────────────────────────────────────────────────

    async def vision(self, input_data: Any, *, temperature: float = INFERENCE_TEMPERATURE) -> Any:
        """图片理解生成。"""
        if not self._vision_model:
            raise ServiceError("图片理解模型配置缺失")

        model = self._vision_model
        if temperature != INFERENCE_TEMPERATURE:
            model = model.bind(temperature=temperature)
        return await model.ainvoke(input_data)


# ── 辅助函数 ──────────────────────────────────────────────────────────────────


def _elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def _messages_preview(messages: list[BaseMessage], limit: int = 120) -> str:
    for msg in messages:
        content = getattr(msg, "content", "")
        if isinstance(content, str) and content:
            return content[:limit].replace("\n", " ")
    return ""


# ── 单例 ──────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_llm() -> Llm:
    """获取 LLM 单例。"""
    return Llm()
