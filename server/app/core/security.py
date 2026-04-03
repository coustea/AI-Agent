import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.core.dependencies import get_session
from app.models.token import TokenBlacklist
from app.models.user import User
from app.modules.user.repository import UserRepository

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
EXPIRE_HOURS = 24

bearer_scheme = HTTPBearer()


def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效 Token")


def is_token_blacklisted(token: str, session: Session) -> bool:
    statement = select(TokenBlacklist).where(TokenBlacklist.token == token)
    return session.exec(statement).first() is not None


def blacklist_token(token: str, session: Session) -> None:
    entry = TokenBlacklist(token=token)
    session.add(entry)
    session.commit()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    token = credentials.credentials
    if is_token_blacklisted(token, session):
        raise HTTPException(status_code=401, detail="Token 已失效")
    user_id = decode_token(token)
    repo = UserRepository(session)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user
