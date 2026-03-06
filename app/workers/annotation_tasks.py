"""
Worker task functions executed by rq workers.

These functions run in separate worker processes - do not import FastAPI
app-level singletons here. Create fresh DB sessions if database access is needed.

All task functions support multiple annotation types (text, image, video, etc.)
via the annotation_type parameter. This makes the system flexible for future
annotation type additions.

Usage:
    These functions are called by rq workers when jobs are enqueued.
    Do not call them directly from API code - use AnnotationQueue.enqueue() instead.
"""
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_db():
    """
    Get a fresh database session for worker use.
    
    Workers run in separate processes, so they need their own sessions.
    """
    from app.core.database import SessionLocal
    return SessionLocal()


def process_resource_uploaded(
    annotation_type: str,
    project_id: int,
    resource_id: Optional[int] = None,
    annotation_id: Optional[int] = None,
    payload: Optional[dict] = None,
    **kwargs
):
    """
    Process a newly uploaded resource.
    
    Triggered when a new text, image, or other resource is uploaded.
    
    Future use cases:
    - Trigger ML pre-annotation
    - Send notifications to project members
    - Update project statistics
    - Generate thumbnails (for images)
    
    Args:
        annotation_type: Type of annotation ('text', 'image', 'video', etc.)
        project_id: Project ID
        resource_id: Resource ID
        annotation_id: Not used for this task type
        payload: Additional data (e.g., filename, file size)
        **kwargs: Additional keyword arguments for extensibility
    """
    payload = payload or {}
    logger.info(
        f"[resource_uploaded] type={annotation_type} project={project_id} "
        f"resource={resource_id} payload={payload}"
    )
    
    # TODO: Add annotation-type-specific processing
    # if annotation_type == "text":
    #     # Text-specific: maybe run NLP pre-processing
    # elif annotation_type == "image":
    #     # Image-specific: generate additional thumbnails, run object detection
    # elif annotation_type == "video":
    #     # Video-specific: extract frames, generate previews
    
    _mark_audit_done(
        task_type="resource_uploaded",
        annotation_type=annotation_type,
        project_id=project_id,
        resource_id=resource_id
    )


def process_annotation_created(
    annotation_type: str,
    project_id: int,
    resource_id: Optional[int] = None,
    annotation_id: Optional[int] = None,
    payload: Optional[dict] = None,
    **kwargs
):
    """
    Process a newly created annotation.
    
    Triggered when an annotator creates/saves an annotation.
    
    Future use cases:
    - Update annotation statistics
    - Trigger quality checks
    - Send notifications
    
    Args:
        annotation_type: Type of annotation ('text', 'image', 'video', etc.)
        project_id: Project ID
        resource_id: Resource ID
        annotation_id: Annotation ID
        payload: Additional data (e.g., annotation summary)
        **kwargs: Additional keyword arguments for extensibility
    """
    payload = payload or {}
    logger.info(
        f"[annotation_created] type={annotation_type} project={project_id} "
        f"annotation={annotation_id} resource={resource_id}"
    )
    
    _mark_audit_done(
        task_type="annotation_created",
        annotation_type=annotation_type,
        project_id=project_id,
        resource_id=resource_id,
        annotation_id=annotation_id
    )


def process_annotation_submitted(
    annotation_type: str,
    project_id: int,
    resource_id: Optional[int] = None,
    annotation_id: Optional[int] = None,
    payload: Optional[dict] = None,
    **kwargs
):
    """
    Process a submitted annotation (ready for review).
    
    Triggered when an annotator submits an annotation for review.
    
    Future use cases:
    - Notify assigned reviewers
    - Update reviewer dashboard in real time
    - Send email notifications
    - Update project metrics
    
    Args:
        annotation_type: Type of annotation ('text', 'image', 'video', etc.)
        project_id: Project ID
        resource_id: Resource ID
        annotation_id: Annotation ID
        payload: Additional data (e.g., annotator info, submission time)
        **kwargs: Additional keyword arguments for extensibility
    """
    payload = payload or {}
    logger.info(
        f"[annotation_submitted] type={annotation_type} project={project_id} "
        f"annotation={annotation_id} for review"
    )
    
    # TODO: Send reviewer notification
    # Example: email_service.notify_reviewer(project_id, annotation_id)
    
    _mark_audit_done(
        task_type="annotation_submitted",
        annotation_type=annotation_type,
        project_id=project_id,
        resource_id=resource_id,
        annotation_id=annotation_id
    )


