"""
Business logic layer for text annotation.
Orchestrates crud + S3 + queue stub.
"""
import logging
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.annotations.text.crud import (
    create_resource,
    get_resource,
    create_annotation,
    get_annotation,
    update_annotation,
    submit_annotation,
    review_annotation
)
from app.annotations.text.queue_stub import TextQueueStub
from app.annotations.base import BaseAnnotationProcessor
from app.utils.s3_utils import (
    upload_file_to_s3,
    download_file_from_s3,
    save_json_to_s3,
    generate_presigned_url
)
from app.models.project_assignment import ProjectAssignment
from app.models.project import Project
import json
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextAnnotationProcessor(BaseAnnotationProcessor):
    """Text annotation implementation of BaseAnnotationProcessor."""
    
    def validate_input(self, data: dict) -> bool:
        """Validate text annotation input."""
        if not data.get("resource_id"):
            return False
        if data.get("annotation_type") not in ["ner", "classification", "sentiment", "general"]:
            return False
        return True
    
    def process_annotation(self, annotation_data: dict) -> dict:
        """Process annotation data."""
        return annotation_data
    
    def get_output_path(self, project_id: int, annotation_id: int) -> str:
        """Generate S3 path for output."""
        return f"projects/{project_id}/outputs/text/{annotation_id}.json"


async def upload_resource(
    db: Session,
    project_id: int,
    user_id: int,
    file: UploadFile,
    name: str
) -> dict:
    """
    Upload a text file as a resource.
    
    1. Get project (access validated by router's check_project_access)
    2. Generate S3 key
    3. Upload file to S3
    4. Read first 500 chars as preview
    5. Create TextResource record
    6. Enqueue task
    """
    # Get project (access already validated by router's check_project_access)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Generate S3 key
    import uuid
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'txt'
    s3_key = f"projects/{project_id}/inputs/uploads/{uuid.uuid4()}.{ext}"
    
    # Upload to S3
    upload_file_to_s3(content, s3_key)
    
    # Generate preview (first 500 chars)
    try:
        text_content = content.decode('utf-8')
        preview = text_content[:500]
    except UnicodeDecodeError:
        preview = None
    
    # Create resource
    resource = create_resource(db, project_id, user_id, {
        "name": name,
        "source_type": "upload",
        "s3_key": s3_key,
        "content_preview": preview,
        "file_size": file_size
    })
    
    # Enqueue task with annotation_type
    queue = TextQueueStub(db, annotation_type="text")
    queue.enqueue(project_id, resource.id, "resource_uploaded", {
        "resource_id": resource.id,
        "uploaded_by": user_id
    })
    
    logger.info(f"Uploaded resource {resource.id} to project {project_id}")
    return resource


async def add_url_resource(
    db: Session,
    project_id: int,
    user_id: int,
    url: str,
    name: str
) -> dict:
    """
    Add a URL as a text resource.
    
    1. Get project (access validated by router's check_project_access)
    2. Create TextResource with URL
    3. Fetch first 500 chars for preview
    4. Store metadata to S3
    5. Enqueue task
    """
    # Get project (access already validated by router's check_project_access)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Fetch preview from URL (best effort)
    preview = None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                text = response.text
                preview = text[:500]
                
                # Store metadata to S3
                import uuid
                s3_key = f"projects/{project_id}/inputs/external/{uuid.uuid4()}.json"
                save_json_to_s3({"url": url, "content": text}, s3_key)
    except Exception as e:
        logger.warning(f"Could not fetch preview from URL: {e}")
    
    # Create resource
    resource = create_resource(db, project_id, user_id, {
        "name": name,
        "source_type": "url",
        "external_url": url,
        "content_preview": preview
    })
    
    # Enqueue task with annotation_type
    queue = TextQueueStub(db, annotation_type="text")
    queue.enqueue(project_id, resource.id, "resource_url_added", {
        "resource_id": resource.id,
        "url": url
    })
    
    logger.info(f"Added URL resource {resource.id} to project {project_id}")
    return resource


