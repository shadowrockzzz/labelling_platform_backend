from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.crud.user import get_user_by_email, create_user
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token
)
from app.schemas.auth import TokenResponse, UserRead, LoginRequest
from app.utils.validators import validate_password_strength

def authenticate_user(db: Session, email: str, password: str) -> Optional[object]:
    """Authenticate a user by email and password."""
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def login(db: Session, login_data: LoginRequest) -> TokenResponse:
    """Login a user and return JWT tokens."""
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserRead.model_validate(user)
    )

def refresh_token(db: Session, refresh_token: str) -> TokenResponse:
    """Refresh an access token using a refresh token."""
    email = decode_refresh_token(refresh_token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = get_user_by_email(db, email=email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Create new access token
    access_token = create_access_token(data={"sub": user.email})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserRead.model_validate(user)
    )

def register_user(db: Session, user_data: dict) -> UserRead:
    """Register a new user (admin only)."""
    email = user_data.get("email")
    password = user_data.get("password")
    
    # Check if user already exists
    existing_user = get_user_by_email(db, email=email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Create user
    user = create_user(db, user_data)
    return UserRead.model_validate(user)

def get_current_user_info(db: Session, email: str) -> UserRead:
    """Get current user information."""
    user = get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserRead.model_validate(user)

def logout() -> dict:
    """Logout a user (invalidate tokens)."""
    # In a real implementation, you would add the refresh token to a blacklist
    # For now, we just return success
    # The client should discard the tokens
    return {"success": True, "message": "Successfully logged out"}