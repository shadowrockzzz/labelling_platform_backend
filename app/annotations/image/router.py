"""
Image Annotation API Router

API endpoints for image annotation functionality.
Mirrors the structure of text annotation router but with image-specific endpoints.

All endpoints are prefixed with /api/v1/annotations/image/projects/{project_id}/
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_active_user
from app.models.user import User
from app.annotations.image import crud, schemas, storage
from app.annotations.image.crud import add_urls_to_resource
from app.annotations.base import QueueTracker


router = APIRouter(prefix="/projects", tags=["Image Annotations"])


# ==================== Annotation Response Helper ====================

def annotation_to_response(annotation) -> dict:
    """Convert annotation ORM object to response dict with annotator/reviewer names."""
    response = {
        'id': annotation.id,
        'resource_id': annotation.resource_id,
        'project_id': annotation.project_id,
        'annotator_id': annotation.annotator_id,
        'reviewer_id': annotation.reviewer_id,
        'annotation_type': annotation.annotation_type,
        'annotation_sub_type': annotation.annotation_sub_type,
        'status': annotation.status,
        'annotation_data': annotation.annotation_data,
        'review_comment': annotation.review_comment,
        'reviewed_at': annotation.reviewed_at,
        'created_at': annotation.created_at,
        'modified_at': annotation.modified_at,
        'submitted_at': annotation.submitted_at,
        'resource': None,
        'annotator_name': None,
        'reviewer_name': None
    }
    
    # Get annotator name from loaded relationship
    if annotation.annotator:
        response['annotator_name'] = annotation.annotator.full_name or annotation.annotator.email
    
    # Get reviewer name if available
    if annotation.reviewer:
        response['reviewer_name'] = annotation.reviewer.full_name or annotation.reviewer.email
    
    # Add resource info if available
    if annotation.resource:
        response['resource'] = add_urls_to_resource(annotation.resource)
    
    return response


# ==================== Helper Functions ====================

def check_project_member(db: Session, project_id: int, user: User) -> bool:
    """Check if user is a member of the project."""
    from app.models.project_assignment import ProjectAssignment
    from app.models.project import Project
    
    # Admin has access to all
    if user.role == 'admin':
        return True
    
    # Check if user is project owner
    project = db.query(Project).filter(Project.id == project_id).first()
    if project and project.owner_id == user.id:
        return True
    
    # Check assignment
    assignment = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user.id
    ).first()
    
    return assignment is not None


def check_annotator(db: Session, project_id: int, user: User) -> bool:
    """Check if user can annotate (annotator role or higher)."""
    if user.role == 'admin':
        return True
    
    from app.models.project_assignment import ProjectAssignment
    assignment = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user.id,
        ProjectAssignment.role.in_(['annotator', 'reviewer'])
    ).first()
    
    return assignment is not None


def check_reviewer(db: Session, project_id: int, user: User) -> bool:
    """Check if user can review (reviewer role or admin)."""
    if user.role == 'admin':
        return True
    
    from app.models.project_assignment import ProjectAssignment
    assignment = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user.id,
        ProjectAssignment.role == 'reviewer'
    ).first()
    
    return assignment is not None


# ==================== Resource Endpoints ====================

@router.post("/{project_id}/resources/upload")
async def upload_image_resource(
    project_id: int,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload an image file for annotation.
    
    Supports JPEG and PNG formats.
    Maximum file size: 50MB
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload to this project"
        )
    
    # Use filename if name not provided
    if not name:
        name = file.filename or "unnamed"
    
    resource = await crud.create_image_resource(
        db=db,
        project_id=project_id,
        file=file,
        name=name,
        uploader_id=current_user.id
    )
    
    # Auto-seed task for this resource
    from app.annotations.shared.task_crud import AnnotationTaskCRUD
    task_crud = AnnotationTaskCRUD(db, resource_type="image")
    task_crud.seed_tasks_from_resources(project_id, [resource.id])
    
    return add_urls_to_resource(resource)


@router.post("/{project_id}/resources/url", response_model=schemas.ImageResourceResponse)
async def create_image_resource_from_url(
    project_id: int,
    resource_data: schemas.ImageResourceURLCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create an image resource from a URL.
    
    The image will be downloaded and stored in MinIO/S3.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add resources to this project"
        )
    
    resource = await crud.create_image_resource_from_url(
        db=db,
        project_id=project_id,
        url=resource_data.external_url,
        name=resource_data.name,
        uploader_id=current_user.id
    )
    
    return add_urls_to_resource(resource)


@router.get("/{project_id}/resources")
def list_image_resources(
    project_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    uploader_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List image resources for a project.
    
    Returns paginated list with presigned URLs for thumbnails.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    resources, total = crud.get_image_resources(
        db=db,
        project_id=project_id,
        page=page,
        limit=limit,
        uploader_id=uploader_id
    )
    
    # Add URLs to each resource
    resources_with_urls = [add_urls_to_resource(r) for r in resources]
    
    return {
        "success": True,
        "data": resources_with_urls,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/{project_id}/resources/{resource_id}")
def get_image_resource(
    project_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific image resource with full image URL.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    resource = crud.get_image_resource(db, resource_id)
    if not resource or resource.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    return add_urls_to_resource(resource)


@router.delete("/{project_id}/resources/{resource_id}", response_model=schemas.SuccessResponse)
def delete_image_resource(
    project_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Archive (soft delete) an image resource.
    
    Only admin or project owner can delete resources.
    """
    from app.models.project import Project
    
    resource = crud.get_image_resource(db, resource_id)
    if not resource or resource.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    # Check permissions
    project = db.query(Project).filter(Project.id == project_id).first()
    if current_user.role != 'admin' and (not project or project.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or project owner can delete resources"
        )
    
    success = crud.delete_image_resource(db, resource_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resource"
        )
    
    return schemas.SuccessResponse(success=True, message="Resource archived successfully")


