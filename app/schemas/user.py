from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role: str = "annotator"  # Default role

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

class UserRead(UserBase):
    id: int
    is_active: bool
    role: str
    created_at: datetime
    modified_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    success: bool = True
    data: UserRead

class UserListResponse(BaseModel):
    success: bool = True
    data: list[UserRead]

class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="New role for the user")

class UserRegister(UserBase):
    password: str
    role: str  # Only admin can create users with specific roles
