"""
SQLAlchemy model for annotation tasks.
"""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from app.core.database import Base


class AnnotationTask(Base):
    """
    Task queue for annotation workflow with locking mechanism.
    
    Each resource (text or image) gets one task entry.
    Annotators claim tasks one at a time with automatic locking.
    """
    __tablename__ = "annotation_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(Integer, nullable=False)  # Polymorphic: text_resources.id or image_resources.id
    resource_type = Column(String(10), nullable=False)  # 'text' or 'image'
    annotator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Status: available -> locked -> in_progress -> submitted -> approved/rejected
    # Can also go: locked -> available (via skip or expiry)
    status = Column(
        String(20), 
        nullable=False, 
        default='available'
    )
    
    locked_at = Column(DateTime, nullable=True)
    lock_expires_at = Column(DateTime, nullable=True)
    annotation_id = Column(Integer, nullable=True)  # FK to annotation once created
    skipped_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = relationship("Project", backref="annotation_tasks")
    annotator = relationship("User", backref="annotation_tasks")
    
    # Indexes
    __table_args__ = (
        Index('idx_annotation_tasks_project_status', 'project_id', 'status'),
        Index('idx_annotation_tasks_annotator_status', 'annotator_id', 'status'),
        # Unique constraint for one task per resource
        # Note: This is also in the migration, but adding here for SQLAlchemy awareness
    )
    
    def __repr__(self):
        return f"<AnnotationTask {self.id} project={self.project_id} status={self.status}>"
    
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
    
    def lock(self, annotator_id: int, lock_duration_hours: int = 2):
        """Lock the task to an annotator."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        self.annotator_id = annotator_id
        self.status = 'locked'
        self.locked_at = now
        self.lock_expires_at = now + timedelta(hours=lock_duration_hours)
    
    def unlock(self):
        """Release the lock, returning task to pool."""
        self.annotator_id = None
        self.status = 'available'
        self.locked_at = None
        self.lock_expires_at = None
    
    def skip(self):
        """Skip the task, incrementing skip count and returning to pool."""
        self.skipped_count += 1
        self.unlock()
    
    def submit(self, annotation_id: int):
        """Mark task as submitted with annotation."""
        self.status = 'submitted'
        self.annotation_id = annotation_id
        self.locked_at = None
        self.lock_expires_at = None