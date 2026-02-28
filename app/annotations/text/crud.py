from sqlalchemy.orm import Session
from typing import Optional, Tuple, List, Dict, Any
from pydantic import ValidationError
import json
from app.annotations.text.models import TextResource, TextAnnotation, TextAnnotationQueue
from app.models.review_correction import ReviewCorrection
from app.annotations.text.schemas import (
    NERAnnotationData,
    POSAnnotationData,
    SentimentAnnotationData,
    RelationAnnotationData,
    SpanAnnotationData,
    ClassificationAnnotationData,
    DependencyAnnotationData,
    CoreferenceAnnotationData,
    SpanData
)
from app.models.project import Project


# ==================== Annotation Data Validation ====================

def validate_annotation_data(annotation_sub_type: str, data: Optional[dict]) -> None:
    """
    Validate annotation_data structure matches the sub-type schema.
    
    Args:
        annotation_sub_type: The annotation sub-type (e.g., 'ner', 'pos', 'sentiment', etc.)
        data: The annotation_data dict to validate
    
    Raises:
        ValueError: If sub-type is invalid or data doesn't match schema
    """
    if not data:
        return
    
    sub_type_schemas = {
        'ner': NERAnnotationData,
        'pos': POSAnnotationData,
        'sentiment': SentimentAnnotationData,
        'relation': RelationAnnotationData,
        'span': SpanAnnotationData,
        'classification': ClassificationAnnotationData,
        'dependency': DependencyAnnotationData,
        'coreference': CoreferenceAnnotationData,
    }
    
    schema_class = sub_type_schemas.get(annotation_sub_type)
    if not schema_class:
        raise ValueError(f"Invalid annotation_sub_type: {annotation_sub_type}. Must be one of: {list(sub_type_schemas.keys())}")
    
    try:
        schema_class(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid annotation_data for {annotation_sub_type}: {e}")


# ==================== Resources CRUD ====================

def create_resource(
    db: Session,
    project_id: int,
    user_id: int,
    resource_data: dict
) -> TextResource:
    """Create a new text resource."""
    resource = TextResource(
        project_id=project_id,
        uploaded_by=user_id,
        **resource_data
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def get_resource(db: Session, resource_id: int) -> Optional[TextResource]:
    """Get a resource by ID."""
    return db.query(TextResource).filter(TextResource.id == resource_id).first()


def list_resources(
    db: Session,
    project_id: int,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[TextResource], int]:
    """List resources for a project with pagination."""
    query = db.query(TextResource).filter(
        TextResource.project_id == project_id,
        TextResource.status == "active"
    )
    
    total = query.count()
    resources = query.offset((page - 1) * limit).limit(limit).all()
    
    return resources, total


def archive_resource(db: Session, resource_id: int) -> Optional[TextResource]:
    """Soft delete a resource by archiving it."""
    resource = get_resource(db, resource_id)
    if resource:
        resource.status = "archived"
        db.commit()
        db.refresh(resource)
    return resource


def get_unannotated_resources(
    db: Session,
    project_id: int,
    user_id: int,
    limit: int = 50
) -> List[TextResource]:
    """
    Get resources that haven't been annotated by the current user.
    
    Returns resources where no annotation exists for this user,
    useful for queue-based annotation workflow.
    
    Args:
        db: Database session
        project_id: Project ID
        user_id: Current user's ID
        limit: Maximum number of resources to return
    
    Returns:
        List of unannotated resources
    """
    # Subquery to get resource_ids that have been annotated by this user
    from sqlalchemy import and_
    
    annotated_resource_ids = db.query(TextAnnotation.resource_id).filter(
        TextAnnotation.project_id == project_id,
        TextAnnotation.annotator_id == user_id,
        TextAnnotation.status.in_(['submitted', 'approved'])  # Only count submitted/approved
    ).subquery()
    
    # Get resources not in the annotated list
    resources = db.query(TextResource).filter(
        TextResource.project_id == project_id,
        TextResource.status == "active",
        TextResource.id.notin_(db.query(annotated_resource_ids.c.resource_id))
    ).order_by(TextResource.created_at.asc()).limit(limit).all()
    
    return resources


def delete_resource(db: Session, resource_id: int) -> bool:
    """Permanently delete a resource."""
    resource = get_resource(db, resource_id)
    if resource:
        db.delete(resource)
        db.commit()
        return True
    return False


# ==================== Annotations CRUD ====================

def create_annotation(
    db: Session,
    project_id: int,
    annotator_id: int,
    data: dict
) -> TextAnnotation:
    """
    Create a new annotation.
    
    Supports both old format (single span) and new format (batch with spans array).
    For batch format, automatically enqueues for review.
    """
    annotation_sub_type = data.get('annotation_sub_type')
    annotation_data = data.get('annotation_data')
    
    # Detect format
    has_old_format = data.get('label') is not None and \
                     data.get('span_start') is not None and \
                     data.get('span_end') is not None
    has_new_format = data.get('spans') is not None and len(data.get('spans', [])) > 0
    
    if has_old_format:
        # Old format: single span annotation
        # Validate annotation_data if sub_type is provided
        if annotation_sub_type and annotation_data:
            validate_annotation_data(annotation_sub_type, annotation_data)
        
        annotation = TextAnnotation(
            project_id=project_id,
            annotator_id=annotator_id,
            status='draft',
            **data
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)
        return annotation
    
    elif has_new_format:
        # New format: batch annotation with multiple spans
        from datetime import datetime
        import uuid
        
        # Prepare spans with IDs
        spans_with_ids = []
        for span in data['spans']:
            span_data = {
                'id': span.get('id', f"span_{uuid.uuid4().hex[:8]}"),
                'text': span.get('text', ''),
                'label': span.get('label', ''),
                'start': span.get('start', 0),
                'end': span.get('end', 0),
                # Include any additional metadata
                'confidence': span.get('confidence'),
                'nested': span.get('nested'),
                'token_index': span.get('token_index'),
                'batch': span.get('batch'),
                'intensity': span.get('intensity'),
                'emotions': span.get('emotions'),
                'subcategory': span.get('subcategory'),
                'overlaps_with': span.get('overlaps_with'),
                'priority': span.get('priority'),
                'chain_id': span.get('chain_id'),
                'mention_type': span.get('mention_type'),
                'is_representative': span.get('is_representative'),
                # Add other fields as needed
            }
            # Filter out None values
            span_data = {k: v for k, v in span_data.items() if v is not None}
            spans_with_ids.append(span_data)
        
        # Create annotation with spans array
        annotation = TextAnnotation(
            project_id=project_id,
            annotator_id=annotator_id,
            annotation_type=data.get('annotation_type', 'text'),
            annotation_sub_type=data.get('annotation_sub_type', 'ner'),
            resource_id=data['resource_id'],
            label=None,  # Not used in batch format
            span_start=None,  # Not used in batch format
            span_end=None,  # Not used in batch format
            annotation_data={'spans': spans_with_ids},
            status='submitted',  # Batch annotations go directly to review
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            submitted_at=datetime.utcnow()  # Auto-submit batch annotations
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)
        
        # Enqueue for review (optional - depends on your workflow)
        # enqueue_task(
        #     db,
        #     project_id=project_id,
        #     resource_id=data['resource_id'],
        #     task_type='review',
        #     payload={'annotation_id': annotation.id},
        #     annotation_type='text',
        #     annotation_id=annotation.id
        # )
        
        return annotation
    
    else:
        # Invalid format
        raise ValueError(
            "Either old format (label, span_start, span_end) or new format (spans array) must be provided"
        )


def get_annotation(db: Session, annotation_id: int) -> Optional[TextAnnotation]:
    """Get an annotation by ID."""
    return db.query(TextAnnotation).filter(TextAnnotation.id == annotation_id).first()


def list_annotations(
    db: Session,
    project_id: int,
    resource_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[TextAnnotation], int]:
    """List annotations for a project with optional filters."""
    query = db.query(TextAnnotation).filter(TextAnnotation.project_id == project_id)
    
    if resource_id is not None:
        query = query.filter(TextAnnotation.resource_id == resource_id)
    
    if status is not None:
        query = query.filter(TextAnnotation.status == status)
    
    query = query.order_by(TextAnnotation.created_at.desc())
    total = query.count()
    annotations = query.offset((page - 1) * limit).limit(limit).all()
    
    return annotations, total


def update_annotation(
    db: Session,
    annotation_id: int,
    updates: dict
) -> Optional[TextAnnotation]:
    """Update an annotation."""
    annotation = get_annotation(db, annotation_id)
    if annotation:
        for key, value in updates.items():
            setattr(annotation, key, value)
        db.commit()
        db.refresh(annotation)
    return annotation


def submit_annotation(db: Session, annotation_id: int) -> Optional[TextAnnotation]:
    """Submit an annotation for review."""
    annotation = get_annotation(db, annotation_id)
    if annotation:
        annotation.status = "submitted"
        from datetime import datetime
        annotation.submitted_at = datetime.utcnow()
        db.commit()
        db.refresh(annotation)
    return annotation


def review_annotation(
    db: Session,
    annotation_id: int,
    reviewer_id: int,
    action: str,
    comment: Optional[str] = None
) -> Optional[TextAnnotation]:
    """Review an annotation (approve or reject)."""
    annotation = get_annotation(db, annotation_id)
    if annotation:
        annotation.status = "approved" if action == "approve" else "rejected"
        annotation.reviewer_id = reviewer_id
        annotation.review_comment = comment
        from datetime import datetime
        annotation.reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(annotation)
    return annotation


# ==================== Single-Annotation Model CRUD (New) ====================

def is_array_annotation(annotation: TextAnnotation) -> bool:
    """
    Check if annotation uses the new array-based format (spans in annotation_data).
    
    Old format: has label, span_start, span_end fields populated
    New format: annotation_data contains "spans" array
    """
    if not annotation.annotation_data:
        return False
    return "spans" in annotation.annotation_data


def get_or_create_annotation(
    db: Session,
    project_id: int,
    annotator_id: int,
    resource_id: int,
    annotation_sub_type: str = "ner"
) -> TextAnnotation:
    """
    Get existing annotation for a resource or create a new one.
    
    This is the main entry point for the single-annotation model.
    Ensures only one annotation exists per resource for a given annotator.
    """
    # Check if annotation already exists for this resource and annotator
    existing = db.query(TextAnnotation).filter(
        TextAnnotation.project_id == project_id,
        TextAnnotation.resource_id == resource_id,
        TextAnnotation.annotator_id == annotator_id,
        TextAnnotation.annotation_sub_type == annotation_sub_type
    ).first()
    
    if existing:
        return existing
    
    # Create new annotation with empty spans array
    from datetime import datetime
    annotation = TextAnnotation(
        project_id=project_id,
        resource_id=resource_id,
        annotator_id=annotator_id,
        annotation_type="text",
        annotation_sub_type=annotation_sub_type,
        label=None,  # Not used in new model
        span_start=None,  # Not used in new model
        span_end=None,  # Not used in new model
        annotation_data={"spans": []},  # Initialize with empty spans array
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


def add_span_to_annotation(
    db: Session,
    annotation_id: int,
    span_data: Dict[str, Any]
) -> Optional[TextAnnotation]:
    """
    Add a new span to an existing annotation.
    
    Args:
        annotation_id: The annotation to add the span to
        span_data: Dictionary containing span data (text, label, start, end, etc.)
    
    Returns:
        Updated annotation or None if not found
    """
    annotation = get_annotation(db, annotation_id)
    if not annotation:
        return None
    
    # Ensure annotation_data has spans array
    if not annotation.annotation_data:
        annotation.annotation_data = {"spans": []}
    elif "spans" not in annotation.annotation_data:
        annotation.annotation_data["spans"] = []
    
    # Create span with unique ID
    import uuid
    span_id = f"span_{uuid.uuid4().hex[:8]}"
    span_data_with_id = {"id": span_id, **span_data}
    
    # Add span to array
    annotation.annotation_data["spans"].append(span_data_with_id)
    
    # Update timestamp
    from datetime import datetime
    annotation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(annotation)
    return annotation


def remove_span_from_annotation(
    db: Session,
    annotation_id: int,
    span_id: str
) -> Optional[TextAnnotation]:
    """
    Remove a specific span from an annotation.
    
    Args:
        annotation_id: The annotation to remove the span from
        span_id: The ID of the span to remove
    
    Returns:
        Updated annotation or None if not found
    """
    annotation = get_annotation(db, annotation_id)
    if not annotation or not annotation.annotation_data:
        return None
    
    spans = annotation.annotation_data.get("spans", [])
    updated_spans = [span for span in spans if span.get("id") != span_id]
    
    if len(updated_spans) == len(spans):
        # Span not found
        return annotation
    
    annotation.annotation_data["spans"] = updated_spans
    
    # Update timestamp
    from datetime import datetime
    annotation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(annotation)
    return annotation


def update_span_in_annotation(
    db: Session,
    annotation_id: int,
    span_id: str,
    span_updates: Dict[str, Any]
) -> Optional[TextAnnotation]:
    """
    Update a specific span within an annotation.
    
    Args:
        annotation_id: The annotation containing the span
        span_id: The ID of the span to update
        span_updates: Dictionary of fields to update
    
    Returns:
        Updated annotation or None if not found
    """
    annotation = get_annotation(db, annotation_id)
    if not annotation or not annotation.annotation_data:
        return None
    
    spans = annotation.annotation_data.get("spans", [])
    span_found = False
    
    for span in spans:
        if span.get("id") == span_id:
            # Update span fields
            for key, value in span_updates.items():
                if value is not None:  # Only update non-None values
                    span[key] = value
            span_found = True
            break
    
    if not span_found:
        return None
    
    # Update timestamp
    from datetime import datetime
    annotation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(annotation)
    return annotation


def get_annotation_with_spans(
    db: Session,
    resource_id: int,
    annotator_id: Optional[int] = None
) -> Optional[TextAnnotation]:
    """
    Get annotation for a resource, including all spans.
    
    Args:
        resource_id: The resource ID
        annotator_id: Optional annotator ID to filter by
    
    Returns:
        Annotation with all spans or None if not found
    """
    query = db.query(TextAnnotation).filter(TextAnnotation.resource_id == resource_id)
    
    if annotator_id is not None:
        query = query.filter(TextAnnotation.annotator_id == annotator_id)
    
    annotation = query.order_by(TextAnnotation.created_at.desc()).first()
    return annotation


# ==================== Queue Stub CRUD ====================

def enqueue_task(
    db: Session,
    project_id: int,
    resource_id: Optional[int],
    task_type: str,
    payload: dict,
    annotation_type: str = "text",
    annotation_id: Optional[int] = None
) -> TextAnnotationQueue:
    """
    Add a task to the queue.
    
    Each queue is identified by (project_id, annotation_type) combination.
    This ensures isolation between different annotation types and projects.
    """
    task = TextAnnotationQueue(
        project_id=project_id,
        annotation_type=annotation_type,
        resource_id=resource_id,
        annotation_id=annotation_id,
        task_type=task_type,
        payload=payload,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_queue_tasks(
    db: Session,
    project_id: int,
    annotation_type: str,
    status: Optional[str] = None
) -> List[TextAnnotationQueue]:
    """
    Get queue tasks for a specific project and annotation_type.
    
    This ensures each annotation type has its own queue per project.
    """
    query = db.query(TextAnnotationQueue).filter(
        TextAnnotationQueue.project_id == project_id,
        TextAnnotationQueue.annotation_type == annotation_type
    )
    
    if status is not None:
        query = query.filter(TextAnnotationQueue.status == status)
    
    return query.order_by(TextAnnotationQueue.created_at.desc()).all()


def mark_task_done(db: Session, task_id: int) -> Optional[TextAnnotationQueue]:
    """Mark a queue task as done."""
    task = db.query(TextAnnotationQueue).filter(TextAnnotationQueue.id == task_id).first()
    if task:
        task.status = "done"
        from datetime import datetime
        task.processed_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
    return task


def mark_task_failed(db: Session, task_id: int, error_message: str) -> Optional[TextAnnotationQueue]:
    """Mark a queue task as failed."""
    task = db.query(TextAnnotationQueue).filter(TextAnnotationQueue.id == task_id).first()
    if task:
        task.status = "failed"
        task.error_message = error_message
        from datetime import datetime
        task.processed_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
    return task


# ==================== Review Correction CRUD ====================

def create_review_correction(
    db: Session,
    annotation_id: int,
    reviewer_id: int,
    corrected_data: Dict[str, Any],
    comment: Optional[str] = None
) -> Optional[ReviewCorrection]:
    """
    Create a new review correction.
    
    Args:
        annotation_id: The annotation being corrected
        reviewer_id: The ID of the reviewer making the correction
        corrected_data: The corrected annotation data
        comment: Optional comment explaining the correction
    
    Returns:
        Created ReviewCorrection or None if annotation not found
    """
    # Get the original annotation
    annotation = get_annotation(db, annotation_id)
    if not annotation:
        return None
    
    # Store original data for comparison
    original_data = None
    if annotation.annotation_data:
        original_data = annotation.annotation_data.copy()
    
    # Create correction
    from datetime import datetime
    correction = ReviewCorrection(
        annotation_id=annotation_id,
        reviewer_id=reviewer_id,
        status="pending",
        original_data=original_data,
        corrected_data=corrected_data,
        comment=comment,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return correction


def get_review_correction(db: Session, correction_id: int) -> Optional[ReviewCorrection]:
    """Get a review correction by ID."""
    return db.query(ReviewCorrection).filter(ReviewCorrection.id == correction_id).first()


def list_review_corrections(
    db: Session,
    annotation_id: Optional[int] = None,
    reviewer_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[ReviewCorrection], int]:
    """
    List review corrections with optional filters.
    
    Args:
        annotation_id: Filter by annotation ID
        reviewer_id: Filter by reviewer ID
        status: Filter by status (pending, accepted, rejected)
        page: Page number for pagination
        limit: Items per page
    
    Returns:
        Tuple of (corrections list, total count)
    """
    query = db.query(ReviewCorrection)
    
    if annotation_id is not None:
        query = query.filter(ReviewCorrection.annotation_id == annotation_id)
    
    if reviewer_id is not None:
        query = query.filter(ReviewCorrection.reviewer_id == reviewer_id)
    
    if status is not None:
        query = query.filter(ReviewCorrection.status == status)
    
    query = query.order_by(ReviewCorrection.created_at.desc())
    total = query.count()
    corrections = query.offset((page - 1) * limit).limit(limit).all()
    
    return corrections, total


def update_review_correction(
    db: Session,
    correction_id: int,
    status: str,
    annotator_response: Optional[str] = None
) -> Optional[ReviewCorrection]:
    """
    Update a review correction (accept or reject).
    
    Args:
        correction_id: The correction ID to update
        status: New status ('accepted' or 'rejected')
        annotator_response: Optional response from annotator
    
    Returns:
        Updated ReviewCorrection or None if not found
    """
    correction = get_review_correction(db, correction_id)
    if not correction:
        return None
    
    correction.status = status
    if annotator_response is not None:
        correction.annotator_response = annotator_response
    
    from datetime import datetime
    correction.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(correction)
    return correction


def accept_review_correction(
    db: Session,
    correction_id: int,
    annotator_response: Optional[str] = None
) -> Optional[TextAnnotation]:
    """
    Accept a review correction and update the original annotation.
    
    Args:
        correction_id: The correction ID to accept
        annotator_response: Optional response from annotator
    
    Returns:
        Updated annotation or None if not found
    """
    # Get the correction
    correction = get_review_correction(db, correction_id)
    if not correction:
        return None
    
    # Get the original annotation
    annotation = get_annotation(db, correction.annotation_id)
    if not annotation:
        return None
    
    # Apply the corrected data to the original annotation
    if correction.corrected_data:
        annotation.annotation_data = correction.corrected_data.copy()
    
    # Mark correction as accepted
    correction.status = "accepted"
    if annotator_response is not None:
        correction.annotator_response = annotator_response
    
    from datetime import datetime
    correction.updated_at = datetime.utcnow()
    annotation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(annotation)
    return annotation
