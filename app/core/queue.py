"""
AnnotationQueue: Redis-backed queue using rq.

This module provides a drop-in replacement for TextQueueStub that uses
Redis/rq for real async processing while maintaining PostgreSQL as an
audit log for compliance and history.

Supports all annotation types: text, image, video, audio, etc.
The annotation_type is passed as a parameter to the constructor.

Usage:
    queue = AnnotationQueue(db_session, annotation_type="text")
    queue.enqueue(project_id, resource_id, task_type, payload)
"""
from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AnnotationQueue:
    """
    Redis-backed queue for annotation tasks with PostgreSQL audit logging.
    
    Drop-in replacement for TextQueueStub with the same interface.
    
    Features:
    - Enqueues real jobs to Redis via rq
    - Writes audit records to PostgreSQL text_annotation_queue
    - Supports all annotation types (text, image, video, etc.)
    - Gracefully handles Redis failures (logs error, continues)
    
    Example:
        queue = AnnotationQueue(db, annotation_type="text")
        result = queue.enqueue(
            project_id=1,
            resource_id=5,
            task_type="resource_uploaded",
            payload={"filename": "doc.txt"}
        )
    """

    def __init__(self, db_session: Session, annotation_type: str = "text"):
        """
        Initialize the queue.
        
        Args:
            db_session: SQLAlchemy database session
            annotation_type: Type of annotation ('text', 'image', 'video', etc.)
        """
        self.db = db_session
        self.annotation_type = annotation_type

    def enqueue(
        self,
        project_id: int,
        resource_id: Optional[int],
        task_type: str,
        payload: dict,
        annotation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Enqueue a task to Redis and write audit log to PostgreSQL.
        
        Args:
            project_id: Project ID
            resource_id: Resource ID (optional for some tasks)
            task_type: Type of task ('resource_uploaded', 'annotation_created', etc.)
            payload: Task data dictionary
            annotation_id: Annotation ID (optional)
            
        Returns:
            Dict with task id, status, task_type, annotation_type, project_id
        """
        from app.annotations.text.models import TextAnnotationQueue
        from app.workers.annotation_tasks import get_task_function_path
        
        # Step 1: Write audit log entry FIRST (so we have an ID)
        db_entry = TextAnnotationQueue(
            project_id=project_id,
            resource_id=resource_id,
            annotation_id=annotation_id,
            annotation_type=self.annotation_type,
            task_type=task_type,
            status="pending",
            payload=payload or {},
            created_at=datetime.utcnow(),
        )
        self.db.add(db_entry)
        self.db.commit()
        self.db.refresh(db_entry)
        
        logger.info(
            f"[Queue] Enqueued {task_type} for project {project_id}, "
            f"type={self.annotation_type}, audit_id={db_entry.id}"
        )

        # Step 2: Enqueue to Redis
        try:
            from app.core.redis_client import get_queue_for_task
            
            func_path = get_task_function_path(task_type)
            if func_path:
                q = get_queue_for_task(task_type)
                job = q.enqueue(
                    func_path,
                    annotation_type=self.annotation_type,
                    project_id=project_id,
                    resource_id=resource_id,
                    annotation_id=annotation_id,
                    payload=payload,
                    job_id=f"{task_type}_{self.annotation_type}_{db_entry.id}",
                )
                db_entry.rq_job_id = job.id
                self.db.commit()
                logger.info(f"[Queue] Redis job {job.id} enqueued for audit {db_entry.id}")
            else:
                logger.warning(f"[Queue] No worker function for task_type='{task_type}'")
        except Exception as e:
            # Redis failure must NOT crash the API request
            # The audit log row is already written; the job can be retried manually
            logger.error(f"[Queue] Failed to enqueue Redis job: {e}")

        return {
            "id": db_entry.id,
            "status": "pending",
            "task_type": task_type,
            "annotation_type": self.annotation_type,
            "project_id": project_id,
            "rq_job_id": db_entry.rq_job_id,
        }

    def get_pending_tasks(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all pending/processing tasks for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of task dictionaries
        """
        from app.annotations.text.models import TextAnnotationQueue
        
        tasks = (
            self.db.query(TextAnnotationQueue)
            .filter(
                TextAnnotationQueue.project_id == project_id,
                TextAnnotationQueue.annotation_type == self.annotation_type,
                TextAnnotationQueue.status.in_(["pending", "processing"]),
            )
            .order_by(TextAnnotationQueue.created_at.desc())
            .all()
        )
        
        return [self._task_to_dict(task) for task in tasks]

    def get_all_tasks(self, project_id: int, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Get all tasks (any status) for a project - full audit log.
        
        Args:
            project_id: Project ID
            limit: Maximum number of tasks to return
            
        Returns:
            List of task dictionaries
        """
        from app.annotations.text.models import TextAnnotationQueue
        
        tasks = (
            self.db.query(TextAnnotationQueue)
            .filter(
                TextAnnotationQueue.project_id == project_id,
                TextAnnotationQueue.annotation_type == self.annotation_type,
            )
            .order_by(TextAnnotationQueue.created_at.desc())
            .limit(limit)
            .all()
        )
        
        return [self._task_to_dict(task) for task in tasks]

    def complete_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Mark a task as done.
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict with id and status, or None if not found
        """
        from app.annotations.text.models import TextAnnotationQueue
        
        task = self.db.get(TextAnnotationQueue, task_id)
        if task:
            task.status = "done"
            task.processed_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"[Queue] Completed task {task_id}")
            return {"id": task.id, "status": "done"}
        return None

    def fail_task(self, task_id: int, error_message: str) -> Optional[Dict[str, Any]]:
        """
        Mark a task as failed with error message.
        
        Args:
            task_id: Task ID
            error_message: Error description
            
        Returns:
            Dict with id, status, and error, or None if not found
        """
        from app.annotations.text.models import TextAnnotationQueue
        
        task = self.db.get(TextAnnotationQueue, task_id)
        if task:
            task.status = "failed"
            task.error_message = error_message
            task.processed_at = datetime.utcnow()
            self.db.commit()
            logger.error(f"[Queue] Failed task {task_id}: {error_message}")
            return {"id": task.id, "status": "failed", "error": error_message}
        return None

    def get_redis_job_status(self, rq_job_id: str) -> Optional[str]:
        """
        Get live status of a job directly from Redis.
        
        Args:
            rq_job_id: Redis Queue job ID
            
        Returns:
            Status string ('queued', 'started', 'finished', 'failed') or None
        """
        if not rq_job_id:
            return None
            
        try:
            from app.core.redis_client import get_redis_connection
            from rq.job import Job
            
            redis_conn = get_redis_connection()
            job = Job.fetch(rq_job_id, connection=redis_conn)
            return job.get_status().value
        except Exception as e:
            logger.debug(f"Could not fetch Redis job status: {e}")
            return None

    def _task_to_dict(self, task) -> Dict[str, Any]:
        """
        Convert a task model to dictionary with optional Redis status.
        
        Args:
            task: TextAnnotationQueue model instance
            
        Returns:
            Dictionary representation of the task
        """
        result = {
            "id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "annotation_type": task.annotation_type,
            "resource_id": task.resource_id,
            "annotation_id": task.annotation_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "processed_at": task.processed_at.isoformat() if task.processed_at else None,
            "error_message": task.error_message,
            "payload": task.payload,
            "rq_job_id": task.rq_job_id,
        }
        
        # Add live Redis status if available
        if task.rq_job_id:
            redis_status = self.get_redis_job_status(task.rq_job_id)
            if redis_status:
                result["redis_status"] = redis_status
        
        return result


# Alias for backward compatibility with existing code that imports TextQueueStub
TextQueueStub = AnnotationQueue