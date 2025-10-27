from pydantic import BaseModel

class DatasetBase(BaseModel):
    name: str

class DatasetCreate(DatasetBase):
    project_id: int

class DatasetRead(DatasetBase):
    id: int
    project_id: int

    class Config:
        orm_mode = True
