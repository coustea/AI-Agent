from sqlmodel import Session, select

from app.core.logging import get_logger
from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.modules.user.schemas import UserRegister, UserUpdate

logger = get_logger(__name__)


class UserService:
    def __init__(self, session: Session):
        self.session = session

    def register(self, data: UserRegister) -> dict | None:
        existing = self.session.exec(
            select(User).where(User.username == data.username)
        ).first()
        if existing:
            logger.warning("Registration failed: username '%s' already exists", data.username)
            return None
        user = User(
            username=data.username,
            password=hash_password(data.password),
            email=data.email,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        logger.info("User registered: id=%s, username='%s'", user.id, user.username)
        return {"user": user}

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def update(self, user_id: int, data: UserUpdate) -> User | None:
        user = self.session.get(User, user_id)
        if not user:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return user
        user.sqlmodel_update(update_data)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def authenticate(self, username: str, password: str) -> dict | None:
        user = self.session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user or not verify_password(password, user.password):
            logger.warning("Login failed for username: '%s'", username)
            return None
        logger.info("User logged in: id=%s, username='%s'", user.id, user.username)
        return {"token": create_token(user.id), "user": user}
