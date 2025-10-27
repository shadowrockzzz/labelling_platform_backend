from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.dataset import DatasetCreate, DatasetRead
from app.crud.dataset import get_datasets_by_project, create_dataset
from app.api.deps import get_current_user

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.get("/{project_id}", response_model=list[DatasetRead])
def list_datasets(project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_datasets_by_project(db, project_id=project_id)

@router.post("/", response_model=DatasetRead)
def create_new_dataset(dataset_in: DatasetCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return create_dataset(db, dataset_in)
