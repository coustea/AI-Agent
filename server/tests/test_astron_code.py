import pytest
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from typing import Any
from app.chat.schemas import TeachingDiagram

BASE_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
API_KEY = "a878422abe46bb3e7daa03bc71c74539:NGNlNmI4ZDk2YjYyNzUwNmQ5ODQxMzVj"
MODEL_NAME = "astron-code-latest"

@pytest.fixture
def chat_model():
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.1
    )

@pytest.mark.asyncio
async def test_astron_code_basic_invocation(chat_model):
    """测试基本模型调用功能"""
    response = await chat_model.ainvoke([HumanMessage(content="Say 'Hello World' and nothing else.")])
    assert response is not None
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_astron_code_json_output(chat_model):
    """测试 JSON 输出功能"""
    class Person(BaseModel):
        name: str = Field(description="The person's name")
        age: int = Field(description="The person's age")
    
    # 使用 structured output (json_mode) 强制输出 JSON，有些模型可能更适配这个
    model_with_structured_output = chat_model.with_structured_output(Person, method="json_mode")
    response = await model_with_structured_output.ainvoke([
        HumanMessage(content="Alice is 25 years old. Please respond with JSON format matching the schema.")
    ])
    
    assert response is not None
    assert response.name.strip() == "Alice"
    assert response.age == 25

@pytest.mark.asyncio
async def test_astron_code_tool_calling(chat_model):
    """测试工具调用 (Tool Calling) 功能"""
    
    # 定义一个测试用的工具（LangChain会自动将其转换为Tool描述）
    def get_weather(location: str) -> str:
        """Get the current weather in a given location."""
        return f"The weather in {location} is sunny."

    # 绑定工具到模型
    model_with_tools = chat_model.bind_tools([get_weather])
    
    # 发送请求，触发工具调用
    response = await model_with_tools.ainvoke([HumanMessage(content="What is the weather in Paris?")])
    
    assert response is not None
    assert hasattr(response, "tool_calls")
    assert len(response.tool_calls) > 0, "Model did not return any tool calls"
    assert response.tool_calls[0]["name"] == "get_weather"
    assert "location" in response.tool_calls[0]["args"]
    assert "Paris" in response.tool_calls[0]["args"]["location"]

@pytest.mark.asyncio
async def test_astron_code_complex_json_output(chat_model):
    """测试复杂的嵌套 JSON 输出能力 (TeachingDiagram)"""
    
    # 模拟一段系统提示词要求生成教学图解
    schema_str = TeachingDiagram.model_json_schema()
    prompt = f"请根据以下概念，生成一个知识框架图 (framework) 类型的教学图解：'人工智能的三大核心要素：数据、算力、算法'。\n\n你必须严格遵守以下 JSON Schema 输出数据，不要输出任何其他的分析或 Markdown 格式，只输出纯 JSON 字符串：\n{schema_str}"
    
    try:
        # 去掉 json_mode 限制，有些基于 GLM 的模型在使用特定 API 参数时反而会失效，直接用最朴素的 Prompt 激发
        response = await chat_model.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        import json
        
        # 尝试从中提取 json
        s = content.strip()
        if s.startswith("```json"):
            s = s[7:]
        if s.startswith("```"):
            s = s[3:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
        
        data = json.loads(s)
        parsed_response = TeachingDiagram.model_validate(data)
    except Exception as e:
        pytest.fail(f"Complex JSON generation failed: {e}. Model output was: {getattr(response, 'content', '')}")
        
    assert parsed_response is not None
    assert parsed_response.graph_type == "framework"
    assert hasattr(parsed_response.visual_content, "modules")
    assert len(parsed_response.visual_content.modules) > 0
    assert "人工智能" in parsed_response.title or "AI" in parsed_response.title


@pytest.mark.asyncio
async def test_astron_code_universal_tier1_candidate(chat_model):
    """测试终极的通用第一层方案候选：结合 bind_tools + Prompt Schema 注入"""
    
    schema_str = TeachingDiagram.model_json_schema()
    import json
    schema_str = json.dumps(schema_str, ensure_ascii=False)
    
    prompt = (
        "请根据以下概念，生成一个知识框架图 (framework) 类型的教学图解：'人工智能的三大核心要素：数据、算力、算法'。\n\n"
        "[IMPORTANT INSTRUCTION]\n"
        "You must invoke the tool provided to output the data. "
        "The arguments you pass to the tool MUST strictly follow this JSON Schema:\n"
        f"{schema_str}\n"
    )
    
    # 定义工具
    name = "generate_teaching_diagram"
    desc = "Generate a structured teaching diagram."
    tools = [{
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": TeachingDiagram.model_json_schema(),
        },
    }]
    
    # 使用最高兼容性的 tool_choice 格式强制调用
    model_with_tools = chat_model.bind_tools(
        tools,
        tool_choice={"type": "function", "function": {"name": name}}
    )
    
    try:
        response = await model_with_tools.ainvoke([HumanMessage(content=prompt)])
    except Exception as e:
        pytest.fail(f"API call failed: {e}")
        
    tool_calls = getattr(response, "tool_calls", [])
    assert len(tool_calls) > 0, f"Model did not return tool_calls. Content was: {getattr(response, 'content', '')}"
    
    args = tool_calls[0].get("args") if isinstance(tool_calls[0], dict) else getattr(tool_calls[0], "args", None)
    assert args is not None, "Tool call missing args"
    
    if isinstance(args, str):
        args = json.loads(args)
        
    # [新增] 修复部分大模型在 Tool Calling 时，把嵌套对象误当成字符串 (Stringified JSON) 输出的通病
    def _parse_nested_json_strings(data: Any) -> Any:
        if isinstance(data, dict):
            return {k: _parse_nested_json_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [_parse_nested_json_strings(v) for v in data]
        elif isinstance(data, str):
            s = data.strip()
            if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, (dict, list)):
                        return parsed
                except json.JSONDecodeError:
                    # 尝试修复 LLM 生成的 JSON 字符串中常见的缺失冒号问题
                    try:
                        import re
                        s_fixed = re.sub(r'("[\w_]+")\s*(?=[\[{"])', r'\1: ', s)
                        parsed = json.loads(s_fixed)
                        if isinstance(parsed, (dict, list)):
                            return parsed
                    except Exception:
                        pass
        return data

    cleaned_args = _parse_nested_json_strings(args)

    try:
        parsed_response = TeachingDiagram.model_validate(cleaned_args)
    except Exception as e:
        pytest.fail(f"Pydantic validation failed on tool arguments. Cleaned Args: {cleaned_args}\nError: {e}")
        
    assert parsed_response.graph_type == "framework"

