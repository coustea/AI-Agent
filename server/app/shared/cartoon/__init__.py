"""基于通用工具与 HyperFrames CLI 的视频 agent。"""
from app.shared.cartoon.agent import generate
from app.shared.cartoon.schemas import (
    CartoonArtifact, CartoonBrief, CartoonGenerationConfig,
    CartoonGenerationError, CartoonInput, CartoonResourceMetadata, LessonDepth,
)
from app.shared.cartoon.tool import GenerateVideoToolArgs, build_cartoon_subagent_tool
