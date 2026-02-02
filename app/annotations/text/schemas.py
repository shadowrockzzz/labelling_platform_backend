from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime


# ==================== Resource Schemas ====================

class ResourceUploadCreate(BaseModel):
    name: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern="^upload$")
    # file is handled via multipart, not in this schema

    class Config:
        from_attributes = True


class ResourceURLCreate(BaseModel):
    name: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern="^url$")
    external_url: str = Field(..., min_length=1)

    class Config:
        from_attributes = True


class ResourceResponse(BaseModel):
    id: int
    project_id: int
    name: str
    source_type: str
    s3_key: Optional[str] = None
    external_url: Optional[str] = None
    content_preview: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


class ResourceWithContentResponse(ResourceResponse):
    full_content: Optional[str] = None


class ResourceListResponse(BaseModel):
    success: bool = True
    data: list[ResourceResponse]
    total: int
    page: int
    limit: int


# ==================== Annotation Schemas ====================

class TextAnnotationCreate(BaseModel):
    resource_id: int = Field(..., gt=0)
    annotation_type: str = Field(default="general")
    label: Optional[str] = None
    span_start: Optional[int] = Field(None, ge=0)
    span_end: Optional[int] = Field(None, ge=0)
    annotation_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class TextAnnotationUpdate(BaseModel):
    label: Optional[str] = None
    span_start: Optional[int] = Field(None, ge=0)
    span_end: Optional[int] = Field(None, ge=0)
    annotation_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class TextAnnotationResponse(BaseModel):
    id: int
    resource_id: int
    project_id: int
    annotator_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    annotation_type: str
    status: str
    label: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    annotation_data: Optional[Dict[str, Any]] = None
    review_comment: Optional[str] = None
    output_s3_key: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TextAnnotationListResponse(BaseModel):
    success: bool = True
    data: list[TextAnnotationResponse]
    total: int


# ==================== Review Schemas ====================

class ReviewAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    comment: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Queue Stub Schemas ====================

class QueueTaskResponse(BaseModel):
    id: int
    project_id: int
    resource_id: Optional[int] = None
    annotation_id: Optional[int] = None
    task_type: str
    status: str
    payload: Dict[str, Any]
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class QueueListResponse(BaseModel):
    success: bool = True
    data: list[QueueTaskResponse]