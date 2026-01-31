import re
from typing import Optional

def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength requirements.
    Returns (is_valid, error_message).
    
    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 number
    - At least 1 special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least 1 uppercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least 1 number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least 1 special character"
    
    return True, None

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_role(role: str) -> bool:
    """Validate role is one of the allowed roles."""
    valid_roles = ["admin", "project_manager", "reviewer", "annotator"]
    return role in valid_roles

def validate_project_status(status: str) -> bool:
    """Validate project status."""
    valid_statuses = ["active", "completed", "archived"]
    return status in valid_statuses