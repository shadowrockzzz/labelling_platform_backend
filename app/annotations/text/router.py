"""
FastAPI router for text annotation endpoints.
This router is mounted in main.py at prefix="/api/v1/annotations/text"
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.utils.dependencies import get_current_active_user, require_annotator
from app.models.user import User
from app.annotations.text.schemas import (
    ResourceUploadCreate,
    ResourceURLCreate,
    ResourceResponse,
    ResourceWithContentResponse,
    ResourceListResponse,
    TextAnnotationCreate,
    TextAnnotationUpdate,
    TextAnnotationResponse,
    TextAnnotationListResponse,
    ReviewAction,
    QueueTaskResponse,
    QueueListResponse
)
from app.annotations.text import service
from app.annotations.text.crud import (
    get_resource,
    list_resources,
    archive_resource,
    list_annotations,
    update_annotation,
    get_annotation
)
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment

router = APIRouter(prefix="/projects", tags=["Text Annotations"])


def check_project_access(db: Session, project_id: int, user: User) -> Project:
    """Check if user has access to project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Admin has access to all
    if user.role == "admin":
        return project
    
    # Check if user is owner or assigned
    is_owner = project.owner_id == user.id
    is_assigned = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user.id
    ).first()
    
    if not is_owner and not is_assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    return project


# ==================== Resource Endpoints ====================

@router.post("/{project_id}/resources/upload", response_model=ResourceResponse)
async def upload_resource_endpoint(
    project_id: int,
    file: UploadFile = File(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """Upload a text file as a resource."""
    project = check_project_access(db, project_id, current_user)
    
    resource = await service.upload_resource(db, project_id, current_user.id, file, name)
    return resource


@router.post("/{project_id}/resources/url", response_model=ResourceResponse)
async def add_url_resource_endpoint(
    project_id: int,
    resource_data: ResourceURLCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """Add a URL as a text resource."""
    project = check_project_access(db, project_id, current_user)
    
    resource = await service.add_url_resource(
        db, project_id, current_user.id,
        resource_data.external_url, resource_data.name
    )
    return resource


@router.get("/{project_id}/resources", response_model=ResourceListResponse)
def list_resources_endpoint(
    project_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List resources for a project."""
    project = check_project_access(db, project_id, current_user)
    
    resources, total = list_resources(db, project_id, page, limit)
    return ResourceListResponse(
        success=True,
        data=resources,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{project_id}/resources/{resource_id}", response_model=ResourceWithContentResponse)
def get_resource_endpoint(
    project_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a resource with full content."""
    project = check_project_access(db, project_id, current_user)
    
    resource = get_resource(db, resource_id)
    if not resource or resource.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    resource_data = service.get_resource_with_content(db, resource_id)
    return resource_data


@router.delete("/{project_id}/resources/{resource_id}")
def delete_resource_endpoint(
    project_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """Archive/delete a resource (manager/admin only)."""
    project = check_project_access(db, project_id, current_user)
    
    # Only manager or admin can delete
    if current_user.role not in ["admin", "project_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project managers and admins can delete resources"
        )
    
    resource = get_resource(db, resource_id)
    if not resource or resource.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    archive_resource(db, resource_id)
    return {"success": True, "message": "Resource archived successfully"}


# ==================== Annotation Endpoints ====================

@router.post("/{project_id}/annotations", response_model=TextAnnotationResponse)
def create_annotation_endpoint(
    project_id: int,
    annotation_data: TextAnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new annotation. Any authenticated user can create annotations."""
    project = check_project_access(db, project_id, current_user)
    
    annotation = service.create_annotation_service(
        db, project_id, current_user.id, annotation_data.model_dump()
    )
    return annotation


@router.get("/{project_id}/annotations", response_model=TextAnnotationListResponse)
def list_annotations_endpoint(
    project_id: int,
    resource_id: int = Query(None),
    status_filter: str = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List annotations for a project with optional filters."""
    project = check_project_access(db, project_id, current_user)
    
    annotations, total = list_annotations(
        db, project_id, resource_id, status_filter, page, limit
    )
    return TextAnnotationListResponse(
        success=True,
        data=annotations,
        total=total
    )


@router.get("/{project_id}/annotations/{annotation_id}", response_model=TextAnnotationResponse)
def get_annotation_endpoint(
    project_id: int,
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific annotation."""
    project = check_project_access(db, project_id, current_user)
    
    annotation = get_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    return annotation


@router.put("/{project_id}/annotations/{annotation_id}", response_model=TextAnnotationResponse)
def update_annotation_endpoint(
    project_id: int,
    annotation_id: int,
    annotation_data: TextAnnotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """Update an annotation (annotator only)."""
    project = check_project_access(db, project_id, current_user)
    
    annotation = get_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Only the annotator can update their own annotation
    if annotation.annotator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own annotations"
        )
    
    annotation = update_annotation(db, annotation_id, annotation_data.model_dump(exclude_unset=True))
    return annotation


@router.post("/{project_id}/annotations/{annotation_id}/submit", response_model=TextAnnotationResponse)
def submit_annotation_endpoint(
    project_id: int,
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """Submit an annotation for review."""
    project = check_project_access(db, project_id, current_user)
    
    annotation = service.submit_annotation_service(db, annotation_id, current_user.id)
    return annotation


@router.post("/{project_id}/annotations/{annotation_id}/review", response_model=TextAnnotationResponse)
def review_annotation_endpoint(
    project_id: int,
    annotation_id: int,
    review_data: ReviewAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """Review an annotation (approve/reject)."""
    project = check_project_access(db, project_id, current_user)
    
    annotation = service.review_annotation_service(
        db, annotation_id, current_user.id,
        review_data.action, review_data.comment
    )
    return annotation


# ==================== Queue Stub Endpoints ====================

@router.get("/{project_id}/queue", response_model=QueueListResponse)
def get_queue_tasks_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """
    Get queue tasks for a project's text annotation queue.
    Each project has separate queues for each annotation type.
    Only admin/PM can view queue.
    """
    project = check_project_access(db, project_id, current_user)
    
    # Only manager or admin can view queue
    if current_user.role not in ["admin", "project_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project managers and admins can view queue"
        )
    
    from app.annotations.text.crud import get_queue_tasks
    # Get tasks for this project's text annotation queue
    tasks = get_queue_tasks(db, project_id, annotation_type="text")
    
    return QueueListResponse(
        success=True,
        data=tasks
    )
