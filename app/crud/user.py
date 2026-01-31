from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get list of users with pagination."""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user_in: UserCreate):
    """Create a new user (admin only)."""
    hashed_password = get_password_hash(user_in['password'])
    user = User(
        email=user_in['email'],
        full_name=user_in['full_name'],
        hashed_password=hashed_password,
        role=user_in['role'] if 'role' in user_in else "annotator"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user_id: int, user_in: dict) -> Optional[User]:
    """Update user information."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        return None
    
    for field, value in user_in.items():
        if hasattr(user, field):
            setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user (soft delete)."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        return False
    
    user.is_active = False
    db.commit()
    return True
