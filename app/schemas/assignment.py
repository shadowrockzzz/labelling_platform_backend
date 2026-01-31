from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AssignmentCreate(BaseModel):
    project_id: int
    user_id: int
    role: str  # 'project_manager', 'reviewer', 'annotator'

class AssignmentRead(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class AssignmentWithUser(AssignmentRead):
    user_email: str
    user_full_name: Optional[str] = None

class TeamMemberResponse(BaseModel):
    success: bool = True
    data: List[AssignmentWithUser]

class AddTeamMembersRequest(BaseModel):
    user_ids: List[int]

class SuccessResponse(BaseModel):
    success: bool = True
    message: str