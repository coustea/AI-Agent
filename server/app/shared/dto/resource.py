from typing import Optional

from pydantic import BaseModel, Field


class LearningTask(BaseModel):
    course: str = Field(..., description="课程/主题")
    gap: str = Field(..., description="知识瓶颈/核心痛点")
    need: str = Field(default="review", description="资源偏好: exam/review/deep")
    extra: str = Field(default="", description="额外需求")


class ResourceGenerateRequest(BaseModel):
    learning_task: LearningTask
    selected_resources: Optional[list[str]] = Field(
        default=None,
        description="可选：指定要生成的资源类型；未传或为空时默认全量生成",
    )
