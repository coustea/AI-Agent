"""
资源 Agent 通用校验工具。

提供跨 Agent 的共享校验辅助函数：
- extract_last_ai_content: 提取最后一条 AI 消息内容
- make_validation_result: 构建标准校验返回字典
"""

from typing import Any

from langchain_core.messages import AIMessage, AnyMessage


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
