"""
CRUD operations for review tasks with UUID tracking.
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.annotations.shared.review_models import ReviewTask


def get_review_task(db: Session, task_id: UUID) -> Optional[ReviewTask]:
    """Get a review task by ID."""
    return db.query(ReviewTask).filter(ReviewTask.id == task_id).first()


def get_review_tasks_by_annotation(
    db: Session, 
    annotation_id: int, 
    annotation_type: str
) -> List[ReviewTask]:
    """Get all review tasks for an annotation."""
    return db.query(ReviewTask).filter(
        ReviewTask.annotation_id == annotation_id,
        ReviewTask.annotation_type == annotation_type
    ).order_by(ReviewTask.review_level).all()


def get_available_review_tasks(
    db: Session,
    project_id: int,
    review_level: int,
    reviewer_id: Optional[int] = None
) -> List[ReviewTask]:
    """
    Get available review tasks for a specific level.
    
    Returns tasks that are:
    - At the specified review level
    - Status is 'available' OR locked but expired
    - Not locked by another reviewer
    """
    now = datetime.utcnow()
    
    query = db.query(ReviewTask).filter(
        ReviewTask.project_id == project_id,
        ReviewTask.review_level == review_level,
        or_(
            ReviewTask.status == 'available',
            and_(
                ReviewTask.status == 'locked',
                ReviewTask.lock_expires_at < now
            )
        )
    )
    
    # If reviewer_id provided, also include tasks already locked by this reviewer
    if reviewer_id:
        query = query.filter(
            or_(
                ReviewTask.reviewer_id.is_(None),
                ReviewTask.reviewer_id == reviewer_id
            )
        )
    
    return query.order_by(ReviewTask.created_at).all()


def get_or_create_review_task(
    db: Session,
    project_id: int,
    annotation_id: int,
    annotation_type: str,
    review_level: int,
    previous_task_id: Optional[UUID] = None
) -> ReviewTask:
    """
    Get existing review task or create a new one.
    
    If a task already exists for this annotation/level with status 'approved' or 'rejected',
    a NEW task is created (for re-review after rejection).
    """
    # Check for existing available/pending task
    existing = db.query(ReviewTask).filter(
        ReviewTask.annotation_id == annotation_id,
        ReviewTask.annotation_type == annotation_type,
        ReviewTask.review_level == review_level,
        ReviewTask.status.in_(['available', 'locked'])
    ).first()
    
    if existing:
        return existing
    
    # Create new task
    new_task = ReviewTask(
        project_id=project_id,
        annotation_id=annotation_id,
        annotation_type=annotation_type,
        review_level=review_level,
        previous_review_task_id=previous_task_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def lock_review_task(
    db: Session,
    task_id: UUID,
    reviewer_id: int,
    lock_duration_minutes: int = 30
) -> Optional[ReviewTask]:
    """
    Lock a review task to a reviewer.
    
    Returns None if task is already locked by another reviewer.
    """
    task = get_review_task(db, task_id)
    if not task:
        return None
    
    # Check if already locked by another reviewer
    if task.is_locked and task.reviewer_id != reviewer_id:
        return None
    
    # Lock the task
    task.lock(reviewer_id, lock_duration_minutes)
    db.commit()
    db.refresh(task)
    return task


def unlock_review_task(db: Session, task_id: UUID) -> Optional[ReviewTask]:
    """Release the lock on a review task."""
    task = get_review_task(db, task_id)
    if not task:
        return None
    
    task.unlock()
    db.commit()
    db.refresh(task)
    return task


def approve_review_task(
    db: Session,
    task_id: UUID,
    comment: Optional[str] = None
) -> Optional[ReviewTask]:
    """Mark a review task as approved."""
    task = get_review_task(db, task_id)
    if not task:
        return None
    
    task.approve(comment)
    db.commit()
    db.refresh(task)
    return task


def reject_review_task(
    db: Session,
    task_id: UUID,
    comment: Optional[str] = None
) -> Optional[ReviewTask]:
    """Mark a review task as rejected."""
    task = get_review_task(db, task_id)
    if not task:
        return None
    
    task.reject(comment)
    db.commit()
    db.refresh(task)
    return task


def mark_review_task_edited(
    db: Session,
    task_id: UUID,
    comment: Optional[str] = None
) -> Optional[ReviewTask]:
    """Mark that a reviewer made edits to the annotation."""
    task = get_review_task(db, task_id)
    if not task:
        return None
    
    task.edit(comment)
    db.commit()
    db.refresh(task)
    return task


def get_next_review_task_for_reviewer(
    db: Session,
    project_id: int,
    review_level: int,
    reviewer_id: int
) -> Optional[ReviewTask]:
    """
    Get the next available review task for a reviewer.
    
    First checks if reviewer already has a locked task.
    If not, locks and returns the next available task.
    """
    # Check for existing locked task
    locked_task = db.query(ReviewTask).filter(
        ReviewTask.project_id == project_id,
        ReviewTask.review_level == review_level,
        ReviewTask.reviewer_id == reviewer_id,
        ReviewTask.status == 'locked'
    ).first()
    
    if locked_task:
        # Check if lock is still valid
        if locked_task.is_locked:
            return locked_task
        else:
            # Lock expired, extend it
            locked_task.lock(reviewer_id)
            db.commit()
            db.refresh(locked_task)
            return locked_task
    
    # Get next available task
    now = datetime.utcnow()
    next_task = db.query(ReviewTask).filter(
        ReviewTask.project_id == project_id,
        ReviewTask.review_level == review_level,
        or_(
            ReviewTask.status == 'available',
            and_(
                ReviewTask.status == 'locked',
                ReviewTask.lock_expires_at < now
            )
        )
    ).order_by(ReviewTask.created_at).first()
    
    if not next_task:
        return None
    
    # Lock it
    next_task.lock(reviewer_id)
    db.commit()
    db.refresh(next_task)
    return next_task


def release_expired_locks(db: Session) -> int:
    """
    Release all expired locks.
    
    Returns the number of locks released.
    """
    now = datetime.utcnow()
    
    expired_tasks = db.query(ReviewTask).filter(
        ReviewTask.status == 'locked',
        ReviewTask.lock_expires_at < now
    ).all()
    
    count = 0
    for task in expired_tasks:
        task.unlock()
        count += 1
    
    if count > 0:
        db.commit()
    
    return count


def build_review_chain_entry(
    review_task: ReviewTask,
    reviewer_id: int,
    action: str,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a review chain entry for storing in annotation's review_chain.
    """
    return {
        "review_task_id": str(review_task.id),
        "review_level": review_task.review_level,
        "reviewer_id": reviewer_id,
        "action": action,  # approved, rejected, edited
        "comment": comment,
        "acted_at": datetime.utcnow().isoformat()
    }