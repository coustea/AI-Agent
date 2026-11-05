"""共享 Cartoon 视频生成模块（无状态流 + HyperFrames + TTS + ffprobe 校验）。

模块职责结构：
- ``schemas.py``: 数据契约与 DTO 模型
- ``workspace.py``: 物理技能模板复制与工作区初始化
- ``validator.py``: HyperFrames 子组合 HTML/GSAP 契约校验器
- ``renderer.py``: HyperFrames CLI 渲染器与 ffprobe 校验器
- ``tts.py``: 旁白语音合成与 WebVTT 字幕对齐器
- ``agent.py``: ``CartoonAgent`` 主编排智能体
- ``tool.py``: ``build_cartoon_planner_tools`` 与 ``build_cartoon_subagent_tool``
"""

from app.shared.cartoon.agent import CartoonAgent
from app.shared.cartoon.renderer import (
    CartoonMedia,
    HyperFramesReport,
    MediaProbe,
    QualityFinding,
    QualityGateError,
    RenderProfile,
)
from app.shared.cartoon.schemas import (
    CaptionCue,
    CartoonArtifact,
    CartoonBrief,
    CartoonGenerationConfig,
    CartoonGenerationError,
    CartoonResourceMetadata,
    LessonDepth,
    SceneStoryboardSpec,
    SceneVisualStyle,
    SpeechClip,
    VideoDesignPlan,
)
from app.shared.cartoon.tool import (
    GenerateVideoToolArgs,
    build_cartoon_planner_tools,
    build_cartoon_subagent_tool,
    build_verify_scene_tool,
)
from app.shared.cartoon.tts import (
    synthesize_plan_narration,
    synthesize_scene_clip,
    write_webvtt,
)
from app.shared.cartoon.validator import validate_scene_composition_html
from app.shared.cartoon.workspace import (
    copy_scene_skeleton,
    render_root_index_html,
    render_scene_subcomposition_html,
)

__all__ = [
    "CaptionCue",
    "CartoonAgent",
    "CartoonArtifact",
    "CartoonBrief",
    "CartoonGenerationConfig",
    "CartoonGenerationError",
    "CartoonMedia",
    "CartoonResourceMetadata",
    "GenerateVideoToolArgs",
    "HyperFramesReport",
    "LessonDepth",
    "MediaProbe",
    "QualityFinding",
    "QualityGateError",
    "RenderProfile",
    "SceneStoryboardSpec",
    "SceneVisualStyle",
    "SpeechClip",
    "VideoDesignPlan",
    "build_cartoon_planner_tools",
    "build_cartoon_subagent_tool",
    "build_verify_scene_tool",
    "copy_scene_skeleton",
    "render_root_index_html",
    "render_scene_subcomposition_html",
    "synthesize_plan_narration",
    "synthesize_scene_clip",
    "validate_scene_composition_html",
    "write_webvtt",
]
