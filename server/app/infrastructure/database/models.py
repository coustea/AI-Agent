"""Explicit SQLModel registration for database initialization.

Importing these model modules is enough to register every table on
``SQLModel.metadata``. This replaces the old ``import app.modules`` side effect.
"""

from app.models.auth import ActiveToken
from app.models.chat import ChatMessage, ChatSession
from app.models.memory import UserMemory
from app.models.profile import UserProfile, UserProfileHistory
from app.models.resource import GeneratedResource
from app.models.user import User

REGISTERED_MODELS = (
    ActiveToken,
    ChatSession,
    ChatMessage,
    UserMemory,
    UserProfile,
    UserProfileHistory,
    GeneratedResource,
    User,
)


def import_all_models() -> tuple[type, ...]:
    """Return the registered model classes and ensure imports stay explicit."""
    return REGISTERED_MODELS
