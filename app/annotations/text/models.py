from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class TextResource(Base):
    """Represents a source text file/content for annotation."""
    __tablename__ = "text_resources"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(20), nullable=False)  # 'upload' or 'url'
    s3_key = Column(String(500), nullable=True)  # set when source_type='upload'
    external_url = Column(Text, nullable=True)  # set when source_type='url'
    content_preview = Column(Text, nullable=True)  # first 500 chars, cached for quick display
    file_size = Column(Integer, nullable=True)  # in bytes, NULL for url type
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="now()")
    status = Column(String(20), default="active")  # 'active' or 'archived'

    # Relationships
    project = relationship("Project", backref="text_resources")
    annotations = relationship("TextAnnotation", back_populates="resource", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_text_resources_project", "project_id"),
    )

    def __repr__(self):
        return f"<TextResource(id={self.id}, name='{self.name}', source_type='{self.source_type}')>"


class TextAnnotation(Base):
    """Represents one annotation task on one TextResource."""
    __tablename__ = "text_annotations"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("text_resources.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    annotator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null until assigned
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    annotation_type = Column(String(50), nullable=False, default="text")  # module-level: 'text', 'image', 'video', etc.
    annotation_sub_type = Column(String(50), nullable=True)  # sub-types: 'ner', 'pos', 'sentiment', 'relation', 'span', 'classification', 'dependency', 'coreference'
    status = Column(String(30), nullable=False, default="pending")  # uses AnnotationStatus enum values
    label = Column(String(100), nullable=True)
    span_start = Column(Integer, nullable=True)  # char index start (for NER spans)
    span_end = Column(Integer, nullable=True)  # char index end
    annotation_data = Column(JSON, nullable=True)  # flexible payload for any sub-type
    review_comment = Column(Text, nullable=True)
    output_s3_key = Column(String(500), nullable=True)  # path to saved output JSON
    created_at = Column(DateTime(timezone=True), server_default="now()")
    updated_at = Column(DateTime(timezone=True), onupdate="now()")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    resource = relationship("TextResource", back_populates="annotations")
    annotator = relationship("User", foreign_keys=[annotator_id], backref="text_annotations_created")
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="text_annotations_reviewed")
    review_corrections = relationship("ReviewCorrection", back_populates="annotation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_text_annotations_project", "project_id"),
        Index("idx_text_annotations_resource", "resource_id"),
        Index("idx_text_annotations_annotator", "annotator_id"),
        Index("idx_text_annotations_status", "status"),
    )

    def __repr__(self):
        return f"<TextAnnotation(id={self.id}, resource_id={self.resource_id}, sub_type='{self.annotation_sub_type}', status='{self.status}')>"


class TextAnnotationQueue(Base):
    """Queue table for annotation tasks. Supports multiple projects and annotation types."""
    __tablename__ = "text_annotation_queue"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    annotation_type = Column(String(50), nullable=False, default="text", index=True)  # 'text', 'image', 'video', etc.
    resource_id = Column(Integer, ForeignKey("text_resources.id"), nullable=True)
    annotation_id = Column(Integer, ForeignKey("text_annotations.id"), nullable=True)
    task_type = Column(String(50), nullable=False)  # 'create', 'review', 'output'
    status = Column(String(20), default="pending")  # 'pending','processing','done','failed'
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default="now()")
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", backref="queue_tasks")
    resource = relationship("TextResource", backref="queue_tasks")
    annotation = relationship("TextAnnotation", backref="queue_tasks")

    # Composite index for efficient querying by project_id + annotation_type
    __table_args__ = (
        Index("idx_queue_project_annotation", "project_id", "annotation_type"),
    )

    def __repr__(self):
        return f"<TextAnnotationQueue(id={self.id}, project_id={self.project_id}, annotation_type='{self.annotation_type}', task_type='{self.task_type}', status='{self.status}')>"