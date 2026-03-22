"""JWT token utilities."""

import os
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import jwt, JWTError

SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRE_DAYS: int = 7


def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())

    to_encode = {
        "sub": username,
        "exp": expire,
        "jti": jti,
        "iat": now,
    }

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise e


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return decode_token(token)
    except JWTError:
        return None


def get_token_username(token: str) -> Optional[str]:
    payload = verify_token(token)
    return payload.get("sub") if payload else None