# ==================== Annotation Endpoints ====================

@router.post("/{project_id}/annotations", response_model=schemas.ImageAnnotationResponse)
def create_annotation(
    project_id: int,
    annotation_data: schemas.ImageAnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new image annotation.
    """
    if not check_annotator(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to annotate in this project"
        )
    
    annotation = crud.create_image_annotation(
        db=db,
        project_id=project_id,
        resource_id=annotation_data.resource_id,
        annotator_id=current_user.id,
        annotation_sub_type=annotation_data.annotation_sub_type.value,
        annotation_data=annotation_data.annotation_data
    )
    
    # Track in queue
    tracker = QueueTracker(db, annotation_type="image")
    tracker.track_created(
        project_id=project_id,
        annotation_id=annotation.id,
        resource_id=annotation_data.resource_id,
        sub_type=annotation_data.annotation_sub_type.value
    )
    
    return annotation


@router.get("/{project_id}/annotations", response_model=schemas.ImageAnnotationListResponse)
def list_annotations(
    project_id: int,
    resource_id: Optional[int] = None,
    annotator_id: Optional[int] = None,
    status: Optional[str] = None,
    sub_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List annotations with optional filters.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    annotations, total = crud.get_image_annotations(
        db=db,
        project_id=project_id,
        resource_id=resource_id,
        annotator_id=annotator_id,
        status_filter=status,
        sub_type=sub_type,
        page=page,
        limit=limit
    )
    
    # Transform annotations to include annotator/reviewer names
    data = [annotation_to_response(ann) for ann in annotations]
    
    return schemas.ImageAnnotationListResponse(
        success=True,
        data=data,
        total=total
    )


@router.get("/{project_id}/annotations/{annotation_id}", response_model=schemas.ImageAnnotationResponse)
def get_annotation(
    project_id: int,
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific annotation with resource details.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Add resource info
    response = schemas.ImageAnnotationResponse.from_orm(annotation)
    if annotation.resource:
        response.resource = add_urls_to_resource(annotation.resource)
    
    return response


@router.put("/{project_id}/annotations/{annotation_id}", response_model=schemas.ImageAnnotationResponse)
def update_annotation(
    project_id: int,
    annotation_id: int,
    update_data: schemas.ImageAnnotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an annotation.
    
    Allowed by: original annotator, admin, or reviewer.
    Only updates if status is draft or rejected.
    """
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Check permission: owner, admin, or reviewer
    is_owner = annotation.annotator_id == current_user.id
    is_admin = current_user.role == 'admin'
    is_reviewer = check_reviewer(db, project_id, current_user)
    
    if not (is_owner or is_admin or is_reviewer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this annotation"
        )
    
    annotation = crud.update_image_annotation(
        db=db,
        annotation_id=annotation_id,
        annotation_data=update_data.annotation_data,
        annotation_sub_type=update_data.annotation_sub_type.value if update_data.annotation_sub_type else None
    )
    
    return annotation


@router.delete("/{project_id}/annotations/{annotation_id}", response_model=schemas.SuccessResponse)
def delete_annotation(
    project_id: int,
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an annotation.
    
    Only draft annotations can be deleted.
    """
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Check ownership
    if annotation.annotator_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this annotation"
        )
    
    success = crud.delete_image_annotation(db, annotation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete annotation"
        )
    
    return schemas.SuccessResponse(success=True, message="Annotation deleted successfully")


@router.post("/{project_id}/annotations/{annotation_id}/submit")
def submit_annotation_for_review(
    project_id: int,
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit annotation for review.
    
    Changes status from 'draft' to 'submitted'.
    """
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Check ownership
    if annotation.annotator_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to submit this annotation"
        )
    
    annotation = crud.submit_annotation(db, annotation_id)
    
    # Track in queue (non-blocking - errors logged but don't fail request)
    tracker = QueueTracker(db, annotation_type="image")
    tracker.track_submitted(
        project_id=project_id,
        annotation_id=annotation.id,
        resource_id=annotation.resource_id
    )
    
    # Return with annotator name using helper
    return annotation_to_response(annotation)


@router.post("/{project_id}/annotations/{annotation_id}/review", response_model=schemas.ImageAnnotationResponse)
def review_annotation(
    project_id: int,
    annotation_id: int,
    review_data: schemas.ReviewAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Review an annotation (approve or reject).
    
    Only reviewers and admins can perform this action.
    """
    if not check_reviewer(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to review annotations"
        )
    
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    annotation = crud.review_annotation(
        db=db,
        annotation_id=annotation_id,
        reviewer_id=current_user.id,
        action=review_data.action,
        comment=review_data.comment
    )
    
    return annotation


# ==================== Single Shape Operations ====================

@router.post("/{project_id}/resources/{resource_id}/shapes", response_model=schemas.ImageAnnotationResponse)
def add_shape(
    project_id: int,
    resource_id: int,
    shape_data: schemas.ShapeCreate,
    annotation_sub_type: str = Query(..., description="Annotation sub-type: bounding_box, polygon, segmentation, keypoint, classification"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add a single shape to annotation.
    
    Creates annotation if it doesn't exist.
    """
    if not check_annotator(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to annotate in this project"
        )
    
    annotation = crud.add_shape_to_annotation(
        db=db,
        project_id=project_id,
        resource_id=resource_id,
        user_id=current_user.id,
        shape_data=shape_data.shape_data,
        annotation_sub_type=annotation_sub_type
    )
    
    return annotation


@router.get("/{project_id}/resources/{resource_id}/annotation", response_model=schemas.ImageAnnotationResponse)
def get_resource_annotation(
    project_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get annotation for a resource by the current user.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    annotation = crud.get_annotation_by_resource_and_user(
        db=db,
        resource_id=resource_id,
        user_id=current_user.id
    )
    
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No annotation found for this resource"
        )
    
    return annotation


@router.put("/{project_id}/annotations/{annotation_id}/shapes/{shape_id}", response_model=schemas.ImageAnnotationResponse)
def update_shape(
    project_id: int,
    annotation_id: int,
    shape_id: str,
    shape_data: schemas.ShapeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a specific shape in annotation.
    
    Allowed by: original annotator, admin, or reviewer.
    """
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Check permission: owner, admin, or reviewer
    is_owner = annotation.annotator_id == current_user.id
    is_admin = current_user.role == 'admin'
    is_reviewer = check_reviewer(db, project_id, current_user)
    
    if not (is_owner or is_admin or is_reviewer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this annotation"
        )
    
    annotation = crud.update_shape_in_annotation(
        db=db,
        annotation_id=annotation_id,
        shape_id=shape_id,
        shape_data=shape_data.shape_data
    )
    
    return annotation


@router.delete("/{project_id}/annotations/{annotation_id}/shapes/{shape_id}", response_model=schemas.ImageAnnotationResponse)
def delete_shape(
    project_id: int,
    annotation_id: int,
    shape_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a specific shape from annotation.
    
    Allowed by: original annotator, admin, or reviewer.
    """
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Check permission: owner, admin, or reviewer
    is_owner = annotation.annotator_id == current_user.id
    is_admin = current_user.role == 'admin'
    is_reviewer = check_reviewer(db, project_id, current_user)
    
    if not (is_owner or is_admin or is_reviewer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this annotation"
        )
    
    annotation = crud.delete_shape_from_annotation(
        db=db,
        annotation_id=annotation_id,
        shape_id=shape_id
    )
    
    return annotation


# ==================== Review Corrections ====================

@router.post("/{project_id}/annotations/{annotation_id}/corrections", response_model=schemas.ImageReviewCorrectionResponse)
def create_correction(
    project_id: int,
    annotation_id: int,
    correction_data: schemas.ImageReviewCorrectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a review correction suggestion.
    
    Only reviewers can create corrections.
    """
    if not check_reviewer(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create corrections"
        )
    
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    correction = crud.create_review_correction(
        db=db,
        annotation_id=annotation_id,
        reviewer_id=current_user.id,
        corrected_data=correction_data.corrected_data,
        comment=correction_data.comment
    )
    
    return correction


@router.get("/{project_id}/annotations/{annotation_id}/corrections", response_model=schemas.ImageReviewCorrectionListResponse)
def list_corrections(
    project_id: int,
    annotation_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List corrections for an annotation.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    corrections = crud.get_review_corrections(
        db=db,
        annotation_id=annotation_id,
        status_filter=status
    )
    
    return schemas.ImageReviewCorrectionListResponse(
        success=True,
        data=corrections,
        total=len(corrections)
    )


@router.get("/{project_id}/corrections/{correction_id}", response_model=schemas.ImageReviewCorrectionResponse)
def get_correction(
    project_id: int,
    correction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific correction.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    correction = crud.get_review_correction(db, correction_id)
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    # Verify project
    if correction.annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    return correction


@router.put("/{project_id}/corrections/{correction_id}", response_model=schemas.ImageReviewCorrectionResponse)
def update_correction(
    project_id: int,
    correction_id: int,
    update_data: schemas.ImageReviewCorrectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update correction status (accept/reject).
    
    Only the original annotator can update corrections.
    """
    correction = crud.get_review_correction(db, correction_id)
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    # Verify project and ownership
    if correction.annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    if correction.annotation.annotator_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this correction"
        )
    
    correction = crud.update_review_correction(
        db=db,
        correction_id=correction_id,
        status=update_data.status.value,
        annotator_response=update_data.annotator_response
    )
    
    return correction


@router.post("/{project_id}/corrections/{correction_id}/accept", response_model=schemas.ImageAnnotationResponse)
def accept_correction(
    project_id: int,
    correction_id: int,
    annotator_response: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Accept and apply correction to annotation.
    
    Only the original annotator can accept corrections.
    """
    correction = crud.get_review_correction(db, correction_id)
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    # Verify project and ownership
    if correction.annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    if correction.annotation.annotator_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to accept this correction"
        )
    
    correction, annotation = crud.accept_and_apply_correction(
        db=db,
        correction_id=correction_id,
        annotator_response=annotator_response
    )
    
    return annotation


# ==================== Queue Endpoints ====================

@router.get("/{project_id}/queue", response_model=schemas.QueueListResponse)
def get_queue(
    project_id: int,
    pending_only: bool = Query(False, description="Only show pending/processing tasks"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get queue tasks for a project's image annotation queue.
    
    Uses Redis-backed AnnotationQueue with PostgreSQL audit logging.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    # Only manager or admin can view full queue
    if current_user.role not in ["admin", "project_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project managers and admins can view queue"
        )
    
    from app.core.queue import AnnotationQueue
    
    queue = AnnotationQueue(db, annotation_type="image")
    
    if pending_only:
        tasks = queue.get_pending_tasks(project_id)
    else:
        tasks = queue.get_all_tasks(project_id)
    
    return schemas.QueueListResponse(
        success=True,
        data=tasks,
        total=len(tasks)
    )


@router.get("/{project_id}/queue/unannotated")
def get_unannotated_resources_endpoint(
    project_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get resources that haven't been annotated by the current user.
    
    Useful for queue-based annotation workflow.
    """
    if not check_annotator(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to annotate in this project"
        )
    
    resources = crud.get_unannotated_resources(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        limit=limit
    )
    
    # Add URLs to each resource
    resources_with_urls = [add_urls_to_resource(r) for r in resources]
    
    return {
        "success": True,
        "data": resources_with_urls,
        "total": len(resources_with_urls)
    }


@router.get("/{project_id}/queue/pending-review")
def get_pending_review_endpoint(
    project_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get annotations pending review.
    """
    if not check_reviewer(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to review in this project"
        )
    
    annotations = crud.get_pending_review_annotations(
        db=db,
        project_id=project_id,
        limit=limit
    )
    
    return {
        "success": True,
        "data": annotations,
        "total": len(annotations)
    }


# ==================== Resource Pool Endpoints ====================

@router.post("/{project_id}/resources/bulk-upload")
async def bulk_upload_image_resources(
    project_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Bulk upload multiple image files for PM-provided resource pool.
    
    Only project managers and admins can use this endpoint.
    """
    from app.models.project import Project
    
    # Check if user is admin or project manager
    if current_user.role not in ['admin', 'project_manager']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and project managers can bulk upload resources"
        )
    
    # Verify project exists and has PM-provided resources
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.config.get('resource_provider') != 'project_manager':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This project is not configured for PM-provided resources"
        )
    
    uploaded_resources = []
    uploaded_resource_ids = []
    errors = []
    
    for file in files:
        try:
            resource = await crud.create_image_resource(
                db=db,
                project_id=project_id,
                file=file,
                name=file.filename or "unnamed",
                uploader_id=current_user.id
            )
            uploaded_resources.append(add_urls_to_resource(resource))
            uploaded_resource_ids.append(resource.id)
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    # Auto-seed tasks for all uploaded resources
    if uploaded_resource_ids:
        from app.annotations.shared.task_crud import AnnotationTaskCRUD
        task_crud = AnnotationTaskCRUD(db, resource_type="image")
        task_crud.seed_tasks_from_resources(project_id, uploaded_resource_ids)
    
    return {
        "success": True,
        "data": {
            "uploaded": uploaded_resources,
            "errors": errors,
            "total_uploaded": len(uploaded_resources),
            "total_errors": len(errors)
        }
    }


@router.get("/{project_id}/pool/next")
def get_next_pool_resource(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the next available resource from the pool for annotation.
    
    Locks the resource to the current user.
    """
    from app.models.project import Project
    from datetime import datetime
    
    # Check project configuration
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.config.get('resource_provider') != 'project_manager':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This project is not configured for PM-provided resources"
        )
    
    if not check_annotator(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to annotate in this project"
        )
    
    resource = crud.get_next_available_resource(db, project_id)
    if not resource:
        return {
            "success": True,
            "data": None,
            "message": "No available resources in the pool"
        }
    
    # Lock the resource
    resource.pool_status = 'locked'
    resource.locked_by_user_id = current_user.id
    resource.locked_at = datetime.utcnow()
    db.commit()
    db.refresh(resource)
    
    return {
        "success": True,
        "data": add_urls_to_resource(resource)
    }


@router.get("/{project_id}/pool/status")
def get_pool_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the status of the resource pool.
    
    Returns counts by status and list of locked resources.
    """
    from app.models.project import Project
    from app.annotations.image.models import ImageResource
    
    # Check project configuration
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if current_user.role not in ['admin', 'project_manager']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and project managers can view pool status"
        )
    
    # Get counts by status
    from sqlalchemy import func
    
    counts = db.query(
        ImageResource.pool_status,
        func.count(ImageResource.id)
    ).filter(
        ImageResource.project_id == project_id
    ).group_by(
        ImageResource.pool_status
    ).all()
    
    status_counts = {
        'available': 0,
        'locked': 0,
        'completed': 0,
        'skipped': 0
    }
    
    for status_val, count in counts:
        if status_val in status_counts:
            status_counts[status_val] = count
    
    # Get locked resources with user info
    locked_resources = db.query(ImageResource).filter(
        ImageResource.project_id == project_id,
        ImageResource.pool_status == 'locked'
    ).all()
    
    locked_data = []
    for r in locked_resources:
        locked_data.append({
            'id': r.id,
            'name': r.name,
            'pool_status': r.pool_status,
            'locked_by': {
                'id': r.locked_by.id,
                'full_name': r.locked_by.full_name,
                'email': r.locked_by.email
            } if r.locked_by else None,
            'locked_at': r.locked_at.isoformat() if r.locked_at else None
        })
    
    return {
        "success": True,
        "data": {
            "counts": status_counts,
            "locked_resources": locked_data,
            "total": sum(status_counts.values())
        }
    }


@router.post("/{project_id}/resources/{resource_id}/skip")
def skip_pool_resource(
    project_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Skip a resource, returning it to the pool and getting the next one.
    """
    from datetime import datetime
    
    resource = crud.get_image_resource(db, resource_id)
    if not resource or resource.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    if resource.locked_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have this resource locked"
        )
    
    # Release the lock
    resource.pool_status = 'available'
    resource.locked_by_user_id = None
    resource.locked_at = None
    db.commit()
    
    # Get next available resource
    next_resource = crud.get_next_available_resource(db, project_id)
    if next_resource:
        next_resource.pool_status = 'locked'
        next_resource.locked_by_user_id = current_user.id
        next_resource.locked_at = datetime.utcnow()
        db.commit()
        db.refresh(next_resource)
        
        return {
            "success": True,
            "data": add_urls_to_resource(next_resource),
            "message": "Resource skipped, new resource assigned"
        }
    
    return {
        "success": True,
        "data": None,
        "message": "Resource skipped, no more available resources"
    }


@router.post("/{project_id}/resources/{resource_id}/release-lock")
def release_resource_lock(
    project_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Release the lock on a resource (PM only).
    Also releases the corresponding annotation_task if it exists.
    """
    from app.annotations.shared.task_models import AnnotationTask
    
    resource = crud.get_image_resource(db, resource_id)
    if not resource or resource.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    if current_user.role not in ['admin', 'project_manager']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and project managers can release locks"
        )
    
    # Release the lock on the resource
    resource.pool_status = 'available'
    resource.locked_by_user_id = None
    resource.locked_at = None
    
    # Also release the corresponding annotation_task if it exists
    task = db.query(AnnotationTask).filter(
        AnnotationTask.project_id == project_id,
        AnnotationTask.resource_id == resource_id,
        AnnotationTask.resource_type == 'image',
        AnnotationTask.status == 'locked'
    ).first()
    
    if task:
        task.status = 'available'
        task.annotator_id = None
        task.locked_at = None
        task.lock_expires_at = None
        db.add(task)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Lock released successfully"
    }


# ==================== Review Pool Endpoints ====================

@router.get("/{project_id}/review-pool/next")
def get_next_review_annotation(
    project_id: int,
    level: int = Query(1, ge=1, description="Review level"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the next annotation for review at the specified level.
    """
    from datetime import datetime
    
    if not check_reviewer(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to review in this project"
        )
    
    annotation = crud.get_next_annotation_for_review(db, project_id, level, current_user.id)
    
    if not annotation:
        return {
            "success": True,
            "data": None,
            "message": "No annotations waiting for review at this level"
        }
    
    # Lock for review
    annotation.review_locked_by = current_user.id
    annotation.review_locked_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "data": annotation_to_response(annotation)
    }


@router.post("/{project_id}/annotations/{annotation_id}/skip-review")
def skip_review_annotation(
    project_id: int,
    annotation_id: int,
    level: int = Query(1, ge=1, description="Review level"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Skip an annotation review, releasing the lock and getting the next one.
    """
    from datetime import datetime
    
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Release the lock
    annotation.review_locked_by = None
    annotation.review_locked_at = None
    db.commit()
    
    # Get next annotation for review
    next_annotation = crud.get_next_annotation_for_review(db, project_id, level, current_user.id)
    
    if next_annotation:
        next_annotation.review_locked_by = current_user.id
        next_annotation.review_locked_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "data": annotation_to_response(next_annotation),
            "message": "Review skipped, next annotation assigned"
        }
    
    return {
        "success": True,
        "data": None,
        "message": "Review skipped, no more annotations waiting"
    }
