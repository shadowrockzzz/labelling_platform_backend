from pydantic import BaseModel, Field, HttpUrl, validator, model_validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import uuid


# ==================== Generic Span Schema for Single-Annotation Model ====================

class SpanData(BaseModel):
    """Generic span data structure for all annotation types in single-annotation model."""
    id: Optional[str] = Field(default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}")
    text: str
    label: str 
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    
    # Optional metadata fields (based on annotation sub-type)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    nested: Optional[bool] = False
    token_index: Optional[int] = None
    batch: Optional[bool] = False
    intensity: Optional[int] = Field(None, ge=0, le=100)
    emotions: Optional[Dict[str, float]] = None
    head_entity: Optional[Dict[str, Any]] = None
    tail_entity: Optional[Dict[str, Any]] = None
    relation_label: Optional[str] = None
    subcategory: Optional[str] = None
    overlaps_with: Optional[List[int]] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    classes: Optional[List[Dict[str, Any]]] = None
    classification_type: Optional[str] = None
    reasoning: Optional[str] = None
    head_token: Optional[str] = None
    dependent_token: Optional[str] = None
    head_index: Optional[int] = None
    dependent_index: Optional[int] = None
    relation: Optional[str] = None
    is_root: Optional[bool] = False
    chain_id: Optional[str] = None
    mention_type: Optional[str] = None
    is_representative: Optional[bool] = False
    other_mentions: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


# ==================== Annotation Sub-Type Data Schemas (Legacy - for backward compatibility) ====================

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
    """Schema for creating annotations. Supports both old (single span) and new (spans array) formats."""
    resource_id: int = Field(..., gt=0)
    annotation_type: str = Field(default="text")  # Always 'text' for this module
    annotation_sub_type: Optional[str] = Field(default="ner")  # 'ner', 'pos', 'sentiment', 'relation', 'span', 'classification', 'dependency', 'coreference'
    
    # Old format fields (backward compatibility)
    label: Optional[str] = None
    span_start: Optional[int] = Field(None, ge=0)
    span_end: Optional[int] = Field(None, ge=0)
    annotation_data: Optional[Dict[str, Any]] = None
    
    # New format: spans array
    spans: Optional[List[SpanData]] = None

    @model_validator(mode='after')
    def validate_annotation_format(cls, values):
        """Validate that either old format OR new format is provided, not both."""
        has_old_format = values.label is not None and \
                       values.span_start is not None and \
                       values.span_end is not None
        has_new_format = values.spans is not None and len(values.spans or []) > 0
        
        if not has_old_format and not has_new_format:
            raise ValueError(
                "Either old format (label, span_start, span_end) or new format (spans array) must be provided"
            )
        
        if has_old_format and has_new_format:
            raise ValueError(
                "Cannot provide both old format and new format simultaneously"
            )
        
        # Validate spans if provided (new format)
        if has_new_format:
            spans = values.spans
            cls._validate_spans(spans)
        
        return values
    
    @staticmethod
    def _validate_spans(spans: List[SpanData]):
        """Validate spans array: check for overlaps and correct ordering."""
        if not spans:
            return
        
        # Check that start < end for each span
        for i, span in enumerate(spans):
            if span.start is None or span.end is None:
                raise ValueError(f"Span {i+1}: start and end positions must be provided")
            if span.start >= span.end:
                raise ValueError(
                    f"Span {i+1}: start ({span.start}) must be less than end ({span.end})"
                )
            if not span.text:
                raise ValueError(f"Span {i+1}: text cannot be empty")
            if not span.label:
                raise ValueError(f"Span {i+1}: label cannot be empty")
        
        # Sort spans by start position for overlap detection
        sorted_spans = sorted(spans, key=lambda x: x.start if x.start is not None else 0)
        
        # Check for overlapping spans
        for i in range(len(sorted_spans) - 1):
            current = sorted_spans[i]
            next_span = sorted_spans[i + 1]
            if current.end > next_span.start:
                raise ValueError(
                    f"Spans overlap: '{current.text}' [{current.start}:{current.end}] "
                    f"overlaps with '{next_span.text}' [{next_span.start}:{next_span.end}]"
                )

    class Config:
        from_attributes = True


class SpanCreate(BaseModel):
    """Schema for adding a single span to an existing annotation."""
    text: str
    label: str
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    
    # Optional metadata fields
    confidence: Optional[float] = Field(None, ge=0, le=1)
    nested: Optional[bool] = False
    token_index: Optional[int] = None
    batch: Optional[bool] = False
    intensity: Optional[int] = Field(None, ge=0, le=100)
    emotions: Optional[Dict[str, float]] = None
    head_entity: Optional[Dict[str, Any]] = None
    tail_entity: Optional[Dict[str, Any]] = None
    relation_label: Optional[str] = None
    subcategory: Optional[str] = None
    overlaps_with: Optional[List[int]] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    classes: Optional[List[Dict[str, Any]]] = None
    classification_type: Optional[str] = None
    reasoning: Optional[str] = None
    head_token: Optional[str] = None
    dependent_token: Optional[str] = None
    head_index: Optional[int] = None
    dependent_index: Optional[int] = None
    relation: Optional[str] = None
    is_root: Optional[bool] = False
    chain_id: Optional[str] = None
    mention_type: Optional[str] = None
    is_representative: Optional[bool] = False
    other_mentions: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class SpanUpdate(BaseModel):
    """Schema for updating a specific span within an annotation."""
    text: Optional[str] = None
    label: Optional[str] = None
    start: Optional[int] = Field(None, ge=0)
    end: Optional[int] = Field(None, ge=0)
    
    # Optional metadata fields
    confidence: Optional[float] = Field(None, ge=0, le=1)
    nested: Optional[bool] = None
    token_index: Optional[int] = None
    batch: Optional[bool] = None
    intensity: Optional[int] = Field(None, ge=0, le=100)
    emotions: Optional[Dict[str, float]] = None
    head_entity: Optional[Dict[str, Any]] = None
    tail_entity: Optional[Dict[str, Any]] = None
    relation_label: Optional[str] = None
    subcategory: Optional[str] = None
    overlaps_with: Optional[List[int]] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    classes: Optional[List[Dict[str, Any]]] = None
    classification_type: Optional[str] = None
    reasoning: Optional[str] = None
    head_token: Optional[str] = None
    dependent_token: Optional[str] = None
    head_index: Optional[int] = None
    dependent_index: Optional[int] = None
    relation: Optional[str] = None
    is_root: Optional[bool] = None
    chain_id: Optional[str] = None
    mention_type: Optional[str] = None
    is_representative: Optional[bool] = None
    other_mentions: Optional[List[Dict[str, Any]]] = None

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
    payload: Dict[str, Any] = {}
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class QueueListResponse(BaseModel):
    success: bool = True
    data: list[QueueTaskResponse]
    total: int


# ==================== Review Correction Schemas ====================

class ReviewCorrectionCreate(BaseModel):
    """Schema for creating a review correction."""
    annotation_id: int
    corrected_data: Dict[str, Any]
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewCorrectionUpdate(BaseModel):
    """Schema for updating a review correction status."""
    status: str = Field(..., pattern="^(pending|accepted|rejected)$")
    annotator_response: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewCorrectionResponse(BaseModel):
    """Schema for review correction response."""
    id: int
    annotation_id: int
    reviewer_id: int
    reviewer_username: Optional[str] = None
    status: str
    original_data: Optional[Dict[str, Any]] = None
    corrected_data: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None
    annotator_response: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewCorrectionListResponse(BaseModel):
    """Schema for list of review corrections."""
    success: bool = True
    data: list[ReviewCorrectionResponse]
    total: int


