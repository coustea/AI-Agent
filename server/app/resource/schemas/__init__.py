"""资源域公共 Schema 导出。"""

# ── Meta ──────────────────────────────────────────────────────────────────
from app.resource.schemas.meta import (
    AGENT_DEFAULT_ORDER,
    AGENT_META,
)

# ── Request ───────────────────────────────────────────────────────────────
from app.resource.schemas.request import (
    AgentConfigs,
    AgentSelection,
    ResourceGenerationRequest,
)

# ── Plan ──────────────────────────────────────────────────────────────────
from app.resource.schemas.plan import (
    DownstreamContext,
    PlanValidationError,
    ResourcePlan,
    validate_resource_plan,
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
)

__all__ = [
    # Constants
    "AGENT_META",
    "AGENT_DEFAULT_ORDER",
    # Request models
    "ResourceGenerationRequest",
    "AgentConfigs",
    "AgentSelection",
    # Planning
    "ResourcePlan",
    "PlanValidationError",
    "validate_resource_plan",
    "DownstreamContext",
    # Runtime input/output
    "AgentResult",
    "ResourceInput",
    "NodeInput",
    "GeneratedResourceItem",
    "ResourceBundle",
    "ResourceStatusSnapshot",
]
