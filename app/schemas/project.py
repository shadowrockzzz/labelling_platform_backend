from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class ProjectRead(ProjectBase):
    id: int
    owner_id: int
    owner_name: Optional[str] = None
    status: str
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
