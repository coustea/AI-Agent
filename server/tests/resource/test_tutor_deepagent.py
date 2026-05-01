from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLlmManager:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    async def ainvoke_structured(self, model_type, schema, messages, **kwargs):
        self.calls.append(
            {
                "model_type": model_type,
                "schema": schema,
                "messages": messages,
                "structured_kwargs": kwargs,
            }
        )
        payload = self.outputs.pop(0)
        if isinstance(payload, Exception):
            raise payload
        if isinstance(payload, BaseModel):
            return payload
        return schema.model_validate(payload)

    async def ainvoke(self, model_type, messages, *, model_kwargs=None, **_kwargs):
        self.calls.append(
            {
                "model_type": model_type,
                "messages": messages,
                "model_kwargs": model_kwargs or {},
            }
        )
        payload = self.outputs.pop(0)
        if isinstance(payload, Exception):
            raise payload
        if isinstance(payload, str):
            return FakeResponse(payload)
        if isinstance(payload, BaseModel):
            return FakeResponse(payload.model_dump_json(by_alias=True, ensure_ascii=False))
        return FakeResponse(json.dumps(payload, ensure_ascii=False))


class FakeCtxService:
    async def save_message(self, **_kwargs):
        return None

    async def build_profile_context(self, _user_id):
        return ""

    async def build_long_term_memory_context(self, _user_id):
        return ""

    async def build_recent_chat_context(
        self,
        *,
        user_id,
        session_id,
        user_message,
        image_urls,
        file_urls,
    ):
        return [HumanMessage(content=user_message)], ""

    @staticmethod
    def build_file_context(_image_urls, _file_urls):
        return ""

    async def post_turn_pipeline(self, **_kwargs):
        return None


