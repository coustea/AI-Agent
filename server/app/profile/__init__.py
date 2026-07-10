"""共享学习者画像模块。"""

# 汇总导出画像相关的请求、响应、服务与类型定义
from app.profile.request import OnboardingUpdate, GlobalTutoringProfileUpdate
from app.profile.response import (
    BaseInfoData,
    OnboardingResponse,
    StudentProfileData,
    GlobalProfileResponse,
)
from app.profile.service import ProfileService, get_profile_service, _user_base_info_dict
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
    "_user_base_info_dict",
]
