"""
Image Annotation Models

Database models for image annotation functionality.
Mirrors the structure of text annotation models but with image-specific fields.

Supported annotation types:
- bounding_box: Rectangle annotations (x, y, width, height)
- polygon: Multi-point polygon annotations
- segmentation: Pixel-level segmentation masks
- keypoint: Keypoint/landmark annotations
- classification: Image-level classification labels
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text, Index, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime


class ImageResource(Base):
    """
    Represents an image file for annotation.
    Stores metadata about the image including dimensions, file path in MinIO/S3,
    and other relevant information.
    """
    __tablename__ = "image_resources"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    
    # File storage info
    file_path = Column(String(500), nullable=True)  # Path in MinIO/S3: images/{project_id}/{resource_id}/original.{ext}
    thumbnail_path = Column(String(500), nullable=True)  # Thumbnail path: images/{project_id}/{resource_id}/thumbnail.jpg
    
    # Image dimensions
    width = Column(Integer, nullable=True)  # Image width in pixels
    height = Column(Integer, nullable=True)  # Image height in pixels
    
    # File info
    file_size = Column(Integer, nullable=True)  # File size in bytes
    mime_type = Column(String(50), nullable=True)  # e.g., 'image/jpeg', 'image/png'
    
    # Source type
    source_type = Column(String(20), nullable=False, default="file")  # 'file' or 'url'
    external_url = Column(Text, nullable=True)  # Original URL if source_type='url'
    
    # Additional metadata (EXIF data, etc.)
    image_metadata = Column(JSON, nullable=True)  # Stores EXIF and other metadata
    
    # Status
    is_archived = Column(Boolean, default=False)
    
    # Resource pool fields
    pool_status = Column(String(20), default="available")  # 'available', 'locked', 'completed', 'skipped'
    locked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default="now()")
    modified_at = Column(DateTime(timezone=True), onupdate="now()")

    # Relationships
    project = relationship("Project", backref="image_resources")
    uploader = relationship("User", foreign_keys=[uploader_id], backref="uploaded_image_resources")
    locked_by = relationship("User", foreign_keys=[locked_by_user_id], backref="locked_image_resources")
    annotations = relationship("ImageAnnotation", back_populates="resource", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_image_resources_project", "project_id"),
        Index("idx_image_resources_uploader", "uploader_id"),
        Index("idx_image_resources_archived", "is_archived"),
        Index("idx_image_resources_pool_status", "pool_status"),
    )

    def __repr__(self):
        return f"<ImageResource(id={self.id}, name='{self.name}', dimensions={self.width}x{self.height}, pool_status='{self.pool_status}')>"


class ImageAnnotation(Base):
    """
    Represents an annotation on an ImageResource.
    Supports multiple annotation sub-types with flexible JSON data storage.
    
    Annotation sub-types:
    - bounding_box: { boxes: [{ id, x, y, width, height, label, color, confidence }] }
    - polygon: { polygons: [{ id, points: [[x,y], ...], label, color, closed }] }
    - segmentation: { segments: [{ id, mask_path, label, color, area }] }
    - keypoint: { keypoints: [{ id, points: {name: [x,y]}, label, skeleton, visibility }] }
    - classification: { classifications: [{ id, label, confidence, attributes }] }
    """
    __tablename__ = "image_annotations"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("image_resources.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    annotator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Annotation type info
    annotation_type = Column(String(50), nullable=False, default="image")  # Always 'image' for this module
    annotation_sub_type = Column(String(50), nullable=False, default="bounding_box")  
    # Options: 'bounding_box', 'polygon', 'segmentation', 'keypoint', 'classification'
    
    # Status
    status = Column(String(30), nullable=False, default="draft")  
    # Options: 'draft', 'submitted', 'in_review', 'approved', 'rejected', 'pending_correction'
    
    # Multi-level review
    current_review_level = Column(Integer, default=0)  # 0=with annotator, 1=with level-1 reviewer, 2=with level-2, etc.
    
    # Annotation data - flexible JSON structure based on sub_type
    annotation_data = Column(JSON, nullable=True)
    
    # Review info
    review_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Review locking for pool mode
    review_locked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_locked_at = Column(DateTime(timezone=True), nullable=True)
    
    # UUID tracking for annotation and review chain
    annotator_task_id = Column(UUID(as_uuid=True), nullable=True)  # Links to AnnotationTask
    review_chain = Column(JSONB, default=list)  # List of review actions with UUIDs and user IDs
    final_output_uuid = Column(UUID(as_uuid=True), nullable=True)  # Generated when fully approved
    final_output_data = Column(JSONB, nullable=True)  # Final approved annotation with all metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default="now()")
    modified_at = Column(DateTime(timezone=True), onupdate="now()")
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    resource = relationship("ImageResource", back_populates="annotations")
    annotator = relationship("User", foreign_keys=[annotator_id], backref="image_annotations_created")
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="image_annotations_reviewed")
    review_lock_user = relationship("User", foreign_keys=[review_locked_by], backref="review_locked_image_annotations")
    corrections = relationship("ImageReviewCorrection", back_populates="annotation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_image_annotations_project", "project_id"),
        Index("idx_image_annotations_resource", "resource_id"),
        Index("idx_image_annotations_annotator", "annotator_id"),
        Index("idx_image_annotations_status", "status"),
        Index("idx_image_annotations_sub_type", "annotation_sub_type"),
        Index("idx_image_annotations_review_level", "current_review_level"),
    )

    def __repr__(self):
        return f"<ImageAnnotation(id={self.id}, resource_id={self.resource_id}, sub_type='{self.annotation_sub_type}', status='{self.status}', review_level={self.current_review_level})>"


class ImageReviewCorrection(Base):
    """
    Represents a correction suggestion from a reviewer to an annotator.
    Allows reviewers to propose changes without directly modifying the annotation.
    The original annotator can accept or reject the correction.
    """
    __tablename__ = "image_review_corrections"

    id = Column(Integer, primary_key=True, index=True)
    annotation_id = Column(Integer, ForeignKey("image_annotations.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Corrected data
    corrected_data = Column(JSON, nullable=False)  # The proposed correction
    
    # Status
    status = Column(String(20), nullable=False, default="pending")  
    # Options: 'pending', 'accepted', 'rejected'
    
    # Review level tracking
    reviewer_level = Column(Integer, nullable=True)  # Which review level made this correction
    
    # Comments
    comment = Column(Text, nullable=True)  # Reviewer's comment about the correction
    annotator_response = Column(Text, nullable=True)  # Annotator's response when accepting/rejecting
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default="now()")
    modified_at = Column(DateTime(timezone=True), onupdate="now()")

    # Relationships
    annotation = relationship("ImageAnnotation", back_populates="corrections")
    reviewer = relationship("User", backref="image_review_corrections")

    __table_args__ = (
        Index("idx_image_corrections_annotation", "annotation_id"),
        Index("idx_image_corrections_reviewer", "reviewer_id"),
        Index("idx_image_corrections_status", "status"),
    )

    def __repr__(self):
        return f"<ImageReviewCorrection(id={self.id}, annotation_id={self.annotation_id}, status='{self.status}')>"


class ImageAnnotationQueue(Base):
    """
    Queue table for image annotation tasks.
    Supports task management for annotation and review workflows.
    """
    __tablename__ = "image_annotation_queue"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("image_resources.id"), nullable=True)
    annotation_id = Column(Integer, ForeignKey("image_annotations.id"), nullable=True)
    
    # Task info
    task_type = Column(String(50), nullable=False)  # 'annotate', 'review', 'export', 'review_started', 'review_approved_level_n', 'review_rejected_level_n'
    status = Column(String(20), default="pending")  # 'pending', 'processing', 'done', 'failed'
    priority = Column(Integer, default=0)  # Higher priority = processed first
    
    # Assigned user
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Multi-level review tracking
    review_level = Column(Integer, nullable=True)  # Which review level this task is for
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Which reviewer handled this
    
    # Additional data
    payload = Column(JSON, nullable=True)  # Additional task configuration
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default="now()")
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", backref="image_queue_tasks")
    resource = relationship("ImageResource", backref="queue_tasks")
    annotation = relationship("ImageAnnotation", backref="queue_tasks")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_image_queue_tasks")
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="image_queue_tasks_reviewed")

    __table_args__ = (
        Index("idx_image_queue_project", "project_id"),
        Index("idx_image_queue_status", "status"),
        Index("idx_image_queue_assigned", "assigned_to"),
        Index("idx_image_queue_review_level", "review_level"),
        Index("idx_image_queue_reviewer", "reviewer_id"),
    )

    def __repr__(self):
        return f"<ImageAnnotationQueue(id={self.id}, project_id={self.project_id}, task_type='{self.task_type}', status='{self.status}', review_level={self.review_level})>"