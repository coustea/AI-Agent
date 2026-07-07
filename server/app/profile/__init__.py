"""共享学习者画像模块。"""

from app.profile.request import OnboardingUpdate, GlobalTutoringProfileUpdate
from app.profile.response import (
    BaseInfoData,
    OnboardingResponse,
    StudentProfileData,
    GlobalProfileResponse,
)
from app.profile.service import ProfileService, get_profile_service
from app.profile.types import ALL_DIMENSIONS, DIMENSION_NAMES

__all__ = [
    "ALL_DIMENSIONS",
    "BaseInfoData",
    "DIMENSION_NAMES",
    "OnboardingResponse",
    "OnboardingUpdate",
    "GlobalTutoringProfileUpdate",
    "GlobalProfileResponse",
    "ProfileService",
    "StudentProfileData",
    "get_profile_service",
]
