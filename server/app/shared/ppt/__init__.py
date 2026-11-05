"""共享 PPT 生成模块（无状态流 + python-pptx + OOXML 校验 + 缩略图网格审查）。

模块职责结构：
- ``schemas.py``: 数据契约与 DTO 模型
- ``workspace.py``: 物理技能模板复制与工作区初始化
- ``validator.py``: OOXML 几何与排版确定性校验器
- ``renderer.py``: PNG 缩略图、网格联系表与 HTML 播放器渲染器
- ``agent.py``: ``PPTAgent`` 主编排与 ``PPTService``
- ``tool.py``: ``build_ppt_planner_tools`` 与 ``build_ppt_subagent_tool``
"""

from app.shared.ppt.agent import (
    PPTAgent,
    PPTService,
    ProgressCallback,
    ppt_pipeline_metadata,
)
from app.shared.ppt.renderer import (
    build_thumbnail_grid,
    publish_viewer_html,
    render_pptx_thumbnails,
)
from app.shared.ppt.schemas import (
    DeckDesignPlan,
    PRESET_PALETTES,
    PPTArtifact,
    PPTGenerationError,
    PPTModel,
    PPTPreferences,
    PPTSource,
    PathPPT,
    ResourcePPT,
    SlideLayoutType,
    SlideSpec,
    ThemeTokens,
)
from app.shared.ppt.tool import (
    GeneratePPTToolArgs,
    _compile_and_audit_workspace,
    _test_single_slide_script,
    build_ppt_planner_tools,
    build_ppt_subagent_tool,
    build_test_slide_tool,
)
from app.shared.ppt.validator import audit_pptx, audit_single_slide
from app.shared.ppt.workspace import (
    copy_slide_skeleton,
    generate_slide_python_code,
    write_workspace_scaffold,
)

__all__ = [
    "DeckDesignPlan",
    "GeneratePPTToolArgs",
    "PPTAgent",
    "PPTArtifact",
    "PPTGenerationError",
    "PPTModel",
    "PPTPreferences",
    "PPTService",
    "PPTSource",
    "PRESET_PALETTES",
    "PathPPT",
    "ProgressCallback",
    "ResourcePPT",
    "SlideLayoutType",
    "SlideSpec",
    "ThemeTokens",
    "_compile_and_audit_workspace",
    "_test_single_slide_script",
    "audit_pptx",
    "audit_single_slide",
    "build_ppt_planner_tools",
    "build_ppt_subagent_tool",
    "build_test_slide_tool",
    "build_thumbnail_grid",
    "copy_slide_skeleton",
    "generate_slide_python_code",
    "ppt_pipeline_metadata",
    "publish_viewer_html",
    "render_pptx_thumbnails",
    "write_workspace_scaffold",
]