def process_annotation_approved(
    annotation_type: str,
    project_id: int,
    resource_id: Optional[int] = None,
    annotation_id: Optional[int] = None,
    payload: Optional[dict] = None,
    **kwargs
):
    """
    Process an approved annotation.
    
    Triggered when a reviewer approves an annotation.
    
    Future use cases:
    - Notify annotator of approval
    - Update project completion metrics
    - Trigger export of approved annotations
    - Add to training dataset
    
    Args:
        annotation_type: Type of annotation ('text', 'image', 'video', etc.)
        project_id: Project ID
        resource_id: Resource ID
        annotation_id: Annotation ID
        payload: Additional data (e.g., reviewer info, approval time)
        **kwargs: Additional keyword arguments for extensibility
    """
    payload = payload or {}
    logger.info(
        f"[annotation_approved] type={annotation_type} project={project_id} "
        f"annotation={annotation_id}"
    )
    
    # TODO: Notify annotator, update stats
    
    _mark_audit_done(
        task_type="annotation_approved",
        annotation_type=annotation_type,
        project_id=project_id,
        resource_id=resource_id,
        annotation_id=annotation_id
    )


def process_annotation_rejected(
    annotation_type: str,
    project_id: int,
    resource_id: Optional[int] = None,
    annotation_id: Optional[int] = None,
    payload: Optional[dict] = None,
    **kwargs
):
    """
    Process a rejected annotation.
    
    Triggered when a reviewer rejects an annotation.
    
    Future use cases:
    - Notify annotator of rejection with feedback
    - Track rejection reasons for quality improvement
    - Re-queue for revision
    
    Args:
        annotation_type: Type of annotation ('text', 'image', 'video', etc.)
        project_id: Project ID
        resource_id: Resource ID
        annotation_id: Annotation ID
        payload: Additional data (e.g., rejection reason, reviewer feedback)
        **kwargs: Additional keyword arguments for extensibility
    """
    payload = payload or {}
    rejection_reason = payload.get("rejection_reason", "Not specified")
    logger.info(
        f"[annotation_rejected] type={annotation_type} project={project_id} "
        f"annotation={annotation_id} reason={rejection_reason}"
    )
    
    # TODO: Notify annotator with feedback
    
    _mark_audit_done(
        task_type="annotation_rejected",
        annotation_type=annotation_type,
        project_id=project_id,
        resource_id=resource_id,
        annotation_id=annotation_id
    )


def process_output(
    annotation_type: str,
    project_id: int,
    resource_id: Optional[int] = None,
    annotation_id: Optional[int] = None,
    payload: Optional[dict] = None,
    **kwargs
):
    """
    Process an export/output request.
    
    Triggered when a user requests to export annotations.
    
    Future use cases:
    - Generate COCO format export
    - Generate YOLO format export
    - Generate spaCy format export
    - Create downloadable archives
    
    Args:
        annotation_type: Type of annotation ('text', 'image', 'video', etc.)
        project_id: Project ID
        resource_id: Resource ID (if exporting specific resource)
        annotation_id: Annotation ID (if exporting specific annotation)
        payload: Additional data (e.g., export format, filters)
        **kwargs: Additional keyword arguments for extensibility
    """
    payload = payload or {}
    export_format = payload.get("format", "json")
    logger.info(
        f"[output] type={annotation_type} project={project_id} "
        f"format={export_format}"
    )
    
    # TODO: Implement export logic based on format
    # if export_format == "coco":
    #     generate_coco_export(project_id, annotation_type)
    # elif export_format == "yolo":
    #     generate_yolo_export(project_id, annotation_type)
    
    _mark_audit_done(
        task_type="output",
        annotation_type=annotation_type,
        project_id=project_id,
        resource_id=resource_id,
        annotation_id=annotation_id
    )


def _mark_audit_done(
    task_type: str,
    annotation_type: str,
    project_id: int,
    resource_id: Optional[int] = None,
    annotation_id: Optional[int] = None
):
    """
    Mark the matching audit log row as done after a job completes.
    
    This updates the PostgreSQL text_annotation_queue table to reflect
    that the task has been processed successfully.
    
    Args:
        task_type: Type of task
        annotation_type: Type of annotation
        project_id: Project ID
        resource_id: Resource ID (optional)
        annotation_id: Annotation ID (optional)
    """
    db = _get_db()
    try:
        from app.annotations.text.models import TextAnnotationQueue
        
        # Find the matching pending task
        query = db.query(TextAnnotationQueue).filter(
            TextAnnotationQueue.project_id == project_id,
            TextAnnotationQueue.task_type == task_type,
            TextAnnotationQueue.annotation_type == annotation_type,
            TextAnnotationQueue.status == "pending"
        )
        
        if resource_id is not None:
            query = query.filter(TextAnnotationQueue.resource_id == resource_id)
        if annotation_id is not None:
            query = query.filter(TextAnnotationQueue.annotation_id == annotation_id)
        
        record = query.first()
        
        if record:
            record.status = "done"
            record.processed_at = datetime.utcnow()
            db.commit()
            logger.debug(f"Marked audit record {record.id} as done")
        else:
            logger.warning(
                f"No matching pending audit record found for "
                f"task_type={task_type}, annotation_type={annotation_type}, "
                f"project_id={project_id}"
            )
    except Exception as e:
        logger.error(f"Failed to mark audit record done: {e}")
        db.rollback()
    finally:
        db.close()


