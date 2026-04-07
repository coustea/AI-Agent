"""
多智能体资源生成系统 — 集成测试。

测试范围：
1. 各 Agent 在 mock LLM 下的完整工作流执行
2. Coordinator 的并发调度和 SSE 事件推送
3. 多 Agent 端到端协作流程
4. 错误恢复和降级机制
5. 返回值格式验证

这些测试 mock 掉 LLM 调用，验证整个 Agent 编排流程能否走通。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.resource_generator.sse import AgentEventEmitter


# ==========================================
# Fixtures
# ==========================================

def _mock_llm_response(text: str):
    """构造 mock LLM 响应对象。"""
    mock_resp = MagicMock()
    mock_resp.content = text
    return mock_resp


def _make_mock_llm(responses: list[str]):
    """创建一个按顺序返回多个响应的 mock LLM。"""
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(side_effect=[_mock_llm_response(r) for r in responses])
    return mock_llm


# ==========================================
# 1. Content Agent 集成测试
# ==========================================


class TestContentAgentIntegration:
    """Content Agent 完整工作流测试。"""

    @pytest.mark.asyncio
    async def test_full_workflow_generates_content(self):
        """大纲 → 扩展 → 审查通过 → 返回内容。"""
        from app.modules.resource_generator.content_writer_agent import ContentWriter

        agent = ContentWriter.__new__(ContentWriter)
        agent.llm = _make_mock_llm([
            "# TCP三次握手 深度解析\n## 概述\n## 核心讲解\n## 案例\n## 总结",
            "# TCP三次握手 深度解析\n\n## 概述\nTCP三次握手是传输控制协议建立连接的核心机制。"
            "客户端和服务端通过三次报文交换完成连接建立，确保双方的发送和接收能力正常。\n\n"
            "## 核心讲解\n\n### 第一次握手（SYN）\n"
            "客户端发送SYN报文，进入SYN_SENT状态。此时客户端告知服务端自己的初始序列号。\n\n"
            "### 第二次握手（SYN+ACK）\n"
            "服务端收到SYN后，回复SYN+ACK报文，确认客户端的序列号并发送自己的序列号。\n\n"
            "### 第三次握手（ACK）\n"
            "客户端收到SYN+ACK后，发送ACK确认，连接建立完成。\n\n"
            "## 案例分析\n"
            "在实际抓包中，三次握手的数据包如下：SYN → SYN-ACK → ACK，时序清晰可见。\n\n"
            "## 总结\n"
            "三次握手保证了全双工通信的可靠性，缺一不可。",
            '{"passed": true, "feedback": ""}',
        ])
        agent.graph = agent._build_graph()

        result = await agent.generate_content(
            topic="TCP三次握手",
            course="计算机网络",
            major="计算机科学",
        )

        assert result["success"] is True
        assert "TCP" in result["content"]
        assert result["outline"] != ""
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error(self):
        """LLM 调用失败时返回 error。"""
        from app.modules.resource_generator.content_writer_agent import ContentWriter

        agent = ContentWriter.__new__(ContentWriter)
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("API 超时"))
        agent.llm = mock_llm
        agent.graph = agent._build_graph()

        result = await agent.generate_content(topic="TCP三次握手")

        # 工作流不会崩溃，而是通过 error 状态优雅降级
        assert result["success"] is False
        assert result["content"] == ""


# ==========================================
# 2. Quiz Agent 集成测试
# ==========================================


class TestQuizAgentIntegration:
    """Quiz Agent 完整工作流测试。"""

    @pytest.mark.asyncio
    async def test_full_workflow_generates_quiz(self):
        """生成题目 → 校验通过 → 返回结构化题目。"""
        from app.modules.resource_generator.quiz_agent import QuizAgent

        valid_quiz = json.dumps({
            "questions": [
                {
                    "difficulty": "basic",
                    "question_type": "choice",
                    "stem": "TCP三次握手中，第一次握手客户端发送的标志位是？",
                    "options": ["SYN", "ACK", "FIN", "RST"],
                    "answer": "SYN",
                    "explanation": "第一次握手客户端发送SYN报文请求建立连接。",
                },
                {
                    "difficulty": "intermediate",
                    "question_type": "choice",
                    "stem": "为什么三次握手不能用两次替代？",
                    "options": ["防止旧连接干扰", "节约带宽", "提高速度", "减少延迟"],
                    "answer": "防止旧连接干扰",
                    "explanation": "两次握手无法防止已失效的连接请求突然到达服务器导致错误建立连接。",
                },
                {
                    "difficulty": "challenge",
                    "question_type": "short_answer",
                    "stem": "描述SYN Flood攻击的原理。",
                    "options": None,
                    "answer": "攻击者发送大量伪造源IP的SYN包，服务端为每个SYN分配资源等待ACK，最终耗尽资源。",
                    "explanation": "SYN Flood利用三次握手的半连接状态消耗服务器资源。",
                },
            ]
        })

        agent = QuizAgent.__new__(QuizAgent)
        agent.llm = _make_mock_llm([valid_quiz])
        agent.graph = agent._build_graph()

        result = await agent.generate_quiz(
            topic="TCP三次握手",
            course="计算机网络",
            knowledge_level="中等",
        )

        assert result["success"] is True
        assert len(result["questions"]) == 3
        assert result["questions"][0]["difficulty"] == "basic"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_invalid_then_retry_succeeds(self):
        """第一次返回无效 JSON，重试后通过。"""
        from app.modules.resource_generator.quiz_agent import QuizAgent

        valid_quiz = json.dumps({
            "questions": [
                {"difficulty": "basic", "question_type": "choice", "stem": f"Q{i}",
                 "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "ok"}
                for i in range(4)
            ] + [
                {"difficulty": "intermediate", "question_type": "short_answer", "stem": "Q_adv",
                 "options": None, "answer": "ans", "explanation": "ok"},
            ]
        })

        agent = QuizAgent.__new__(QuizAgent)
        agent.llm = _make_mock_llm([
            "这不是有效的JSON",  # 第一次失败
            valid_quiz,  # 第二次成功
        ])
        agent.graph = agent._build_graph()

        result = await agent.generate_quiz(topic="TCP")

        assert result["success"] is True
        assert len(result["questions"]) == 5


# ==========================================
# 3. Reading Agent 集成测试
# ==========================================


class TestReadingAgentIntegration:
    """Reading Agent 完整工作流测试。"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        from app.modules.resource_generator.reading_agent import ReadingAgent

        valid_reading = json.dumps({
            "recommendations": [
                {
                    "title": "TCP/IP详解 卷1",
                    "author_or_source": "W. Richard Stevens",
                    "abstract": "深入讲解TCP/IP协议栈的经典教材，从链路层到应用层全面覆盖。",
                    "relevance": "帮助你从底层理解TCP三次握手的原理",
                    "type": "book",
                },
                {
                    "title": "RFC 793: Transmission Control Protocol",
                    "author_or_source": "IETF",
                    "abstract": "TCP协议的官方规范文档，定义了连接建立、数据传输和连接释放的标准流程。",
                    "relevance": "直接阅读TCP协议的原始定义",
                    "type": "documentation",
                },
                {
                    "title": "计算机网络：自顶向下方法",
                    "author_or_source": "Kurose & Ross",
                    "abstract": "以应用层到物理层的自顶向下方式讲解计算机网络，内容丰富且易于理解。",
                    "relevance": "适合你的学习风格，配合图解理解",
                    "type": "book",
                },
            ]
        })

        agent = ReadingAgent.__new__(ReadingAgent)
        agent.llm = _make_mock_llm([valid_reading])
        agent.graph = agent._build_graph()

        result = await agent.generate_reading(
            topic="TCP三次握手",
            course="计算机网络",
            cognitive_style="视觉学习型",
        )

        assert result["success"] is True
        assert len(result["recommendations"]) == 3
        assert result["recommendations"][0]["type"] == "book"


