"""
Redis connection and queue instances.

This module provides singleton Redis connections and named queues for the
annotation platform. Import these throughout the app instead of creating
new connections.

Architecture:
- annotations queue: For resource uploads and annotation creation
- reviews queue: For review workflow (submit, approve, reject)
- default queue: For exports and miscellaneous tasks

Supports all annotation types: text, image, video, audio, etc.
The annotation_type is passed as a parameter to each job, not routed to different queues.
"""
import logging
import redis
from rq import Queue
from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton Redis connection
_redis_conn = None


def get_redis_connection():
    """
    Get or create the singleton Redis connection.
    
    Returns:
        redis.Redis: The Redis connection instance
    """
    global _redis_conn
    if _redis_conn is None:
        try:
            _redis_conn = redis.from_url(settings.REDIS_URL, decode_responses=False)
            # Test connection
            _redis_conn.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_URL}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_conn = None
            raise
    return _redis_conn


def get_queue(name: str) -> Queue:
    """
    Get a queue by name.
    
    Args:
        name: Queue name ('annotations', 'reviews', 'default')
        
    Returns:
        Queue: The rq Queue instance
    """
    conn = get_redis_connection()
    return Queue(name, connection=conn)


# Pre-defined queue instances for common use
# These are lazily initialized when first accessed
class QueueRegistry:
    """Registry of named queues with lazy initialization."""
    
    _queues = {}
    
    @classmethod
    def get_annotations_queue(cls) -> Queue:
        """Get the annotations queue (resource uploads, annotation creation)."""
        if "annotations" not in cls._queues:
            cls._queues["annotations"] = get_queue("annotations")
        return cls._queues["annotations"]
    
    @classmethod
    def get_reviews_queue(cls) -> Queue:
        """Get the reviews queue (submit, approve, reject)."""
        if "reviews" not in cls._queues:
            cls._queues["reviews"] = get_queue("reviews")
        return cls._queues["reviews"]
    
    @classmethod
    def get_default_queue(cls) -> Queue:
        """Get the default queue (exports, misc)."""
        if "default" not in cls._queues:
            cls._queues["default"] = get_queue("default")
        return cls._queues["default"]
    
    @classmethod
    def get_queue_by_task_type(cls, task_type: str) -> Queue:
        """
        Get the appropriate queue for a task type.
        
        Routing logic:
        - resource_uploaded, annotation_created → annotations queue
        - annotation_submitted, annotation_approved, annotation_rejected → reviews queue
        - output, * (default) → default queue
        
        Args:
            task_type: The type of task
            
        Returns:
            Queue: The appropriate queue for the task
        """
        routing = {
            "resource_uploaded": "annotations",
            "annotation_created": "annotations",
            "annotation_submitted": "reviews",
            "annotation_approved": "reviews",
            "annotation_rejected": "reviews",
            "output": "default",
        }
        queue_name = routing.get(task_type, "default")
        
        if queue_name == "annotations":
            return cls.get_annotations_queue()
        elif queue_name == "reviews":
            return cls.get_reviews_queue()
        else:
            return cls.get_default_queue()


# Convenience functions that match the expected interface
def get_queue_for_task(task_type: str) -> Queue:
    """
    Get the appropriate queue for a task type.
    
    This is the main entry point for getting queues.
    
    Args:
        task_type: The type of task (e.g., 'resource_uploaded', 'annotation_submitted')
        
    Returns:
        Queue: The appropriate queue for the task
    """
    return QueueRegistry.get_queue_by_task_type(task_type)


# For backward compatibility and dependency injection
redis_conn = None  # Will be initialized on first use


def get_redis():
    """
    Get Redis connection for dependency injection in FastAPI.
    
    Use this in Depends() if you need direct Redis access.
    """
    return get_redis_connection()