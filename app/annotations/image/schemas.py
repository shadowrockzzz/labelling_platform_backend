"""
Image Annotation Pydantic Schemas

Request and response schemas for image annotation API endpoints.
Mirrors the structure of text annotation schemas but with image-specific fields.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class ImageSourceEnum(str, Enum):
    """Source type for image resources."""
    FILE = "file"
    URL = "url"


class AnnotationStatusEnum(str, Enum):
    """Status options for annotations."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class AnnotationSubTypeEnum(str, Enum):
    """Annotation sub-types for image annotations."""
    BOUNDING_BOX = "bounding_box"
    POLYGON = "polygon"
    SEGMENTATION = "segmentation"
    KEYPOINT = "keypoint"
    CLASSIFICATION = "classification"


class CorrectionStatusEnum(str, Enum):
    """Status options for review corrections."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# ==================== Shape Schemas ====================

class BoundingBoxShape(BaseModel):
    """Schema for a single bounding box annotation."""
    id: str = Field(..., description="Unique identifier for the box")
    x: float = Field(..., ge=0, description="X coordinate of top-left corner")
    y: float = Field(..., ge=0, description="Y coordinate of top-left corner")
    width: float = Field(..., gt=0, description="Width of the bounding box")
    height: float = Field(..., gt=0, description="Height of the bounding box")
    label: str = Field(..., description="Label/class of the object")
    color: str = Field(default="#FF5733", description="Color for visualization")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score (0-1)")


class PolygonShape(BaseModel):
    """Schema for a single polygon annotation."""
    id: str = Field(..., description="Unique identifier for the polygon")
    points: List[List[float]] = Field(..., min_length=3, description="List of [x, y] coordinate pairs")
    label: str = Field(..., description="Label/class of the object")
    color: str = Field(default="#33FF57", description="Color for visualization")
    closed: bool = Field(default=True, description="Whether the polygon is closed")


class SegmentationShape(BaseModel):
    """Schema for a single segmentation mask."""
    id: str = Field(..., description="Unique identifier for the segment")
    mask_path: Optional[str] = Field(None, description="Path to the mask file in storage")
    label: str = Field(..., description="Label/class of the segment")
    color: str = Field(default="#3357FF", description="Color for visualization")
    area: Optional[int] = Field(None, ge=0, description="Area in pixels")
    # For RLE (Run-Length Encoding) if used
    rle: Optional[Dict[str, Any]] = Field(None, description="RLE encoded mask data")


class KeypointShape(BaseModel):
    """Schema for a single keypoint annotation."""
    id: str = Field(..., description="Unique identifier for the keypoints")
    points: Dict[str, List[float]] = Field(..., description="Named keypoints as {name: [x, y, visibility]}")
    label: str = Field(..., description="Label/class of the object")
    skeleton: Optional[List[List[int]]] = Field(None, description="Skeleton connections as pairs of indices")
    visibility: Optional[List[int]] = Field(None, description="Visibility flags for each point (0=hidden, 1=visible)")


class ClassificationShape(BaseModel):
    """Schema for a single image classification."""
    id: str = Field(..., description="Unique identifier for the classification")
    label: str = Field(..., description="Assigned class label")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score (0-1)")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes")


# ==================== Annotation Data Schemas ====================

class BoundingBoxData(BaseModel):
    """Data structure for bounding box annotations."""
    boxes: List[BoundingBoxShape] = Field(default_factory=list)


class PolygonData(BaseModel):
    """Data structure for polygon annotations."""
    polygons: List[PolygonShape] = Field(default_factory=list)


class SegmentationData(BaseModel):
    """Data structure for segmentation annotations."""
    segments: List[SegmentationShape] = Field(default_factory=list)


class KeypointData(BaseModel):
    """Data structure for keypoint annotations."""
    keypoints: List[KeypointShape] = Field(default_factory=list)


class ClassificationData(BaseModel):
    """Data structure for classification annotations."""
    classifications: List[ClassificationShape] = Field(default_factory=list)


# ==================== Resource Schemas ====================

class ImageResourceBase(BaseModel):
    """Base schema for image resources."""
    name: str = Field(..., min_length=1, max_length=255)


class ImageResourceCreate(ImageResourceBase):
    """Schema for creating an image resource via URL."""
    source_type: ImageSourceEnum = ImageSourceEnum.FILE
    external_url: Optional[str] = None


class ImageResourceURLCreate(ImageResourceBase):
    """Schema for creating an image resource from URL."""
    external_url: str = Field(..., description="URL to fetch the image from")


class ImageResourceResponse(ImageResourceBase):
    """Schema for image resource response."""
    id: int
    project_id: int
    uploader_id: Optional[int]
    file_path: Optional[str]
    thumbnail_path: Optional[str]
    width: Optional[int]
    height: Optional[int]
    file_size: Optional[int]
    mime_type: Optional[str]
    source_type: str
    external_url: Optional[str]
    image_metadata: Optional[Dict[str, Any]]
    is_archived: bool
    created_at: datetime
    modified_at: Optional[datetime]
    
    # URLs for accessing the image
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    class Config:
        from_attributes = True


class ImageResourceListResponse(BaseModel):
    """Schema for list of image resources."""
    success: bool = True
    data: List[ImageResourceResponse]
    total: int
    page: int
    limit: int


# ==================== Annotation Schemas ====================

class ImageAnnotationBase(BaseModel):
    """Base schema for image annotations."""
    annotation_sub_type: AnnotationSubTypeEnum = AnnotationSubTypeEnum.BOUNDING_BOX
    annotation_data: Optional[Dict[str, Any]] = None


class ImageAnnotationCreate(ImageAnnotationBase):
    """Schema for creating an image annotation."""
    resource_id: int


class ImageAnnotationUpdate(BaseModel):
    """Schema for updating an image annotation."""
    annotation_data: Optional[Dict[str, Any]] = None
    annotation_sub_type: Optional[AnnotationSubTypeEnum] = None


class ImageAnnotationResponse(BaseModel):
    """Schema for image annotation response."""
    id: int
    resource_id: int
    project_id: int
    annotator_id: Optional[int]
    reviewer_id: Optional[int]
    annotation_type: str
    annotation_sub_type: str
    status: str
    annotation_data: Optional[Dict[str, Any]]
    review_comment: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    modified_at: Optional[datetime]
    submitted_at: Optional[datetime]
    
    # Related resource info
    resource: Optional[ImageResourceResponse] = None
    
    # Annotator/reviewer names for display
    annotator_name: Optional[str] = None
    reviewer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ImageAnnotationListResponse(BaseModel):
    """Schema for list of image annotations."""
    success: bool = True
    data: List[ImageAnnotationResponse]
    total: int


# ==================== Shape Operation Schemas ====================

class ShapeCreate(BaseModel):
    """Schema for creating a single shape."""
    shape_data: Dict[str, Any] = Field(..., description="Shape data (varies by sub_type)")


class ShapeUpdate(BaseModel):
    """Schema for updating a single shape."""
    shape_data: Dict[str, Any] = Field(..., description="Updated shape data")


# ==================== Review Schemas ====================

class ReviewAction(BaseModel):
    """Schema for review action on annotation."""
    action: str = Field(..., pattern="^(approve|reject)$")
    comment: Optional[str] = None


# ==================== Correction Schemas ====================

class ImageReviewCorrectionCreate(BaseModel):
    """Schema for creating a review correction."""
    corrected_data: Dict[str, Any] = Field(..., description="The proposed corrected annotation data")
    comment: Optional[str] = Field(None, description="Reviewer's comment")


class ImageReviewCorrectionUpdate(BaseModel):
    """Schema for updating a review correction."""
    status: CorrectionStatusEnum
    annotator_response: Optional[str] = None


class ImageReviewCorrectionResponse(BaseModel):
    """Schema for review correction response."""
    id: int
    annotation_id: int
    reviewer_id: int
    corrected_data: Dict[str, Any]
    status: str
    comment: Optional[str]
    annotator_response: Optional[str]
    created_at: datetime
    modified_at: Optional[datetime]
    
    # Reviewer name for display
    reviewer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ImageReviewCorrectionListResponse(BaseModel):
    """Schema for list of review corrections."""
    success: bool = True
    data: List[ImageReviewCorrectionResponse]
    total: int


# ==================== Queue Schemas ====================

class QueueTaskResponse(BaseModel):
    """Schema for a queue task."""
    id: int
    project_id: int
    resource_id: Optional[int]
    annotation_id: Optional[int]
    task_type: str
    status: str
    priority: int
    assigned_to: Optional[int]
    payload: Optional[Dict[str, Any]]
    created_at: datetime
    processed_at: Optional[datetime]
    error_message: Optional[str]
    
    # Related info
    resource_name: Optional[str] = None
    assigned_user_name: Optional[str] = None

    class Config:
        from_attributes = True


class QueueListResponse(BaseModel):
    """Schema for list of queue tasks."""
    success: bool = True
    data: List[QueueTaskResponse]
    total: int


# ==================== Common Response Schemas ====================

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None