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
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default="now()")
    modified_at = Column(DateTime(timezone=True), onupdate="now()")

    # Relationships
    project = relationship("Project", backref="image_resources")
    uploader = relationship("User", backref="uploaded_image_resources")
    annotations = relationship("ImageAnnotation", back_populates="resource", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_image_resources_project", "project_id"),
        Index("idx_image_resources_uploader", "uploader_id"),
        Index("idx_image_resources_archived", "is_archived"),
    )

    def __repr__(self):
        return f"<ImageResource(id={self.id}, name='{self.name}', dimensions={self.width}x{self.height})>"


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
    # Options: 'draft', 'submitted', 'approved', 'rejected'
    
    # Annotation data - flexible JSON structure based on sub_type
    annotation_data = Column(JSON, nullable=True)
    
    # Review info
    review_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default="now()")
    modified_at = Column(DateTime(timezone=True), onupdate="now()")
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    resource = relationship("ImageResource", back_populates="annotations")
    annotator = relationship("User", foreign_keys=[annotator_id], backref="image_annotations_created")
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="image_annotations_reviewed")
    corrections = relationship("ImageReviewCorrection", back_populates="annotation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_image_annotations_project", "project_id"),
        Index("idx_image_annotations_resource", "resource_id"),
        Index("idx_image_annotations_annotator", "annotator_id"),
        Index("idx_image_annotations_status", "status"),
        Index("idx_image_annotations_sub_type", "annotation_sub_type"),
    )

    def __repr__(self):
        return f"<ImageAnnotation(id={self.id}, resource_id={self.resource_id}, sub_type='{self.annotation_sub_type}', status='{self.status}')>"


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
    task_type = Column(String(50), nullable=False)  # 'annotate', 'review', 'export'
    status = Column(String(20), default="pending")  # 'pending', 'processing', 'done', 'failed'
    priority = Column(Integer, default=0)  # Higher priority = processed first
    
    # Assigned user
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
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
    assignee = relationship("User", backref="assigned_image_queue_tasks")

    __table_args__ = (
        Index("idx_image_queue_project", "project_id"),
        Index("idx_image_queue_status", "status"),
        Index("idx_image_queue_assigned", "assigned_to"),
    )

    def __repr__(self):
        return f"<ImageAnnotationQueue(id={self.id}, project_id={self.project_id}, task_type='{self.task_type}', status='{self.status}')>"