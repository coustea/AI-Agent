"""Password hashing and verification utilities."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password (bcrypt)
            
    Returns:
        bool: True if password matches, False otherwise
        
    Example:
        >>> verify_password("myPassword", hashed)
        True
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Args:
        password: Plain text password to hash
            
    Returns:
        str: Hashed password (bcrypt)
        
    Example:
        >>> hashed = get_password_hash("myPassword")
        >>> print(hashed)
        $2b$12$LQv3c1yqBWVHxkd0LHAkO3...
    """
    return pwd_context.hash(password)
