"""
FastAPI router for text annotation endpoints.
This router is mounted in main.py at prefix="/api/v1/annotations/text"
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
    QueueListResponse,
    SpanCreate,
    SpanUpdate,
    ReviewCorrectionCreate,
    ReviewCorrectionUpdate,
    ReviewCorrectionResponse,
    ReviewCorrectionListResponse
)
from app.annotations.text import service
from app.annotations.text.crud import (
    get_resource,
    list_resources,
    archive_resource,
    list_annotations,
    update_annotation,
    get_annotation,
    create_review_correction,
    get_review_correction,
    list_review_corrections,
    update_review_correction,
    accept_review_correction
)
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment

router = APIRouter(prefix="/projects", tags=["Text Annotations"])


# ==================== Annotation Response Helper ====================

def annotation_to_response(annotation) -> dict:
    """Convert annotation ORM object to response dict with annotator/reviewer names."""
    logger.debug(f"[annotation_to_response] Processing annotation ID: {annotation.id}")
    logger.debug(f"[annotation_to_response] annotator_id: {annotation.annotator_id}")
    logger.debug(f"[annotation_to_response] reviewer_id: {annotation.reviewer_id}")
    
    response = {
        'id': annotation.id,
        'resource_id': annotation.resource_id,
        'project_id': annotation.project_id,
        'annotator_id': annotation.annotator_id,
        'reviewer_id': annotation.reviewer_id,
        'annotation_type': annotation.annotation_type,
        'annotation_sub_type': annotation.annotation_sub_type,
        'status': annotation.status,
        'label': annotation.label,
        'span_start': annotation.span_start,
        'span_end': annotation.span_end,
        'annotation_data': annotation.annotation_data,
        'review_comment': annotation.review_comment,
        'reviewed_at': annotation.reviewed_at,
        'created_at': annotation.created_at,
        'updated_at': annotation.updated_at,
        'submitted_at': annotation.submitted_at,
        'annotator_name': None,
        'reviewer_name': None
    }
    
    # Get annotator name from loaded relationship
    logger.debug(f"[annotation_to_response] annotation.annotator exists: {annotation.annotator is not None}")
    if annotation.annotator:
        logger.debug(f"[annotation_to_response] annotator.full_name: '{annotation.annotator.full_name}'")
        logger.debug(f"[annotation_to_response] annotator.email: '{annotation.annotator.email}'")
        response['annotator_name'] = annotation.annotator.full_name or annotation.annotator.email
        logger.debug(f"[annotation_to_response] Set annotator_name to: '{response['annotator_name']}'")
    else:
        logger.warning(f"[annotation_to_response] annotator relationship is None for annotation {annotation.id}")
    
    # Get reviewer name if available
    if annotation.reviewer:
        response['reviewer_name'] = annotation.reviewer.full_name or annotation.reviewer.email
    
    return response


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

@router.get("/{project_id}/queue/unannotated")
def get_unannotated_resources_endpoint(
    project_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get text resources that haven't been annotated by the current user.
    
    Useful for queue-based annotation workflow where annotators only see
    resources they need to annotate, not ones they've already worked on.
    """
    project = check_project_access(db, project_id, current_user)
    
    from app.annotations.text.crud import get_unannotated_resources
    resources = get_unannotated_resources(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        limit=limit
    )
    
    return {
        "success": True,
        "data": resources,
        "total": len(resources)
    }


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
    # Note: Relaxing access restriction for development
    # In production, you may want to use check_project_access(db, project_id, current_user)
    # For now, just verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    annotation = service.create_annotation_service(
        db, project_id, current_user.id, annotation_data.model_dump()
    )
    return annotation


