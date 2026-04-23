"""Profile module — 画像构建与事实提取服务。"""

from __future__ import annotations

from app.profile.service import profile_service, ProfileService
from app.profile.fact_extraction import FactExtractionService
from app.profile.profile_building import ProfileBuildingService


def build_fact_extraction_service(module_name: str = "mentor") -> FactExtractionService:
    """构建长期记忆提取服务。"""
    return FactExtractionService(module_name=module_name)


def build_profile_building_service(module_name: str = "mentor") -> ProfileBuildingService:
    """构建画像合并服务。"""
    return ProfileBuildingService(module_name=module_name)


__all__ = [
    # 服务类
    "profile_service",
    "ProfileService",
    "FactExtractionService",
    "ProfileBuildingService",
    "build_fact_extraction_service",
    "build_profile_building_service",
]
