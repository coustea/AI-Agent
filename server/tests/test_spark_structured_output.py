"""测试星火模型通过 LangChain ChatOpenAI 的结构化输出能力。"""

import asyncio
import json
import os

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import get


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SPARK_INTEGRATION") != "1",
    reason="真实 Spark 结构化输出探针默认跳过；设置 RUN_SPARK_INTEGRATION=1 手动运行。",
)

_MODEL_CFG = get("models", {}) or {}
SPARK_MAX_API_PASSWORD = _MODEL_CFG.get("api_key", "test-key")
SPARK_MAX_API_BASE = (_MODEL_CFG.get("base_url", "https://spark-api-open.xf-yun.com/v1") or "").rstrip("/chat/completions").rstrip("/")
SPARK_MAX_MODEL_NAME = _MODEL_CFG.get("model_name", "generalv3.5")


class UserInfo(BaseModel):
    """测试用的用户信息结构。"""

    name: str
    age: int
    hobbies: list[str]


class AnalysisResult(BaseModel):
    """测试用的分析结果结构。"""

    sentiment: str
    confidence: float
    keywords: list[str]


@pytest.mark.asyncio
async def test_with_structured_output():
    """测试方式一：使用 with_structured_output 方法。"""
    print("\n=== 测试 with_structured_output ===")

    llm = ChatOpenAI(
        model=SPARK_MAX_MODEL_NAME,
        api_key=SPARK_MAX_API_PASSWORD,
        base_url=SPARK_MAX_API_BASE,
        temperature=0.3,
    )

    # 绑定结构化输出 schema
    structured_llm = llm.with_structured_output(UserInfo)

    messages = [
        SystemMessage(content="你是一个信息提取助手，请从用户输入中提取结构化信息。"),
        HumanMessage(content="张三今年25岁，他平时喜欢打篮球、听音乐和看电影。"),
    ]

    try:
        result = await structured_llm.ainvoke(messages)
        print(f"结果类型: {type(result)}")
        print(f"结果内容: {result}")
        if isinstance(result, UserInfo):
            print("✅ 成功解析为 UserInfo 实例")
            print(f"  - name: {result.name}")
            print(f"  - age: {result.age}")
            print(f"  - hobbies: {result.hobbies}")
        else:
            print(f"⚠️ 返回类型不是 UserInfo: {result}")
    except Exception as e:
        print(f"❌ with_structured_output 失败: {e}")


@pytest.mark.asyncio
async def test_response_format_json_object():
    """测试方式二：使用 response_format 参数。"""
    print("\n=== 测试 response_format: json_object ===")

    llm = ChatOpenAI(
        model=SPARK_MAX_MODEL_NAME,
        api_key=SPARK_MAX_API_PASSWORD,
        base_url=SPARK_MAX_API_BASE,
        temperature=0.3,
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    messages = [
        SystemMessage(content="你必须始终以 JSON 格式返回结果，不要包含任何其他文字。"),
        HumanMessage(
            content="分析这段文本的情感：'今天天气真好，心情很愉快！' 返回 JSON 包含 sentiment（情感）、confidence（置信度 0-1）、keywords（关键词列表）。"
        ),
    ]

    try:
        result = await llm.ainvoke(messages)
        print(f"原始结果: {result.content}")
        parsed = json.loads(result.content)
        print(f"解析后: {json.dumps(parsed, indent=2, ensure_ascii=False)}")
        print("✅ response_format json_object 成功")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"原始内容: {result.content}")
    except Exception as e:
        print(f"❌ response_format 失败: {e}")


@pytest.mark.asyncio
async def test_response_format_with_schema():
    """测试方式三：使用 response_format 指定 JSON schema（如果支持）。"""
    print("\n=== 测试 response_format with json_schema ===")

    # 星火可能不支持 json_schema，先尝试
    schema = UserInfo.model_json_schema()

    llm = ChatOpenAI(
        model=SPARK_MAX_MODEL_NAME,
        api_key=SPARK_MAX_API_PASSWORD,
        base_url=SPARK_MAX_API_BASE,
        temperature=0.3,
        model_kwargs={
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "UserInfo",
                    "schema": schema,
                    "strict": True,
                }
            }
        },
    )

    messages = [
        SystemMessage(content="提取用户信息，严格按照 JSON schema 返回。"),
        HumanMessage(content="李四，30岁，爱好是游泳和阅读。"),
    ]

    try:
        result = await llm.ainvoke(messages)
        print(f"原始结果: {result.content}")
        parsed = json.loads(result.content)
        user = UserInfo(**parsed)
        print(f"✅ json_schema 成功: {user}")
    except Exception as e:
        print(f"❌ json_schema 失败（可能不支持）: {e}")


@pytest.mark.asyncio
async def test_bind_tools():
    """测试方式四：使用 bind_tools 模拟结构化输出。"""
    print("\n=== 测试 bind_tools ===")

    from langchain_core.tools import tool

    @tool
    def extract_user_info(name: str, age: int, hobbies: list[str]) -> dict:
        """提取用户的基本信息。

        Args:
            name: 用户姓名
            age: 用户年龄
            hobbies: 用户爱好列表

        Returns:
            提取的用户信息字典
        """
        return {"name": name, "age": age, "hobbies": hobbies}

    llm = ChatOpenAI(
        model=SPARK_MAX_MODEL_NAME,
        api_key=SPARK_MAX_API_PASSWORD,
        base_url=SPARK_MAX_API_BASE,
        temperature=0.3,
    )

    llm_with_tools = llm.bind_tools([extract_user_info])

    messages = [
        SystemMessage(content="使用 extract_user_info 工具提取用户信息。"),
        HumanMessage(content="王五，28岁，喜欢编程和打游戏。"),
    ]

    try:
        result = await llm_with_tools.ainvoke(messages)
        print(f"结果: {result}")
        if result.tool_calls:
            print(f"✅ tool_calls: {result.tool_calls}")
            for tc in result.tool_calls:
                print(f"  - {tc['name']}: {tc['args']}")
        else:
            print(f"⚠️ 没有 tool_calls，内容: {result.content}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ bind_tools 失败: {e}")


async def main():
    """运行所有测试。"""
    print("=" * 60)
    print("星火模型结构化输出测试")
    print(f"API Base: {SPARK_MAX_API_BASE}")
    print("=" * 60)

    await test_with_structured_output()
    await test_response_format_json_object()
    await test_response_format_with_schema()
    await test_bind_tools()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
