"""
多智能体资源生成系统 — 单元测试。

测试范围：
1. 各 Agent 图结构是否正确构建
2. 各节点函数在 mock LLM 下的行为
3. 验证/校验逻辑（纯逻辑，不依赖 LLM）
4. 条件边（retry/end）决策逻辑
5. SSE 事件发射器
6. JSON 提取辅助函数
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ==========================================
# Fixtures：为所有 Agent 提供统一的 mock LLM
# ==========================================


def _make_mock_llm(response_text: str):
    """创建一个返回固定文本的 mock LLM。"""
    mock_resp = MagicMock()
    mock_resp.content = response_text
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_resp)
    return mock_llm


@pytest.fixture
def mock_llm_ok():
    """返回固定成功响应的 mock LLM。"""
    return _make_mock_llm("这是模拟的 LLM 响应内容。")


# ==========================================
# 1. 图结构测试：验证每个 Agent 的 LangGraph 拓扑
# ==========================================


class TestGraphStructure:
    """验证各 Agent 的 StateGraph 图结构。"""

    def test_content_writer_nodes(self):
        from app.modules.resource_generator.content_writer_agent import ContentWriter

        agent = ContentWriter.__new__(ContentWriter)
        agent.llm = MagicMock()
        agent.graph = agent._build_graph()
        node_names = set(agent.graph.nodes.keys())
        assert "__start__" in node_names
        assert "generate_outline" in node_names
        assert "expand_content" in node_names
        assert "review_quality" in node_names

    def test_quiz_agent_nodes(self):
        from app.modules.resource_generator.quiz_agent import QuizAgent

        agent = QuizAgent.__new__(QuizAgent)
        agent.llm = MagicMock()
        agent.graph = agent._build_graph()
        node_names = set(agent.graph.nodes.keys())
        assert "__start__" in node_names
        assert "generate_questions" in node_names
        assert "validate_structure" in node_names

    def test_reading_agent_nodes(self):
        from app.modules.resource_generator.reading_agent import ReadingAgent

        agent = ReadingAgent.__new__(ReadingAgent)
        agent.llm = MagicMock()
        agent.graph = agent._build_graph()
        node_names = set(agent.graph.nodes.keys())
        assert "__start__" in node_names
        assert "generate_recommendations" in node_names
        assert "critique_quality" in node_names

    def test_code_agent_nodes(self):
        from app.modules.resource_generator.code_agent import CodeAgent

        agent = CodeAgent.__new__(CodeAgent)
        agent.llm = MagicMock()
        agent.graph = agent._build_graph()
        node_names = set(agent.graph.nodes.keys())
        assert "__start__" in node_names
        assert "generate_code" in node_names
        assert "validate_syntax" in node_names
        assert "add_explanation" in node_names

    def test_media_agent_nodes(self):
        from app.modules.resource_generator.media_agent import MediaAgent

        agent = MediaAgent.__new__(MediaAgent)
        agent.llm = MagicMock()
        agent.graph = agent._build_graph()
        node_names = set(agent.graph.nodes.keys())
        assert "__start__" in node_names
        assert "generate_script" in node_names
        assert "validate_completeness" in node_names

    def test_mindmap_agent_nodes(self):
        from app.modules.resource_generator.mindmap_agent import MindmapGenerator

        agent = MindmapGenerator.__new__(MindmapGenerator)
        agent.llm = MagicMock()
        agent.graph = agent.build_graph()
        node_names = set(agent.graph.nodes.keys())
        assert "__start__" in node_names
        assert "generate_markdown" in node_names
        assert "call_mcp_tool" in node_names
        assert "reflect" in node_names


# ==========================================
# 2. 条件边测试：retry / end 决策
# ==========================================


class TestConditionalEdges:
    """验证各 Agent 的 retry/end 决策逻辑。"""

    def test_content_should_retry_when_not_passed(self):
        from app.modules.resource_generator.content_writer_agent import ContentWriter

        assert ContentWriter._should_retry({"review_passed": False, "retry_count": 0}) == "retry"
        assert ContentWriter._should_retry({"review_passed": False, "retry_count": 1}) == "retry"

    def test_content_should_end_when_passed(self):
        from app.modules.resource_generator.content_writer_agent import ContentWriter

        assert ContentWriter._should_retry({"review_passed": True, "retry_count": 0}) == "end"

    def test_content_should_end_when_max_retries(self):
        from app.modules.resource_generator.content_writer_agent import ContentWriter

        assert ContentWriter._should_retry({"review_passed": False, "retry_count": 2}) == "end"

    def test_quiz_should_retry(self):
        from app.modules.resource_generator.quiz_agent import QuizAgent

        assert QuizAgent._should_retry({"validation_passed": False, "retry_count": 0}) == "retry"
        assert QuizAgent._should_retry({"validation_passed": True, "retry_count": 0}) == "end"
        assert QuizAgent._should_retry({"validation_passed": False, "retry_count": 2}) == "end"

    def test_reading_should_retry(self):
        from app.modules.resource_generator.reading_agent import ReadingAgent

        assert ReadingAgent._should_retry({"critique_passed": False, "retry_count": 0}) == "retry"
        assert ReadingAgent._should_retry({"critique_passed": True}) == "end"

    def test_code_should_retry(self):
        from app.modules.resource_generator.code_agent import CodeAgent

        assert CodeAgent._should_retry({"validation_passed": False, "retry_count": 0}) == "retry"
        assert CodeAgent._should_retry({"validation_passed": True}) == "end"
        assert CodeAgent._should_retry({"validation_passed": False, "retry_count": 2}) == "end"

    def test_media_should_retry(self):
        from app.modules.resource_generator.media_agent import MediaAgent

        assert MediaAgent._should_retry({"validation_passed": False, "retry_count": 0}) == "retry"
        assert MediaAgent._should_retry({"validation_passed": True}) == "end"


# ==========================================
# 3. 验证/校验逻辑测试（纯逻辑，不依赖 LLM）
# ==========================================


class TestQuizValidation:
    """Quiz Agent 的结构校验逻辑。"""

    @pytest.mark.asyncio
    async def test_valid_quiz_passes(self):
        from app.modules.resource_generator.quiz_agent import QuizAgent, QuizOutput

        agent = QuizAgent.__new__(QuizAgent)
        raw = json.dumps({
            "questions": [
                {"difficulty": "basic", "question_type": "choice", "stem": "Q1",
                 "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "因为A"},
                {"difficulty": "intermediate", "question_type": "short_answer", "stem": "Q2",
                 "options": None, "answer": "Ans", "explanation": "解释"},
                {"difficulty": "challenge", "question_type": "choice", "stem": "Q3",
                 "options": ["A", "B", "C", "D"], "answer": "B", "explanation": "因为B"},
            ]
        })
        state = {"questions_json": raw, "error": None}
        result = await agent._validate_structure(state)
        assert result["validation_passed"] is True
        assert len(result["parsed_questions"]) == 3

    @pytest.mark.asyncio
    async def test_invalid_json_fails(self):
        from app.modules.resource_generator.quiz_agent import QuizAgent

        agent = QuizAgent.__new__(QuizAgent)
        state = {"questions_json": "not valid json{{{", "error": None}
        result = await agent._validate_structure(state)
        assert result["validation_passed"] is False
        assert "JSON" in result["validation_feedback"]

    @pytest.mark.asyncio
    async def test_too_few_questions_fails(self):
        from app.modules.resource_generator.quiz_agent import QuizAgent

        agent = QuizAgent.__new__(QuizAgent)
        raw = json.dumps({
            "questions": [
                {"difficulty": "basic", "question_type": "choice", "stem": "Q1",
                 "options": ["A", "B"], "answer": "A", "explanation": "ok"},
            ]
        })
        state = {"questions_json": raw, "error": None}
        result = await agent._validate_structure(state)
        assert result["validation_passed"] is False
        assert "不足" in result["validation_feedback"]

    @pytest.mark.asyncio
    async def test_single_difficulty_fails(self):
        from app.modules.resource_generator.quiz_agent import QuizAgent

        agent = QuizAgent.__new__(QuizAgent)
        raw = json.dumps({
            "questions": [
                {"difficulty": "basic", "question_type": "choice", "stem": f"Q{i}",
                 "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "ok"}
                for i in range(4)
            ]
        })
        state = {"questions_json": raw, "error": None}
        result = await agent._validate_structure(state)
        assert result["validation_passed"] is False
        assert "难度" in result["validation_feedback"]

    @pytest.mark.asyncio
    async def test_error_propagates(self):
        from app.modules.resource_generator.quiz_agent import QuizAgent

        agent = QuizAgent.__new__(QuizAgent)
        state = {"questions_json": "", "error": "LLM 调用超时"}
        result = await agent._validate_structure(state)
        assert result["validation_passed"] is False
        assert "LLM" in result["validation_feedback"]


class TestReadingValidation:
    """Reading Agent 的结构校验逻辑。"""

    @pytest.mark.asyncio
    async def test_valid_reading_passes(self):
        from app.modules.resource_generator.reading_agent import ReadingAgent

        agent = ReadingAgent.__new__(ReadingAgent)
        raw = json.dumps({
            "recommendations": [
                {
                    "title": "TCP/IP 详解",
                    "author_or_source": "W. Richard Stevens",
                    "abstract": "这是一本深入讲解TCP/IP协议栈的经典著作，涵盖从链路层到应用层的全部内容。",
                    "relevance": "帮助你理解网络通信的底层原理",
                    "type": "book",
                },
                {
                    "title": "RFC 793: TCP",
                    "author_or_source": "IETF",
                    "abstract": "TCP协议的原始规范文档，定义了三次握手等核心机制的标准描述。",
                    "relevance": "直接了解TCP协议的官方定义",
                    "type": "documentation",
                },
                {
                    "title": "计算机网络博客",
                    "author_or_source": "某技术博客",
                    "abstract": "系列博客文章，用通俗易懂的语言讲解网络协议的核心概念。",
                    "relevance": "适合你的学习风格",
                    "type": "blog",
                },
            ]
        })
        state = {"recommendations_json": raw, "error": None}
        result = await agent._critique_quality(state)
        assert result["critique_passed"] is True
        assert len(result["parsed_recommendations"]) == 3

    @pytest.mark.asyncio
    async def test_short_abstract_fails(self):
        from app.modules.resource_generator.reading_agent import ReadingAgent

        agent = ReadingAgent.__new__(ReadingAgent)
        raw = json.dumps({
            "recommendations": [
                {
                    "title": "书1",
                    "author_or_source": "作者1",
                    "abstract": "太短了",
                    "relevance": "相关",
                    "type": "book",
                },
                {
                    "title": "书2",
                    "author_or_source": "作者2",
                    "abstract": "这也是一本关于TCP协议的深度解析书籍，值得一读",
                    "relevance": "有帮助",
                    "type": "paper",
                },
            ]
        })
        state = {"recommendations_json": raw, "error": None}
        result = await agent._critique_quality(state)
        assert result["critique_passed"] is False
        assert "摘要过短" in result["critique_feedback"]

    @pytest.mark.asyncio
    async def test_single_type_fails(self):
        from app.modules.resource_generator.reading_agent import ReadingAgent

        agent = ReadingAgent.__new__(ReadingAgent)
        raw = json.dumps({
            "recommendations": [
                {
                    "title": f"书{i}",
                    "author_or_source": f"作者{i}",
                    "abstract": "这是一本深入讲解计算机网络协议的权威教材，内容系统全面",
                    "relevance": f"推荐理由{i}",
                    "type": "book",
                }
                for i in range(5)
            ]
        })
        state = {"recommendations_json": raw, "error": None}
        result = await agent._critique_quality(state)
        assert result["critique_passed"] is False
        assert "类型单一" in result["critique_feedback"]


class TestCodeValidation:
    """Code Agent 的校验逻辑。"""

    def test_detect_python(self):
        from app.modules.resource_generator.code_agent import _detect_language

        assert _detect_language("```python\nprint('hi')\n```") == "python"

    def test_detect_javascript(self):
        from app.modules.resource_generator.code_agent import _detect_language

        assert _detect_language("```javascript\nconsole.log('hi')\n```") == "javascript"

    def test_detect_unknown_no_block(self):
        from app.modules.resource_generator.code_agent import _detect_language

        assert _detect_language("no code block here") == "unknown"

    def test_extract_code_block(self):
        from app.modules.resource_generator.code_agent import _extract_code_block

        md = "一些说明\n```python\nx = 1\nprint(x)\n```\n更多说明"
        assert _extract_code_block(md) == "x = 1\nprint(x)"

    def test_validate_python_syntax_ok(self):
        from app.modules.resource_generator.code_agent import _validate_python_syntax

        ok, msg = _validate_python_syntax("x = 1\nprint(x)\n")
        assert ok is True
        assert msg == ""

    def test_validate_python_syntax_error(self):
        from app.modules.resource_generator.code_agent import _validate_python_syntax

        ok, msg = _validate_python_syntax("def foo(\n")
        assert ok is False
        assert "语法错误" in msg

    def test_validate_code_basic_too_short(self):
        from app.modules.resource_generator.code_agent import _validate_code_basic

        ok, msg = _validate_code_basic("x=1\n", "python")
        assert ok is False
        assert "行数不足" in msg

    def test_validate_code_basic_ok(self):
        from app.modules.resource_generator.code_agent import _validate_code_basic

        code = "\n".join(f"line_{i} = {i}" for i in range(15))
        ok, msg = _validate_code_basic(code, "python")
        assert ok is True

    def test_validate_code_basic_too_many_placeholders(self):
        from app.modules.resource_generator.code_agent import _validate_code_basic

        lines = [f"line_{i} = {i}" for i in range(15)]
        lines[3] = "TODO: implement this"
        lines[5] = "FIXME: broken"
        lines[7] = "... "
        code = "\n".join(lines)
        ok, msg = _validate_code_basic(code, "python")
        assert ok is False
        assert "占位符" in msg


class TestMediaValidation:
    """Media Agent 的校验逻辑。"""

    def test_count_scenes(self):
        from app.modules.resource_generator.media_agent import _count_scenes

        md = (
            "# 标题\n"
            "### 场景 1：开头\n"
            "内容\n"
            "### 场景 2：中间\n"
            "内容\n"
            "### 场景 3：结尾\n"
            "内容\n"
        )
        assert _count_scenes(md) == 3

    def test_count_scenes_zero(self):
        from app.modules.resource_generator.media_agent import _count_scenes

        assert _count_scenes("没有场景的内容") == 0

    def test_check_placeholders(self):
        from app.modules.resource_generator.media_agent import _check_placeholders

        issues = _check_placeholders("正常内容")
        assert len(issues) == 0

        issues = _check_placeholders("这里有个TODO需要处理")
        assert len(issues) == 1
        assert "占位符" in issues[0]

    def test_check_scene_completeness_ok(self):
        from app.modules.resource_generator.media_agent import _check_scene_completeness

        md = (
            "### 场景 1：TCP握手\n"
            "**旁白**：让我们来了解TCP三次握手的过程。\n"
            "**画面**：蓝色数据包从客户端飞向服务器。\n"
        )
        issues = _check_scene_completeness(md)
        assert len(issues) == 0

    def test_check_scene_completeness_missing_narration(self):
        from app.modules.resource_generator.media_agent import _check_scene_completeness

        md = (
            "### 场景 1：TCP握手\n"
            "**画面**：蓝色数据包从客户端飞向服务器。\n"
        )
        issues = _check_scene_completeness(md)
        assert any("旁白" in i for i in issues)


class TestContentReview:
    """Content Agent 的字数检查逻辑。"""

    @pytest.mark.asyncio
    async def test_short_content_rejected(self):
        """内容过短应在字数检查阶段被拦截。"""
        from app.modules.resource_generator.content_writer_agent import ContentWriter

        agent = ContentWriter.__new__(ContentWriter)
        agent.llm = MagicMock()
        short_content = "太短了" * 10  # 约 30 字
        state = {
            "content": short_content,
            "outline": "# 大纲",
            "error": None,
            "topic": "TCP",
            "user_profile": "{}",
        }
        result = await agent._review_quality(state)
        assert result["review_passed"] is False
        assert "字数" in result["review_feedback"]


# ==========================================
# 4. JSON 提取辅助函数测试
# ==========================================


class TestJsonExtraction:
    """测试各 Agent 的 JSON 提取逻辑。"""

    def test_extract_plain_json(self):
        from app.modules.resource_generator.content_writer_agent import _extract_json

        text = '{"passed": true, "feedback": ""}'
        result = _extract_json(text)
        assert result["passed"] is True

    def test_extract_json_in_fenced_block(self):
        from app.modules.resource_generator.content_writer_agent import _extract_json

        text = '```json\n{"passed": false, "feedback": "太短"}\n```'
        result = _extract_json(text)
        assert result["passed"] is False
        assert "太短" in result["feedback"]

    def test_extract_json_with_surrounding_text(self):
        from app.modules.resource_generator.content_writer_agent import _extract_json

        text = '好的，这是审查结果：\n{"passed": true, "feedback": ""}\n以上是结论。'
        result = _extract_json(text)
        assert result["passed"] is True

    def test_extract_json_invalid_returns_default(self):
        from app.modules.resource_generator.content_writer_agent import _extract_json

        result = _extract_json("完全没有JSON的内容")
        assert result["passed"] is False

    def test_quiz_extract_json_text(self):
        from app.modules.resource_generator.quiz_agent import _extract_json_text

        raw = '```json\n{"questions": []}\n```'
        result = _extract_json_text(raw)
        assert json.loads(result) == {"questions": []}


# ==========================================
# 5. SSE 事件发射器测试
# ==========================================


class TestSSEEmitter:
    """验证 SSE 事件发射器的行为。"""

    @pytest.mark.asyncio
    async def test_emit_and_collect(self):
        from app.modules.resource_generator.sse import AgentEventEmitter

        emitter = AgentEventEmitter()
        await emitter.emit_coordinator("parsing", "正在解析...")
        await emitter.emit_agent_start("doc")
        await emitter.emit_agent_done("doc", data={"success": True})
        await emitter.emit_done("完成")

        events = []
        async for chunk in emitter.stream():
            events.append(chunk)

        assert len(events) == 4
        assert '"type": "coordinator"' in events[0]
        assert '"type": "agent_start"' in events[1]
        assert '"type": "agent_done"' in events[2]
        assert '"type": "done"' in events[3]

    @pytest.mark.asyncio
    async def test_sse_format(self):
        from app.modules.resource_generator.sse import AgentEventEmitter

        emitter = AgentEventEmitter()
        await emitter.emit_done("测试")

        chunks = []
        async for chunk in emitter.stream():
            chunks.append(chunk)

        assert chunks[0].startswith("data: ")
        assert chunks[0].endswith("\n\n")

    @pytest.mark.asyncio
    async def test_agent_error_event(self):
        from app.modules.resource_generator.sse import AgentEventEmitter

        emitter = AgentEventEmitter()
        await emitter.emit_agent_error("quiz", "JSON解析失败")
        await emitter.emit_done("结束")

        events = []
        async for chunk in emitter.stream():
            events.append(chunk)

        assert '"type": "agent_error"' in events[0]
        assert "JSON解析失败" in events[0]


# ==========================================
# 6. Coordinator 注册表与降级任务
# ==========================================


class TestCoordinatorRegistry:
    """验证 Agent 注册表和降级逻辑。"""

    def test_registry_has_six_agents(self):
        from app.modules.resource_generator.coordinator_agent import AGENT_REGISTRY

        assert len(AGENT_REGISTRY) == 6
        assert set(AGENT_REGISTRY.keys()) == {
            "content", "mindmap", "quiz", "reading", "media", "code",
        }

    def test_registry_each_has_type(self):
        from app.modules.resource_generator.coordinator_agent import AGENT_REGISTRY

        types = set()
        for info in AGENT_REGISTRY.values():
            assert "role" in info
            assert "desc" in info
            assert "type" in info
            types.add(info["type"])
        # 6 个 Agent 应有 6 个不同的 type
        assert len(types) == 6

    def test_default_tasks_covers_all_agents(self):
        from app.modules.resource_generator.coordinator_agent import CoordinatorAgent

        task = {"course": "计算机网络", "gap": "TCP三次握手"}
        defaults = CoordinatorAgent._default_tasks(task)
        agent_names = {t["agent"] for t in defaults}
        assert agent_names == {"content", "mindmap", "quiz", "reading", "media", "code"}
        assert len(defaults) == 6
