from pydantic import BaseModel
from typing import Any

class AnnotationBase(BaseModel):
    dataset_id: int
    annotation_data: Any

class AnnotationCreate(AnnotationBase):
    labeler_id: int

class AnnotationRead(AnnotationBase):
    id: int
    created_at: str

    class Config:
        orm_mode = True
