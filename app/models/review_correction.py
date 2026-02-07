"""
Review correction model.
Stores reviewer corrections to annotations, maintaining audit trail.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class ReviewCorrection(Base):
    """
    ReviewCorrection stores corrections made by reviewers.
    
    This allows reviewers to suggest changes to annotations without
    directly modifying the original, maintaining an audit trail.
    The original annotator can then accept or reject the correction.
    """
    __tablename__ = "review_corrections"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to original annotation
    annotation_id = Column(Integer, ForeignKey("text_annotations.id"), nullable=False, index=True)
    
    # Who made the correction (reviewer)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Status of the correction
    status = Column(String(20), nullable=False, default="pending")  # pending, accepted, rejected
    
    # Original annotation data (for comparison)
    original_data = Column(JSON, nullable=True)
    
    # Corrected annotation data (reviewer's changes)
    corrected_data = Column(JSON, nullable=True)
    
    # Reviewer's explanation for the correction
    comment = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional: Original annotator's response
    annotator_response = Column(Text, nullable=True)
    
    # Relationships
    annotation = relationship("TextAnnotation", back_populates="review_corrections")
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def to_dict(self):
        """Convert to dictionary for API responses."""
        created_at_str = self.created_at.isoformat() if self.created_at is not None else None
        updated_at_str = self.updated_at.isoformat() if self.updated_at is not None else None
        
        return {
            "id": self.id,
            "annotation_id": self.annotation_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_username": self.reviewer.username if self.reviewer else None,
            "status": self.status,
            "original_data": self.original_data,
            "corrected_data": self.corrected_data,
            "comment": self.comment,
            "annotator_response": self.annotator_response,
            "created_at": created_at_str,
            "updated_at": updated_at_str
        }