def test_diagram_generate_node_skips_when_disabled():
    from app.chat.agent import TutorAgent

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager([])

    state = {
        "need_diagram": False,
        "messages": [HumanMessage(content="TCP 三次握手是什么？")],
        "answer_text": "TCP 三次握手用于建立可靠连接。",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"] is None
    assert tutor.llm_manager.calls == []


def test_diagram_generate_node_generates_sequence_when_requested():
    from app.chat.agent import TutorAgent
    from app.chat.schemas import DiagramDecision

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager(
        [
            DiagramDecision(need_diagram=True, diagram_type="sequence", reason="适合时序图"),
            "sequenceDiagram\n    participant client as 客户端\n    participant server as 服务器\n    client->>server: SYN",
        ]
    )
    tutor.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}

    state = {
        "need_diagram": True,
        "messages": [HumanMessage(content="TCP 三次握手是什么？请配图解释")],
        "answer_text": "TCP 三次握手包括 SYN、SYN-ACK、ACK。",
        "profile_context": "",
        "fact_context": "",
        "recent_chat_context": "",
        "attachment_analysis_context": "",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert tutor.llm_manager.calls[0]["model_type"] == "spark"
    assert tutor.llm_manager.calls[0]["structured_kwargs"]["strict"] is True
    assert "structured_kwargs" not in tutor.llm_manager.calls[1]
    assert result["diagram"]["type"] == "sequence"
    assert result["diagram"]["render"]["engine"] == "mermaid"
    assert result["diagram"]["render"]["source"].startswith("sequenceDiagram")
    assert "client->>server: SYN" in result["diagram"]["render"]["source"]


def test_diagram_generate_node_accepts_mermaid_fenced_output():
    from app.chat.agent import TutorAgent
    from app.chat.schemas import DiagramDecision

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager(
        [
            DiagramDecision(need_diagram=True, diagram_type="hierarchy", reason="适合层级图"),
            "```mermaid\ngraph TD\n    root[计算机网络] --> tcpip[TCP/IP]\n```",
        ]
    )
    tutor.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}

    state = {
        "need_diagram": True,
        "messages": [HumanMessage(content="输出一份关于计算机网络的知识图解")],
        "answer_text": "计算机网络可从体系结构、传输机制和应用协议来理解。",
        "profile_context": "",
        "fact_context": "",
        "recent_chat_context": "",
        "attachment_analysis_context": "",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"]["type"] == "hierarchy"
    assert result["diagram"]["render"]["source"] == "graph TD\n    root[计算机网络] --> tcpip[TCP/IP]"


def test_diagram_generate_node_uses_last_ai_message_when_answer_text_missing():
    from app.chat.agent import TutorAgent
    from app.chat.schemas import DiagramDecision

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager(
        [
            DiagramDecision(need_diagram=True, diagram_type="sequence", reason="适合时序图"),
            "sequenceDiagram\n    client->>server: SYN",
        ]
    )
    tutor.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}

    state = {
        "need_diagram": True,
        "messages": [
            HumanMessage(content="TCP 三次握手是什么？请配图解释"),
            AIMessage(content="客户端发送 SYN，服务器返回 SYN-ACK，客户端发送 ACK。"),
        ],
        "profile_context": "",
        "fact_context": "",
        "recent_chat_context": "",
        "attachment_analysis_context": "",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"]["type"] == "sequence"
    assert result["diagram"]["render"]["source"].startswith("sequenceDiagram")


def test_diagram_generate_node_keeps_llm_authored_mermaid_sequence():
    from app.chat.agent import TutorAgent
    from app.chat.schemas import DiagramDecision

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager(
        [
            DiagramDecision(need_diagram=True, diagram_type="sequence", reason="适合时序图"),
            "sequenceDiagram\n"
            "    participant client as 客户端\n"
            "    participant server as 服务端\n"
            "    client->>server: SYN seq=x 请求建立连接\n"
            "    server->>client: SYN ACK seq=y ack=x+1\n"
            "    client->>server: ACK ack=y+1 连接建立",
        ]
    )
    tutor.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}

    state = {
        "need_diagram": True,
        "messages": [HumanMessage(content="请用图解说明 TCP 三次握手")],
        "answer_text": "客户端先发 SYN，服务端回 SYN+ACK，客户端再发 ACK。",
        "profile_context": "",
        "fact_context": "",
        "recent_chat_context": "",
        "attachment_analysis_context": "",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"]["type"] == "sequence"
    source = result["diagram"]["render"]["source"]
    assert "SYN seq=x 请求建立连接" in source
    assert "SYN ACK seq=y ack=x+1" in source
    assert "ACK ack=y+1 连接建立" in source


def test_decide_diagram_returns_none_when_user_requested_diagram_without_valid_type():
    from app.chat.agent import TutorAgent
    from app.chat.schemas import DiagramDecision

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager(
        [
            DiagramDecision(need_diagram=False, diagram_type=None, reason="简单问题"),
        ]
    )
    tutor.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}

    decision = asyncio.run(
        tutor._decide_diagram(
            question="TCP 三次握手是什么？请配图解释",
            answer="客户端向服务器发送 SYN，服务器返回 SYN-ACK，客户端再发送 ACK。",
            state={"need_diagram": True},
        )
    )

    assert decision.need_diagram is False
    assert decision.diagram_type is None


def test_diagram_generate_node_returns_none_when_structured_output_is_unavailable():
    from app.chat.agent import TutorAgent

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager([RuntimeError("This response_format type is unavailable now")])
    tutor.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}

    state = {
        "need_diagram": True,
        "messages": [
            HumanMessage(content="TCP 三次握手是什么？请配图解释"),
            AIMessage(content="客户端发送 SYN，服务器返回 SYN-ACK，客户端发送 ACK。"),
        ],
        "profile_context": "",
        "fact_context": "",
        "recent_chat_context": "",
        "attachment_analysis_context": "",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"] is None


def test_diagram_generate_node_returns_none_when_tool_choice_is_unsupported():
    from app.chat.agent import TutorAgent

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager([RuntimeError("spark does not support this tool_choice")])
    tutor.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}

    state = {
        "need_diagram": True,
        "messages": [
            HumanMessage(content="TCP 三次握手是什么？请配图解释"),
            AIMessage(content="客户端发送 SYN，服务器返回 SYN-ACK，客户端发送 ACK。"),
        ],
        "profile_context": "",
        "fact_context": "",
        "recent_chat_context": "",
        "attachment_analysis_context": "",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))
    assert result["diagram"] is None


