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


router = APIRouter(prefix="/projects", tags=["Image Annotations"])


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
    
    return schemas.ImageAnnotationListResponse(
        success=True,
        data=annotations,
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
    
    Only the original annotator can update, and only if status is draft or rejected.
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


@router.post("/{project_id}/annotations/{annotation_id}/submit", response_model=schemas.ImageAnnotationResponse)
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
    return annotation


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
    """
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    if annotation.annotator_id != current_user.id and current_user.role != 'admin':
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
    """
    annotation = crud.get_image_annotation(db, annotation_id)
    if not annotation or annotation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    if annotation.annotator_id != current_user.id and current_user.role != 'admin':
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
    task_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get queue tasks for a project.
    """
    if not check_project_member(db, project_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this project"
        )
    
    tasks = crud.get_queue_tasks(
        db=db,
        project_id=project_id,
        user_id=current_user.id if current_user.role != 'admin' else None,
        task_type=task_type
    )
    
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