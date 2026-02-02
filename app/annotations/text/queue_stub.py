"""
Queue stub for text annotation.
Simulates a message queue locally until RabbitMQ is wired in.
The interface matches what a real RabbitMQ publisher would look like.
"""
from sqlalchemy.orm import Session
from app.annotations.text.crud import enqueue_task as enqueue_task_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextQueueStub:
    """
    Simulates a message queue using local database.
    Each queue is identified by project_id AND annotation_type combination.
    In production, replace this with RabbitMQ/Redis - the interface stays the same.
    """
    
    def __init__(self, db_session: Session, annotation_type: str = "text"):
        """
        Initialize queue stub.
        
        Args:
            db_session: SQLAlchemy database session
            annotation_type: Type of annotation (e.g., 'text', 'image', 'video')
        """
        self.db = db_session
        self.annotation_type = annotation_type
    
    def enqueue(self, project_id: int, resource_id: int, task_type: str, payload: dict, annotation_id: int = None) -> dict:
        """
        Saves task to text_annotation_queue table with annotation_type.
        
        In production, this becomes:
            rabbitmq_client.publish(exchange, routing_key, payload)
        
        Args:
            project_id: Project identifier
            resource_id: Resource identifier (optional for some tasks)
            task_type: Type of task (e.g., 'resource_uploaded', 'annotation_submitted')
            payload: Task data dictionary
            annotation_id: Annotation identifier (optional)
            
        Returns:
            Dict with task id, status, and annotation_type
        """
        logger.info(f"[QUEUE STUB] Enqueued {task_type} for project {project_id}, annotation_type={self.annotation_type}")
        
        task = enqueue_task_db(
            db=self.db,
            project_id=project_id,
            resource_id=resource_id,
            task_type=task_type,
            payload=payload,
            annotation_type=self.annotation_type,
            annotation_id=annotation_id
        )
        
        return {
            "id": task.id,
            "status": "pending",
            "task_type": task_type,
            "annotation_type": self.annotation_type,
            "project_id": project_id
        }
    
    def get_pending_tasks(self, project_id: int) -> list[dict]:
        """
        Returns all pending tasks for a project and annotation_type.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of pending tasks for this (project_id, annotation_type) combination
            
        In production, this would query RabbitMQ for pending messages.
        """
        from app.annotations.text.crud import get_queue_tasks
        
        tasks = get_queue_tasks(self.db, project_id, self.annotation_type, status="pending")
        return [
            {
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "annotation_type": task.annotation_type,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "payload": task.payload
            }
            for task in tasks
        ]
    
    def complete_task(self, task_id: int) -> dict:
        """
        Marks task as done.
        
        In production, this would acknowledge the RabbitMQ message.
        """
        from app.annotations.text.crud import mark_task_done
        
        task = mark_task_done(self.db, task_id)
        if task:
            logger.info(f"[QUEUE STUB] Completed task {task_id}")
            return {
                "id": task.id,
                "status": "done"
            }
        return None
    
    def fail_task(self, task_id: int, error_message: str) -> dict:
        """
        Marks task as failed with error.
        
        In production, this would dead-letter the RabbitMQ message.
        """
        from app.annotations.text.crud import mark_task_failed
        
        task = mark_task_failed(self.db, task_id, error_message)
        if task:
            logger.error(f"[QUEUE STUB] Failed task {task_id}: {error_message}")
            return {
                "id": task.id,
                "status": "failed",
                "error": error_message
            }
        return None