def test_diagram_generate_node_failure_does_not_raise():
    from app.chat.agent import TutorAgent

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm_manager = FakeLlmManager([RuntimeError("structured output unavailable")])
    tutor.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}

    state = {
        "need_diagram": True,
        "messages": [HumanMessage(content="进程和线程有什么区别？")],
        "answer_text": "进程是资源分配单位，线程是调度单位。",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"] is None


def test_chat_stream_done_event_includes_diagram_resource(monkeypatch):
    from app.chat import agent as chat_agent

    diagram = {
        "type": "compare",
        "title": "进程和线程",
        "summary": "对比资源和调度差异",
        "spec": {
            "items": [
                {"label": "进程", "description": "资源分配单位", "points": ["独立地址空间"]},
                {"label": "线程", "description": "CPU调度单位", "points": ["共享进程资源"]},
            ],
            "dimensions": ["资源", "调度"],
        },
        "render": {
            "engine": "mermaid",
            "format": "text",
            "source": "flowchart LR\n    item_1[\"进程\"]\n    item_2[\"线程\"]",
        },
    }

    class FakeGraph:
        async def astream_events(self, _initial_state, **_kwargs):
            yield {"event": "on_chain_start", "name": "classify"}
            yield {
                "event": "on_chain_end",
                "name": "classify",
                "data": {"output": {"route": "direct", "execution_mode": "direct"}},
            }
            yield {"event": "on_chain_start", "name": "direct_answer"}
            yield {
                "event": "on_chat_model_stream",
                "name": "ChatSparkLLM",
                "metadata": {"langgraph_node": "direct_answer"},
                "data": {"chunk": AIMessage(content="这是")},
            }
            yield {
                "event": "on_chat_model_stream",
                "name": "ChatSparkLLM",
                "metadata": {"langgraph_node": "direct_answer"},
                "data": {"chunk": AIMessage(content="最终整合后的回答")},
            }
            yield {
                "event": "on_chain_end",
                "name": "direct_answer",
                "data": {
                    "output": {
                        "messages": [AIMessage(content="这是最终整合后的回答")],
                        "answer_text": "这是最终整合后的回答",
                        "termination_reason": "direct_answer_done",
                    }
                },
            }
            yield {"event": "on_chain_start", "name": "diagram_generate"}
            yield {
                "event": "on_chain_end",
                "name": "diagram_generate",
                "data": {"output": {"diagram": diagram}},
            }

    tutor = chat_agent.TutorAgent.__new__(chat_agent.TutorAgent)
    tutor.memory_layer = FakeCtxService()
    tutor.graph = FakeGraph()
    tutor._background_tasks = set()
    tutor._spawn_background = lambda coro, **_kwargs: coro.close()

    async def fake_ensure_graph():
        return None

    tutor._ensure_graph = fake_ensure_graph

    events = []

    async def collect():
        async for event in tutor.chat_stream(
            user_id=1,
            user_message="进程和线程有什么区别？",
            session_id="s1",
            need_diagram=True,
        ):
            events.append(event)

    asyncio.run(collect())

    token_events = [event for event in events if event["event"] == "token"]
    status_events = [event for event in events if event["event"] == "status"]
    done_events = [event for event in events if event["event"] == "done"]

    assert token_events == [
        {"event": "token", "data": "这是"},
        {"event": "token", "data": "最终整合后的回答"},
    ]
    assert status_events[-1]["data"]["stage"] == "diagram_generate"
    assert done_events[0]["data"]["resources"]["diagram"]["type"] == "compare"
    assert done_events[0]["data"]["resources"]["diagram"]["render"]["engine"] == "mermaid"
    assert done_events[0]["data"]["resources"]["video"] is None
