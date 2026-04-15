"""Application container."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.adapters.repositories.conversation_store import SqlConversationStore
from app.adapters.repositories.learner_state_store import SqlLearnerStateStore
from app.adapters.repositories.resource_bundle_store import SqlResourceBundleStore
from app.adapters.repositories.user_account_store import UserAccountStore
from app.adapters.storage.local_file_store import LocalFileStore
from app.runtime.chat.tutor_runtime import TutorChatRuntime
from app.runtime.profile.profile_runtime import LearnerProfileRuntime
from app.runtime.resource.resource_runtime import ResourceGenerationRuntime
from app.usecases.auth import AuthUseCases
from app.usecases.chat import ChatUseCases
from app.usecases.profile import ProfileUseCases
from app.usecases.resource import ResourceUseCases


@dataclass
class AppContainer:
    file_store: LocalFileStore
    auth_usecases: AuthUseCases
    chat_usecases: ChatUseCases
    profile_usecases: ProfileUseCases
    resource_usecases: ResourceUseCases
    chat_runtime: TutorChatRuntime
    profile_runtime: LearnerProfileRuntime
    resource_runtime: ResourceGenerationRuntime

    async def aclose(self) -> None:
        await self.chat_runtime.aclose()
        await self.resource_runtime.aclose()


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    file_store = LocalFileStore()
    account_store = UserAccountStore()
    conversation_store = SqlConversationStore()
    learner_state_store = SqlLearnerStateStore()
    bundle_store = SqlResourceBundleStore()

    chat_runtime = TutorChatRuntime()
    profile_runtime = LearnerProfileRuntime()
    resource_runtime = ResourceGenerationRuntime()

    return AppContainer(
        file_store=file_store,
        auth_usecases=AuthUseCases(account_store, profile_runtime),
        chat_usecases=ChatUseCases(conversation_store, file_store, chat_runtime),
        profile_usecases=ProfileUseCases(learner_state_store),
        resource_usecases=ResourceUseCases(bundle_store, resource_runtime),
        chat_runtime=chat_runtime,
        profile_runtime=profile_runtime,
        resource_runtime=resource_runtime,
    )
