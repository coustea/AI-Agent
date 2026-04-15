"""Learner-state repository adapter."""

from __future__ import annotations

from app.domain.profile.profile_service import profile_service
from app.ports.learner_state import LearnerStateStore


class SqlLearnerStateStore(LearnerStateStore):
    async def get_profile(self, user_id: int):
        return await profile_service.get_user_profile(user_id)

    async def get_profile_history(self, user_id: int, limit: int = 20):
        return await profile_service.get_profile_history(user_id, limit)
