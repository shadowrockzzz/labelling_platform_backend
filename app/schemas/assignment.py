from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class AssignmentCreate(BaseModel):
    project_id: int
    user_id: int
    role: str  # 'project_manager', 'reviewer', 'annotator'
    review_level: Optional[int] = None  # Only for reviewers: 1, 2, 3... (1 = first reviewer)


class AssignmentUpdate(BaseModel):
    review_level: Optional[int] = None  # Update reviewer level


class AssignmentRead(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: str
    review_level: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AssignmentWithUser(AssignmentRead):
    user_email: str
    user_full_name: Optional[str] = None
    user_role: Optional[str] = None  # Include user role from User model


class ReviewerWithLevel(BaseModel):
    """Reviewer with their assigned review level."""
    assignment_id: int
    user_id: int
    user_email: str
    user_full_name: Optional[str] = None
    review_level: int


class ProjectTeamResponse(BaseModel):
    """Response with team members separated by role."""
    success: bool = True
    data: dict  # Will contain {manager, reviewers, annotators}


class TeamMemberResponse(BaseModel):
    success: bool = True
    data: List[AssignmentWithUser]


class AddTeamMembersRequest(BaseModel):
    user_ids: List[int]


class AddReviewerRequest(BaseModel):
    """Request to add a reviewer with a specific level."""
    user_id: int
    review_level: int = 1  # Default to level 1


class AddReviewersRequest(BaseModel):
    """Request to add multiple reviewers with their levels."""
    reviewers: List[AddReviewerRequest]


class UpdateReviewerLevelRequest(BaseModel):
    """Request to update a reviewer's level."""
    review_level: int


class SuccessResponse(BaseModel):
    success: bool = True
    message: str