# ==========================================
# 4. Code Agent 集成测试
# ==========================================


class TestCodeAgentIntegration:
    """Code Agent 完整工作流测试（含 add_explanation 节点）。"""

    @pytest.mark.asyncio
    async def test_full_workflow_with_explanation(self):
        from app.modules.resource_generator.code_agent import CodeAgent

        code_md = (
            "## TCP三次握手模拟\n\n"
            "```python\n"
            "import socket\n"
            "import struct\n"
            "\n"
            "def simulate_tcp_handshake():\n"
            "    \"\"\"模拟TCP三次握手过程\"\"\"\n"
            "    # 第一次握手：客户端发送SYN\n"
            "    client_seq = 1000\n"
            "    print(f'[客户端] 发送 SYN, seq={client_seq}')\n"
            "    \n"
            "    # 第二次握手：服务端回复SYN+ACK\n"
            "    server_seq = 2000\n"
            "    print(f'[服务端] 回复 SYN+ACK, seq={server_seq}, ack={client_seq + 1}')\n"
            "    \n"
            "    # 第三次握手：客户端发送ACK\n"
            "    print(f'[客户端] 发送 ACK, ack={server_seq + 1}')\n"
            "    print('连接建立成功！')\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    simulate_tcp_handshake()\n"
            "```\n\n"
            "运行结果：连接建立成功！"
        )

        explained_md = (
            "## TCP三次握手模拟（带解析）\n\n"
            "本示例用Python模拟TCP三次握手的基本流程。\n\n"
            "```python\n"
            "# [1] 导入必要的库\n"
            "import socket\n"
            "\n"
            "# [2] 定义模拟函数\n"
            "def simulate_tcp_handshake():\n"
            "    # [3] 第一次握手\n"
            "    client_seq = 1000\n"
            "    print(f'[客户端] SYN seq={client_seq}')\n"
            "```\n\n"
            "**解析：**\n1. 导入库\n2. 定义函数\n3. 第一次握手发送SYN"
        )

        agent = CodeAgent.__new__(CodeAgent)
        agent.llm = _make_mock_llm([code_md, explained_md])
        agent.graph = agent._build_graph()

        result = await agent.generate_code(
            topic="TCP三次握手",
            course="计算机网络",
        )

        assert result["success"] is True
        assert result["detected_language"] == "python"
        assert "simulate_tcp_handshake" in result["code_only"]
        assert result["error"] is None


