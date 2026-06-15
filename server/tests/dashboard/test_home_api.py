from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.dashboard import api as dashboard_api
from app.dashboard.api import (
    _low_score_dimensions,
    _score_evidence,
    _score_json,
)
from app.infra.models import GeneratedResource
from app.profile.types import ALL_DIMENSIONS, DIMENSION_NAMES


class _ExecResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def first(self) -> Any:
        return self._value

    def all(self) -> list[Any]:
        return [self._value] if self._value is not None else []


class _DashboardSession:
    async def exec(self, stmt: Any) -> _ExecResult:
        return _ExecResult(None)

    async def merge(self, instance: Any) -> Any:
        return instance


def test_score_json_pass_through():
    data = {"overall_score": 80}
    assert _score_json(data) is data


def test_score_json_returns_empty_on_non_dict():
    assert _score_json(None) == {}
    assert _score_json("not a dict") == {}


def test_low_score_dimensions_returns_lowest_below_60():
    score = {
        "dimension_scores": {
            "major_background": 85,
            "student_stage": 30,
            "course_context": 55,
            "learning_goal_type": 70,
        }
    }
    result = _low_score_dimensions(score, limit=3)
    assert result == [DIMENSION_NAMES["student_stage"], DIMENSION_NAMES["course_context"]]


def test_low_score_dimensions_ignores_zero_and_above_60():
    score = {
        "dimension_scores": {
            "major_background": 0,
            "student_stage": 60,
            "course_context": 100,
        }
    }
    result = _low_score_dimensions(score)
    assert result == []


def test_score_evidence_returns_items():
    score = {
        "dimension_evidence": {
            "weak_knowledge_points": ["线性代数", "矩阵运算", "概率论"],
        }
    }
    assert _score_evidence(score, "weak_knowledge_points") == ["线性代数", "矩阵运算", "概率论"]


def test_score_evidence_respects_limit():
    score = {
        "dimension_evidence": {
            "weak_knowledge_points": ["A", "B", "C", "D", "E"],
        }
    }
    assert len(_score_evidence(score, "weak_knowledge_points", limit=2)) == 2


def test_score_evidence_skips_empty_strings():
    score = {
        "dimension_evidence": {
            "weak_knowledge_points": ["  ", "", "有效项"],
        }
    }
    assert _score_evidence(score, "weak_knowledge_points") == ["有效项"]


def test_score_evidence_returns_empty_when_no_data():
    assert _score_evidence({}, "weak_knowledge_points") == []


def test_profile_radar_dimensions_match_all_dimensions(monkeypatch):
    score_json = {
        "overall_score": 72,
        "dimension_scores": {
            "major_background": 80,
            "student_stage": None,
            "course_context": 75,
            "weak_knowledge_points": 40,
        },
        "dimension_evidence": {
            "major_background": ["计算机专业"],
            "course_context": ["线性代数"],
        },
        "scored_at": "2026-06-07T10:00:00+08:00",
    }
    profile = SimpleNamespace(
        user_id=7,
        module="mentor",
        profile_json={},
        profile_score_json=score_json,
        updated_at=datetime.now(timezone.utc),
    )

    async def get_or_create_global_profile(user_id: int) -> Any:
        return profile

    monkeypatch.setattr(
        dashboard_api,
        "get_profile_service",
        lambda: SimpleNamespace(get_or_create_global_profile=get_or_create_global_profile),
    )

    import asyncio

    response = asyncio.run(dashboard_api.get_profile_radar(
        current_user=SimpleNamespace(id=7),
        session=_DashboardSession(),
    ))
    import json
    payload = json.loads(response.body.decode("utf-8"))["data"]

    dimensions = payload["dimensions"]
    assert [item["key"] for item in dimensions] == list(ALL_DIMENSIONS)
    assert [item["label"] for item in dimensions] == [
        DIMENSION_NAMES[key] for key in ALL_DIMENSIONS
    ]

    major = next(item for item in dimensions if item["key"] == "major_background")
    assert major == {
        "key": "major_background",
        "label": "专业背景",
        "score": 80,
        "evidence": ["计算机专业"],
        "missing": False,
    }

    student = next(item for item in dimensions if item["key"] == "student_stage")
    assert student["score"] == 0
    assert student["missing"] is True
    assert student["evidence"] == []

    assert "section_coverage" not in payload
    assert "evidence_quality" not in payload
    assert "confidence" not in payload
    assert "knowledge_mastery" not in payload


def test_profile_radar_weak_areas_from_low_scores(monkeypatch):
    score_json = {
        "overall_score": 45,
        "dimension_scores": {
            "major_background": 80,
            "student_stage": 20,
            "course_context": 55,
            "weak_knowledge_points": 10,
        },
        "dimension_evidence": {},
        "scored_at": "2026-06-07T10:00:00+08:00",
    }
    profile = SimpleNamespace(
        user_id=7,
        module="mentor",
        profile_json={},
        profile_score_json=score_json,
        updated_at=datetime.now(timezone.utc),
    )

    async def get_or_create_global_profile(user_id: int) -> Any:
        return profile

    monkeypatch.setattr(
        dashboard_api,
        "get_profile_service",
        lambda: SimpleNamespace(get_or_create_global_profile=get_or_create_global_profile),
    )

    import asyncio

    response = asyncio.run(dashboard_api.get_profile_radar(
        current_user=SimpleNamespace(id=7),
        session=_DashboardSession(),
    ))
    import json
    payload = json.loads(response.body.decode("utf-8"))["data"]

    assert len(payload["weak_areas"]) > 0
    assert DIMENSION_NAMES["weak_knowledge_points"] in payload["weak_areas"]


def test_generated_resource_model_exposes_source_field_for_dashboard_filters():
    assert "source" in GeneratedResource.model_fields
