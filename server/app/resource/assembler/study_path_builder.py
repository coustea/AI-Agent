# -*- coding: utf-8 -*-
"""学习路径构建器。

根据生成的资源构建推荐的学习路径。
"""

from __future__ import annotations

from typing import Any

from app.path import planner as path_planner
from app.resource.registry import ESTIMATED_MINUTES
from app.resource.schemas import GeneratedResourceItem, ResourceAgentId, ResourceGenerationRequest, StudyPathStep


class StudyPathBuilder:
    """学习路径构建器：根据资源类型构建推荐学习顺序。"""

    # 步骤标题映射
    STEP_TITLES = {
        "content": "先阅读课程讲解文档",
        "diagram": "查看知识图解",
        "mindmap": "浏览思维导图",
        "code": "学习代码实操案例",
        "quiz": "完成练习题",
        "reading": "阅读拓展材料",
    }

    # 步骤原因映射
    STEP_REASONS = {
        "content": "建立对主题的整体理解",
        "diagram": "通过可视化加深理解",
        "mindmap": "梳理知识结构",
        "code": "通过实践加深理解",
        "quiz": "检验学习效果",
        "reading": "扩展知识面",
    }

    def build(
        self,
        resources: list[GeneratedResourceItem],
        *,
        profile: dict[str, Any] | None = None,
        request: ResourceGenerationRequest | None = None,
    ) -> list[StudyPathStep]:
        """把资源项交给 path 模块规划，再转换为资源包内的学习步骤。"""
        resource_types = [res.type.value for res in resources]
        profile_json = self._profile_json(profile or {})
        plan = path_planner.build_resource_study_plan(
            resource_types,
            profile_json=profile_json,
            learning_scenario=request.learning_scenario.value if request else None,
            learning_need=request.learning_need if request else None,
        )

        path: list[StudyPathStep] = []
        order = 1
        for stage in plan.stages:
            for node in stage.nodes:
                if node.id not in resource_types:
                    continue
                path.append(StudyPathStep(
                    order=order,
                    resource_type=ResourceAgentId(node.id),
                    title=node.title or self.STEP_TITLES.get(node.id, f"学习 {node.id}"),
                    reason=node.recommendation_reason or node.desc or self.STEP_REASONS.get(node.id, "巩固学习"),
                    estimated_time=ESTIMATED_MINUTES.get(node.id),
                ))
                order += 1

        return path

    def _profile_json(self, profile: dict[str, Any]) -> dict[str, Any] | None:
        profile_json = profile.get("profile_json")
        if isinstance(profile_json, dict):
            return profile_json
        return profile if profile else None
