from __future__ import annotations

from pathlib import Path

import pytest

from app.profile.service import ProfileService
from app.profile.types import default_profile_json, default_score_json


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_global_profile_json_has_no_legacy_fields() -> None:
    data = default_profile_json
    assert set(data.keys()) == {"base_info", "dimensions"}
    forbidden = {
        "learning_profile",
        "global_profile",
        "course_profiles",
        "knowledge_mastery",
        "initial_strategy",
        "profile_meta",
        "schema_version",
    }
    assert forbidden.isdisjoint(data.keys())


def test_score_json_has_strict_fields_only() -> None:
    data = default_score_json
    assert set(data.keys()) == {"overall_score", "dimension_scores", "dimension_evidence", "scored_at"}
    assert "confidence" not in data
    assert "section_coverage" not in data
    assert "evidence_quality" not in data


def test_profile_service_no_compatibility_aliases() -> None:
    assert not hasattr(ProfileService, "get_or_create_profile")
    assert not hasattr(ProfileService, "apply_tutoring_profile_update")
    assert not hasattr(ProfileService, "process_tutoring_update")
    assert not hasattr(ProfileService, "infer_tutoring_patch")


def test_legacy_prompt_file_removed() -> None:
    assert not (REPO_ROOT / "app" / "profile" / "prompts" / "profile.md").exists()


@pytest.mark.parametrize(
    "relative_path, forbidden",
    [
        ("app/auth/service.py", "apply_tutoring_profile_update"),
        ("app/evaluation/service.py", "apply_tutoring_profile_update"),
        ("app/dashboard/api.py", "knowledge_mastery"),
        ("app/dashboard/api.py", "initial_strategy"),
        ("app/dashboard/api.py", "section_coverage"),
        ("app/dashboard/api.py", "evidence_quality"),
    ],
)
def test_backend_source_has_no_legacy_profile_references(relative_path: str, forbidden: str) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert forbidden not in text
