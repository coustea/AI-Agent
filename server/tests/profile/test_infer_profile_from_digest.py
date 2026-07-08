"""infer_profile_from_digest 单元测试。

验证：
- should_update=True 时调用 save_dimensions + score_profile
- should_update=False 时不调 score_profile，仅 bump updated_at
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.profile.service import ProfileService
from app.profile.types import DimensionValue, GlobalTutoringInferenceOutput


@pytest.mark.asyncio
async def test_infer_profile_from_digest_updates_when_should_update():
    """should_update=True 时调用 save_dimensions + score_profile。"""
    svc = ProfileService()
    svc.llm = MagicMock()
    svc.llm.ainvoke_json = AsyncMock(return_value=GlobalTutoringInferenceOutput(
        should_update=True,
        dimensions_patch={
            "knowledge_level": DimensionValue(
                value="更新后描述", evidence=["周概要：推进数据结构"]
            )
        },
    ))

    fake_db = MagicMock()
    fake_digest = MagicMock(digest_markdown="本周周概要内容")

    with patch.object(svc, "get_or_create_weekly_digest", new=AsyncMock(return_value=fake_digest)), \
         patch.object(svc, "get_dimensions", new=AsyncMock(return_value={})), \
         patch.object(svc, "save_dimensions", new=AsyncMock()) as mock_save, \
         patch.object(svc, "score_profile", new=AsyncMock(return_value={"overall_score": 72})) as mock_score, \
         patch("app.profile.service.session_scope") as mock_ss:
        mock_ss.return_value.__aenter__ = AsyncMock(return_value=fake_db)
        mock_ss.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await svc.infer_profile_from_digest(user_id=1)

    assert result["profile_updated"] is True
    mock_save.assert_called_once()
    mock_score.assert_called_once_with(user_id=1)


@pytest.mark.asyncio
async def test_infer_profile_from_digest_no_update_bumps_updated_at():
    """should_update=False 时不调 score_profile，仅 bump updated_at。"""
    svc = ProfileService()
    svc.llm = MagicMock()
    svc.llm.ainvoke_json = AsyncMock(return_value=GlobalTutoringInferenceOutput(
        should_update=False,
        dimensions_patch={},
    ))

    fake_profile = MagicMock(updated_at=None)
    fake_db = MagicMock()

    with patch.object(svc, "get_or_create_weekly_digest", new=AsyncMock(return_value=MagicMock(digest_markdown="md"))), \
         patch.object(svc, "get_dimensions", new=AsyncMock(return_value={})), \
         patch.object(svc, "save_dimensions", new=AsyncMock()) as mock_save, \
         patch.object(svc, "score_profile", new=AsyncMock()) as mock_score, \
         patch.object(svc, "get_profile", new=AsyncMock(return_value=fake_profile)):
        with patch("app.profile.service.session_scope") as mock_ss:
            mock_ss.return_value.__aenter__ = AsyncMock(return_value=fake_db)
            mock_ss.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.infer_profile_from_digest(user_id=1)

    assert result["profile_updated"] is False
    mock_save.assert_not_called()
    mock_score.assert_not_called()
    assert fake_profile.updated_at is not None  # 被 bump
    fake_db.add.assert_called_with(fake_profile)
