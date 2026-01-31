from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.users import router as users_router
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, MeResponse, SuccessResponse
from app.services.auth_service import login, refresh_token, get_current_user_info, logout
from app.utils.dependencies import get_current_active_user, require_admin
from app.schemas.user import UserRegister

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login_endpoint(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint.
    Returns access token, refresh token, and user information.
    """
    return login(db, login_data)

@router.post("/refresh", response_model=TokenResponse)
def refresh_endpoint(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    return refresh_token(db, refresh_data.refresh_token)

@router.post("/logout", response_model=SuccessResponse)
def logout_endpoint():
    """
    Logout endpoint.
    Client should discard tokens after calling this endpoint.
    """
    return logout()

@router.get("/me", response_model=MeResponse)
def get_me(
    current_user = Depends(get_current_active_user)
):
    """
    Get current user information.
    """
    return MeResponse(
        success=True,
        data=current_user
    )

@router.post("/register")
def register_user_endpoint(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Register a new user (Admin only).
    Password must meet strength requirements.
    """
    from app.services.auth_service import register_user
    
    new_user = register_user(db, user_data.model_dump())
    
    return {
        "success": True,
        "message": "User created successfully",
        "data": new_user
    }