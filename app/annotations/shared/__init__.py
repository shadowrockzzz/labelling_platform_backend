"""
Shared annotation task module.

Provides task queue functionality for both text and image annotations.
"""

from .task_models import AnnotationTask
from .task_schemas import (
    AnnotationTaskBase,
    AnnotationTaskCreate,
    AnnotationTaskResponse,
    AnnotationTaskWithResource,
    AnnotationTaskStats,
)
from .task_crud import AnnotationTaskCRUD

__all__ = [
    "AnnotationTask",
    "AnnotationTaskBase",
    "AnnotationTaskCreate",
    "AnnotationTaskResponse",
    "AnnotationTaskWithResource",
    "AnnotationTaskStats",
    "AnnotationTaskCRUD",
]