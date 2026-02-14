"""
Image Annotation CRUD Operations

Database operations for image annotation functionality.
Mirrors the structure of text annotation CRUD but with image-specific logic.
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.annotations.image.models import (
    ImageResource,
    ImageAnnotation,
    ImageReviewCorrection,
    ImageAnnotationQueue
)
from app.annotations.image.schemas import (
    AnnotationStatusEnum,
    AnnotationSubTypeEnum,
    CorrectionStatusEnum
)
from app.annotations.image.storage import (
    upload_image_to_storage,
    generate_thumbnail_content,
    get_presigned_url,
    delete_image_from_storage,
    delete_masks_from_storage,
    extract_image_metadata,
    validate_image,
    download_image_from_url,
    create_resource_paths
)


# ==================== Resource CRUD ====================

async def create_image_resource(
    db: Session,
    project_id: int,
    file,
    name: str,
    uploader_id: int
) -> ImageResource:
    """
    Create a new image resource from uploaded file.
    """
    # Validate image
    is_valid, error_msg = await validate_image(file)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    
    # Extract metadata
    metadata = await extract_image_metadata(file)
    
    # Create database record first to get ID
    resource = ImageResource(
        project_id=project_id,
        uploader_id=uploader_id,
        name=name,
        source_type='file',
        width=metadata.get('width'),
        height=metadata.get('height'),
        mime_type=file.content_type,
        file_size=file.size if hasattr(file, 'size') else None,
        image_metadata=metadata
    )
    db.add(resource)
    db.flush()  # Get the ID without committing
    
    try:
        # Upload to storage
        file_path, thumbnail_path = await upload_image_to_storage(
            file, project_id, resource.id
        )
        
        resource.file_path = file_path
        resource.thumbnail_path = thumbnail_path
        
        db.commit()
        db.refresh(resource)
        return resource
        
    except Exception as e:
        db.rollback()
        raise e


async def create_image_resource_from_url(
    db: Session,
    project_id: int,
    url: str,
    name: str,
    uploader_id: int
) -> ImageResource:
    """
    Create a new image resource from URL.
    """
    # Download image from URL
    content, content_type = await download_image_from_url(url)
    
    # Extract metadata
    import io
    from PIL import Image
    img = Image.open(io.BytesIO(content))
    metadata = {
        'width': img.width,
        'height': img.height,
        'format': img.format,
        'mode': img.mode
    }
    
    # Create database record
    resource = ImageResource(
        project_id=project_id,
        uploader_id=uploader_id,
        name=name,
        source_type='url',
        external_url=url,
        width=metadata.get('width'),
        height=metadata.get('height'),
        mime_type=content_type,
        file_size=len(content),
        image_metadata=metadata
    )
    db.add(resource)
    db.flush()
    
    try:
        # Upload to storage
        ext = 'jpg' if content_type == 'image/jpeg' else 'png'
        file_path, thumbnail_path = create_resource_paths(project_id, resource.id, ext)
        
        # Upload using boto3 directly
        from app.utils.s3_utils import upload_file_to_s3
        upload_file_to_s3(content, file_path, content_type)
        
        # Generate and upload thumbnail
        thumbnail_content = await generate_thumbnail_content(content)
        upload_file_to_s3(thumbnail_content, thumbnail_path, 'image/jpeg')
        
        resource.file_path = file_path
        resource.thumbnail_path = thumbnail_path
        
        db.commit()
        db.refresh(resource)
        return resource
        
    except Exception as e:
        db.rollback()
        raise e


def get_image_resource(db: Session, resource_id: int) -> Optional[ImageResource]:
    """Get image resource by ID."""
    return db.query(ImageResource).filter(
        ImageResource.id == resource_id,
        ImageResource.is_archived == False
    ).first()


def get_image_resources(
    db: Session,
    project_id: int,
    page: int = 1,
    limit: int = 20,
    uploader_id: Optional[int] = None
) -> tuple[List[ImageResource], int]:
    """
    Get paginated list of image resources for a project.
    Returns tuple of (resources, total_count).
    """
    query = db.query(ImageResource).filter(
        ImageResource.project_id == project_id,
        ImageResource.is_archived == False
    )
    
    if uploader_id:
        query = query.filter(ImageResource.uploader_id == uploader_id)
    
    query = query.order_by(desc(ImageResource.created_at))
    
    total = query.count()
    resources = query.offset((page - 1) * limit).limit(limit).all()
    
    return resources, total


def delete_image_resource(db: Session, resource_id: int) -> bool:
    """Soft delete image resource (archive)."""
    resource = db.query(ImageResource).filter(ImageResource.id == resource_id).first()
    if not resource:
        return False
    
    resource.is_archived = True
    db.commit()
    return True


def add_urls_to_resource(resource: ImageResource) -> dict:
    """Add presigned URLs to resource for API response."""
    resource_dict = {
        'id': resource.id,
        'project_id': resource.project_id,
        'uploader_id': resource.uploader_id,
        'name': resource.name,
        'file_path': resource.file_path,
        'thumbnail_path': resource.thumbnail_path,
        'width': resource.width,
        'height': resource.height,
        'file_size': resource.file_size,
        'mime_type': resource.mime_type,
        'source_type': resource.source_type,
        'external_url': resource.external_url,
        'image_metadata': resource.image_metadata,
        'is_archived': resource.is_archived,
        'created_at': resource.created_at,
        'modified_at': resource.modified_at,
        'image_url': None,
        'thumbnail_url': None
    }
    
    if resource.file_path:
        resource_dict['image_url'] = get_presigned_url(resource.file_path)
    if resource.thumbnail_path:
        resource_dict['thumbnail_url'] = get_presigned_url(resource.thumbnail_path)
    
    return resource_dict


# ==================== Annotation CRUD ====================

def create_image_annotation(
    db: Session,
    project_id: int,
    resource_id: int,
    annotator_id: int,
    annotation_sub_type: str = 'bounding_box',
    annotation_data: Optional[dict] = None
) -> ImageAnnotation:
    """Create a new image annotation."""
    # Verify resource exists
    resource = get_image_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image resource not found"
        )
    
    annotation = ImageAnnotation(
        resource_id=resource_id,
        project_id=project_id,
        annotator_id=annotator_id,
        annotation_type='image',
        annotation_sub_type=annotation_sub_type,
        status=AnnotationStatusEnum.DRAFT.value,
        annotation_data=annotation_data
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


def get_image_annotation(db: Session, annotation_id: int) -> Optional[ImageAnnotation]:
    """Get image annotation by ID."""
    return db.query(ImageAnnotation).filter(ImageAnnotation.id == annotation_id).first()


def get_image_annotations(
    db: Session,
    project_id: int,
    resource_id: Optional[int] = None,
    annotator_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    sub_type: Optional[str] = None,
    page: int = 1,
    limit: int = 50
) -> tuple[List[ImageAnnotation], int]:
    """
    Get paginated list of image annotations with filters.
    """
    query = db.query(ImageAnnotation).filter(ImageAnnotation.project_id == project_id)
    
    if resource_id:
        query = query.filter(ImageAnnotation.resource_id == resource_id)
    if annotator_id:
        query = query.filter(ImageAnnotation.annotator_id == annotator_id)
    if status_filter:
        query = query.filter(ImageAnnotation.status == status_filter)
    if sub_type:
        query = query.filter(ImageAnnotation.annotation_sub_type == sub_type)
    
    query = query.order_by(desc(ImageAnnotation.created_at))
    
    total = query.count()
    annotations = query.offset((page - 1) * limit).limit(limit).all()
    
    return annotations, total


def get_annotation_by_resource_and_user(
    db: Session,
    resource_id: int,
    user_id: int
) -> Optional[ImageAnnotation]:
    """Get annotation for a resource by specific user."""
    return db.query(ImageAnnotation).filter(
        ImageAnnotation.resource_id == resource_id,
        ImageAnnotation.annotator_id == user_id
    ).first()


def update_image_annotation(
    db: Session,
    annotation_id: int,
    annotation_data: Optional[dict] = None,
    annotation_sub_type: Optional[str] = None
) -> Optional[ImageAnnotation]:
    """Update an existing annotation."""
    annotation = get_image_annotation(db, annotation_id)
    if not annotation:
        return None
    
    # Only allow updates if in draft or rejected status
    if annotation.status not in [AnnotationStatusEnum.DRAFT.value, AnnotationStatusEnum.REJECTED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update annotation in current status"
        )
    
    if annotation_data is not None:
        annotation.annotation_data = annotation_data
    if annotation_sub_type is not None:
        annotation.annotation_sub_type = annotation_sub_type
    
    annotation.modified_at = datetime.utcnow()
    db.commit()
    db.refresh(annotation)
    return annotation


def delete_image_annotation(db: Session, annotation_id: int) -> bool:
    """Delete annotation (only if in draft status)."""
    annotation = get_image_annotation(db, annotation_id)
    if not annotation:
        return False
    
    if annotation.status != AnnotationStatusEnum.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete annotation that is not in draft status"
        )
    
    db.delete(annotation)
    db.commit()
    return True


def submit_annotation(db: Session, annotation_id: int) -> Optional[ImageAnnotation]:
    """Submit annotation for review."""
    annotation = get_image_annotation(db, annotation_id)
    if not annotation:
        return None
    
    if annotation.status != AnnotationStatusEnum.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit annotations in draft status"
        )
    
    annotation.status = AnnotationStatusEnum.SUBMITTED.value
    annotation.submitted_at = datetime.utcnow()
    db.commit()
    db.refresh(annotation)
    return annotation


def review_annotation(
    db: Session,
    annotation_id: int,
    reviewer_id: int,
    action: str,
    comment: Optional[str] = None
) -> Optional[ImageAnnotation]:
    """Review annotation (approve or reject)."""
    annotation = get_image_annotation(db, annotation_id)
    if not annotation:
        return None
    
    if annotation.status != AnnotationStatusEnum.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review submitted annotations"
        )
    
    if action == 'approve':
        annotation.status = AnnotationStatusEnum.APPROVED.value
    elif action == 'reject':
        annotation.status = AnnotationStatusEnum.REJECTED.value
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve' or 'reject'"
        )
    
    annotation.reviewer_id = reviewer_id
    annotation.review_comment = comment
    annotation.reviewed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(annotation)
    return annotation


# ==================== Shape Operations ====================

def add_shape_to_annotation(
    db: Session,
    project_id: int,
    resource_id: int,
    user_id: int,
    shape_data: dict,
    annotation_sub_type: str
) -> ImageAnnotation:
    """
    Add a single shape to annotation.
    Creates annotation if it doesn't exist.
    """
    # Get or create annotation
    annotation = get_annotation_by_resource_and_user(db, resource_id, user_id)
    
    if not annotation:
        # Create new annotation
        annotation = create_image_annotation(
            db=db,
            project_id=project_id,
            resource_id=resource_id,
            annotator_id=user_id,
            annotation_sub_type=annotation_sub_type,
            annotation_data={'boxes': [], 'polygons': [], 'segments': [], 'keypoints': [], 'classifications': []}
        )
    
    # Generate unique ID for shape
    shape_id = str(uuid.uuid4())
    shape_data['id'] = shape_id
    
    # Get current data and make a copy to ensure SQLAlchemy detects the change
    data = annotation.annotation_data or {}
    data = dict(data)  # Create a new dict to trigger SQLAlchemy change detection
    
    # Ensure all keys exist
    for key in ['boxes', 'polygons', 'segments', 'keypoints', 'classifications']:
        if key not in data:
            data[key] = []
    
    # Add shape to appropriate list based on sub_type
    if annotation_sub_type == 'bounding_box':
        data['boxes'] = list(data['boxes']) + [shape_data]
    elif annotation_sub_type == 'polygon':
        data['polygons'] = list(data['polygons']) + [shape_data]
    elif annotation_sub_type == 'segmentation':
        data['segments'] = list(data['segments']) + [shape_data]
    elif annotation_sub_type == 'keypoint':
        data['keypoints'] = list(data['keypoints']) + [shape_data]
    elif annotation_sub_type == 'classification':
        data['classifications'] = list(data['classifications']) + [shape_data]
    
    # Assign the new dict to trigger SQLAlchemy update
    annotation.annotation_data = data
    annotation.annotation_sub_type = annotation_sub_type
    annotation.modified_at = datetime.utcnow()
    
    # Use flag_modified to ensure SQLAlchemy detects JSON field change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(annotation, 'annotation_data')
    
    db.commit()
    db.refresh(annotation)
    return annotation


def update_shape_in_annotation(
    db: Session,
    annotation_id: int,
    shape_id: str,
    shape_data: dict
) -> Optional[ImageAnnotation]:
    """Update a specific shape in annotation."""
    from sqlalchemy.orm.attributes import flag_modified
    
    annotation = get_image_annotation(db, annotation_id)
    if not annotation:
        return None
    
    data = dict(annotation.annotation_data or {})  # Make a copy
    
    # Find and update the shape in all shape lists
    for key in ['boxes', 'polygons', 'segments', 'keypoints', 'classifications']:
        if key in data:
            for i, shape in enumerate(data[key]):
                if shape.get('id') == shape_id:
                    shape_data['id'] = shape_id  # Preserve the ID
                    # Create new list to ensure change detection
                    data[key] = list(data[key])
                    data[key][i] = shape_data
                    annotation.annotation_data = data
                    annotation.modified_at = datetime.utcnow()
                    flag_modified(annotation, 'annotation_data')
                    db.commit()
                    db.refresh(annotation)
                    return annotation
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Shape not found"
    )


def delete_shape_from_annotation(
    db: Session,
    annotation_id: int,
    shape_id: str
) -> Optional[ImageAnnotation]:
    """Delete a specific shape from annotation."""
    from sqlalchemy.orm.attributes import flag_modified
    
    annotation = get_image_annotation(db, annotation_id)
    if not annotation:
        return None
    
    # Make a copy to ensure change detection
    data = dict(annotation.annotation_data or {})
    
    # Find and delete the shape from all shape lists
    for key in ['boxes', 'polygons', 'segments', 'keypoints', 'classifications']:
        if key in data:
            original_list = list(data[key])
            new_list = [s for s in original_list if s.get('id') != shape_id]
            if len(new_list) < len(original_list):
                data[key] = new_list
                annotation.annotation_data = data
                annotation.modified_at = datetime.utcnow()
                flag_modified(annotation, 'annotation_data')
                db.commit()
                db.refresh(annotation)
                return annotation
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Shape not found"
    )


# ==================== Review Correction CRUD ====================

def create_review_correction(
    db: Session,
    annotation_id: int,
    reviewer_id: int,
    corrected_data: dict,
    comment: Optional[str] = None
) -> ImageReviewCorrection:
    """Create a review correction suggestion."""
    correction = ImageReviewCorrection(
        annotation_id=annotation_id,
        reviewer_id=reviewer_id,
        corrected_data=corrected_data,
        comment=comment,
        status=CorrectionStatusEnum.PENDING.value
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return correction


def get_review_correction(db: Session, correction_id: int) -> Optional[ImageReviewCorrection]:
    """Get review correction by ID."""
    return db.query(ImageReviewCorrection).filter(
        ImageReviewCorrection.id == correction_id
    ).first()


def get_review_corrections(
    db: Session,
    annotation_id: int,
    status_filter: Optional[str] = None
) -> List[ImageReviewCorrection]:
    """Get all corrections for an annotation."""
    query = db.query(ImageReviewCorrection).filter(
        ImageReviewCorrection.annotation_id == annotation_id
    )
    
    if status_filter:
        query = query.filter(ImageReviewCorrection.status == status_filter)
    
    return query.order_by(desc(ImageReviewCorrection.created_at)).all()


def update_review_correction(
    db: Session,
    correction_id: int,
    status: str,
    annotator_response: Optional[str] = None
) -> Optional[ImageReviewCorrection]:
    """Update correction status."""
    correction = get_review_correction(db, correction_id)
    if not correction:
        return None
    
    correction.status = status
    correction.annotator_response = annotator_response
    correction.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(correction)
    return correction


def accept_and_apply_correction(
    db: Session,
    correction_id: int,
    annotator_response: Optional[str] = None
) -> tuple[ImageReviewCorrection, ImageAnnotation]:
    """Accept correction and apply it to the annotation."""
    correction = get_review_correction(db, correction_id)
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction not found"
        )
    
    annotation = get_image_annotation(db, correction.annotation_id)
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Apply correction to annotation
    annotation.annotation_data = correction.corrected_data
    annotation.modified_at = datetime.utcnow()
    
    # Update correction status
    correction.status = CorrectionStatusEnum.ACCEPTED.value
    correction.annotator_response = annotator_response
    correction.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(correction)
    db.refresh(annotation)
    
    return correction, annotation


# ==================== Queue Operations ====================

def get_queue_tasks(
    db: Session,
    project_id: int,
    user_id: Optional[int] = None,
    task_type: Optional[str] = None
) -> List[ImageAnnotationQueue]:
    """Get queue tasks for a project."""
    query = db.query(ImageAnnotationQueue).filter(
        ImageAnnotationQueue.project_id == project_id
    )
    
    if user_id:
        query = query.filter(ImageAnnotationQueue.assigned_to == user_id)
    if task_type:
        query = query.filter(ImageAnnotationQueue.task_type == task_type)
    
    return query.order_by(desc(ImageAnnotationQueue.priority), desc(ImageAnnotationQueue.created_at)).all()


def get_unannotated_resources(
    db: Session,
    project_id: int,
    user_id: int,
    limit: int = 50
) -> List[ImageResource]:
    """
    Get resources that haven't been annotated by the current user.
    Used for queue functionality.
    """
    # Get resource IDs that user has already annotated
    annotated_resource_ids = db.query(ImageAnnotation.resource_id).filter(
        ImageAnnotation.project_id == project_id,
        ImageAnnotation.annotator_id == user_id
    ).all()
    annotated_ids = [r[0] for r in annotated_resource_ids]
    
    # Get resources not in that list
    query = db.query(ImageResource).filter(
        ImageResource.project_id == project_id,
        ImageResource.is_archived == False
    )
    
    if annotated_ids:
        query = query.filter(~ImageResource.id.in_(annotated_ids))
    
    return query.order_by(ImageResource.created_at).limit(limit).all()


def get_pending_review_annotations(
    db: Session,
    project_id: int,
    limit: int = 50
) -> List[ImageAnnotation]:
    """Get annotations pending review for a project."""
    return db.query(ImageAnnotation).filter(
        ImageAnnotation.project_id == project_id,
        ImageAnnotation.status == AnnotationStatusEnum.SUBMITTED.value
    ).order_by(ImageAnnotation.submitted_at).limit(limit).all()