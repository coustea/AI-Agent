"""版本化的资源协同计划与基础产物交接模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ResourcePlanTask(BaseModel):
    """一个 Agent 的可执行任务，不允许用 Markdown 标题隐式编码。"""
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    objective: str = Field(min_length=8, max_length=500)
    focus: list[str] = Field(min_length=1, max_length=8)
    required_elements: list[str] = Field(min_length=1, max_length=10)
    avoid: list[str] = Field(default_factory=list, max_length=8)
    configuration_notes: list[str] = Field(default_factory=list, max_length=8)


class ResourcePlan(BaseModel):
    """规划 Agent 唯一允许交付的结构化、版本化控制协议。"""
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=200)
    learner_goal: str = Field(min_length=8, max_length=600)
    scope: list[str] = Field(min_length=1, max_length=10)
    learning_thread: list[str] = Field(min_length=2, max_length=10)
    coordination_rules: list[str] = Field(min_length=1, max_length=12)
    consistency_rules: list[str] = Field(min_length=1, max_length=10)
    tasks: list[ResourcePlanTask] = Field(min_length=1, max_length=7)

    @field_validator("scope", "learning_thread", "coordination_rules", "consistency_rules")
    @classmethod
    def reject_empty_strings(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if len(cleaned) != len(values):
            raise ValueError("计划列表不能包含空项")
        return cleaned

    @model_validator(mode="after")
    def reject_duplicate_tasks(self) -> "ResourcePlan":
        agent_ids = [task.agent_id for task in self.tasks]
        if len(agent_ids) != len(set(agent_ids)):
            raise ValueError("计划中不能为同一 Agent 分配重复任务")
        return self

    @property
    def agent_ids(self) -> list[str]:
        return [task.agent_id for task in self.tasks]

    def task_for(self, agent_id: str) -> ResourcePlanTask:
        for task in self.tasks:
            if task.agent_id == agent_id:
                return task
        raise KeyError(f"计划未包含 Agent: {agent_id}")


class DownstreamContext(BaseModel):
    """基础 Agent 向聚合 Agent 提供的显式交接内容。"""
    model_config = ConfigDict(extra="forbid")

    source_agent: str
    title: str = ""
    one_sentence_summary: str = ""
    materials: list[str] = Field(default_factory=list, max_length=12)


class PlanValidationError(ValueError):
    pass


def validate_resource_plan(plan: ResourcePlan, expected_agent_ids: list[str]) -> ResourcePlan:
    expected = set(expected_agent_ids)
    actual = set(plan.agent_ids)
    if actual != expected:
        raise PlanValidationError(
            "计划任务分配与已选 Agent 不一致: "
            f"missing={sorted(expected - actual)} unexpected={sorted(actual - expected)}"
        )
    return plan
