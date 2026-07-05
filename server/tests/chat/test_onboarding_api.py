from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class FakeProfileBuilder:
    async def get_onboarding(self, *, user_id: int):
        assert user_id == 7
        return {
            "school": "清华大学",
            "school_level": "双一流",
            "major": "软件工程",
            "grade": "大二",
            "daily_study_time": "1-2h",
            "global_learning_goal": "期末复习",
            "programming_languages": ["Python"],
            "courses": ["数据结构"],
        }

    async def save_onboarding_info(self, *, user_id: int, payload: dict):
        assert user_id == 7
        self.onboarding_payload = payload
        return {
            "user_id": user_id,
            "module": "mentor",
            "profile_json": {"base_info": payload},
            "updated_at": None,
        }

    async def infer_profile_from_onboarding(self, *, user_id: int, payload: dict):
        self.inference_payload = payload


def test_profile_onboarding_get_returns_expected_structure(monkeypatch):
    import app.profile.service as profile_service_module

    fake_builder = FakeProfileBuilder()
    monkeypatch.setattr(profile_service_module, "get_profile_service", lambda *_, **__: fake_builder)

    onboarding = asyncio.run(fake_builder.get_onboarding(user_id=7))
    assert onboarding["school"] == "清华大学"
    assert onboarding["major"] == "软件工程"
    assert onboarding["school_level"] == "双一流"
    assert onboarding["courses"] == ["数据结构"]


def test_profile_onboarding_update_calls_process_onboarding(monkeypatch):
    import app.profile.service as profile_service_module

    builder = FakeProfileBuilder()
    monkeypatch.setattr(profile_service_module, "get_profile_service", lambda *_, **__: builder)

    payload = {
        "school": "清华大学",
        "major": "软件工程",
        "grade": "大二",
        "daily_study_time": "1-2h",
        "global_learning_goal": "期末复习",
        "courses": ["数据结构"],
        "programming_languages": ["Python"],
    }

    result = asyncio.run(builder.save_onboarding_info(user_id=7, payload=payload))
    assert builder.onboarding_payload["school"] == "清华大学"
    assert builder.onboarding_payload["courses"] == ["数据结构"]
    assert result["user_id"] == 7


def test_onboarding_routes_registered_under_profile_api():
    from app.profile import api as profile_api

    profile_routes = [
        route for route in profile_api.router.routes
        if getattr(route, "path", "").startswith("/profile")
    ]
    assert len(profile_routes) > 0
