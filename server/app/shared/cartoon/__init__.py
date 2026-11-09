"""基于通用工具与 HyperFrames CLI 的教学动画视频智能体。"""

from app.shared.cartoon.agent import CartoonAgent, ProgressCallback, generate
from app.shared.cartoon.schemas import (
    CartoonArtifact,
    CartoonBrief,
    CartoonGenerationConfig,
    CartoonGenerationError,
)
from app.shared.cartoon.tool import (
    GenerateVideoToolArgs,
    build_cartoon_tool,
)

__all__ = [
    "CartoonAgent",
    "CartoonArtifact",
    "CartoonBrief",
    "CartoonGenerationConfig",
    "CartoonGenerationError",
    "GenerateVideoToolArgs",
    "ProgressCallback",
    "build_cartoon_tool",
    "generate",
]
