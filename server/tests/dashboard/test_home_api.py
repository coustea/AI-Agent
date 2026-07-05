from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.dashboard import api as dashboard_api
from app.dashboard.api import (
    _low_score_dimensions,
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
            "knowledge_level": 85,
            "cognitive_style": 30,
            "weak_knowledge_points": 55,
            "learning_goal_type": 70,
        }
    }
    result = _low_score_dimensions(score, limit=3)
    assert result == [DIMENSION_NAMES["cognitive_style"], DIMENSION_NAMES["weak_knowledge_points"]]


def test_low_score_dimensions_ignores_zero_and_above_60():
    score = {
        "dimension_scores": {
            "knowledge_level": 0,
            "cognitive_style": 60,
            "weak_knowledge_points": 100,
        }
    }
    result = _low_score_dimensions(score)
    assert result == []


def test_profile_radar_dimensions_match_all_dimensions(monkeypatch):
    score_json = {
        "overall_score": 72,
        "dimension_scores": {
            "knowledge_level": 80,
            "cognitive_style": None,
            "weak_knowledge_points": 40,
            "knowledge_gap_pattern": 75,
        },
        "dimension_evidence": {
            "knowledge_level": ["计算机专业基础知识"],
            "knowledge_gap_pattern": ["数据库知识薄弱"],
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

    async def get_profile(user_id: int, db=None) -> Any:
        return profile

    monkeypatch.setattr(
        dashboard_api,
        "get_profile_service",
        lambda: SimpleNamespace(get_profile=get_profile),
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

    knowledge_level = next(item for item in dimensions if item["key"] == "knowledge_level")
    assert knowledge_level == {
        "key": "knowledge_level",
        "label": "知识基础",
        "score": 80,
    }

    cognitive_style = next(item for item in dimensions if item["key"] == "cognitive_style")
    assert cognitive_style["score"] == 0

    # 维度不再包含 evidence/missing 字段
    assert "evidence" not in knowledge_level
    assert "missing" not in knowledge_level

    # 顶层不再包含 user_id/module/scored_at/updated_at
    assert "user_id" not in payload
    assert "module" not in payload
    assert "scored_at" not in payload
    assert "updated_at" not in payload

    # metrics 不再包含 dimension_evidence
    assert "dimension_evidence" not in payload["metrics"]


def test_profile_radar_weak_areas_from_low_scores(monkeypatch):
    score_json = {
        "overall_score": 45,
        "dimension_scores": {
            "knowledge_level": 80,
            "cognitive_style": 20,
            "weak_knowledge_points": 55,
            "knowledge_gap_pattern": 10,
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

    async def get_profile(user_id: int, db=None) -> Any:
        return profile

    monkeypatch.setattr(
        dashboard_api,
        "get_profile_service",
        lambda: SimpleNamespace(get_profile=get_profile),
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


def test_generated_resource_model_no_source_field_after_simplification():
    """source 列已删除，dashboard 不再按 source 过滤。"""
    assert "source" not in GeneratedResource.model_fields
