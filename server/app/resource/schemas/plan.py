"""多智能体资源规划契约。

PlanningAgent 输出两层信息：
- global_plan：所有 Worker 共享的学习目标、教学策略和大纲
- worker_tasks：按 Agent ID 索引、可直接派发的任务合约

本模块不包含 path 域模型；学习路径规划仍使用自己的持久化与工作流。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


BASE_WORKER_IDS = frozenset({"content", "mindmap", "quiz", "code", "reading"})
WORKER_OUTPUT_FORMATS = {
    "content": "markdown",
    "mindmap": "markdown",
    "quiz": "json",
    "code": "markdown",
    "reading": "json",
}


class TeachingOutlineItem(BaseModel):
    """所有 Worker 共享的单个教学大纲项。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^o[1-9][0-9]*$", description="稳定且唯一的大纲 ID，如 o1、o2")
    title: str = Field(min_length=1, max_length=80)
    learning_objective: str = Field(min_length=1, max_length=300)
    key_points: list[str] = Field(min_length=1, max_length=5)
    must_not_miss: bool

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)


class GlobalTeachingPlan(BaseModel):
    """由全部 Worker 共享、与具体资源形态无关的教学规划。"""

    model_config = ConfigDict(extra="forbid")

    learning_goal: str = Field(min_length=1, max_length=500)
    teaching_strategy: str = Field(min_length=1, max_length=800)
    difficulty: Literal["beginner", "intermediate", "advanced"]
    outline: list[TeachingOutlineItem] = Field(min_length=3, max_length=8)


class AssignedSection(BaseModel):
    """分配给 Worker 的单个大纲任务。"""

    model_config = ConfigDict(extra="forbid")

    outline_id: str = Field(pattern=r"^o[1-9][0-9]*$")
    responsibility: Literal[
        "primary",
        "supporting",
        "assessment",
        "practice",
        "structure",
        "extension",
    ]
    instruction: str = Field(min_length=1, max_length=500)


class WorkerDeliverable(BaseModel):
    """Worker 必须交付的内容形态及要求。"""

    model_config = ConfigDict(extra="forbid")

    format: Literal["markdown", "json"]
    requirements: list[str] = Field(min_length=1, max_length=8)


class WorkerTask(BaseModel):
    """PlanningAgent 生成的、可直接派发给一个 Worker 的任务合约。"""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, max_length=500)
    assigned_sections: list[AssignedSection] = Field(min_length=1, max_length=8)
    deliverable: WorkerDeliverable
    acceptance_criteria: list[str] = Field(min_length=1, max_length=8)
    exclusions: list[str] = Field(min_length=1, max_length=8)
    avoid_overlap_with: list[str] = Field(max_length=4)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)


class TeachingPlan(BaseModel):
    """持久化后的严格教学计划。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["3.0"]
    global_plan: GlobalTeachingPlan
    worker_tasks: dict[str, WorkerTask] = Field(min_length=1)

    @property
    def outline(self) -> list[TeachingOutlineItem]:
        """为覆盖统计提供统一的大纲访问入口。"""
        return self.global_plan.outline

    @property
    def teaching_strategy(self) -> str:
        """为 Worker 运行时配置提供统一的教学策略访问入口。"""
        return self.global_plan.teaching_strategy

    def task_for(self, agent_id: str) -> WorkerTask:
        try:
            return self.worker_tasks[agent_id]
        except KeyError as exc:
            raise ValueError(f"TeachingPlan has no worker task for {agent_id!r}") from exc

    @model_validator(mode="after")
    def validate_plan_contract(self) -> "TeachingPlan":
        worker_ids = set(self.worker_tasks)
        unknown_worker_ids = worker_ids - BASE_WORKER_IDS
        if unknown_worker_ids:
            raise ValueError(f"TeachingPlan contains unsupported workers: {sorted(unknown_worker_ids)}")

        outline_ids = [item.id for item in self.outline]
        if len(outline_ids) != len(set(outline_ids)):
            raise ValueError("TeachingPlan outline IDs must be unique")

        allowed_outline_ids = set(outline_ids)
        assigned_outline_ids: set[str] = set()
        for agent_id, task in self.worker_tasks.items():
            section_ids = [entry.outline_id for entry in task.assigned_sections]
            if len(section_ids) != len(set(section_ids)):
                raise ValueError(f"TeachingPlan worker task contains duplicate outline IDs: {agent_id}")

            unknown_outline_ids = set(section_ids) - allowed_outline_ids
            if unknown_outline_ids:
                raise ValueError(
                    "TeachingPlan worker task references unknown outline IDs: "
                    f"agent={agent_id!r} ids={sorted(unknown_outline_ids)}"
                )
            assigned_outline_ids.update(section_ids)

            expected_format = WORKER_OUTPUT_FORMATS[agent_id]
            if task.deliverable.format != expected_format:
                raise ValueError(
                    f"TeachingPlan worker {agent_id!r} must deliver {expected_format}, "
                    f"got {task.deliverable.format}"
                )

            invalid_overlap_ids = set(task.avoid_overlap_with) - (worker_ids - {agent_id})
            if invalid_overlap_ids:
                raise ValueError(
                    f"TeachingPlan worker {agent_id!r} has invalid avoid_overlap_with: "
                    f"{sorted(invalid_overlap_ids)}"
                )

        required_outline_ids = {item.id for item in self.outline if item.must_not_miss}
        missing_required_ids = required_outline_ids - assigned_outline_ids
        if missing_required_ids:
            raise ValueError(
                f"TeachingPlan leaves required outline IDs unassigned: {sorted(missing_required_ids)}"
            )
        return self



class ReusableAssets(BaseModel):
    examples: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    visual_ideas: list[str] = Field(default_factory=list)
    practice_refs: list[str] = Field(default_factory=list)
    code_refs: list[str] = Field(default_factory=list)


class DownstreamContext(BaseModel):
    """基础 Agent 给聚合 Agent 的结构化交接内容。"""

    model_config = ConfigDict(extra="forbid")

    source_agent: str
    title: str = ""
    one_sentence_summary: str = ""
    materials: list[str] = Field(default_factory=list, max_length=12)
    reusable_assets: ReusableAssets = Field(default_factory=ReusableAssets)