@router.get("/{project_id}/annotations")
def list_annotations_endpoint(
    project_id: int,
    resource_id: int = Query(None),
    status_filter: str = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List annotations for a project with optional filters."""
    logger.info(f"[list_annotations] Fetching annotations for project {project_id}")
    project = check_project_access(db, project_id, current_user)
    
    annotations, total = list_annotations(
        db, project_id, resource_id, status_filter, page, limit
    )
    
    logger.info(f"[list_annotations] Found {len(annotations)} annotations (total: {total})")
    
    # Transform annotations to include annotator/reviewer names
    data = []
    for ann in annotations:
        logger.debug(f"[list_annotations] Processing annotation {ann.id}, annotator_id={ann.annotator_id}")
        response = annotation_to_response(ann)
        logger.debug(f"[list_annotations] Annotation {ann.id} annotator_name: {response.get('annotator_name')}")
        data.append(response)
    
    logger.info(f"[list_annotations] Returning {len(data)} annotations")
    return {
        "success": True,
        "data": data,
        "total": total
    }


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
    
    # If annotation is reviewed (approved or rejected), reset to draft when edited
    update_data = annotation_data.model_dump(exclude_unset=True)
    if annotation.status in ["approved", "rejected"]:
        # Reset to draft and clear review fields
        update_data["status"] = "draft"
        update_data["reviewer_id"] = None
        update_data["review_comment"] = None
        update_data["reviewed_at"] = None
        # Keep the original created_at and annotator_id
    
    annotation = update_annotation(db, annotation_id, update_data)
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
        data=tasks,
        total=len(tasks)
    )


# ==================== Single-Annotation Model Endpoints (New) ====================

@router.post("/{project_id}/resources/{resource_id}/spans", response_model=TextAnnotationResponse)
def add_span_endpoint(
    project_id: int,
    resource_id: int,
    span_data: SpanCreate,
    annotation_sub_type: str = Query("ner", description="Annotation sub-type (ner, pos, sentiment, etc.)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """
    Add a span to an annotation for a resource.
    
    Creates annotation if it doesn't exist, otherwise appends to existing annotation.
    This is the main endpoint for the single-annotation model.
    """
    project = check_project_access(db, project_id, current_user)
    
    annotation = service.add_span_to_annotation_service(
        db, project_id, current_user.id, resource_id,
        annotation_sub_type, span_data.model_dump()
    )
    return annotation


@router.get("/{project_id}/resources/{resource_id}/annotation", response_model=TextAnnotationResponse)
def get_annotation_with_spans_endpoint(
    project_id: int,
    resource_id: int,
    user_id: int = Query(None, description="Filter by annotator ID (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get annotation for a resource with all spans.
    
    Returns the annotation containing all spans for the resource.
    If user_id is provided, returns that user's annotation.
    Otherwise returns the most recent annotation.
    """
    project = check_project_access(db, project_id, current_user)
    
    annotation = service.get_annotation_with_spans_service(
        db, project_id, resource_id, user_id
    )
    
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No annotation found for this resource"
        )
    
    return annotation


@router.put("/{project_id}/annotations/{annotation_id}/spans/{span_id}", response_model=TextAnnotationResponse)
def update_span_endpoint(
    project_id: int,
    annotation_id: int,
    span_id: str,
    span_data: SpanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """
    Update a specific span within an annotation.
    
    Allows editing individual spans without affecting others.
    """
    project = check_project_access(db, project_id, current_user)
    
    annotation = service.update_span_in_annotation_service(
        db, project_id, current_user.id, annotation_id,
        span_id, span_data.model_dump(exclude_unset=True)
    )
    
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation or span not found"
        )
    
    return annotation


