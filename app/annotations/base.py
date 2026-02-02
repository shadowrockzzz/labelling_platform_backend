from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict


class AnnotationStatus(str, Enum):
    """Status enum for all annotation types."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class AnnotationType(str, Enum):
    """Supported annotation types."""
    TEXT = "text"
    # VIDEO = "video"        # to be added later
    # LIDAR = "lidar"
    # RLHF = "rlhf"
    # CODE = "code"


class BaseAnnotationProcessor(ABC):
    """
    Abstract base class that every annotation type must implement.
    Ensures consistent interface across all annotation types.
    """
    
    @abstractmethod
    def validate_input(self, data: Dict) -> bool:
        """
        Validate input data for this annotation type.
        
        Args:
            data: Raw input data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def process_annotation(self, annotation_data: Dict) -> Dict:
        """
        Process annotation data according to type-specific rules.
        
        Args:
            annotation_data: Raw annotation data
            
        Returns:
            Processed annotation data ready for storage
        """
        pass
    
    @abstractmethod
    def get_output_path(self, project_id: int, annotation_id: int) -> str:
        """
        Generate S3 path for annotation output.
        
        Args:
            project_id: Project identifier
            annotation_id: Annotation identifier
            
        Returns:
            S3 key string for output file
        """
        pass