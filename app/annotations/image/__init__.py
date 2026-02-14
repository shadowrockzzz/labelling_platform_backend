"""
Image Annotation Module

This module provides image annotation functionality including:
- Image resource management (upload, storage, retrieval)
- Multiple annotation types (bounding box, polygon, segmentation, keypoint, classification)
- Review and correction workflow
- Queue management for annotation tasks

This module mirrors the text annotation architecture and does not modify any
existing text annotation code.
"""

from app.annotations.image.models import ImageResource, ImageAnnotation, ImageReviewCorrection, ImageAnnotationQueue
from app.annotations.image.schemas import (
    ImageResourceCreate,
    ImageResourceResponse,
    ImageAnnotationCreate,
    ImageAnnotationResponse,
    # ... other schemas
)

__all__ = [
    # Models
    "ImageResource",
    "ImageAnnotation", 
    "ImageReviewCorrection",
    "ImageAnnotationQueue",
    # Schemas will be added as needed
]