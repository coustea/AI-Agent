# -*- coding: utf-8 -*-
"""验证所有 ainvoke_json 使用的 Pydantic schema 能正确解析 JSON。

确保 tool_calling 和 fallback 路径都能成功验证。
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from app.resource.schemas import TeachingPlan, TeachingOutlineItem
from app.resource.agents.reading import ReadingPayload
from app.resource.agents.quiz import QuizPayload
from app.resource.agents.ppt import MaterialDigest, DeckOutline, SlideDraft
from app.resource.agents.video import VideoMaterialDigest, VideoOutline, SceneDraft
from app.path.schemas import AgentLearningPathPlan, AgentQuestionSet
from app.profile.types import (
    OnboardingGlobalInferenceOutput,
    GlobalTutoringInferenceOutput,
    ProfileScoreOutput,
)
from app.chat.schemas import ClassificationResult, TeachingDiagram
from app.chat.memory.types import MemoryUpdateOutput


# ============ 典型 LLM 输出样本 ============

TEACHING_PLAN_JSON = {
    "teaching_strategy": "先直观类比，再协议细节",
    "outline": [
        {
            "id": "o1",
            "title": "HTTP 基础",
            "goal": "理解请求响应模型",
            "key_points": ["GET/POST", "状态码", "请求头"],
            "common_misconceptions": ["HTTP 只能浏览器用"],
            "suggested_examples": ["用 requests 发送 GET"],
            "must_not_miss": True,
        }
    ],
}

READING_PAYLOAD_JSON = {
    "title": "Python 爬虫阅读材料",
    "summary": "从 HTTP 基础到 BeautifulSoup 实战",
    "resources": [
        {
            "id": "r1",
            "title": "HTTP 协议简介",
            "type": "article",
            "url": "https://example.com/http",
            "summary": "HTTP 请求响应模型",
        }
    ],
    "learning_path": [
        {
            "step": 1,
            "title": "了解 HTTP",
            "description": "学习 GET/POST",
            "resource_ids": ["r1"],
            "goal": "理解请求响应",
        }
    ],
    "follow_up_suggestions": ["尝试抓取静态网页"],
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
            "difficulty": "easy",
            "knowledge_points": ["HTTP"],
        }
    ],
}

AGENT_QUESTION_SET_JSON = {
    "questions": [
        {
            "question": "BeautifulSoup 中 find() 返回什么？",
            "choice": {"A": "第一个匹配元素", "B": "所有匹配元素"},
            "answer": "A",
            "analysis": "find 返回第一个匹配",
            "knowledge_points": ["BeautifulSoup"],
        }
    ]
}

MATERIAL_DIGEST_JSON = {
    "topic": "Python 爬虫",
    "audience": "初学者",
    "learning_goal": "掌握基础爬虫",
    "core_concepts": ["requests", "BeautifulSoup"],
    "structure_points": ["HTTP 基础", "HTML 解析"],
    "examples": ["抓取新闻"],
    "process_steps": ["发送请求", "解析响应", "提取数据"],
    "comparisons": ["requests vs urllib"],
    "misconceptions": ["爬虫等于黑客"],
    "practice_prompts": ["抓取豆瓣电影"],
    "code_cases": ["import requests\nresp = requests.get(url)"],
    "source_map": {"reading": ["reading"], "quiz": ["quiz"]},
}

DECK_OUTLINE_JSON = {
    "topic": "Python 爬虫",
    "title": "爬虫入门指南",
    "subtitle": "从零开始",
    "theme": "theme-mac-light",
    "audience_level": "beginner",
    "narrative": "从 HTTP 基础讲起",
    "slides": [
        {
            "slide_id": "s1",
            "index": 1,
            "role": "cover",
            "title": "Python 爬虫入门",
            "learning_objective": "了解爬虫概念",
            "source_agents": ["reading"],
            "layout": "FocusTitle",
            "blocks": [
                {
                    "block_id": "b1",
                    "slot": "title",
                    "type": "Heading",
                    "required_fields": ["text"],
                    "content_hint": "主标题",
                    "min_length": 5,
                }
            ],
        }
    ],
}

SLIDE_DRAFT_JSON = {
    "slide_id": "s1",
    "index": 1,
    "title": "Python 爬虫入门",
    "blocks": [
        {"block_id": "b1", "type": "Heading", "data": {"text": "爬虫入门"}}
    ],
    "speaker_notes": "欢迎大家",
}

AGENT_LEARNING_PATH_PLAN_JSON = {
    "title": "Python 爬虫学习路径",
    "stages": [
        {"stage_id": "s1", "title": "HTTP 基础"}
    ],
    "nodes": [
        {
            "node_id": "n1",
            "stage_id": "s1",
            "title": "HTTP 协议",
            "prerequisites": [],
            "difficulty": "intermediate",
            "priority": 1,
        }
    ],
}

ONBOARDING_GLOBAL_JSON = {
    "dimensions_patch": {
        "learning_style": {"value": "visual", "evidence": ["偏好图表"]},
        "difficulty_preference": {"value": "intermediate", "evidence": []},
    }
}

GLOBAL_TUTORING_JSON = {
    "should_update": True,
    "dimensions_patch": {
        "learning_style": {"value": "kinesthetic", "evidence": ["动手实践"]}
    },
}

PROFILE_SCORE_JSON = {
    "dimension_scores": {"reading": 80, "quiz": 70},
    "dimension_evidence": {"reading": ["阅读理解能力强"]},
}

CLASSIFICATION_RESULT_JSON = {
    "intent": "question",
    "subject": "Python 爬虫",
    "difficulty": "beginner",
    "needs_file_analysis": False,
    "needs_knowledge_search": True,
    "needs_web_search": False,
    "needs_profile": False,
    "needs_long_term_memory": False,
    "needs_recent_evaluation": False,
    "needs_diagram": False,
    "safety_risk": "none",
    "answer_style": "explain",
}

TEACHING_DIAGRAM_JSON = {
    "graph_type": "comparison",
    "title": "requests vs urllib",
    "subtitle": "两种 HTTP 库对比",
    "teaching_goal": "理解两者差异",
    "course": "Python 爬虫",
    "difficulty": "beginner",
    "visual_content": {
        "left_entity": {
            "name": "requests",
            "core_label": "HTTP 库",
            "short_desc": "简洁的 HTTP 客户端",
        },
        "right_entity": {
            "name": "urllib",
            "core_label": "标准库",
            "short_desc": "Python 内置 HTTP 模块",
        },
        "dimensions": [
            {"name": "易用性", "left": "高", "right": "低"},
            {"name": "功能", "left": "丰富", "right": "基础"},
        ],
        "visual_summary": {
            "left_keyword": "简洁",
            "right_keyword": "标准",
            "center_conclusion": "推荐使用 requests",
        },
    },
    "teaching_content": {
        "core_explanation": "两种库的对比",
        "key_points": ["requests 更简洁", "urllib 是标准库"],
        "common_mistakes": ["认为 urllib 性能更好"],
        "examples": ["requests.get(url)"],
        "summary": "推荐使用 requests",
    },
}

MEMORY_UPDATE_OUTPUT_JSON = {
    "need_update": True,
    "memory_markdown": "- 用户喜欢视觉化学习\n- 偏好图表",
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
    "visual_opportunities": ["代码演示", "终端截图"],
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
            "visual_type": "card",
            "content_hint": "主持人开场",
            "required_sources": ["reading"],
        },
        {
            "scene_id": "sc2",
            "index": 2,
            "role": "recap",
            "title": "总结",
            "duration_seconds": 60,
            "learning_objective": "回顾要点",
            "visual_type": "card",
            "content_hint": "总结回顾",
            "required_sources": [],
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
    "visual_type": "card",
    "source_agents": ["reading"],
}


# ============ 测试 ============


class TestTeachingPlanSchema:
    def test_parses_valid_json(self) -> None:
        result = TeachingPlan.model_validate(TEACHING_PLAN_JSON)
        assert result.teaching_strategy == "先直观类比，再协议细节"
        assert len(result.outline) == 1
        assert result.outline[0].id == "o1"

    def test_rejects_invalid_outline_id(self) -> None:
        data = {
            **TEACHING_PLAN_JSON,
            "outline": [{**TEACHING_PLAN_JSON["outline"][0], "id": "invalid"}],
        }
        with pytest.raises(ValidationError):
            TeachingPlan.model_validate(data)


class TestReadingPayloadSchema:
    def test_parses_valid_json(self) -> None:
        result = ReadingPayload.model_validate(READING_PAYLOAD_JSON)
        assert result.title == "Python 爬虫阅读材料"
        assert len(result.resources) == 1
        assert len(result.learning_path) == 1

    def test_parses_minimal_json(self) -> None:
        result = ReadingPayload.model_validate({"title": "t", "summary": "s"})
        assert result.resources == []


class TestQuizPayloadSchema:
    def test_parses_valid_json(self) -> None:
        result = QuizPayload.model_validate(QUIZ_PAYLOAD_JSON)
        assert result.title == "Python 爬虫测验"
        assert len(result.questions) == 1
        assert result.questions[0].answer == "A"


class TestAgentQuestionSetSchema:
    def test_parses_valid_json(self) -> None:
        result = AgentQuestionSet.model_validate(AGENT_QUESTION_SET_JSON)
        assert len(result.questions) == 1
        assert result.questions[0].answer == "A"


class TestMaterialDigestSchema:
    def test_parses_valid_json(self) -> None:
        result = MaterialDigest.model_validate(MATERIAL_DIGEST_JSON)
        assert result.topic != ""
        assert len(result.core_concepts) == 2


class TestDeckOutlineSchema:
    def test_parses_valid_json(self) -> None:
        result = DeckOutline.model_validate(DECK_OUTLINE_JSON)
        assert result.title == "爬虫入门指南"
        assert len(result.slides) == 1

    def test_rejects_empty_slides(self) -> None:
        data = {**DECK_OUTLINE_JSON, "slides": []}
        with pytest.raises(ValidationError):
            DeckOutline.model_validate(data)


class TestSlideDraftSchema:
    def test_parses_valid_json(self) -> None:
        result = SlideDraft.model_validate(SLIDE_DRAFT_JSON)
        assert result.slide_id == "s1"
        assert len(result.blocks) == 1


class TestAgentLearningPathPlanSchema:
    def test_parses_valid_json(self) -> None:
        result = AgentLearningPathPlan.model_validate(AGENT_LEARNING_PATH_PLAN_JSON)
        assert result.title == "Python 爬虫学习路径"
        assert len(result.stages) == 1
        assert len(result.nodes) == 1

    def test_rejects_invalid_node_priority(self) -> None:
        data = {
            **AGENT_LEARNING_PATH_PLAN_JSON,
            "nodes": [{**AGENT_LEARNING_PATH_PLAN_JSON["nodes"][0], "priority": "high"}],
        }
        with pytest.raises(ValidationError):
            AgentLearningPathPlan.model_validate(data)


class TestOnboardingGlobalInferenceOutputSchema:
    def test_parses_valid_json(self) -> None:
        result = OnboardingGlobalInferenceOutput.model_validate(ONBOARDING_GLOBAL_JSON)
        assert "learning_style" in result.dimensions_patch


class TestGlobalTutoringInferenceOutputSchema:
    def test_parses_valid_json(self) -> None:
        result = GlobalTutoringInferenceOutput.model_validate(GLOBAL_TUTORING_JSON)
        assert result.should_update is True
        assert "learning_style" in result.dimensions_patch


class TestProfileScoreOutputSchema:
    def test_parses_valid_json(self) -> None:
        result = ProfileScoreOutput.model_validate(PROFILE_SCORE_JSON)
        assert result.dimension_scores["reading"] == 80


class TestClassificationResultSchema:
    def test_parses_valid_json(self) -> None:
        result = ClassificationResult.model_validate(CLASSIFICATION_RESULT_JSON)
        assert result.intent == "question"
        assert result.subject == "Python 爬虫"


class TestTeachingDiagramSchema:
    def test_parses_valid_json(self) -> None:
        result = TeachingDiagram.model_validate(TEACHING_DIAGRAM_JSON)
        assert result.graph_type == "comparison"
        assert result.title == "requests vs urllib"

    def test_rejects_mismatched_graph_type(self) -> None:
        data = {**TEACHING_DIAGRAM_JSON, "graph_type": "flowchart"}
        with pytest.raises(ValidationError):
            TeachingDiagram.model_validate(data)


class TestMemoryUpdateOutputSchema:
    def test_parses_valid_json(self) -> None:
        result = MemoryUpdateOutput.model_validate(MEMORY_UPDATE_OUTPUT_JSON)
        assert result.need_update is True
        assert result.confidence == 0.9


class TestVideoSchemas:
    def test_video_material_digest_parses(self) -> None:
        result = VideoMaterialDigest.model_validate(VIDEO_MATERIAL_DIGEST_JSON)
        assert result.topic != ""

    def test_video_outline_parses(self) -> None:
        result = VideoOutline.model_validate(VIDEO_OUTLINE_JSON)
        assert result.title == "Python 爬虫视频教程"
        assert len(result.scenes) == 2

    def test_scene_draft_parses(self) -> None:
        result = SceneDraft.model_validate(SCENE_DRAFT_JSON)
        assert result.scene_id == "sc1"


class TestSchemaRoundTrip:
    """验证 schema → JSON → schema 往返一致性。"""

    @pytest.mark.parametrize(
        "schema_cls,data",
        [
            (TeachingPlan, TEACHING_PLAN_JSON),
            (ReadingPayload, READING_PAYLOAD_JSON),
            (QuizPayload, QUIZ_PAYLOAD_JSON),
            (AgentQuestionSet, AGENT_QUESTION_SET_JSON),
            (MaterialDigest, MATERIAL_DIGEST_JSON),
            (DeckOutline, DECK_OUTLINE_JSON),
            (SlideDraft, SLIDE_DRAFT_JSON),
            (AgentLearningPathPlan, AGENT_LEARNING_PATH_PLAN_JSON),
            (OnboardingGlobalInferenceOutput, ONBOARDING_GLOBAL_JSON),
            (GlobalTutoringInferenceOutput, GLOBAL_TUTORING_JSON),
            (ProfileScoreOutput, PROFILE_SCORE_JSON),
            (ClassificationResult, CLASSIFICATION_RESULT_JSON),
            (MemoryUpdateOutput, MEMORY_UPDATE_OUTPUT_JSON),
        ],
    )
    def test_round_trip(self, schema_cls: type, data: dict) -> None:
        instance = schema_cls.model_validate(data)
        dumped = json.loads(instance.model_dump_json())
        restored = schema_cls.model_validate(dumped)
        assert instance.model_dump() == restored.model_dump()
