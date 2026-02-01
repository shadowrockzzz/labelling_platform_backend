from typing import Optional, Union
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

def create_user(db: Session, user_in: Union[UserCreate, dict]):
    """Create a new user (admin only)."""
    # Convert Pydantic model to dictionary if it's not already a dict
    if isinstance(user_in, dict):
        user_data = user_in
    else:
        user_data = user_in.model_dump()
    
    hashed_password = get_password_hash(user_data['password'])
    
    # Map 'name' to 'full_name' for frontend compatibility
    full_name = user_data.get('full_name') or user_data.get('name', '')
    
    user = User(
        email=user_data['email'],
        full_name=full_name,
        hashed_password=hashed_password,
        role=user_data.get('role', 'annotator')
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
    """Delete a user from database (hard delete)."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        return False
    
    db.delete(user)
    db.commit()
    return True
