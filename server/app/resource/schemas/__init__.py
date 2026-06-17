"""Resource domain schemas — re-exported from submodules for backward compatibility.

All external imports via ``from app.resource.schemas import X`` continue to work.
"""

# ── Meta ──────────────────────────────────────────────────────────────────
from app.resource.schemas.meta import (
    AGENT_DEFAULT_ENABLED,
    AGENT_DEFAULT_ORDER,
    AGENT_META,
)

# ── Request ───────────────────────────────────────────────────────────────
from app.resource.schemas.request import (
    AgentConfigs,
    AgentSelection,
    CodeConfig,
    ContentConfig,
    DEFAULT_SELECTED_AGENT_IDS,
    LearningScenario,
    MindmapConfig,
    PptConfig,
    QuizConfig,
    ReadingConfig,
    ResourceAgentId,
    ResourceGenerationRequest,
    VideoConfig,
)

# ── Plan ──────────────────────────────────────────────────────────────────
from app.resource.schemas.plan import (
    AgentAssignment,
    DownstreamContext,
    ReusableAssets,
    TeachingOutlineItem,
    TeachingPlan,
)

# ── Result ────────────────────────────────────────────────────────────────
from app.resource.schemas.result import (
    AgentResult,
    NodeInput,
    ResourceInput,
)

# ── Response ──────────────────────────────────────────────────────────────
from app.resource.schemas.response import (
    GeneratedResourceItem,
    ResourceBundle,
    SingleResourceRequest,
)

__all__ = [
    # Constants
    "AGENT_META",
    "AGENT_DEFAULT_ORDER",
    "AGENT_DEFAULT_ENABLED",
    # Request models
    "ResourceGenerationRequest",
    "SingleResourceRequest",
    # Learning blueprint & planning
    "AgentAssignment",
    "TeachingOutlineItem",
    "TeachingPlan",
    "ReusableAssets",
    "DownstreamContext",
    # Runtime input/output
    "AgentResult",
    "ResourceInput",
    "NodeInput",
    "GeneratedResourceItem",
    "ResourceBundle",
    # Response models
]
