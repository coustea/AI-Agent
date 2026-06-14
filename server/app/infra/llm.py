"""LLM 管理器。

职责：
- 从 config.yaml 加载模型配置
- 提供统一的文本生成和结构化输出接口
- 重试：Tenacity 自动重试机制

使用方式：
    llm = get_llm()

    # 文本生成
    response = await llm.ainvoke(messages)

    # 使用 LangChain 原生工具绑定
    tool_model = llm.model.bind_tools(tools)
    response = await llm.ainvoke(messages, model=tool_model)

    # 结构化 JSON 输出
    result = await llm.ainvoke_json(MySchema, messages)

    # 流式输出
    async for chunk in llm.astream(messages):
        ...

    # 图片理解
    response = await llm.vision(messages)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from app.config import get, INFERENCE_TEMPERATURE, VISION_TEMPERATURE
from app.infra.utils import ServiceError, parse_first_json_object, parse_first_json_value
from app.infra.logging import get_logger

logger = get_logger(__name__)


def _iter_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    s = (text or "").strip()
    candidates: list[dict[str, Any]] = []
    for opener in ("{", "["):
        idx = s.find(opener)
        while idx != -1:
            try:
                value, _end = decoder.raw_decode(s[idx:])
                if isinstance(value, dict):
                    candidates.append(value)
            except json.JSONDecodeError:
                pass
            idx = s.find(opener, idx + 1)
    return candidates


def _flatten_nested_config(data: dict[str, Any], schema: type) -> dict[str, Any]:
    """如果 LLM 输出了嵌套的 config 对象但 schema 期望扁平字段，自动提升到顶层。

    典型场景：PptPayload 的 schema 已扁平化（template_id/topic 是顶层字段），
    但 LLM 仍按旧 prompt 输出 {"config": {"template_id": ...}, "slides": [...]}。
    """
    if not isinstance(data, dict) or "config" not in data:
        return data
    config = data.get("config")
    if not isinstance(config, dict):
        return data
    schema_fields = set(schema.model_fields.keys())
    config_keys_to_lift = [k for k in config if k in schema_fields and k not in data]
    if not config_keys_to_lift:
        return data
    data = dict(data)
    for k in config_keys_to_lift:
        data[k] = config[k]
    del data["config"]
    logger.info("[LLM] 自动扁平化嵌套 config: 提升字段 %s 到顶层", config_keys_to_lift)
    return data


# ============ LLM 管理器 ============

class Llm:
    """统一 LLM 管理器。

    提供四种核心方法：
    - ainvoke(): 异步文本生成
    - astream(): 异步流式输出
    - ainvoke_json(): 异步结构化 JSON 输出
    - vision(): 图片理解
    """

    def __init__(self):
        self._text_model: ChatOpenAI | None = None
        self._vision_model: ChatOpenAI | None = None
        self._text_base_url: str = ""
        self._init()

    @property
    def model(self) -> Any:
        """默认文本模型，供调用方使用 LangChain 原生 bind/bind_tools。"""
        if not self._text_model:
            raise ServiceError("文本模型配置缺失")
        return self._text_model

    def _init(self):
        """初始化模型。"""
        # 文本模型配置
        text_cfg = get("models", {})
        text_cfg = {k: v for k, v in text_cfg.items() if k != "vision"}

        if text_cfg and "model_name" in text_cfg:
            self._text_base_url = text_cfg["base_url"].rstrip("/chat/completions").rstrip("/")
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
            logger.info("[LLM] 文本模型初始化: model=%s base_url=%s", text_cfg["model_name"], self._text_base_url)

        # 图片理解模型配置
        vision_cfg = get("models.vision", {})
        if vision_cfg and "model_name" in vision_cfg:
            self._vision_model = ChatOpenAI(
                model=vision_cfg["model_name"],
                api_key=vision_cfg["api_key"],
                base_url=vision_cfg["base_url"].rstrip("/chat/completions").rstrip("/"),
                temperature=vision_cfg.get("temperature", VISION_TEMPERATURE),
                streaming=False,
                max_retries=vision_cfg.get("max_retries", 2),
                timeout=vision_cfg.get("timeout", 300),
            )
            logger.info("[LLM] 视觉模型初始化: model=%s", vision_cfg["model_name"])

    # ============ 核心方法 ============

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
        if not bind_kwargs:
            return runnable
        return runnable.bind(**bind_kwargs)

    async def ainvoke(
        self,
        input_data,
        *,
        model: Any | None = None,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> Any:
        """异步文本生成。

        Args:
            input_data: 输入数据（消息列表或提示词）。
            temperature: 温度参数。
            max_tokens: 最大 token 数。

        Returns:
            模型响应。
        """
        runnable = self._bind_text_model(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        result = await runnable.ainvoke(input_data)
        return result

    async def astream(
        self,
        input_data,
        *,
        model: Any | None = None,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Any]:
        """异步流式生成。

        Args:
            input_data: 输入数据。
            temperature: 温度参数。
            max_tokens: 最大 token 数。

        Yields:
            流式响应块。
        """
        runnable = self._bind_text_model(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Force provider streaming even when the reusable base model defaults to non-streaming invokes.
        async for chunk in runnable.astream(input_data, stream=True):
            yield chunk

    def _prepare_messages_for_json(self, input_data: Any, schema: type) -> list[BaseMessage]:
        """将不同格式的输入安全转换为 BaseMessage 列表，并强行注入 JSON 格式指令。
        
        为什么需要这个方法？
        当模型无法使用 API 原生 Tool Calling 时，如果不将数据包装成标准的对话消息 (Message)，
        而是直接进行 f"{input_data}" 字符串拼接，会导致多轮对话历史变成 Python 对象的乱码，
        从而使模型产生严重的“格式幻觉”。此方法会安全地保留对话历史，只在最后一条消息注入指令。
        """
        # 1. 统一转成 Message 列表
        if isinstance(input_data, str):
            messages = [HumanMessage(content=input_data)]
        elif isinstance(input_data, BaseMessage):
            messages = [input_data]
        elif isinstance(input_data, list):
            # 浅拷贝避免修改外部传入的原始对话列表
            messages = list(input_data)
        else:
            raise ValueError(f"Unsupported input_data type: {type(input_data)}")

        # 2. 构造必须带有 "JSON" 字眼的强制指令（适配类似 Qwen 这种强规则模型）
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)

        # 提取 required 顶层字段作为显式提醒，防止模型输出嵌套子对象而非根对象
        json_schema = schema.model_json_schema()
        required_fields = json_schema.get("required", [])
        root_reminder = ""
        if required_fields:
            root_reminder = (
                f"\nCRITICAL: The root JSON object MUST contain these required fields: "
                f"{', '.join(required_fields)}. "
                f"Do NOT return a nested sub-object — return the complete root object.\n"
            )

        instruction = (
            f"\n\n[FORMAT INSTRUCTION]\n"
            f"You must return the response as a valid JSON object matching the JSON Schema below.\n"
            f"Do not include any explanation, markdown code fence blocks (like ```json), or extra text outside the JSON object.\n"
            f"{root_reminder}"
            f"JSON Schema:\n{schema_hint}\n"
        )

        # 3. 倒序查找，将指令拼接到最后一条人类或系统消息的末尾
        inserted = False
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if isinstance(msg, (HumanMessage, SystemMessage)):
                from copy import copy
                new_msg = copy(msg)
                new_msg.content = str(msg.content or "") + instruction
                messages[i] = new_msg
                inserted = True
                break
                
        # 4. 如果没找到合适的消息（比如全是 AI 回复），直接插在开头
        if not inserted:
            messages.insert(0, SystemMessage(content=instruction.strip()))
            
        return messages

    async def ainvoke_json(
        self,
        schema: type,
        input_data,
        *,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
        function_name: str | None = None,
        function_description: str | None = None,
    ) -> Any:
        """异步结构化 JSON 输出核心调度器（“三段式瀑布”容错降级机制）。
        
        由于不同厂商大模型对 OpenAI API 的兼容度不一，此方法依次尝试三种提取策略，
        上层策略报错时自动跌入下一层，确保最终拿到 Pydantic 校验通过的 JSON。
        
        执行优先级：
        1. [首选] Tool Calling: 利用大模型的函数调用能力提取（性能最好，支持嵌套数组）。
        2. [降级] JSON Mode: 开启 json_object 模式，要求模型直接吐出原生 JSON。
        3. [兜底] Text Prompt: 关闭高级功能，纯靠正则匹配和大括号清洗兜底提取。
        """
        model = self._bind_text_model(temperature=temperature, max_tokens=max_tokens)
        name = function_name or schema.__name__
        desc = function_description or f"Return {schema.__name__}"
        errors: list[str] = []

        # ============ 提前准备兜底用消息（注入强制 Schema 指令） ============
        # 将提示词增强（显式注入 Schema）提前，无论是哪一层调用都能受益
        enhanced_messages = self._prepare_messages_for_json(input_data, schema)
        input_preview = ""
        for msg in enhanced_messages:
            c = getattr(msg, "content", "")
            if isinstance(c, str) and c:
                input_preview = c[:120].replace("\n", " ")
                break
        logger.info(
            "[LLM] ainvoke_json 开始: schema=%s messages=%d input_preview='%s'",
            schema.__name__, len(enhanced_messages), input_preview,
        )

        # ============ Tier 1: Tool Calling (函数调用) ============
        tools = [{
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                # 注意：为了最大化适配星火、Qwen等第三方模型，这里去掉了 "strict": True
                "parameters": schema.model_json_schema(),
            },
        }]
        try:
            # 使用最高兼容性的 tool_choice 格式：精准定向具体的工具名称，防止模型自由发挥
            runnable = model.bind_tools(
                tools,
                tool_choice={"type": "function", "function": {"name": name}}
            )
            # [关键优化] 把带有详细 Schema 指令的 enhanced_messages 传给大模型
            resp = await runnable.ainvoke(enhanced_messages)

            # 检查是否按预期返回了 tool_calls
            tool_calls = getattr(resp, "tool_calls", []) or []
            content_resp = getattr(resp, "content", "") or ""
            logger.info(
                "[LLM] Tier1 响应: tool_calls=%d content_len=%d",
                len(tool_calls), len(str(content_resp)),
            )
            for tool_call in tool_calls:
                call_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
                if call_name and call_name != name:
                    continue
                args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)
                if args:
                    if isinstance(args, str):
                        args = json.loads(args)
                        
                    # [关键优化] 递归清理嵌套的 JSON 字符串 (Stringified JSON)
                    # 防止部分模型在 Tool Calling 时，把复杂的嵌套对象输出成了格式化字符串
                    def _clean_nested_json(data: Any) -> Any:
                        if isinstance(data, dict):
                            return {k: _clean_nested_json(v) for k, v in data.items()}
                        elif isinstance(data, list):
                            return [_clean_nested_json(v) for v in data]
                        elif isinstance(data, str):
                            s = data.strip()
                            if "{" in s or "[" in s:
                                try:
                                    parsed = parse_first_json_value(s)
                                    if isinstance(parsed, (dict, list)):
                                        return _clean_nested_json(parsed)
                                except (json.JSONDecodeError, TypeError):
                                    pass
                        return data
                        
                    cleaned_args = _clean_nested_json(args)
                    cleaned_args = _flatten_nested_config(cleaned_args, schema)
                    logger.info("[LLM] Tier1(tool_calling) 成功: schema=%s", schema.__name__)
                    return schema.model_validate(cleaned_args)

            # 特殊情况处理：有些奇葩模型即使用 bind_tools 也会把 JSON 塞在普通文本(content)里
            content = getattr(resp, "content", "") or ""
            if content:
                parsed = parse_first_json_object(content)
                parsed = _flatten_nested_config(parsed, schema)
                return schema.model_validate(parsed)
        except Exception as exc:
            errors.append(f"tier1(tool_calling)={type(exc).__name__}: {exc}")
            logger.warning("[LLM] Tier1(tool_calling) 失败: %s: %s", type(exc).__name__, exc)

        # ============ Tier 2: JSON Mode (原生 JSON 模式) ============
        try:
            # 开启 json_object 强校验模式（如果 API 支持的话）
            fallback_model = model.bind(response_format={"type": "json_object"})
            resp = await fallback_model.ainvoke(enhanced_messages)
            content = getattr(resp, "content", "") or ""
            logger.info("[LLM] Tier2(json_mode) 响应: content_len=%d", len(content))
            parsed = parse_first_json_object(content)
            parsed = _flatten_nested_config(parsed, schema)
            return schema.model_validate(parsed)
        except Exception as exc:
            errors.append(f"tier2(json_mode)={type(exc).__name__}: {exc}")
            logger.warning("[LLM] Tier2(json_mode) 失败: %s: %s", type(exc).__name__, exc)

        # ============ Tier 3: Text Prompting (纯文本解析兜底) ============
        # 如果前面两层全挂了（比如本地老模型），直接当做普通对话聊天，然后我们自己清洗
        try:
            resp = await model.ainvoke(enhanced_messages)
            content = getattr(resp, "content", "") or ""
            logger.info("[LLM] Tier3(text) 响应: content_len=%d", len(content))
            
            # _iter_json_objects 能在混杂各种解释文本（甚至 Markdown 语法）的内容中找出所有的 JSON 块
            candidates = _iter_json_objects(content)
            if not candidates:
                parsed = parse_first_json_object(content)
                parsed = _flatten_nested_config(parsed, schema)
                return schema.model_validate(parsed)

            last_error: Exception | None = None
            for candidate in candidates:
                try:
                    candidate = _flatten_nested_config(candidate, schema)
                    return schema.model_validate(candidate)
                except Exception as e:
                    last_error = e
                    continue
            raise ValueError(f"未找到符合 {schema.__name__} 的 JSON 对象") from last_error

        except Exception as exc:
            errors.append(f"tier3(text_prompt)={type(exc).__name__}: {exc}")
            logger.error("[LLM] ainvoke_json 全部失败: schema=%s errors=%s", schema.__name__, "; ".join(errors))
            raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {'; '.join(errors)}")

    async def vision(
        self,
        input_data,
        *,
        temperature: float = INFERENCE_TEMPERATURE,
    ) -> Any:
        """图片理解生成。

        Args:
            input_data: 输入数据（包含图片的消息）。
            temperature: 温度参数。

        Returns:
            模型响应。
        """
        if not self._vision_model:
            raise ServiceError("图片理解模型配置缺失")

        model = self._vision_model
        if temperature != INFERENCE_TEMPERATURE:
            model = model.bind(temperature=temperature)
        result = await model.ainvoke(input_data)
        return result

# ============ 单例 ============

from functools import lru_cache

@lru_cache(maxsize=1)
def get_llm() -> Llm:
    """获取 LLM 单例。"""
    return Llm()