@pytest.mark.asyncio
async def test_astron_code_concurrency(chat_model):
    """测试模型的并发能力"""
    import asyncio
    import time
    
    # 我们并发发送 5 个简单的请求
    CONCURRENCY_LEVEL = 5
    prompt = "请用一句非常简短的话介绍一下你自己。"
    
    start_time = time.time()
    
    async def make_request(i):
        try:
            response = await chat_model.ainvoke([HumanMessage(content=f"{prompt} (请求 ID: {i})")])
            return response.content
        except Exception as e:
            return f"Error: {e}"
            
    # 使用 asyncio.gather 同时发起并发请求
    tasks = [make_request(i) for i in range(CONCURRENCY_LEVEL)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    success_count = sum(1 for r in results if not r.startswith("Error:"))
    
    print(f"\n--- 并发测试结果 ---")
    print(f"并发数量: {CONCURRENCY_LEVEL}")
    print(f"总耗时: {elapsed:.2f} 秒")
    print(f"成功次数: {success_count}/{CONCURRENCY_LEVEL}")
    for i, res in enumerate(results):
        print(f"[{i}] {res}")
        
    assert success_count == CONCURRENCY_LEVEL, f"Concurrency test failed: {CONCURRENCY_LEVEL - success_count} requests failed."

@pytest.mark.asyncio
async def test_astron_code_coordinator_planning(chat_model):
    """测试多智能体系统资源生成的规划输出 (TeachingPlan)"""
    from app.resource.schemas import TeachingPlan
    from app.infra.llm import Llm

    # 临时初始化 Llm 实例来测试它的 ainvoke_json 方法
    llm = Llm()
    llm.chat_model = chat_model

    prompt = (
        "你是一个学习路径规划助手。当前用户的学习需求是：'我想快速了解并上手 Python 爬虫，主要抓取一些静态网页数据'。"
        "请生成一个教学计划，包含主题、目标和 3 个大纲条目。"
    )

    try:
        # 直接使用我们重构后的 ainvoke_json，它会走到完美的 Tier 1
        plan = await llm.ainvoke_json(TeachingPlan, prompt)
    except Exception as e:
        pytest.fail(f"Coordinator planning failed: {e}")

    assert plan is not None
    assert len(plan.outline) > 0
    assert len(plan.agent_assignments) > 0
    for assignment in plan.agent_assignments:
        assert assignment.agent_id
        assert assignment.assigned_outline_ids is not None