# ==========================================
# 5. Media Agent 集成测试
# ==========================================


class TestMediaAgentIntegration:
    """Media Agent 完整工作流测试。"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        from app.modules.resource_generator.media_agent import MediaAgent

        script_md = (
            "# TCP三次握手动画脚本\n\n"
            "### 场景 1：问题引入\n\n"
            "- **旁白**：你是否想过，当你在浏览器输入一个网址时，你的电脑和服务器之间发生了什么？"
            "今天我们来了解TCP三次握手这个核心过程。\n"
            "- **画面**：一台笔记本电脑通过蓝色网线连接到服务器机架，"
            "屏幕上显示浏览器地址栏输入URL的动画，数据包以蓝色光点形式从电脑飞向服务器。\n"
            "- **时长**：15秒\n\n"
            "---\n\n"
            "### 场景 2：第一次握手\n\n"
            "- **旁白**：首先，客户端向服务器发送一个SYN报文，意思是'你好，我想建立连接'。"
            "这个报文里包含了客户端的初始序列号。\n"
            "- **画面**：左侧蓝色圆圈标有'客户端'，发出一个标有'SYN seq=1000'的蓝色箭头，"
            "飞向右侧绿色矩形标有'服务器'。客户端状态变为SYN_SENT。\n"
            "- **时长**：20秒\n\n"
            "---\n\n"
            "### 场景 3：第二三次握手\n\n"
            "- **旁白**：服务器收到SYN后回复SYN+ACK，表示同意连接并附上自己的序列号。"
            "客户端收到后发送ACK确认，连接建立完成。\n"
            "- **画面**：服务器发出红色箭头'SYN+ACK'飞回客户端，"
            "然后客户端发出绿色箭头'ACK'飞向服务器，两侧同时亮起'ESTABLISHED'绿色指示灯。\n"
            "- **时长**：25秒\n\n"
            "---\n\n"
            "### 总结\n"
            "- 总时长预估：60秒\n"
            "- 核心视觉元素：客户端圆圈、服务器矩形、SYN/ACK箭头、状态指示灯\n"
        )

        agent = MediaAgent.__new__(MediaAgent)
        agent.llm = _make_mock_llm([script_md])
        agent.graph = agent._build_graph()

        result = await agent.generate_media(
            topic="TCP三次握手",
            course="计算机网络",
            cognitive_style="偏直觉型",
        )

        assert result["success"] is True
        assert "场景" in result["content"]
        assert "旁白" in result["content"]
        assert "画面" in result["content"]


# ==========================================
# 6. Coordinator 集成测试
# ==========================================


class TestCoordinatorIntegration:
    """Coordinator Agent 的并发调度和 SSE 事件推送测试。"""

    @pytest.mark.asyncio
    async def test_run_agent_dispatches_to_content(self):
        """验证 _run_agent 正确调用 content agent。"""
        from app.modules.resource_generator.coordinator_agent import CoordinatorAgent

        emitter = AgentEventEmitter()
        coordinator = CoordinatorAgent.__new__(CoordinatorAgent)
        coordinator.emitter = emitter

        with patch(
            "app.modules.resource_generator.coordinator_agent.content_writer"
        ) as mock_cw:
            mock_cw.generate_content = AsyncMock(
                return_value={"success": True, "content": "TCP讲解", "outline": "# 大纲", "error": None}
            )

            result = await coordinator._run_agent(
                "content",
                {"topic": "TCP三次握手", "course": "计算机网络"},
                {"knowledge_level": "中等"},
            )

        assert result["success"] is True
        assert result["content"] == "TCP讲解"

    @pytest.mark.asyncio
    async def test_run_agent_dispatches_to_quiz(self):
        with patch(
            "app.modules.resource_generator.coordinator_agent.quiz_agent"
        ) as mock_qa:
            mock_qa.generate_quiz = AsyncMock(
                return_value={"success": True, "questions": [{"stem": "Q1"}], "raw_json": "{}", "error": None}
            )

            emitter = AgentEventEmitter()
            coordinator = CoordinatorAgent.__new__(CoordinatorAgent)
            coordinator.emitter = emitter

            result = await coordinator._run_agent(
                "quiz",
                {"topic": "TCP", "gap": "三次握手"},
                {"knowledge_level": "中等", "error_pattern": ""},
            )

        assert result["success"] is True
        assert len(result["questions"]) == 1

    @pytest.mark.asyncio
    async def test_run_agent_unknown_agent_emits_error(self):
        emitter = AgentEventEmitter()
        coordinator = CoordinatorAgent.__new__(CoordinatorAgent)
        coordinator.emitter = emitter

        result = await coordinator._run_agent("nonexistent", {}, {})

        assert result == {}

    @pytest.mark.asyncio
    async def test_sse_events_sequence(self):
        """验证 Coordinator 推送的 SSE 事件序列。"""
        from app.modules.resource_generator.coordinator_agent import CoordinatorAgent

        emitter = AgentEventEmitter()
        coordinator = CoordinatorAgent.__new__(CoordinatorAgent)
        coordinator.emitter = emitter

        # Mock 所有 agent
        agents_to_mock = [
            "content_writer", "quiz_agent", "reading_agent",
            "code_agent", "media_agent", "mindmap_generator",
        ]
        mocks = {}
        for name in agents_to_mock:
            mocks[name] = patch(
                f"app.modules.resource_generator.coordinator_agent.{name}"
            )

        # 只测试 content + quiz 两个 agent 的任务
        with (
            patch(
                "app.modules.resource_generator.coordinator_agent.content_writer"
            ) as mock_cw,
            patch(
                "app.modules.resource_generator.coordinator_agent.quiz_agent"
            ) as mock_qa,
        ):
            mock_cw.generate_content = AsyncMock(
                return_value={"success": True, "content": "文档", "outline": "", "error": None}
            )
            mock_qa.generate_quiz = AsyncMock(
                return_value={"success": True, "questions": [], "raw_json": "", "error": None}
            )

            # 直接跑两个 agent
            coroutines = [
                coordinator._run_agent("content", {"topic": "TCP"}, {}),
                coordinator._run_agent("quiz", {"topic": "TCP"}, {}),
            ]
            import asyncio
            await asyncio.gather(*coroutines)
            await emitter.emit_done("完成")

        # 收集事件
        events = []
        async for chunk in emitter.stream():
            events.append(chunk)

        # 应该有: 2 * (start + log + done) + done = 7 个事件
        assert len(events) == 7
        event_types = []
        for e in events:
            data = json.loads(e.replace("data: ", "").strip())
            event_types.append(data["type"])

        assert event_types.count("agent_start") == 2
        assert event_types.count("agent_done") == 2
        assert event_types[-1] == "done"

    @pytest.mark.asyncio
    async def test_default_tasks_fallback(self):
        """规划失败时降级到默认 6 个任务。"""
        from app.modules.resource_generator.coordinator_agent import CoordinatorAgent

        task = {"course": "计算机网络", "gap": "TCP三次握手", "need": "review"}
        defaults = CoordinatorAgent._default_tasks(task)

        assert len(defaults) == 6
        topics = [t["parameters"].get("course", "") for t in defaults]
        assert all(t == "计算机网络" for t in topics)


# ==========================================
# 7. 端到端协作测试：完整资源包
# ==========================================


class TestEndToEnd:
    """模拟一个完整的资源生成请求，验证：
    1. 所有 6 个 Agent 被调度
    2. 每个返回正确结构
    3. SSE 事件序列正确
    4. 最终结果包完整
    """

    @pytest.mark.asyncio
    async def test_full_resource_generation(self):
        from app.modules.resource_generator.coordinator_agent import CoordinatorAgent

        emitter = AgentEventEmitter()
        coordinator = CoordinatorAgent.__new__(CoordinatorAgent)
        coordinator.emitter = emitter
        coordinator.llm = _make_mock_llm([
            # planner 响应
            json.dumps({
                "tasks": [
                    {"agent": "content", "description": "生成讲解文档", "parameters": {"topic": "TCP三次握手", "course": "计算机网络"}},
                    {"agent": "quiz", "description": "生成练习题", "parameters": {"topic": "TCP三次握手"}},
                    {"agent": "reading", "description": "推荐阅读", "parameters": {"topic": "TCP三次握手"}},
                    {"agent": "code", "description": "代码案例", "parameters": {"topic": "TCP三次握手"}},
                    {"agent": "media", "description": "动画脚本", "parameters": {"topic": "TCP三次握手"}},
                    {"agent": "mindmap", "description": "思维导图", "parameters": {"topic": "TCP三次握手"}},
                ]
            })
        ])

        # Mock _load_profile
        mock_profile = {
            "knowledge_level": "中等",
            "cognitive_style": "视觉学习型",
            "error_pattern": "容易混淆三次握手和四次挥手",
            "learning_pace": "中等",
            "interest_preference": "网络安全",
        }

        # Mock 所有子 Agent
        with (
            patch("app.modules.resource_generator.coordinator_agent._load_profile", return_value=mock_profile),
            patch("app.modules.resource_generator.coordinator_agent.content_writer") as mock_cw,
            patch("app.modules.resource_generator.coordinator_agent.quiz_agent") as mock_qa,
            patch("app.modules.resource_generator.coordinator_agent.reading_agent") as mock_ra,
            patch("app.modules.resource_generator.coordinator_agent.code_agent") as mock_ca,
            patch("app.modules.resource_generator.coordinator_agent.media_agent") as mock_ma,
            patch("app.modules.resource_generator.coordinator_agent.mindmap_generator") as mock_mm,
        ):
            mock_cw.generate_content = AsyncMock(return_value={
                "success": True, "content": "# TCP三次握手深度解析\n...(2000字)", "outline": "# 大纲", "error": None
            })
            mock_qa.generate_quiz = AsyncMock(return_value={
                "success": True, "questions": [
                    {"difficulty": "basic", "stem": "第一次握手的标志位？", "answer": "SYN", "explanation": "..."}
                ], "raw_json": "{}", "error": None
            })
            mock_ra.generate_reading = AsyncMock(return_value={
                "success": True, "recommendations": [
                    {"title": "TCP/IP详解", "type": "book"}
                ], "raw_json": "{}", "error": None
            })
            mock_ca.generate_code = AsyncMock(return_value={
                "success": True, "content": "```python\n# TCP模拟\n```", "detected_language": "python", "code_only": "# TCP模拟", "error": None
            })
            mock_ma.generate_media = AsyncMock(return_value={
                "success": True, "content": "### 场景 1\n**旁白**：...\n**画面**：...", "error": None
            })
            mock_mm.generate_mindmap = AsyncMock(return_value={
                "success": True, "file_path": "/tmp/tcp_mindmap.html", "html_content": "<html>...</html>", "agent_output": "完成", "error": None
            })

            result = await coordinator.run(user_id=1, task={
                "course": "计算机网络",
                "gap": "TCP三次握手",
                "need": "review",
                "extra": "",
            })

        # 验证结果
        assert "content" in result
        assert "quiz" in result
        assert "reading" in result
        assert "code" in result
        assert "media" in result
        assert "mindmap" in result

        assert result["content"]["success"] is True
        assert "TCP" in result["content"]["content"]
        assert result["quiz"]["success"] is True
        assert len(result["quiz"]["questions"]) > 0
        assert result["reading"]["success"] is True
        assert result["code"]["success"] is True
        assert result["code"]["detected_language"] == "python"
        assert result["media"]["success"] is True
        assert result["mindmap"]["success"] is True

        # 验证 SSE 事件序列
        events = []
        async for chunk in emitter.stream():
            events.append(chunk)

        event_data = [json.loads(e.replace("data: ", "").strip()) for e in events]

        # 协调器事件
        coord_events = [e for e in event_data if e["type"] == "coordinator"]
        assert len(coord_events) >= 2  # parsing + dispatching + integrating

        # 每个 Agent 的 start + done
        start_events = [e for e in event_data if e["type"] == "agent_start"]
        done_events = [e for e in event_data if e["type"] == "agent_done"]
        assert len(start_events) == 6
        assert len(done_events) == 6

        # 最终 done 事件
        final_done = [e for e in event_data if e["type"] == "done"]
        assert len(final_done) == 1