@router.delete("/{project_id}/annotations/{annotation_id}/spans/{span_id}", response_model=TextAnnotationResponse)
def delete_span_endpoint(
    project_id: int,
    annotation_id: int,
    span_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """
    Remove a specific span from an annotation.
    
    Deletes only the specified span, leaving other spans intact.
    """
    project = check_project_access(db, project_id, current_user)
    
    annotation = service.remove_span_from_annotation_service(
        db, project_id, current_user.id, annotation_id, span_id
    )
    
    return annotation


# ==================== Review Correction Endpoints ====================

@router.post("/{project_id}/annotations/{annotation_id}/corrections", response_model=ReviewCorrectionResponse)
def create_correction_endpoint(
    project_id: int,
    annotation_id: int,
    correction_data: ReviewCorrectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """
    Create a review correction.
    
    Allows reviewers to suggest changes to annotations without directly modifying them.
    The original annotator can then accept or reject the correction.
    """
    project = check_project_access(db, project_id, current_user)
    
    # Verify annotation exists and belongs to this project
    annotation = get_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Only reviewers or admins can create corrections
    if current_user.role not in ["admin", "reviewer", "project_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only reviewers can create corrections"
        )
    
    correction = create_review_correction(
        db,
        annotation_id,
        current_user.id,
        correction_data.corrected_data,
        correction_data.comment
    )
    
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create correction"
        )
    
    return correction


@router.get("/{project_id}/annotations/{annotation_id}/corrections", response_model=ReviewCorrectionListResponse)
def list_corrections_endpoint(
    project_id: int,
    annotation_id: int,
    status_filter: str = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all review corrections for an annotation.
    
    Can filter by status (pending, accepted, rejected).
    """
    project = check_project_access(db, project_id, current_user)
    
    # Verify annotation exists
    annotation = get_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    corrections, total = list_review_corrections(
        db,
        annotation_id=annotation_id,
        status=status_filter,
        page=page,
        limit=limit
    )
    
    return ReviewCorrectionListResponse(
        success=True,
        data=corrections,
        total=total
    )


@router.get("/{project_id}/corrections/{correction_id}", response_model=ReviewCorrectionResponse)
def get_correction_endpoint(
    project_id: int,
    correction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific review correction."""
    project = check_project_access(db, project_id, current_user)
    
    correction = get_review_correction(db, correction_id)
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    # Verify the correction is for an annotation in this project
    annotation = get_annotation(db, correction.annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found in this project"
        )
    
    return correction


@router.put("/{project_id}/corrections/{correction_id}", response_model=ReviewCorrectionResponse)
def update_correction_endpoint(
    project_id: int,
    correction_id: int,
    update_data: ReviewCorrectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """
    Update a review correction (accept or reject).
    
    Only the original annotator can accept/reject corrections to their annotation.
    """
    project = check_project_access(db, project_id, current_user)
    
    correction = get_review_correction(db, correction_id)
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    # Verify the correction is for an annotation in this project
    annotation = get_annotation(db, correction.annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found in this project"
        )
    
    # Only the original annotator can respond to corrections
    if annotation.annotator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the original annotator can respond to corrections"
        )
    
    # Only pending corrections can be updated
    if correction.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending corrections can be updated"
        )
    
    updated_correction = update_review_correction(
        db,
        correction_id,
        update_data.status,
        update_data.annotator_response
    )
    
    if not updated_correction:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update correction"
        )
    
    return updated_correction


@router.post("/{project_id}/corrections/{correction_id}/accept", response_model=TextAnnotationResponse)
def accept_correction_endpoint(
    project_id: int,
    correction_id: int,
    annotator_response: str = Query(None, description="Optional response from annotator"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator)
):
    """
    Accept a review correction and apply it to the original annotation.
    
    Accepting applies the corrected data to the original annotation
    and marks the correction as accepted.
    """
    project = check_project_access(db, project_id, current_user)
    
    correction = get_review_correction(db, correction_id)
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    # Verify the correction is for an annotation in this project
    annotation = get_annotation(db, correction.annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found in this project"
        )
    
    # Only the original annotator can accept corrections
    if annotation.annotator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the original annotator can accept corrections"
        )
    
    # Only pending corrections can be accepted
    if correction.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending corrections can be accepted"
        )
    
    updated_annotation = accept_review_correction(
        db,
        correction_id,
        annotator_response
    )
    
    if not updated_annotation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept correction"
        )
    
    return updated_annotation
