"""
SQLAlchemy model for review tasks with UUID tracking.
"""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from app.core.database import Base


class ReviewTask(Base):
    """
    Review task queue with UUID tracking per review level.
    
    Each review stage (level 1, level 2, etc.) gets its own ReviewTask with a unique UUID.
    This provides full audit trail from annotation through all review stages.
    """
    __tablename__ = "review_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    annotation_id = Column(Integer, nullable=False)  # Polymorphic: text_annotations.id or image_annotations.id
    annotation_type = Column(String(10), nullable=False)  # 'text' or 'image'
    review_level = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Status: available -> locked -> in_review -> approved/rejected
    status = Column(String(20), nullable=False, default='available')
    
    # Locking mechanism
    locked_at = Column(DateTime(timezone=True), nullable=True)
    lock_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Actions taken at this review stage
    action = Column(String(20), nullable=True)  # approved, rejected, edited
    action_comment = Column(Text, nullable=True)
    action_at = Column(DateTime(timezone=True), nullable=True)
    
    # Link to previous review task (for audit chain)
    previous_review_task_id = Column(UUID(as_uuid=True), ForeignKey("review_tasks.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = relationship("Project", backref="review_tasks")
    reviewer = relationship("User", backref="review_tasks")
    previous_task = relationship("ReviewTask", remote_side=[id], backref="next_tasks")
    
    # Indexes
    __table_args__ = (
        Index('idx_review_tasks_project_level_status', 'project_id', 'review_level', 'status'),
        Index('idx_review_tasks_annotation', 'annotation_id', 'annotation_type'),
        Index('idx_review_tasks_reviewer', 'reviewer_id'),
    )
    
    def __repr__(self):
        return f"<ReviewTask {str(self.id)[:8]} level={self.review_level} status={self.status}>"
    
    @property
    def short_id(self) -> str:
        """Return first 8 characters of UUID for display."""
        return str(self.id)[:8]
    
    @property
    def is_locked(self) -> bool:
        """Check if task is currently locked."""
        return self.status == 'locked' and self.lock_expires_at and self.lock_expires_at > datetime.now(timezone.utc)
    
    @property
    def is_expired(self) -> bool:
        """Check if lock has expired."""
        if self.lock_expires_at is None:
            return False
        return self.status == 'locked' and self.lock_expires_at < datetime.now(timezone.utc)
    
    def lock(self, reviewer_id: int, lock_duration_minutes: int = 30):
        """Lock the task to a reviewer."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        self.reviewer_id = reviewer_id
        self.status = 'locked'
        self.locked_at = now
        self.lock_expires_at = now + timedelta(minutes=lock_duration_minutes)
    
    def unlock(self):
        """Release the lock, returning task to pool."""
        self.reviewer_id = None
        self.status = 'available'
        self.locked_at = None
        self.lock_expires_at = None
    
    def approve(self, comment: str = None):
        """Mark task as approved."""
        self.status = 'approved'
        self.action = 'approved'
        self.action_comment = comment
        self.action_at = datetime.now(timezone.utc)
        self.locked_at = None
        self.lock_expires_at = None
    
    def reject(self, comment: str = None):
        """Mark task as rejected."""
        self.status = 'rejected'
        self.action = 'rejected'
        self.action_comment = comment
        self.action_at = datetime.now(timezone.utc)
        self.locked_at = None
        self.lock_expires_at = None
    
    def edit(self, comment: str = None):
        """Mark that reviewer made edits."""
        self.action = 'edited'
        self.action_comment = comment
        self.action_at = datetime.now(timezone.utc)
