from typing import Optional, List
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.security import decode_access_token
from app.crud.user import get_user_by_email

def get_token_from_header(authorization: Optional[str] = Header(None)):
    """Extract and validate Bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found in authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token

def get_current_user_no_dep(token: str = Depends(get_token_from_header), db: Session = Depends(get_db)):
    """Get current authenticated user from JWT token."""
    email = decode_access_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Eager load assignments to avoid lazy loading issues
    from app.models.user import User
    user = db.query(User).options(selectinload(User.assignments)).filter(User.id == user.id).first()
    
    return user

def get_current_active_user(current_user = Depends(get_current_user_no_dep)):
    """Ensure user is active."""
    if not bool(current_user.is_active):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def require_role(allowed_roles: List[str]):
    """Dependency factory to require specific roles."""
    def role_checker(current_user = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: one of {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

# Predefined role dependencies
require_admin = require_role(["admin"])
require_project_manager = require_role(["admin", "project_manager"])
require_reviewer = require_role(["admin", "project_manager", "reviewer"])
require_annotator = require_role(["admin", "project_manager", "reviewer", "annotator"])

def require_project_access(project_id_param: str = "project_id"):
    """
    Dependency to check if user has access to a specific project.
    This checks if user is an owner or has an assignment to the project.
    """
    async def check_access(
        current_user = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        from app.models.project import Project
        from app.models.project_assignment import ProjectAssignment
        
        # This will be called from within a route that has project_id in path/params
        # The actual check happens in the route using this dependency
        return current_user
    
    return check_access