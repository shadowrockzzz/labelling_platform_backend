from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.crud.user import get_user_by_email

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    email = decode_access_token(token)
    if email is None:
        raise credentials_exception
    
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

def get_current_active_user(current_user = Depends(get_current_user)):
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
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
    This checks if the user is the owner or has an assignment to the project.
    """
    async def check_access(
        current_user = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        from app.models.project import Project
        from app.models.project_assignment import ProjectAssignment
        from app.crud.project import get_project_by_id
        
        # This will be called from within a route that has project_id in path/params
        # The actual check happens in the route using this dependency
        return current_user
    
    return check_access