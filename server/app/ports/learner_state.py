"""Learner-state ports."""

from __future__ import annotations

from typing import Protocol


class LearnerStateStore(Protocol):
    async def get_profile(self, user_id: int): ...

    async def get_profile_history(self, user_id: int, limit: int = 20): ...
