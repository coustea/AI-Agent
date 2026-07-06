# -*- coding: utf-8 -*-
"""验证核心 Pydantic schema 能正确解析 JSON。"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from app.resource.schemas import ResourcePlan
from app.resource.agents.reading import ReadingPayload
from app.resource.agents.quiz import QuizPayload
from app.shared.video.schemas import VideoMaterialDigest, VideoOutline, SceneDraft
from app.chat.memory.types import MemoryUpdateOutput


# ============ 典型 LLM 输出样本 ============

RESOURCE_PLAN_JSON = {
    "content": "# 资源生成协同计划\n\n## 1. 用户需求理解\n- 理解三次握手\n\n### [content]\n- 生成目标：讲解TCP三次握手\n\n### [mindmap]\n- 生成目标：知识结构",
    "title": "TCP三次握手",
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

VIDEO_MATERIAL_DIGEST_JSON = {
    "topic": "Python 爬虫",
    "audience": "初学者",
    "learning_goal": "理解爬虫原理",
    "core_concepts": ["requests", "BeautifulSoup"],
    "facts": ["requests 是最流行的 HTTP 库"],
    "examples": ["import requests"],
    "process_steps": ["发送请求", "解析响应"],
    "misconceptions": ["爬虫不是黑客工具"],
    "practice_prompts": ["尝试抓取一个网页"],
    "visual_opportunities": ["代码演示"],
    "source_map": {"content": ["o1"]},
}

VIDEO_OUTLINE_JSON = {
    "title": "Python 爬虫视频教程",
    "topic": "Python 爬虫",
    "duration_seconds": 120,
    "scenes": [
        {
            "scene_id": "sc1",
            "index": 1,
            "role": "hook",
            "title": "简介",
            "duration_seconds": 60,
            "learning_objective": "了解爬虫概念",
            "visual_type": "title_intro",
            "content_hint": "主持人开场",
            "required_sources": ["reading"],
        },
    ],
}

SCENE_DRAFT_JSON = {
    "scene_id": "sc1",
    "index": 1,
    "title": "开场介绍",
    "narration": "今天我们学习 Python 爬虫",
    "captions": ["欢迎"],
    "on_screen_text": ["Python 爬虫入门"],
    "visual_prompt": "主持人讲解",
    "visual_type": "concept_explain",
    "visual": {"concept": "网络爬虫", "explanation": "自动获取网页内容的程序"},
    "source_agents": ["reading"],
}


# ============ 测试 ============


class TestResourcePlanSchema:
    def test_parses_valid_json(self) -> None:
        result = ResourcePlan.model_validate(RESOURCE_PLAN_JSON)
        assert result.title == "TCP三次握手"
        assert result.agent_ids == ["content", "mindmap"]
        assert result.has_agent("content")

    def test_rejects_empty_content(self) -> None:
        with pytest.raises(ValidationError):
            ResourcePlan.model_validate({"content": "", "title": "test"})


class TestReadingPayloadSchema:
    def test_parses_valid_json(self) -> None:
        result = ReadingPayload.model_validate(READING_PAYLOAD_JSON)
        assert len(result.resources) == 1
        assert result.resources[0].title == "HTTP 协议简介"


class TestQuizPayloadSchema:
    def test_parses_valid_json(self) -> None:
        result = QuizPayload.model_validate(QUIZ_PAYLOAD_JSON)
        assert result.questions[0].answer == "A"


class TestVideoSchemas:
    def test_video_material_digest_parses(self) -> None:
        result = VideoMaterialDigest.model_validate(VIDEO_MATERIAL_DIGEST_JSON)
        assert result.topic != ""

    def test_scene_draft_parses(self) -> None:
        result = SceneDraft.model_validate(SCENE_DRAFT_JSON)
        assert result.scene_id == "sc1"


class TestSchemaRoundTrip:
    """验证 schema → JSON → schema 往返一致性。"""

    @pytest.mark.parametrize(
        "schema_cls,data",
        [
            (ResourcePlan, RESOURCE_PLAN_JSON),
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
