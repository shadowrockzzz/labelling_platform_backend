"""
CRUD operations for annotation tasks with atomic locking.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

from .task_models import AnnotationTask
from .task_schemas import (
    AnnotationTaskCreate,
    AnnotationTaskResponse,
    AnnotationTaskWithResource,
    AnnotationTaskStats,
    AnnotationTaskClaimResponse,
    SeedTasksResponse,
)


class AnnotationTaskCRUD:
    """CRUD operations for annotation tasks."""
    
    # Lock duration in hours
    LOCK_DURATION_HOURS = 2
    
    def __init__(self, db: Session, resource_type: str):
        """
        Initialize CRUD with database session and resource type.
        
        Args:
            db: SQLAlchemy session
            resource_type: 'text' or 'image'
        """
        self.db = db
        self.resource_type = resource_type
    
    def create_task(self, project_id: int, resource_id: int) -> AnnotationTask:
        """
        Create a new annotation task for a resource.
        
        Args:
            project_id: Project ID
            resource_id: Resource ID (text_resources.id or image_resources.id)
            
        Returns:
            Created AnnotationTask
        """
        # Check if task already exists
        existing = self.db.query(AnnotationTask).filter(
            AnnotationTask.project_id == project_id,
            AnnotationTask.resource_id == resource_id,
            AnnotationTask.resource_type == self.resource_type
        ).first()
        
        if existing:
            return existing
        
        task = AnnotationTask(
            project_id=project_id,
            resource_id=resource_id,
            resource_type=self.resource_type,
            status='available'
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def get_task(self, task_id: UUID) -> Optional[AnnotationTask]:
        """Get a task by ID."""
        return self.db.query(AnnotationTask).filter(
            AnnotationTask.id == task_id
        ).first()
    
    def get_task_with_resource(self, task_id: UUID, resource_getter) -> Optional[AnnotationTaskWithResource]:
        """
        Get a task with embedded resource data.
        
        Args:
            task_id: Task UUID
            resource_getter: Function to get resource by ID
            
        Returns:
            AnnotationTaskWithResource or None
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        resource = resource_getter(task.resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource {task.resource_id} not found"
            )
        
        return self._build_task_with_resource(task, resource)
    
    def _build_task_with_resource(self, task: AnnotationTask, resource: Any, 
                                    resource_content: str = None, 
                                    resource_url: str = None) -> AnnotationTaskWithResource:
        """Build AnnotationTaskWithResource from task and resource."""
        resource_dict = {}
        if hasattr(resource, '__dict__'):
            resource_dict = {k: v for k, v in resource.__dict__.items() 
                           if not k.startswith('_')}
        
        # For image resources, we need to generate a presigned URL from the file_path
        if self.resource_type == 'image' and not resource_url:
            # First check if URL is already in resource_dict
            if isinstance(resource_dict, dict):
                resource_url = resource_dict.get('image_url') or resource_dict.get('url') or resource_dict.get('presigned_url')
            
            # If no URL in dict, we need to generate it from file_path
            if not resource_url and hasattr(resource, 'file_path') and resource.file_path:
                try:
                    # Import here to avoid circular imports
                    from app.annotations.image.storage import get_presigned_url
                    resource_url = get_presigned_url(resource.file_path)
                except Exception as e:
                    logger.error(f"Failed to generate presigned URL: {e}")
            
            # Fallback checks
            if not resource_url and hasattr(resource, 'image_url'):
                resource_url = resource.image_url
            if not resource_url and hasattr(resource, 'url'):
                resource_url = resource.url
        
        # For text resources, extract content if available
        if self.resource_type == 'text' and not resource_content:
            if isinstance(resource_dict, dict):
                resource_content = resource_dict.get('full_content') or resource_dict.get('content_preview')
            if not resource_content and hasattr(resource, 'full_content'):
                resource_content = resource.full_content
            if not resource_content and hasattr(resource, 'content_preview'):
                resource_content = resource.content_preview
        
        return AnnotationTaskWithResource(
            id=task.id,
            project_id=task.project_id,
            resource_id=task.resource_id,
            resource_type=task.resource_type,
            annotator_id=task.annotator_id,
            status=task.status,
            locked_at=task.locked_at,
            lock_expires_at=task.lock_expires_at,
            annotation_id=task.annotation_id,
            skipped_count=task.skipped_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            short_id=task.short_id,
            resource=resource_dict,
            resource_content=resource_content,
            resource_url=resource_url
        )
    
    def claim_task_atomic(self, project_id: int, annotator_id: int, 
                           resource_getter) -> AnnotationTaskClaimResponse:
        """
        Atomically claim the next available task using SELECT FOR UPDATE SKIP LOCKED.
        
        This prevents race conditions when multiple users try to claim tasks simultaneously.
        
        Args:
            project_id: Project ID
            annotator_id: User ID claiming the task
            resource_getter: Function to get resource by ID
            
        Returns:
            AnnotationTaskClaimResponse with claimed task
            
        Raises:
            HTTPException: If no tasks available or user already has a locked task
        """
        # First check if user already has a locked task in this project
        existing_locked = self.db.query(AnnotationTask).filter(
            AnnotationTask.project_id == project_id,
            AnnotationTask.annotator_id == annotator_id,
            AnnotationTask.status == 'locked'
        ).first()
        
        if existing_locked:
            # Return the existing locked task
            resource = resource_getter(existing_locked.resource_id)
            task_with_resource = self._build_task_with_resource(existing_locked, resource)
            return AnnotationTaskClaimResponse(
                task=task_with_resource,
                message="Resumed your existing task"
            )
        
        # Use raw SQL for atomic claim with SKIP LOCKED
        claim_sql = text("""
            UPDATE annotation_tasks 
            SET status = 'locked',
                annotator_id = :annotator_id,
                locked_at = NOW(),
                lock_expires_at = NOW() + INTERVAL ':lock_hours hours',
                updated_at = NOW()
            WHERE id = (
                SELECT id FROM annotation_tasks 
                WHERE project_id = :project_id 
                AND resource_type = :resource_type
                AND status = 'available'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, project_id, resource_id, resource_type, annotator_id, 
                      status, locked_at, lock_expires_at, annotation_id, 
                      skipped_count, created_at, updated_at
        """)
        
        result = self.db.execute(
            claim_sql,
            {
                "project_id": project_id,
                "resource_type": self.resource_type,
                "annotator_id": annotator_id,
                "lock_hours": self.LOCK_DURATION_HOURS
            }
        )
        row = result.fetchone()
        self.db.commit()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tasks available in this project"
            )
        
        # Convert row to task object
        task = AnnotationTask(
            id=row[0],
            project_id=row[1],
            resource_id=row[2],
            resource_type=row[3],
            annotator_id=row[4],
            status=row[5],
            locked_at=row[6],
            lock_expires_at=row[7],
            annotation_id=row[8],
            skipped_count=row[9],
            created_at=row[10],
            updated_at=row[11]
        )
        
        # Get resource
        resource = resource_getter(task.resource_id)
        task_with_resource = self._build_task_with_resource(task, resource)
        
        return AnnotationTaskClaimResponse(
            task=task_with_resource,
            message=f"Task claimed successfully. Lock expires in {self.LOCK_DURATION_HOURS} hours."
        )
    
    def _update_resource_pool_status(self, resource_id: int, pool_status: str, 
                                       locked_by_user_id: int = None) -> None:
        """
        Update the pool_status on the resource table.
        
        Args:
            resource_id: Resource ID
            pool_status: New pool status ('available', 'locked', 'completed', 'skipped')
            locked_by_user_id: User ID who locked the resource (or None to clear)
        """
        if self.resource_type == 'image':
            from app.annotations.image.models import ImageResource
            resource = self.db.query(ImageResource).filter(
                ImageResource.id == resource_id
            ).first()
        else:
            from app.annotations.text.models import TextResource
            resource = self.db.query(TextResource).filter(
                TextResource.id == resource_id
            ).first()
        
        if resource:
            resource.pool_status = pool_status
            if locked_by_user_id:
                resource.locked_by_user_id = locked_by_user_id
                resource.locked_at = datetime.utcnow()
            else:
                resource.locked_by_user_id = None
                resource.locked_at = None
            self.db.add(resource)
    
    def claim_task_fallback(self, project_id: int, annotator_id: int,
                             resource_getter) -> AnnotationTaskClaimResponse:
        """
        Fallback claim method for databases without SKIP LOCKED support.
        
        Uses application-level locking with unique constraint.
        """
        # Check for existing locked task
        existing_locked = self.db.query(AnnotationTask).filter(
            AnnotationTask.project_id == project_id,
            AnnotationTask.annotator_id == annotator_id,
            AnnotationTask.status == 'locked'
        ).first()
        
        if existing_locked:
            resource = resource_getter(existing_locked.resource_id)
            task_with_resource = self._build_task_with_resource(existing_locked, resource)
            return AnnotationTaskClaimResponse(
                task=task_with_resource,
                message="Resumed your existing task"
            )
        
        # Find first available task
        task = self.db.query(AnnotationTask).filter(
            AnnotationTask.project_id == project_id,
            AnnotationTask.resource_type == self.resource_type,
            AnnotationTask.status == 'available'
        ).order_by(AnnotationTask.created_at.asc()).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tasks available in this project"
            )
        
        # Lock it
        task.lock(annotator_id, self.LOCK_DURATION_HOURS)
        
        # Update resource pool status
        self._update_resource_pool_status(task.resource_id, 'locked', annotator_id)
        
        self.db.commit()
        self.db.refresh(task)
        
        resource = resource_getter(task.resource_id)
        task_with_resource = self._build_task_with_resource(task, resource)
        
        return AnnotationTaskClaimResponse(
            task=task_with_resource,
            message=f"Task claimed successfully. Lock expires in {self.LOCK_DURATION_HOURS} hours."
        )
    
    def skip_task(self, task_id: UUID, annotator_id: int) -> Tuple[bool, str]:
        """
        Skip a task, returning it to the pool.
        
        Args:
            task_id: Task UUID
            annotator_id: User ID (must be the task's owner)
            
        Returns:
            Tuple of (success, message)
        """
        task = self.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.annotator_id != annotator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only skip your own tasks"
            )
        
        if task.status not in ['locked', 'in_progress']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot skip task with status '{task.status}'"
            )
        
        task.skip()
        
        # Update resource pool status - set back to available
        self._update_resource_pool_status(task.resource_id, 'available')
        
        self.db.commit()
        
        return True, "Task skipped and returned to pool"
    
    def submit_task(self, task_id: UUID, annotator_id: int, annotation_id: int) -> Tuple[bool, str]:
        """
        Mark a task as submitted with the annotation ID.
        
        Args:
            task_id: Task UUID
            annotator_id: User ID (must be the task's owner)
            annotation_id: Created annotation ID
            
        Returns:
            Tuple of (success, message)
        """
        task = self.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.annotator_id != annotator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only submit your own tasks"
            )
        
        if task.status not in ['locked', 'in_progress']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit task with status '{task.status}'"
            )
        
        task.submit(annotation_id)
        
        # Update resource pool status - set to completed (clear lock)
        self._update_resource_pool_status(task.resource_id, 'completed')
        
        self.db.commit()
        
        return True, "Task submitted successfully"
    
    def get_my_active_task(self, project_id: int, annotator_id: int, 
                           resource_getter) -> Optional[AnnotationTaskWithResource]:
        """
        Get the user's currently active task in a project.
        
        Args:
            project_id: Project ID
            annotator_id: User ID
            resource_getter: Function to get resource by ID
            
        Returns:
            Active task with resource or None
        """
        task = self.db.query(AnnotationTask).filter(
            AnnotationTask.project_id == project_id,
            AnnotationTask.annotator_id == annotator_id,
            AnnotationTask.status.in_(['locked', 'in_progress'])
        ).first()
        
        if not task:
            return None
        
        resource = resource_getter(task.resource_id)
        return self._build_task_with_resource(task, resource)
    
    def get_task_stats(self, project_id: int) -> AnnotationTaskStats:
        """
        Get statistics for tasks in a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            AnnotationTaskStats
        """
        from sqlalchemy import func
        
        # Get counts by status
        counts = self.db.query(
            AnnotationTask.status,
            func.count(AnnotationTask.id)
        ).filter(
            AnnotationTask.project_id == project_id,
            AnnotationTask.resource_type == self.resource_type
        ).group_by(AnnotationTask.status).all()
        
        stats = AnnotationTaskStats()
        for status_val, count in counts:
            stats.total += count
            if status_val == 'available':
                stats.available = count
            elif status_val == 'locked':
                stats.locked = count
            elif status_val == 'in_progress':
                stats.in_progress = count
            elif status_val == 'submitted':
                stats.submitted = count
            elif status_val == 'approved':
                stats.approved = count
            elif status_val == 'rejected':
                stats.rejected = count
        
        return stats
    
    def seed_tasks_from_resources(self, project_id: int, 
                                    resource_ids: List[int] = None) -> SeedTasksResponse:
        """
        Create tasks for resources that don't have them yet.
        
        Args:
            project_id: Project ID
            resource_ids: Specific resource IDs to seed, or None for all
            
        Returns:
            SeedTasksResponse with counts
        """
        created_count = 0
        skipped_count = 0
        
        for resource_id in resource_ids or []:
            try:
                task = self.create_task(project_id, resource_id)
                if task.created_at == task.updated_at:
                    created_count += 1
                else:
                    skipped_count += 1
            except Exception:
                skipped_count += 1
        
        return SeedTasksResponse(
            created_count=created_count,
            skipped_count=skipped_count,
            message=f"Created {created_count} tasks, skipped {skipped_count} existing"
        )
    
    def release_expired_locks(self) -> int:
        """
        Release all expired locks.
        
        Returns:
            Number of locks released
        """
        expired_tasks = self.db.query(AnnotationTask).filter(
            AnnotationTask.status == 'locked',
            AnnotationTask.lock_expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_tasks)
        for task in expired_tasks:
            task.unlock()
        
        self.db.commit()
        return count
    
    def validate_task_ownership(self, task_id: UUID, user_id: int, 
                                 allow_reviewer: bool = False) -> AnnotationTask:
        """
        Validate that a user owns a task or is a reviewer/admin.
        
        Args:
            task_id: Task UUID
            user_id: User ID
            allow_reviewer: Allow reviewers and admins to access
            
        Returns:
            The task if valid
            
        Raises:
            HTTPException: If not authorized
        """
        task = self.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.annotator_id == user_id:
            return task
        
        if allow_reviewer:
            # Check if user is reviewer/admin (caller should verify role)
            return task
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this task"
        )