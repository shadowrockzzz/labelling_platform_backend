from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
from pydantic import ValidationError
from app.annotations.text.models import TextResource, TextAnnotation, TextAnnotationQueue
from app.annotations.text.schemas import (
    NERAnnotationData,
    POSAnnotationData,
    SentimentAnnotationData,
    RelationAnnotationData,
    SpanAnnotationData,
    ClassificationAnnotationData,
    DependencyAnnotationData,
    CoreferenceAnnotationData
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
    
    Validates annotation_data structure if annotation_sub_type is provided.
    """
    annotation_sub_type = data.get('annotation_sub_type')
    annotation_data = data.get('annotation_data')
    
    # Validate annotation_data if sub_type is provided
    if annotation_sub_type and annotation_data:
        validate_annotation_data(annotation_sub_type, annotation_data)
    
    annotation = TextAnnotation(
        project_id=project_id,
        annotator_id=annotator_id,
        **data
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


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