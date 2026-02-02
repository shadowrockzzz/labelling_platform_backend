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
        # annotation_sub_type can be any of the 8 types
        valid_sub_types = ["ner", "pos", "sentiment", "relation", "span", "classification", "dependency", "coreference"]
        sub_type = data.get("annotation_sub_type", "ner")
        if sub_type not in valid_sub_types:
            return False
        return True
    
    def process_annotation(self, annotation_data: dict) -> dict:
        """Process annotation data."""
        return annotation_data
    
    def get_output_path(self, project_id: int, annotation_id: int) -> str:
        """Generate S3 path for output."""
        return f"projects/{project_id}/outputs/text/{annotation_id}.json"


def format_annotation_output(annotation) -> dict:
    """
    Format annotation to type-specific JSON output structure.
    
    Returns different structure based on annotation.annotation_sub_type.
    """
    sub_type = annotation.annotation_sub_type or "ner"
    resource_text = annotation.annotation_data.get("text", "") if annotation.annotation_data else ""
    
    base_output = {
        "annotation_id": annotation.id,
        "annotation_type": "text",
        "sub_type": sub_type,
        "project_id": annotation.project_id,
        "resource_id": annotation.resource_id,
        "status": annotation.status,
        "created_at": annotation.created_at.isoformat() if annotation.created_at else None,
    }
    
    if sub_type == "ner":
        base_output.update({
            "entities": [{
                "label": annotation.label,
                "text": annotation.annotation_data.get("entity_text", resource_text),
                "start": annotation.span_start,
                "end": annotation.span_end,
                "confidence": annotation.annotation_data.get("confidence", 1.0)
            }] if annotation.label and annotation.span_start is not None else []
        })
    
    elif sub_type == "pos":
        base_output.update({
            "tokens": [{
                "token": annotation.annotation_data.get("token", ""),
                "pos": annotation.label,
                "start": annotation.span_start,
                "end": annotation.span_end
            }] if annotation.label and annotation.span_start is not None else []
        })
    
    elif sub_type == "sentiment":
        base_output.update({
            "segments": [{
                "text": annotation.annotation_data.get("text", resource_text),
                "sentiment": annotation.label,
                "intensity": annotation.annotation_data.get("intensity", 0),
                "start": annotation.span_start,
                "end": annotation.span_end,
                "emotions": annotation.annotation_data.get("emotions", {})
            }] if annotation.label and annotation.span_start is not None else []
        })
    
    elif sub_type == "relation":
        base_output.update({
            "relations": [{
                "head": annotation.annotation_data.get("head_entity", {}),
                "tail": annotation.annotation_data.get("tail_entity", {}),
                "relation": annotation.annotation_data.get("relation_label", annotation.label),
                "confidence": annotation.annotation_data.get("confidence", 1.0)
            }] if annotation.annotation_data else []
        })
    
    elif sub_type == "span":
        base_output.update({
            "spans": [{
                "text": annotation.annotation_data.get("text", resource_text),
                "category": annotation.label,
                "subcategory": annotation.annotation_data.get("subcategory"),
                "start": annotation.span_start,
                "end": annotation.span_end,
                "priority": annotation.annotation_data.get("priority", 1),
                "overlaps_with": annotation.annotation_data.get("overlaps_with", [])
            }] if annotation.label and annotation.span_start is not None else []
        })
    
    elif sub_type == "classification":
        base_output.update({
            "document_classes": annotation.annotation_data.get("classes", []) if annotation.annotation_data else [],
            "classification_type": annotation.annotation_data.get("classification_type", "multi_class") if annotation.annotation_data else "multi_class"
        })
    
    elif sub_type == "dependency":
        base_output.update({
            "dependencies": [{
                "head": annotation.annotation_data.get("head_token", ""),
                "head_index": annotation.annotation_data.get("head_index", 0),
                "dependent": annotation.annotation_data.get("dependent_token", ""),
                "dependent_index": annotation.annotation_data.get("dependent_index", 0),
                "relation": annotation.annotation_data.get("relation", annotation.label)
            }] if annotation.annotation_data else [],
            "root_token": annotation.annotation_data.get("root_token", "") if annotation.annotation_data else ""
        })
    
    elif sub_type == "coreference":
        base_output.update({
            "chains": [{
                "chain_id": annotation.annotation_data.get("chain_id", ""),
                "mentions": [{
                    "text": annotation.annotation_data.get("mention_text", resource_text),
                    "start": annotation.span_start,
                    "end": annotation.span_end,
                    "type": annotation.annotation_data.get("mention_type", "proper_noun"),
                    "is_representative": annotation.annotation_data.get("is_representative", False)
                }] if annotation.span_start is not None else []
            }] if annotation.annotation_data else []
        })
    
    return base_output


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
    
    # Enqueue task with annotation_type='text' and annotation_sub_type
    queue = TextQueueStub(db, annotation_type="text")
    queue.enqueue(project_id, resource.id, "resource_uploaded", {
        "resource_id": resource.id,
        "uploaded_by": user_id,
        "annotation_sub_type": None  # Resource upload doesn't have sub-type
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
    
    # Enqueue task with annotation_type='text' and annotation_sub_type
    queue = TextQueueStub(db, annotation_type="text")
    queue.enqueue(project_id, resource.id, "resource_url_added", {
        "resource_id": resource.id,
        "url": url,
        "annotation_sub_type": None  # URL resource doesn't have sub-type
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
    
    # Enqueue with annotation_type='text', annotation_sub_type, and annotation_id
    queue = TextQueueStub(db, annotation_type="text")
    queue.enqueue(annotation.project_id, annotation.resource_id, "annotation_submitted", {
        "annotation_id": annotation.id,
        "annotator_id": user_id,
        "annotation_sub_type": annotation.annotation_sub_type
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
        
        # Use type-specific output format
        output_data = format_annotation_output(annotation)
        
        save_json_to_s3(output_data, s3_key)
        
        # Update annotation with S3 key
        update_annotation(db, annotation_id, {"output_s3_key": s3_key})
    
    # Enqueue with annotation_type='text', annotation_sub_type, and annotation_id
    queue = TextQueueStub(db, annotation_type="text")
    queue.enqueue(annotation.project_id, annotation.resource_id, "annotation_reviewed", {
        "annotation_id": annotation.id,
        "reviewer_id": reviewer_id,
        "action": action,
        "annotation_sub_type": annotation.annotation_sub_type
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
    # We return resource with optional full_content
    
    return {
        "id": resource.id,
        "project_id": resource.project_id,
        "name": resource.name,
        "source_type": resource.source_type,
        "s3_key": resource.s3_key,
        "external_url": resource.external_url,
        "content_preview": resource.content_preview,
        "file_size": resource.file_size,
        "uploaded_by": resource.uploaded_by,
        "created_at": resource.created_at,
        "status": resource.status,
        "full_content": full_content
    }
