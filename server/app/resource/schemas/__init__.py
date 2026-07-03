"""资源域公共 Schema 导出。"""

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
    CartoonConfig,
    CodeConfig,
    ContentConfig,
    DEFAULT_SELECTED_AGENT_IDS,
    LearningScenario,
    MindmapConfig,
    QuizConfig,
    ReadingConfig,
    ResourceAgentId,
    ResourceGenerationRequest,
    VideoConfig,
)

# ── Plan ──────────────────────────────────────────────────────────────────
from app.resource.schemas.plan import (
    DownstreamContext,
    GlobalTeachingPlan,
    ReusableAssets,
    TeachingOutlineItem,
    TeachingPlan,
    AssignedSection,
    WorkerDeliverable,
    WorkerTask,
    create_planning_output_model,
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
    ResourceStatusSnapshot,
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
    "TeachingPlan",
    "TeachingOutlineItem",
    "GlobalTeachingPlan",
    "AssignedSection",
    "WorkerDeliverable",
    "WorkerTask",
    "create_planning_output_model",
    "ReusableAssets",
    "DownstreamContext",
    # Runtime input/output
    "AgentResult",
    "ResourceInput",
    "NodeInput",
    "GeneratedResourceItem",
    "ResourceBundle",
    "ResourceStatusSnapshot",
    # Response models
]
