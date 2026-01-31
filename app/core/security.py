from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from app.core.config import settings

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt with rounds=12 for longer password support."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt with rounds=12."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def decode_access_token(token: str) -> Optional[str]:
    """Decode an access token and return the email/subject."""
    payload = verify_token(token)
    if payload is None:
        return None
    if payload.get("type") != "access":
        return None
    email: str = payload.get("sub")
    return email

def decode_refresh_token(token: str) -> Optional[str]:
    """Decode a refresh token and return the email/subject."""
    payload = verify_token(token)
    if payload is None:
        return None
    if payload.get("type") != "refresh":
        return None
    email: str = payload.get("sub")
    return email

class TokenProvider:
    """Token provider for backward compatibility."""
    def create_token(self, email: str) -> str:
        return create_access_token({"sub": email})
    
    def decode_token(self, token: str) -> Optional[str]:
        return decode_access_token(token)

token_provider = TokenProvider()

