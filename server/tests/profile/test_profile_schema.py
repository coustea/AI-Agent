from __future__ import annotations

from app.infra.models import CourseProfile, GlobalProfile


def test_course_profile_schema_v2() -> None:
    # Verify CourseProfile has the correct columns
    assert "global_profile_id" in CourseProfile.model_fields
    assert "course_key" in CourseProfile.model_fields
    assert "course_name" in CourseProfile.model_fields
    assert "aliases" in CourseProfile.model_fields
    assert "profile_markdown" in CourseProfile.model_fields

    # Verify CourseProfile does not have old JSON/Score fields
    assert "profile_json" not in CourseProfile.model_fields
    assert "profile_score_json" not in CourseProfile.model_fields


def test_global_profile_schema_v2() -> None:
    # Verify GlobalProfile still exposes JSON and Score fields
    assert "profile_json" in GlobalProfile.model_fields
    assert "profile_score_json" in GlobalProfile.model_fields
