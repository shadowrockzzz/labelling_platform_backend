"""
Shared review router for both text and image annotations.
Provides endpoints for multi-level review workflow with UUID tracking.
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project_assignment import ProjectAssignment
from app.annotations.shared.review_models import ReviewTask
from app.annotations.shared.review_crud import (
    get_review_task,
    get_next_review_task_for_reviewer,
    lock_review_task,
    approve_review_task,
    reject_review_task,
    mark_review_task_edited,
    get_or_create_review_task,
    build_review_chain_entry
)
from app.annotations.shared.review_schemas import (
    ReviewTaskResponse,
    ReviewActionRequest,
    StartReviewResponse,
    ReviewPoolStats
)


def create_review_router(
    annotation_type: str,
    get_annotation_by_id_func,
    get_resource_by_annotation_func,
    update_annotation_func,
    get_max_review_level_func
):
    """
    Factory function to create a review router for text or image annotations.
    
    Args:
        annotation_type: 'text' or 'image'
        get_annotation_by_id_func: Function to get annotation by ID
        get_resource_by_annotation_func: Function to get resource for annotation
        update_annotation_func: Function to update annotation
        get_max_review_level_func: Function to get max review level for project
    """
    router = APIRouter()
    
    def format_review_task_response(task: ReviewTask) -> dict:
        """Format a review task for response."""
        return {
            "id": task.id,
            "project_id": task.project_id,
            "annotation_id": task.annotation_id,
            "annotation_type": task.annotation_type,
            "review_level": task.review_level,
            "reviewer_id": task.reviewer_id,
            "status": task.status,
            "locked_at": task.locked_at,
            "lock_expires_at": task.lock_expires_at,
            "action": task.action,
            "action_comment": task.action_comment,
            "action_at": task.action_at,
            "previous_review_task_id": task.previous_review_task_id,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "short_id": task.short_id,
            "is_locked": task.is_locked if hasattr(task, 'is_locked') else False
        }
    
    @router.get("/projects/{project_id}/review-pool/start", response_model=StartReviewResponse)
    async def start_review(
        project_id: int,
        review_level: int = 1,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """
        Start reviewing - get next available task for this reviewer's level.
        
        If reviewer already has a locked task, returns that task.
        If not, locks and returns the next available task.
        """
        # Check user is assigned as reviewer at this level
        assignment = db.query(ProjectAssignment).filter(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.user_id == current_user.id,
            ProjectAssignment.role == 'reviewer',
            ProjectAssignment.review_level == review_level
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You are not assigned as a level {review_level} reviewer for this project"
            )
        
        # Get next available review task
        review_task = get_next_review_task_for_reviewer(
            db=db,
            project_id=project_id,
            review_level=review_level,
            reviewer_id=current_user.id
        )
        
        if not review_task:
            return StartReviewResponse(
                review_task=None,
                annotation=None,
                resource=None,
                message="No tasks available for review at your level",
                has_task=False
            )
        
        # Get the annotation
        annotation = get_annotation_by_id_func(db, review_task.annotation_id)
        if not annotation:
            # Clean up orphaned review task
            db.delete(review_task)
            db.commit()
            return StartReviewResponse(
                review_task=None,
                annotation=None,
                resource=None,
                message="Task no longer exists",
                has_task=False
            )
        
        # Get the resource
        resource = get_resource_by_annotation_func(db, annotation.id)
        
        return StartReviewResponse(
            review_task=format_review_task_response(review_task),
            annotation={
                "id": annotation.id,
                "resource_id": annotation.resource_id,
                "status": annotation.status,
                "current_review_level": annotation.current_review_level,
                "annotation_data": annotation.annotation_data,
                "annotator_task_id": str(annotation.annotator_task_id) if annotation.annotator_task_id else None,
                "review_chain": annotation.review_chain or [],
                "annotator_id": annotation.annotator_id,
                "created_at": annotation.created_at.isoformat() if annotation.created_at else None,
                "submitted_at": annotation.submitted_at.isoformat() if annotation.submitted_at else None
            },
            resource=resource,
            message="Task locked for review",
            has_task=True
        )
    
    @router.post("/review-tasks/{task_id}/action", response_model=ReviewTaskResponse)
    async def review_action(
        task_id: UUID,
        request: ReviewActionRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """
        Perform a review action: approve, reject, or edit.
        
        - Approve: Move to next review level, or mark as fully approved
        - Reject: Send back to previous level or annotator
        - Edit: Reviewer directly modifies the annotation
        """
        review_task = get_review_task(db, task_id)
        if not review_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review task not found"
            )
        
        # Verify this reviewer owns the task
        if review_task.reviewer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have this task locked"
            )
        
        # Get the annotation
        annotation = get_annotation_by_id_func(db, review_task.annotation_id)
        if not annotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotation not found"
            )
        
        # Get max review level for this project
        max_review_level = get_max_review_level_func(db, review_task.project_id)
        
        # Build review chain entry
        chain_entry = build_review_chain_entry(
            review_task=review_task,
            reviewer_id=current_user.id,
            action=request.action,
            comment=request.comment
        )
        
        if request.action == "approve":
            # Approve the review task
            approve_review_task(db, task_id, request.comment)
            
            # Update annotation
            if review_task.review_level >= max_review_level:
                # This was the final reviewer - mark as fully approved
                annotation.status = "approved"
                annotation.reviewed_at = datetime.utcnow()
                
                # Generate final output UUID
                annotation.final_output_uuid = uuid4()
                
                # Build final output data with all participant info
                participants = {
                    "annotator": {
                        "user_id": annotation.annotator_id,
                        "task_id": str(annotation.annotator_task_id) if annotation.annotator_task_id else None,
                        "submitted_at": annotation.submitted_at.isoformat() if annotation.submitted_at else None
                    }
                }
                
                # Add all reviewers from review chain
                review_chain = annotation.review_chain or []
                for entry in review_chain:
                    level = entry.get("review_level", 0)
                    participants[f"reviewer_level_{level}"] = {
                        "user_id": entry.get("reviewer_id"),
                        "task_id": entry.get("review_task_id"),
                        "action": entry.get("action"),
                        "acted_at": entry.get("acted_at")
                    }
                
                # Add current reviewer
                participants[f"reviewer_level_{review_task.review_level}"] = {
                    "user_id": current_user.id,
                    "task_id": str(review_task.id),
                    "action": "approved",
                    "acted_at": chain_entry["acted_at"]
                }
                
                # Build final output data
                annotation.final_output_data = {
                    "final_output_uuid": str(annotation.final_output_uuid),
                    "annotator_task_id": str(annotation.annotator_task_id) if annotation.annotator_task_id else None,
                    "annotation_id": annotation.id,
                    "resource_id": annotation.resource_id,
                    "project_id": annotation.project_id,
                    "participants": participants,
                    "review_chain": review_chain + [chain_entry],
                    "annotation_data": annotation.annotation_data,
                    "approved_at": datetime.utcnow().isoformat()
                }
            else:
                # Move to next review level
                annotation.status = "in_review"
                annotation.current_review_level = review_task.review_level + 1
                
                # Create review task for next level
                get_or_create_review_task(
                    db=db,
                    project_id=review_task.project_id,
                    annotation_id=annotation.id,
                    annotation_type=annotation_type,
                    review_level=review_task.review_level + 1,
                    previous_task_id=review_task.id
                )
            
            # Add to review chain
            if annotation.review_chain is None:
                annotation.review_chain = []
            annotation.review_chain.append(chain_entry)
            
            db.commit()
            
        elif request.action == "reject":
            # Reject the review task
            reject_review_task(db, task_id, request.comment)
            
            if review_task.review_level == 1:
                # Send back to annotator
                annotation.status = "rejected"
                annotation.current_review_level = 0
                annotation.review_comment = request.comment
            else:
                # Send back to previous reviewer level
                annotation.status = "in_review"
                annotation.current_review_level = review_task.review_level - 1
                
                # Create a new review task for previous level
                get_or_create_review_task(
                    db=db,
                    project_id=review_task.project_id,
                    annotation_id=annotation.id,
                    annotation_type=annotation_type,
                    review_level=review_task.review_level - 1,
                    previous_task_id=review_task.id
                )
            
            # Add to review chain
            if annotation.review_chain is None:
                annotation.review_chain = []
            annotation.review_chain.append(chain_entry)
            
            db.commit()
            
        elif request.action == "edit":
            # Reviewer is editing the annotation directly
            if not request.annotation_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="annotation_data is required for edit action"
                )
            
            # Update annotation data
            update_annotation_func(db, annotation.id, request.annotation_data)
            
            # Mark task as edited
            mark_review_task_edited(db, task_id, request.comment)
            
            # Add to review chain
            if annotation.review_chain is None:
                annotation.review_chain = []
            annotation.review_chain.append(chain_entry)
            
            db.commit()
        
        # Refresh and return
        review_task = get_review_task(db, task_id)
        return format_review_task_response(review_task)
    
    @router.post("/review-tasks/{task_id}/skip")
    async def skip_review(
        task_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """
        Skip a review task - release lock and get next available task.
        """
        review_task = get_review_task(db, task_id)
        if not review_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review task not found"
            )
        
        # Verify this reviewer owns the task
        if review_task.reviewer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have this task locked"
            )
        
        # Release the lock
        review_task.unlock()
        db.commit()
        
        # Get next task
        next_task = get_next_review_task_for_reviewer(
            db=db,
            project_id=review_task.project_id,
            review_level=review_task.review_level,
            reviewer_id=current_user.id
        )
        
        if not next_task:
            return {"message": "No more tasks available", "next_task": None}
        
        # Get annotation for next task
        annotation = get_annotation_by_id_func(db, next_task.annotation_id)
        resource = get_resource_by_annotation_func(db, annotation.id) if annotation else None
        
        return {
            "message": "Task skipped",
            "next_task": format_review_task_response(next_task),
            "annotation": {
                "id": annotation.id,
                "status": annotation.status,
                "annotation_data": annotation.annotation_data
            } if annotation else None,
            "resource": resource
        }
    
    @router.get("/projects/{project_id}/review-pool/stats", response_model=ReviewPoolStats)
    async def get_review_pool_stats(
        project_id: int,
        review_level: int = 1,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """
        Get statistics for the review pool at a specific level.
        """
        # Get counts
        total_available = db.query(ReviewTask).filter(
            ReviewTask.project_id == project_id,
            ReviewTask.review_level == review_level,
            ReviewTask.status == 'available'
        ).count()
        
        total_locked = db.query(ReviewTask).filter(
            ReviewTask.project_id == project_id,
            ReviewTask.review_level == review_level,
            ReviewTask.status == 'locked'
        ).count()
        
        total_completed = db.query(ReviewTask).filter(
            ReviewTask.project_id == project_id,
            ReviewTask.review_level == review_level,
            ReviewTask.status.in_(['approved', 'rejected'])
        ).count()
        
        my_locked_count = db.query(ReviewTask).filter(
            ReviewTask.project_id == project_id,
            ReviewTask.review_level == review_level,
            ReviewTask.status == 'locked',
            ReviewTask.reviewer_id == current_user.id
        ).count()
        
        return ReviewPoolStats(
            project_id=project_id,
            review_level=review_level,
            total_available=total_available,
            total_locked=total_locked,
            total_completed=total_completed,
            my_locked_count=my_locked_count
        )
    
    @router.get("/review-tasks/{task_id}", response_model=ReviewTaskResponse)
    async def get_review_task_details(
        task_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """Get details of a specific review task."""
        review_task = get_review_task(db, task_id)
        if not review_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review task not found"
            )
        
        return format_review_task_response(review_task)
    
    return router