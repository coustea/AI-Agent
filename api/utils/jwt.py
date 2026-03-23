"""JWT token utilities."""

import os
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import jwt, JWTError

from api.db.models import settings
from api.utils.security import get_password_hash, verify_password


# Use settings from models.py
SECRET_KEY: str = settings.secret_key or secrets.token_urlsafe(32)
ALGORITHM: str = settings.algorithm
ACCESS_TOKEN_EXPIRE_HOURS: int = settings.access_token_expire_hours

# Debug: print SECRET_KEY once
import os
if os.getenv('DEBUG_SECRET_KEY') == '1':
    print(f"[JWT DEBUG] SECRET_KEY loaded: {repr(SECRET_KEY)}")


def create_access_token(
    username: str, 
    expires_delta: Optional[timedelta] = None
) -> tuple[str, int]:
    """
    Create JWT access token.
    
    Args:
        username: Username to encode in token
        expires_delta: Custom expiration time (optional)
            
    Returns:
        tuple: (access_token, expires_in_seconds)
        
    Example:
        >>> token, expires_in = create_access_token("testuser")
        >>> print(f"Token: {token}, Expires in: {expires_in}s")
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    jti = str(uuid.uuid4())  # JWT ID for token blacklisting

    to_encode = {
        "sub": username,  # Subject (username)
        "exp": expire,   # Expiration time
        "iat": datetime.now(timezone.utc),  # Issued at
        "jti": jti,       # JWT ID
    }

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    expires_in = int((expire - datetime.now(timezone.utc)).total_seconds())

    return token, expires_in


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload, or None if invalid
    """
    try:
        return decode_token(token)
    except ValueError:
        return None


def get_token_username(token: str) -> Optional[str]:
    """
    Extract username from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        str: Username, or None if token is invalid
    """
    payload = verify_token(token)
    if not payload:
        return None
    return payload.get("sub")


def get_token_jti(token: str) -> Optional[str]:
    """
    Extract JWT ID from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        str: JWT ID, or None if token is invalid
    """
    payload = verify_token(token)
    if not payload:
        return None
    return payload.get("jti")
