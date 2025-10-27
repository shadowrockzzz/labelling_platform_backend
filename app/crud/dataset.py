from sqlalchemy.orm import Session
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate

def get_datasets_by_project(db: Session, project_id: int):
    return db.query(Dataset).filter(Dataset.project_id == project_id).all()

def create_dataset(db: Session, dataset_in: DatasetCreate):
    dataset = Dataset(name=dataset_in.name, project_id=dataset_in.project_id)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset
