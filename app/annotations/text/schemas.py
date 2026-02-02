from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ==================== Annotation Sub-Type Data Schemas ====================

class NERAnnotationData(BaseModel):
    """Data structure for Named Entity Recognition annotations."""
    entity_text: str
    confidence: Optional[float] = None
    nested: Optional[bool] = False

    class Config:
        from_attributes = True


class POSAnnotationData(BaseModel):
    """Data structure for Part-of-Speech Tagging annotations."""
    token: str
    token_index: int
    batch: Optional[bool] = False

    class Config:
        from_attributes = True


class SentimentAnnotationData(BaseModel):
    """Data structure for Sentiment/Emotion annotations."""
    text: str
    intensity: int = Field(..., ge=0, le=100)  # 0-100 scale
    emotions: Optional[Dict[str, float]] = {}

    class Config:
        from_attributes = True


class RelationAnnotationData(BaseModel):
    """Data structure for Relation Extraction annotations."""
    head_entity: Dict[str, Any]  # { "text", "label", "start", "end" }
    tail_entity: Dict[str, Any]  # { "text", "label", "start", "end" }
    relation_label: str
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


class SpanAnnotationData(BaseModel):
    """Data structure for Span/Sequence Labeling annotations."""
    text: str
    category: str
    subcategory: Optional[str] = None
    overlaps_with: Optional[List[int]] = []
    priority: int = Field(..., ge=1, le=5)  # 1 (highest) to 5 (lowest)

    class Config:
        from_attributes = True


class ClassificationAnnotationData(BaseModel):
    """Data structure for Classification annotations."""
    classes: List[Dict[str, Any]]  # [{ "label", "confidence" }]
    classification_type: str = Field(..., pattern="^(binary|multi_class|multi_label)$")
    reasoning: Optional[str] = None

    class Config:
        from_attributes = True


class DependencyAnnotationData(BaseModel):
    """Data structure for Dependency Parsing annotations."""
    head_token: str
    dependent_token: str
    head_index: int
    dependent_index: int
    relation: str
    is_root: bool = False

    class Config:
        from_attributes = True


class CoreferenceAnnotationData(BaseModel):
    """Data structure for Coreference Resolution annotations."""
    mention_text: str
    chain_id: str
    mention_type: str = Field(..., pattern="^(pronoun|proper_noun|common_noun)$")
    is_representative: bool = False
    other_mentions: Optional[List[Dict[str, Any]]] = []  # [{ "text", "start", "end" }]

    class Config:
        from_attributes = True


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
    annotation_type: str = Field(default="text")  # Always 'text' for this module
    annotation_sub_type: Optional[str] = Field(default="ner")  # 'ner', 'pos', 'sentiment', 'relation', 'span', 'classification', 'dependency', 'coreference'
    label: Optional[str] = None
    span_start: Optional[int] = Field(None, ge=0)
    span_end: Optional[int] = Field(None, ge=0)
    annotation_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class TextAnnotationUpdate(BaseModel):
    annotation_sub_type: Optional[str] = None
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
    annotation_sub_type: Optional[str] = None
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
    annotation_type: str
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