from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.user import UserResponse, UserListResponse, UserUpdate, RoleUpdateRequest
from app.services.user_service import (
    list_users,
    get_user,
    update_user_role,
    modify_user,
    delete_user_from_db,
    activate_user,
    update_self_profile
)
from app.utils.dependencies import (
    require_admin,
    require_project_manager,
    get_current_active_user
)

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def get_current_user_endpoint(
    current_user = Depends(get_current_active_user)
):
    """
    Get current user's profile.
    """
    return UserResponse(success=True, data=current_user)

@router.put("/me", response_model=UserResponse)
def update_current_user_endpoint(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Update current user's own profile (name and bio only).
    """
    user = update_self_profile(db, current_user.id, user_update)
    return UserResponse(success=True, data=user)

@router.get("", response_model=UserListResponse)
def get_users_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get list of all users (Admin only).
    Supports pagination with skip and limit parameters.
    """
    users = list_users(db, skip=skip, limit=limit)
    return UserListResponse(success=True, data=users)

@router.get("/{user_id}", response_model=UserResponse)
def get_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Get a specific user by ID (Admin/Manager only).
    """
    user = get_user(db, user_id)
    return UserResponse(success=True, data=user)

@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Update user information (Admin only).
    """
    user = modify_user(db, user_id, user_update)
    return UserResponse(success=True, data=user)

@router.delete("/{user_id}")
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Delete a user from database (Admin only).
    This is a hard delete - user is permanently removed from database.
    """
    result = delete_user_from_db(db, user_id)
    return result

@router.put("/{user_id}/role", response_model=UserResponse)
def update_user_role_endpoint(
    user_id: int,
    role_update: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Update a user's role (Admin only).
    Valid roles: admin, project_manager, reviewer, annotator
    """
    user = update_user_role(db, user_id, role_update.role)
    return UserResponse(success=True, data=user)

@router.put("/{user_id}/activate")
def activate_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Activate a deactivated user (Admin only).
    """
    result = activate_user(db, user_id)
    return result