# Task function registry for easy lookup
TASK_FUNCTION_MAP = {
    "resource_uploaded": f"{__name__}.process_resource_uploaded",
    "annotation_created": f"{__name__}.process_annotation_created",
    "annotation_submitted": f"{__name__}.process_annotation_submitted",
    "annotation_approved": f"{__name__}.process_annotation_approved",
    "annotation_rejected": f"{__name__}.process_annotation_rejected",
    "output": f"{__name__}.process_output",
    "release_expired_locks": f"{__name__}.release_expired_locks",
}


def release_expired_locks(
    annotation_type: str = "text",
    lock_expiry_minutes: int = 120,
    **kwargs
):
    """
    Release expired locks on resources and annotation tasks.
    
    This job should be scheduled to run periodically (e.g., every 5-10 minutes)
    via RQ scheduler or cron.
    
    Releases locks that have been held longer than lock_expiry_minutes.
    This prevents resources from being stuck in "locked" state if an
    annotator's session ends unexpectedly.
    
    Args:
        annotation_type: Type of annotation ('text', 'image')
        lock_expiry_minutes: Lock expiry threshold in minutes (default: 120 = 2 hours)
    """
    from datetime import timedelta
    
    db = _get_db()
    expiry_threshold = datetime.utcnow() - timedelta(minutes=lock_expiry_minutes)
    
    released_tasks = 0
    released_resources = 0
    
    try:
        # Release expired annotation task locks
        from app.annotations.shared.task_models import AnnotationTask
        
        expired_tasks = db.query(AnnotationTask).filter(
            AnnotationTask.status == 'locked',
            AnnotationTask.lock_expires_at < datetime.utcnow()
        ).all()
        
        for task in expired_tasks:
            task.status = 'available'
            task.annotator_id = None
            task.locked_at = None
            task.lock_expires_at = None
            released_tasks += 1
            logger.info(f"Released expired task lock: task_id={task.id}")
        
        db.commit()
        
        # Release expired resource locks (text resources)
        if annotation_type == "text":
            from app.annotations.text.models import TextResource
            
            expired_resources = db.query(TextResource).filter(
                TextResource.pool_status == 'locked',
                TextResource.locked_at < expiry_threshold
            ).all()
            
            for resource in expired_resources:
                resource.pool_status = 'available'
                resource.locked_by_user_id = None
                resource.locked_at = None
                released_resources += 1
                logger.info(f"Released expired resource lock: resource_id={resource.id}")
            
            db.commit()
        
        # Release expired resource locks (image resources)
        elif annotation_type == "image":
            from app.annotations.image.models import ImageResource
            
            expired_resources = db.query(ImageResource).filter(
                ImageResource.pool_status == 'locked',
                ImageResource.locked_at < expiry_threshold
            ).all()
            
            for resource in expired_resources:
                resource.pool_status = 'available'
                resource.locked_by_user_id = None
                resource.locked_at = None
                released_resources += 1
                logger.info(f"Released expired image resource lock: resource_id={resource.id}")
            
            db.commit()
        
        logger.info(
            f"[release_expired_locks] Released {released_tasks} task locks, "
            f"{released_resources} resource locks for {annotation_type}"
        )
        
    except Exception as e:
        logger.error(f"Failed to release expired locks: {e}")
        db.rollback()
    finally:
        db.close()
    
    return {
        "released_tasks": released_tasks,
        "released_resources": released_resources,
        "annotation_type": annotation_type
    }


def get_task_function_path(task_type: str) -> Optional[str]:
    """
    Get the dotted path to a task function by task type.
    
    Args:
        task_type: The type of task
        
    Returns:
        The dotted path to the function, or None if not found
    """
    return TASK_FUNCTION_MAP.get(task_type)