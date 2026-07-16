import pytest
from app.infra.models import UserProfile
try:
    from app.infra.models import LearningAssessmentReport
except ImportError:
    LearningAssessmentReport = None

def test_assessment_report_has_markdown_not_json_report_content():
    assert LearningAssessmentReport is not None, "LearningAssessmentReport model should be defined"
    fields = LearningAssessmentReport.model_fields
    assert "facts_snapshot" in fields
    assert "report_markdown" in fields
    assert "report_content" not in fields

def test_user_profile_strategy_fields_do_not_replace_score_fields():
    fields = UserProfile.model_fields
    assert {"guidance_strategy", "guidance_updated_at", "last_assessment_report_id"} <= set(fields)
    assert {"overall_score", "scored_at"} <= set(fields)
