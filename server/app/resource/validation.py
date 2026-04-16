"""
资源 Agent 通用校验工具。

提供跨 Agent 的共享校验辅助函数：
- extract_json_from_text: 从 LLM 响应中提取 JSON
- extract_last_ai_content: 提取最后一条 AI 消息内容
- make_validation_result: 构建标准校验返回字典
- validate_json_response: JSON + Pydantic 统一校验流程
"""

import json
import re
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage

# 匹配 fenced code block 中的 JSON（```json ... ``` 或 ``` ... ```）
_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def extract_json_from_text(text: str) -> str:
    """从文本中提取 JSON 内容，支持 fenced code block 和裸 JSON。

    Args:
        text: 可能包含 JSON 的原始文本

    Returns:
        提取到的 JSON 字符串，未匹配则返回原文本
    """
    # 先去掉首尾空白，避免 fenced code block 前后换行影响匹配。
    text = text.strip()
    match = _FENCE_RE.search(text)
    if match:
        # 优先提取 ```json ... ``` 里的内容，因为这是最常见的模型输出格式。
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        # 如果没有 code fence，就退化为提取最外层 JSON 对象。
        return text[start:end]
    return text


def extract_last_ai_content(
    messages: list[AnyMessage],
    skip_tool_calls: bool = False,
) -> str:
    """提取消息列表中最后一条 AI 消息的文本内容。

    Args:
        messages: LangChain 消息列表
        skip_tool_calls: 是否跳过包含 tool_calls 的 AI 消息

    Returns:
        最后一条 AI 消息的内容字符串，未找到返回空字符串
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            if skip_tool_calls and msg.tool_calls:
                # 某些 Agent 会先返回带工具调用的 AIMessage，这里允许调用方跳过它们。
                continue
            content = msg.content
            return content.strip() if isinstance(content, str) else str(content).strip()
    return ""


def make_validation_result(
    is_valid: bool,
    retry_count: int,
    feedback: str = "",
    **fields: Any,
) -> dict[str, Any]:
    """构建标准的校验结果字典。

    Args:
        is_valid: 是否通过校验
        retry_count: 当前重试次数（自动 +1）
        feedback: 校验反馈信息
        **fields: 附加字段（如 questions_json、parsed_questions 等）

    Returns:
        适合从 _validate_node 返回的字典
    """
    # 统一返回结构，避免每个 Agent 的 validate 节点手写一套字段。
    result: dict[str, Any] = {
        "is_valid": is_valid,
        "validation_feedback": feedback,
        "retry_count": retry_count + 1,
    }
    result.update(fields)
    return result


def validate_json_response(
    raw: str,
    pydantic_model: type,
    retry_count: int,
    error_prefix: str = "响应结构",
) -> tuple[bool, str, Any, dict[str, Any]]:
    """JSON + Pydantic 模型统一校验流程。

    典型调用：
        is_valid, feedback, validated, extra = validate_json_response(
            raw, QuizOutput, retry_count, "题目结构"
        )
        if not is_valid:
            return {**extra, "questions_json": raw, "parsed_questions": []}

    Args:
        raw: LLM 原始响应文本
        pydantic_model: Pydantic 模型类（如 QuizOutput、ReadingOutput）
        retry_count: 当前重试次数
        error_prefix: 错误消息前缀

    Returns:
        (is_valid, feedback, validated_instance, extra_dict)
        - is_valid: 是否通过校验
        - feedback: 错误反馈（通过时为空字符串）
        - validated_instance: Pydantic 模型实例（失败时为 None）
        - extra_dict: 校验失败时的标准返回字典（通过时为空字典）
    """
    if not raw:
        feedback = "未生成内容"
        return False, feedback, None, make_validation_result(False, retry_count, feedback)

    # 先把模型输出里的 JSON 片段剥离出来，再进入反序列化。
    json_text = extract_json_from_text(raw)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        feedback = f"JSON 解析失败: {e}。请确保输出合法 JSON。"
        return False, feedback, None, make_validation_result(False, retry_count, feedback)

    try:
        # 让 Pydantic 负责字段级结构校验，避免 Agent 各自重复写 schema 判断。
        validated = pydantic_model.model_validate(data)
    except Exception as e:
        feedback = f"{error_prefix}不合法: {e}"
        return False, feedback, None, make_validation_result(False, retry_count, feedback)

    return True, "", validated, {}
