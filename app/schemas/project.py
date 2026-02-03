from pydantic import BaseModel, validator
from typing import Optional, Any, List, Dict
from datetime import datetime
import re

class LabelConfig(BaseModel):
    """Configuration for a single label."""
    name: str
    color: str
    
    @validator('color')
    def validate_color(cls, v):
        """Validate hex color format."""
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color (e.g., #3B82F6)')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validate label name."""
        if not v or not v.strip():
            raise ValueError('Label name cannot be empty')
        return v.strip().upper()

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    annotation_type: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    
    @validator('config')
    def validate_config(cls, v):
        """Validate project configuration including label settings."""
        if not v:
            return v
            
        # Validate label configuration if present
        if 'customLabels' in v:
            if not isinstance(v['customLabels'], list):
                raise ValueError('customLabels must be an array')
            
            if len(v['customLabels']) == 0:
                raise ValueError('At least one label is required when using custom labels')
            
            if len(v['customLabels']) > 20:
                raise ValueError('Maximum of 20 labels allowed')
            
            # Validate each label
            for idx, label in enumerate(v['customLabels']):
                if not isinstance(label, dict):
                    raise ValueError(f'Label at index {idx} must be an object')
                
                try:
                    LabelConfig(**label)
                except Exception as e:
                    raise ValueError(f'Label at index {idx}: {str(e)}')
            
            # Check for duplicate label names
            label_names = [label['name'].upper() for label in v['customLabels']]
            if len(label_names) != len(set(label_names)):
                raise ValueError('Label names must be unique')
        
        return v

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    annotation_type: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    owner_id: Optional[int] = None
    
    @validator('config')
    def validate_config(cls, v):
        """Validate project configuration including label settings."""
        if not v:
            return v
            
        # Validate label configuration if present
        if 'customLabels' in v:
            if not isinstance(v['customLabels'], list):
                raise ValueError('customLabels must be an array')
            
            if len(v['customLabels']) == 0:
                raise ValueError('At least one label is required when using custom labels')
            
            if len(v['customLabels']) > 20:
                raise ValueError('Maximum of 20 labels allowed')
            
            # Validate each label
            for idx, label in enumerate(v['customLabels']):
                if not isinstance(label, dict):
                    raise ValueError(f'Label at index {idx} must be an object')
                
                try:
                    LabelConfig(**label)
                except Exception as e:
                    raise ValueError(f'Label at index {idx}: {str(e)}')
            
            # Check for duplicate label names
            label_names = [label['name'].upper() for label in v['customLabels']]
            if len(label_names) != len(set(label_names)):
                raise ValueError('Label names must be unique')
        
        return v

class ProjectRead(ProjectBase):
    id: int
    owner_id: int
    owner_name: Optional[str] = None
    status: str
    annotation_type: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    created_at: datetime
    modified_at: Optional[datetime] = None
    reviewer_count: int = 0
    annotator_count: int = 0

    class Config:
        from_attributes = True

class ProjectResponse(BaseModel):
    success: bool = True
    data: ProjectRead

class ProjectListResponse(BaseModel):
    success: bool = True
    data: list[ProjectRead]