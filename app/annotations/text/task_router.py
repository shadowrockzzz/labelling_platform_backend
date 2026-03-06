"""
API router for text annotation tasks.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_annotator, require_project_manager
from app.models.user import User
from app.annotations.shared.task_crud import AnnotationTaskCRUD
from app.annotations.shared.task_schemas import (
    AnnotationTaskResponse,
    AnnotationTaskWithResource,
    AnnotationTaskClaimResponse,
    AnnotationTaskSkipResponse,
    AnnotationTaskSubmitResponse,
    AnnotationTaskStats,
    SeedTasksRequest,
    SeedTasksResponse,
)
from app.annotations.text.models import TextResource
from app.annotations.text.crud import get_resource

router = APIRouter(prefix="/tasks", tags=["Text Annotation Tasks"])


def get_task_crud(db: Session = Depends(get_db)) -> AnnotationTaskCRUD:
    """Get task CRUD instance for text resources."""
    return AnnotationTaskCRUD(db, resource_type="text")


@router.post("/claim", response_model=AnnotationTaskClaimResponse)
def claim_task(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_crud: AnnotationTaskCRUD = Depends(get_task_crud),
):
    """
    Claim the next available annotation task.
    
    If user already has a locked task, returns that task instead.
    Task is locked for 2 hours.
    """
    def resource_getter(resource_id):
        return get_resource(db, resource_id)
    
    return task_crud.claim_task_fallback(project_id, int(current_user.id), resource_getter)


@router.get("/my-active", response_model=Optional[AnnotationTaskWithResource])
def get_my_active_task(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_crud: AnnotationTaskCRUD = Depends(get_task_crud),
):
    """Get the current user's active task in this project, if any."""
    def resource_getter(resource_id):
        return get_resource(db, resource_id)
    
    return task_crud.get_my_active_task(project_id, int(current_user.id), resource_getter)


@router.get("/stats", response_model=AnnotationTaskStats)
def get_task_stats(
    project_id: int,
    task_crud: AnnotationTaskCRUD = Depends(get_task_crud),
):
    """Get statistics for tasks in a project."""
    return task_crud.get_task_stats(project_id)


@router.get("/{task_id}", response_model=AnnotationTaskWithResource)
def get_task(
    project_id: int,
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_crud: AnnotationTaskCRUD = Depends(get_task_crud),
):
    """
    Get a specific task by ID with resource data.
    
    User must own the task or be a reviewer/admin.
    """
    task = task_crud.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check ownership or reviewer permission
    if task.annotator_id != current_user.id:
        if current_user.role not in ["reviewer", "admin", "project_manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this task"
            )
    
    def resource_getter(resource_id):
        return get_resource(db, resource_id)
    
    return task_crud.get_task_with_resource(task_id, resource_getter)


@router.post("/{task_id}/skip", response_model=AnnotationTaskSkipResponse)
def skip_task(
    project_id: int,
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    task_crud: AnnotationTaskCRUD = Depends(get_task_crud),
):
    """
    Skip a task, returning it to the pool.
    
    Only the task owner can skip it.
    """
    success, message = task_crud.skip_task(task_id, int(current_user.id))
    return AnnotationTaskSkipResponse(
        message=message,
        task_id=task_id
    )


@router.post("/{task_id}/submit", response_model=AnnotationTaskSubmitResponse)
def submit_task(
    project_id: int,
    task_id: UUID,
    annotation_id: int,
    current_user: User = Depends(get_current_active_user),
    task_crud: AnnotationTaskCRUD = Depends(get_task_crud),
):
    """
    Mark a task as submitted after annotation is created.
    
    Only the task owner can submit it.
    """
    success, message = task_crud.submit_task(task_id, int(current_user.id), annotation_id)
    return AnnotationTaskSubmitResponse(
        message=message,
        task_id=task_id,
        annotation_id=annotation_id
    )


@router.post("/seed", response_model=SeedTasksResponse)
def seed_tasks(
    project_id: int,
    request: Optional[SeedTasksRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_manager),
    task_crud: AnnotationTaskCRUD = Depends(get_task_crud),
):
    """
    Create tasks from existing resources.
    
    Admin/Project Manager only.
    If resource_ids not specified, seeds all resources in the project.
    """
    # Get all resource IDs if not specified
    if not request or not request.resource_ids:
        resources = db.query(TextResource.id).filter(
            TextResource.project_id == project_id
        ).all()
        resource_ids = [r[0] for r in resources]
    else:
        resource_ids = request.resource_ids
    
    return task_crud.seed_tasks_from_resources(project_id, resource_ids)