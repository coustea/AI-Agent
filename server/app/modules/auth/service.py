from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.modules.auth.schemas import UserRead, UserRegister, UserUpdate

logger = get_logger(__name__)


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, data: UserRegister) -> dict | None:
        existing = (await self.session.exec(
            select(User).where(User.username == data.username)
        )).first()
        if existing:
            logger.warning("Registration failed: username '%s' already exists", data.username)
            return None
        user = User(
            username=data.username,
            password=hash_password(data.password),
            email=data.email,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        logger.info("User registered: id=%s, username='%s'", user.id, user.username)
        return {"user": UserRead.model_validate({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "major": user.major,
            "grade": user.grade,
            "school": user.school,
            "created_at": user.created_at,
        })}

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def update(self, user_id: int, data: UserUpdate) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        await self.session.refresh(user)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return user
        user.sqlmodel_update(update_data)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(self, username: str, password: str) -> dict | None:
        user = (await self.session.exec(
            select(User).where(User.username == username)
        )).first()
        if not user:
            logger.warning("Login failed for username: '%s'", username)
            return None
        await self.session.refresh(user)
        if not verify_password(password, user.password):
            logger.warning("Login failed for username: '%s'", username)
            return None
        logger.info("User logged in: id=%s, username='%s'", user.id, user.username)
        user_id = user.id
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "major": user.major,
            "grade": user.grade,
            "school": user.school,
            "created_at": user.created_at,
        }
        token = await create_token(user_id, self.session)
        return {"token": token, "user": UserRead.model_validate(user_data)}
