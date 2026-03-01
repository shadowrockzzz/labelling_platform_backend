from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AnnotationStatus(str, Enum):
    """Status enum for all annotation types."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class AnnotationType(str, Enum):
    """Supported annotation types."""
    TEXT = "text"
    IMAGE = "image"
    # VIDEO = "video"        # to be added later
    # LIDAR = "lidar"
    # RLHF = "rlhf"
    # CODE = "code"


class QueueTracker:
    """
    Helper class for tracking annotation events in the Redis queue.
    
    Provides a simple interface to track annotation lifecycle events
    (created, updated, submitted, reviewed) in the queue system.
    
    Usage:
        tracker = QueueTracker(db_session, annotation_type="image")
        tracker.track(project_id=1, annotation_id=5, task_type="annotation_created", payload={...})
    """
    
    def __init__(self, db_session, annotation_type: str):
        """
        Initialize queue tracker.
        
        Args:
            db_session: SQLAlchemy database session
            annotation_type: Type of annotation ('text', 'image', 'video', etc.)
        """
        self.db = db_session
        self.annotation_type = annotation_type
    
    def track(
        self,
        project_id: int,
        task_type: str,
        resource_id: Optional[int] = None,
        annotation_id: Optional[int] = None,
        payload: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Track an annotation event in the queue.
        
        Args:
            project_id: Project ID
            task_type: Event type (annotation_created, annotation_submitted, etc.)
            resource_id: Resource ID (optional)
            annotation_id: Annotation ID (optional)
            payload: Additional event data (optional)
            
        Returns:
            Queue task dict or None if tracking failed
        """
        try:
            from app.core.queue import AnnotationQueue
            
            queue = AnnotationQueue(self.db, annotation_type=self.annotation_type)
            result = queue.enqueue(
                project_id=project_id,
                resource_id=resource_id,
                task_type=task_type,
                payload=payload or {},
                annotation_id=annotation_id,
            )
            logger.info(
                f"[QueueTracker] Tracked {task_type} for {self.annotation_type} "
                f"annotation {annotation_id} in project {project_id}"
            )
            return result
        except Exception as e:
            # Queue tracking failure must NOT crash the API
            # Rollback any partial queue transaction to keep session clean
            logger.error(f"[QueueTracker] Failed to track {task_type}: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass
            return None
    
    def track_created(self, project_id: int, annotation_id: int, resource_id: Optional[int] = None, **kwargs) -> Optional[Dict]:
        """Track annotation creation."""
        return self.track(project_id, "annotation_created", resource_id, annotation_id, kwargs)
    
    def track_updated(self, project_id: int, annotation_id: int, resource_id: Optional[int] = None, **kwargs) -> Optional[Dict]:
        """Track annotation update."""
        return self.track(project_id, "annotation_updated", resource_id, annotation_id, kwargs)
    
    def track_submitted(self, project_id: int, annotation_id: int, resource_id: Optional[int] = None, **kwargs) -> Optional[Dict]:
        """Track annotation submission for review."""
        return self.track(project_id, "annotation_submitted", resource_id, annotation_id, kwargs)
    
    def track_reviewed(self, project_id: int, annotation_id: int, action: str, resource_id: Optional[int] = None, **kwargs) -> Optional[Dict]:
        """Track annotation review (approve/reject)."""
        payload = {"action": action, **kwargs}
        return self.track(project_id, "annotation_reviewed", resource_id, annotation_id, payload)
    
    def track_resource_uploaded(self, project_id: int, resource_id: int, **kwargs) -> Optional[Dict]:
        """Track resource upload."""
        return self.track(project_id, "resource_uploaded", resource_id, payload=kwargs)


class BaseAnnotationProcessor(ABC):
    """
    Abstract base class that every annotation type must implement.
    Ensures consistent interface across all annotation types.
    """
    
    @abstractmethod
    def validate_input(self, data: Dict) -> bool:
        """
        Validate input data for this annotation type.
        
        Args:
            data: Raw input data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def process_annotation(self, annotation_data: Dict) -> Dict:
        """
        Process annotation data according to type-specific rules.
        
        Args:
            annotation_data: Raw annotation data
            
        Returns:
            Processed annotation data ready for storage
        """
        pass
    
    @abstractmethod
    def get_output_path(self, project_id: int, annotation_id: int) -> str:
        """
        Generate S3 path for annotation output.
        
        Args:
            project_id: Project identifier
            annotation_id: Annotation identifier
            
        Returns:
            S3 key string for output file
        """
        pass