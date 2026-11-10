# -*- coding: utf-8 -*-
"""验证核心 Pydantic schema 能正确解析 JSON。"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from app.resource.schemas import (
    ReadingPayload,
    QuizPayload,
    ResourceGenerationRequest,
    ResourceRunState,
)
from app.chat.memory import MemoryUpdateOutput


# ============ 典型 LLM 输出样本 ============

RESOURCE_REQUEST_JSON = {
    "topic": "TCP 三次握手",
    "learning_goal": "掌握TCP三次握手与四次挥手的核心原理与状态流转过程",
    "target_resources": ["content", "mindmap"],
    "difficulty": "intermediate",
    "preferences": {
        "programming_language": "python",
        "voice": "teacher",
    },
}

READING_PAYLOAD_JSON = {
    "resources": [
        {
            "id": "r1",
            "type": "article",
            "title": "HTTP 协议简介",
            "url": "https://example.com/http",
            "language": "中文",
            "difficulty": "medium",
        }
    ],
}

QUIZ_PAYLOAD_JSON = {
    "title": "Python 爬虫测验",
    "summary": "检验 HTTP 和 BeautifulSoup 知识",
    "questions": [
        {
            "id": 1,
            "type": "single_choice",
            "question": "HTTP GET 请求的语义是什么？",
            "options": [
                {"label": "A", "content": "获取资源"},
                {"label": "B", "content": "提交数据"},
                {"label": "C", "content": "删除资源"},
                {"label": "D", "content": "更新资源"},
            ],
            "answer": "A",
            "explanation": "GET 用于获取资源",
            "difficulty": "basic",
            "knowledge_points": ["HTTP"],
        }
    ],
}

MEMORY_UPDATE_OUTPUT_JSON = {
    "need_update": True,
    "memory_markdown": "- 用户喜欢视觉化学习",
    "confidence": 0.9,
    "update_reason": "发现新的学习偏好",
}


# ============ 测试 ============


class TestResourceRequestSchema:
    def test_parses_valid_json(self) -> None:
        result = ResourceGenerationRequest.model_validate(RESOURCE_REQUEST_JSON)
        assert result.learning_goal.startswith("掌握TCP三次握手")
        assert result.target_resources == ["content", "mindmap"]
        assert "content" in result.target_resources

    def test_rejects_empty_topic(self) -> None:
        with pytest.raises(ValidationError):
            ResourceGenerationRequest.model_validate({"topic": "", "target_resources": ["content"]})


class TestReadingPayloadSchema:
    def test_parses_valid_json(self) -> None:
        result = ReadingPayload.model_validate(READING_PAYLOAD_JSON)
        assert len(result.resources) == 1
        assert result.resources[0].title == "HTTP 协议简介"


class TestQuizPayloadSchema:
    def test_parses_valid_json(self) -> None:
        result = QuizPayload.model_validate(QUIZ_PAYLOAD_JSON)
        assert result.questions[0].answer == "A"


class TestSchemaRoundTrip:
    """验证 schema → JSON → schema 往返一致性。"""

    @pytest.mark.parametrize(
        "schema_cls,data",
        [
            (ResourceGenerationRequest, RESOURCE_REQUEST_JSON),
            (ReadingPayload, READING_PAYLOAD_JSON),
            (QuizPayload, QUIZ_PAYLOAD_JSON),
            (MemoryUpdateOutput, MEMORY_UPDATE_OUTPUT_JSON),
        ],
    )
    def test_round_trip(self, schema_cls: type, data: dict) -> None:
        instance = schema_cls.model_validate(data)
        dumped = json.loads(instance.model_dump_json())
        restored = schema_cls.model_validate(dumped)
        assert instance.model_dump() == restored.model_dump()
