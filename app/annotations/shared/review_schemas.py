"""
Pydantic schemas for review task operations.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ReviewTaskBase(BaseModel):
    """Base schema for review tasks."""
    review_level: int = Field(..., ge=1, description="Review level (1, 2, 3, ...)")


class ReviewTaskCreate(ReviewTaskBase):
    """Schema for creating a review task."""
    project_id: int
    annotation_id: int
    annotation_type: str  # 'text' or 'image'
    previous_review_task_id: Optional[UUID] = None


class ReviewTaskResponse(BaseModel):
    """Schema for review task response."""
    id: UUID
    project_id: int
    annotation_id: int
    annotation_type: str
    review_level: int
    reviewer_id: Optional[int] = None
    status: str
    locked_at: Optional[datetime] = None
    lock_expires_at: Optional[datetime] = None
    action: Optional[str] = None
    action_comment: Optional[str] = None
    action_at: Optional[datetime] = None
    previous_review_task_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Computed fields
    short_id: str = Field(..., description="First 8 chars of UUID for display")
    is_locked: bool = False
    
    class Config:
        from_attributes = True


class ReviewActionRequest(BaseModel):
    """Schema for review action (approve/reject/edit)."""
    action: str = Field(..., pattern="^(approve|reject|edit)$")
    comment: Optional[str] = None
    annotation_data: Optional[Dict[str, Any]] = None  # For edit action


class StartReviewRequest(BaseModel):
    """Schema for starting a review."""
    pass  # No body needed, uses URL params


class StartReviewResponse(BaseModel):
    """Schema for start review response."""
    review_task: Optional[ReviewTaskResponse] = None
    annotation: Optional[Dict[str, Any]] = None
    resource: Optional[Dict[str, Any]] = None
    message: str = "No tasks available for review"
    has_task: bool = False


class ReviewChainEntry(BaseModel):
    """Schema for a single review chain entry."""
    review_task_id: str
    review_level: int
    reviewer_id: int
    action: str  # approved, rejected, edited
    comment: Optional[str] = None
    acted_at: str


class FinalOutputResponse(BaseModel):
    """Schema for final approved annotation output."""
    final_output_uuid: UUID
    annotator_task_id: Optional[UUID] = None
    annotation_id: int
    resource_id: int
    project_id: int
    participants: Dict[str, Any]  # Contains annotator and reviewer info
    review_chain: List[ReviewChainEntry]
    annotation_data: Dict[str, Any]
    created_at: datetime
    approved_at: datetime


class ReviewPoolStats(BaseModel):
    """Schema for review pool statistics."""
    project_id: int
    review_level: int
    total_available: int
    total_locked: int
    total_completed: int
    my_locked_count: int = 0