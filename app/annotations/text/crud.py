from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
from app.annotations.text.models import TextResource, TextAnnotation, TextAnnotationQueue
from app.models.project import Project


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
    """Create a new annotation."""
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
    payload: dict
) -> TextAnnotationQueue:
    """Add a task to the queue."""
    task = TextAnnotationQueue(
        project_id=project_id,
        resource_id=resource_id,
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
    status: Optional[str] = None
) -> List[TextAnnotationQueue]:
    """Get queue tasks for a project, optionally filtered by status."""
    query = db.query(TextAnnotationQueue).filter(TextAnnotationQueue.project_id == project_id)
    
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