def create_annotation_service(
    db: Session,
    project_id: int,
    user_id: int,
    data: dict
) -> dict:
    """
    Create a new annotation.
    
    1. Validate user is annotator on project
    2. Validate resource exists and belongs to project
    3. Create annotation
    """
    # Validate user is assigned as annotator or higher
    assignment = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user_id
    ).first()
    
    if not assignment and user_id != db.query(Project).filter(Project.id == project_id).first().owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be assigned to this project to create annotations"
        )
    
    # Validate resource
    resource = get_resource(db, data["resource_id"])
    if not resource or resource.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found or does not belong to this project"
        )
    
    # Create annotation
    annotation = create_annotation(db, project_id, user_id, data)
    logger.info(f"Created annotation {annotation.id} by user {user_id}")
    return annotation


def submit_annotation_service(
    db: Session,
    annotation_id: int,
    user_id: int
) -> dict:
    """
    Submit an annotation for review.
    
    1. Validate annotation belongs to user
    2. Validate status
    3. Update and enqueue
    """
    annotation = get_annotation(db, annotation_id)
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    if annotation.annotator_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit your own annotations"
        )
    
    if annotation.status not in ["pending", "in_progress"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit pending or in-progress annotations"
        )
    
    # Submit
    annotation = submit_annotation(db, annotation_id)
    
    # Enqueue with annotation_type and annotation_id
    queue = TextQueueStub(db, annotation_type="text")
    queue.enqueue(annotation.project_id, annotation.resource_id, "annotation_submitted", {
        "annotation_id": annotation.id,
        "annotator_id": user_id
    }, annotation_id=annotation.id)
    
    logger.info(f"Submitted annotation {annotation_id}")
    return annotation


def review_annotation_service(
    db: Session,
    annotation_id: int,
    reviewer_id: int,
    action: str,
    comment: Optional[str] = None
) -> dict:
    """
    Review an annotation (approve/reject).
    
    1. Validate reviewer has access
    2. Validate status
    3. Update and save to S3 if approved
    """
    annotation = get_annotation(db, annotation_id)
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )
    
    # Validate reviewer is assigned to project
    assignment = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == annotation.project_id,
        ProjectAssignment.user_id == reviewer_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be assigned to this project to review annotations"
        )
    
    if annotation.status not in ["submitted", "under_review"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review submitted annotations"
        )
    
    # Review
    annotation = review_annotation(db, annotation_id, reviewer_id, action, comment)
    
    # If approved, save output to S3
    if action == "approve":
        processor = TextAnnotationProcessor()
        s3_key = processor.get_output_path(annotation.project_id, annotation.id)
        
        output_data = {
            "annotation_id": annotation.id,
            "project_id": annotation.project_id,
            "resource_id": annotation.resource_id,
            "annotation_type": annotation.annotation_type,
            "sub_type": annotation.annotation_type,
            "label": annotation.label,
            "span": {
                "start": annotation.span_start,
                "end": annotation.span_end,
                "text": ""  # Would need to fetch from resource
            },
            "annotation_data": annotation.annotation_data,
            "status": annotation.status,
            "annotator_id": annotation.annotator_id,
            "reviewer_id": annotation.reviewer_id,
            "review_comment": annotation.review_comment,
            "created_at": annotation.created_at.isoformat() if annotation.created_at else None,
            "submitted_at": annotation.submitted_at.isoformat() if annotation.submitted_at else None,
            "reviewed_at": annotation.reviewed_at.isoformat() if annotation.reviewed_at else None
        }
        
        save_json_to_s3(output_data, s3_key)
        
        # Update annotation with S3 key
        update_annotation(db, annotation_id, {"output_s3_key": s3_key})
    
    # Enqueue with annotation_type and annotation_id
    queue = TextQueueStub(db, annotation_type="text")
    queue.enqueue(annotation.project_id, annotation.resource_id, "annotation_reviewed", {
        "annotation_id": annotation.id,
        "reviewer_id": reviewer_id,
        "action": action
    }, annotation_id=annotation.id)
    
    logger.info(f"Reviewed annotation {annotation_id}: {action}")
    return annotation


def get_resource_with_content(db: Session, resource_id: int) -> dict:
    """
    Get resource with full content.
    
    1. Fetch TextResource
    2. If upload type, fetch from S3
    3. If URL type, return URL
    """
    resource = get_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    full_content = None
    
    if resource.source_type == "upload" and resource.s3_key:
        try:
            content = download_file_from_s3(resource.s3_key)
            full_content = content.decode('utf-8')
        except Exception as e:
            logger.error(f"Error downloading from S3: {e}")
    
    # For URL type, client will fetch content
    # We return the resource with optional full_content
    
    return {
        **resource.__dict__,
        "full_content": full_content
    }