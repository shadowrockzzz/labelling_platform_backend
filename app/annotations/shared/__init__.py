"""
Shared annotation task module.

Provides task queue functionality for both text and image annotations.
Also provides multi-level review workflow with UUID tracking.
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

# Review task models and CRUD
from .review_models import ReviewTask
from .review_schemas import (
    ReviewTaskBase,
    ReviewTaskCreate,
    ReviewTaskResponse,
    ReviewActionRequest,
    StartReviewRequest,
    StartReviewResponse,
    ReviewChainEntry,
    FinalOutputResponse,
    ReviewPoolStats,
)
from .review_crud import (
    get_review_task,
    get_review_tasks_by_annotation,
    get_available_review_tasks,
    get_or_create_review_task,
    lock_review_task,
    unlock_review_task,
    approve_review_task,
    reject_review_task,
    mark_review_task_edited,
    get_next_review_task_for_reviewer,
    release_expired_locks,
    build_review_chain_entry,
)
from .review_router import create_review_router

__all__ = [
    # Annotation Task
    "AnnotationTask",
    "AnnotationTaskBase",
    "AnnotationTaskCreate",
    "AnnotationTaskResponse",
    "AnnotationTaskWithResource",
    "AnnotationTaskStats",
    "AnnotationTaskCRUD",
    # Review Task
    "ReviewTask",
    "ReviewTaskBase",
    "ReviewTaskCreate",
    "ReviewTaskResponse",
    "ReviewActionRequest",
    "StartReviewRequest",
    "StartReviewResponse",
    "ReviewChainEntry",
    "FinalOutputResponse",
    "ReviewPoolStats",
    # Review CRUD functions
    "get_review_task",
    "get_review_tasks_by_annotation",
    "get_available_review_tasks",
    "get_or_create_review_task",
    "lock_review_task",
    "unlock_review_task",
    "approve_review_task",
    "reject_review_task",
    "mark_review_task_edited",
    "get_next_review_task_for_reviewer",
    "release_expired_locks",
    "build_review_chain_entry",
    # Review router factory
    "create_review_router",
]
