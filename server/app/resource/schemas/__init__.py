"""资源域公共 Schema 导出。"""

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
    ResourceInput,
)

# ── Response ──────────────────────────────────────────────────────────────
from app.resource.schemas.response import (
    GeneratedResourceItem,
    ResourceAgentSnapshot,
    ResourceBundle,
    ResourceBundleMetadata,
    ResourceStatusSnapshot,
)

__all__ = [
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
    "GeneratedResourceItem",
    "ResourceAgentSnapshot",
    "ResourceBundle",
    "ResourceBundleMetadata",
    "ResourceStatusSnapshot",
]
