from sqlmodel import Session

from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.modules.user.repository import UserRepository
from app.modules.user.schemas import UserRegister, UserUpdate


class UserService:
    def __init__(self, session: Session):
        self.repo = UserRepository(session)

    def register(self, data: UserRegister) -> User:
        user = User(
            username=data.username,
            password=hash_password(data.password),
        )
        return self.repo.create(user)

    def get_by_id(self, user_id: str) -> User | None:
        return self.repo.get_by_id(user_id)

    def update(self, user_id: str, data: UserUpdate) -> User | None:
        user = self.repo.get_by_id(user_id)
        if not user:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        return self.repo.update(user)

    def authenticate(self, username: str, password: str) -> dict | None:
        user = self.repo.get_by_username(username)
        if not user or not verify_password(password, user.password):
            return None
        return {"token": create_token(user.id), "user": user}
