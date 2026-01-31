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
    deactivate_user,
    activate_user
)
from app.utils.dependencies import require_admin, require_project_manager, get_current_active_user

router = APIRouter(prefix="/users", tags=["Users"])

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
def deactivate_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Deactivate a user (Admin only).
    This is a soft delete - the user is marked as inactive.
    """
    result = deactivate_user(db, user_id)
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
