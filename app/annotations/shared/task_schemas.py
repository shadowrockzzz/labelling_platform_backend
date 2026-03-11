"""
Pydantic schemas for annotation tasks.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class AnnotationTaskBase(BaseModel):
    """Base schema for annotation tasks."""
    project_id: int
    resource_id: int
    resource_type: str = Field(..., pattern="^(text|image)$")


class AnnotationTaskCreate(AnnotationTaskBase):
    """Schema for creating a new annotation task."""
    pass


class AnnotationTaskResponse(AnnotationTaskBase):
    """Schema for annotation task response."""
    id: UUID
    annotator_id: Optional[int] = None
    status: str
    locked_at: Optional[datetime] = None
    lock_expires_at: Optional[datetime] = None
    annotation_id: Optional[int] = None
    skipped_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    # Computed field for display
    short_id: str = Field(..., description="First 8 characters of UUID")
    
    class Config:
        from_attributes = True


class AnnotationTaskWithResource(AnnotationTaskResponse):
    """Schema for annotation task with embedded resource data."""
    resource: Dict[str, Any] = Field(..., description="Full resource object (text content or image metadata)")
    resource_content: Optional[str] = Field(None, description="Text content for text resources")
    resource_url: Optional[str] = Field(None, description="Presigned URL for image resources")


class AnnotationTaskStats(BaseModel):
    """Statistics for annotation tasks in a project."""
    total: int = 0
    available: int = 0
    locked: int = 0
    in_progress: int = 0
    submitted: int = 0
    approved: int = 0
    rejected: int = 0
    
    class Config:
        from_attributes = True


class AnnotationTaskClaimResponse(BaseModel):
    """Response for task claim operation."""
    task: Optional[AnnotationTaskWithResource] = None
    message: str = "Task claimed successfully"


class AnnotationTaskSkipResponse(BaseModel):
    """Response for task skip operation."""
    message: str = "Task skipped and returned to pool"
    task_id: UUID


class AnnotationTaskSubmitResponse(BaseModel):
    """Response for task submit operation."""
    message: str = "Task submitted successfully"
    task_id: UUID
    annotation_id: int


class SeedTasksRequest(BaseModel):
    """Request for seeding tasks from existing resources."""
    resource_ids: Optional[List[int]] = Field(None, description="Specific resource IDs to seed. If None, seeds all.")


class SeedTasksResponse(BaseModel):
    """Response for seeding tasks."""
    created_count: int
    skipped_count: int  # Already existing
    message: str