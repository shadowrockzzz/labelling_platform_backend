from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.user import get_user_by_email, get_users, get_user_by_id, update_user, delete_user
from app.schemas.user import UserCreate, UserUpdate, UserRead
from app.core.security import get_password_hash
from app.utils.validators import validate_role

def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[UserRead]:
    """Get list of all users."""
    users = get_users(db, skip=skip, limit=limit)
    return [UserRead.model_validate(user) for user in users]

def get_user(db: Session, user_id: int) -> UserRead:
    """Get a specific user by ID."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserRead.model_validate(user)

def update_user_role(db: Session, user_id: int, new_role: str) -> UserRead:
    """Update a user's role."""
    # Validate role
    if not validate_role(new_role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: admin, project_manager, reviewer, annotator"
        )
    
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent users from changing their own role
    # This should be checked at the route level
    
    user.role = new_role
    db.commit()
    db.refresh(user)
    
    return UserRead.model_validate(user)

def modify_user(db: Session, user_id: int, user_update: UserUpdate) -> UserRead:
    """Update user information."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Map 'name' to 'full_name' for frontend compatibility
    if "name" in update_data and "full_name" not in update_data:
        update_data["full_name"] = update_data.pop("name")
    
    # Validate role if being updated
    if "role" in update_data:
        if not validate_role(update_data["role"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserRead.model_validate(user)

def deactivate_user(db: Session, user_id: int) -> dict:
    """Deactivate a user (soft delete)."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    db.commit()
    
    return {"success": True, "message": "User deactivated successfully"}

def activate_user(db: Session, user_id: int) -> dict:
    """Activate a user."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    return {"success": True, "message": "User activated successfully"}

def update_self_profile(db: Session, user_id: int, user_update: UserUpdate) -> UserRead:
    """Update current user's own profile (name and bio only)."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Map 'name' to 'full_name' for frontend compatibility
    if "name" in update_data and "full_name" not in update_data:
        update_data["full_name"] = update_data.pop("name")
    
    # Only allow updating name and bio for self-profile updates
    allowed_fields = {"full_name", "bio"}
    filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    for field, value in filtered_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserRead.model_validate(user)
