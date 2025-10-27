from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate

def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Project).offset(skip).limit(limit).all()

def create_project(db: Session, project_in: ProjectCreate, owner_id: int):
    project = Project(name=project_in.name, description=project_in.description, owner_id=owner_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
