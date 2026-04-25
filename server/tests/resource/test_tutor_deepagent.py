from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class FakeStructuredLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeDiagramLLM:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.models = []
        self.structured_llms = []

    def with_structured_output(self, model_cls):
        self.models.append(model_cls)
        structured = FakeStructuredLLM(self.outputs.pop(0))
        self.structured_llms.append(structured)
        return structured


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
    tutor.diagram_llm = FakeDiagramLLM([])

    state = {
        "need_diagram": False,
        "messages": [HumanMessage(content="TCP 三次握手是什么？")],
        "answer_text": "TCP 三次握手用于建立可靠连接。",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"] is None
    assert tutor.diagram_llm.models == []


def test_diagram_generate_node_generates_sequence_when_requested():
    from app.chat.agent import TutorAgent
    from app.chat.diagram_schemas import DiagramDecision, SequenceDiagram

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.diagram_llm = FakeDiagramLLM(
        [
            DiagramDecision(need_diagram=True, diagram_type="sequence", reason="适合时序图"),
            {
                "type": "sequence",
                "title": "TCP三次握手",
                "summary": "展示连接建立过程",
                "spec": {
                    "actors": [
                        {"id": "client", "label": "客户端", "description": "发起连接"},
                        {"id": "server", "label": "服务器", "description": "接受连接"},
                    ],
                    "messages": [
                        {
                            "from": "client",
                            "to": "server",
                            "label": "SYN",
                            "description": "请求建立连接",
                        }
                    ],
                },
            },
        ]
    )

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

    assert tutor.diagram_llm.models[0].__name__ == "DiagramDecision"
    assert tutor.diagram_llm.models[1] is SequenceDiagram
    assert result["diagram"]["type"] == "sequence"
    assert result["diagram"]["spec"]["messages"][0]["from"] == "client"


def test_diagram_generate_node_failure_does_not_raise():
    from app.chat.agent import TutorAgent

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.diagram_llm = FakeDiagramLLM([RuntimeError("structured output unavailable")])

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
    done_events = [event for event in events if event["event"] == "done"]

    assert token_events == [{"event": "token", "data": "这是最终整合后的回答"}]
    assert done_events[0]["data"]["resources"]["diagram"]["type"] == "compare"
    assert done_events[0]["data"]["resources"]["video"] is None
