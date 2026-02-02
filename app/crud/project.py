from typing import Optional
from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

def get_projects(db: Session, skip: int = 0, limit: int = 100):
    """Get all projects with pagination."""
    return db.query(Project).offset(skip).limit(limit).all()

def get_project_by_id(db: Session, project_id: int) -> Optional[Project]:
    """Get a specific project by ID."""
    return db.query(Project).filter(Project.id == project_id).first()

def create_project(db: Session, project_in: ProjectCreate, owner_id: int) -> Project:
    """Create a new project."""
    project = Project(
        name=project_in.name,
        description=project_in.description,
        owner_id=owner_id,
        annotation_type=project_in.annotation_type,
        config=project_in.config
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def update_project(db: Session, project_id: int, project_in: ProjectUpdate) -> Optional[Project]:
    """Update a project."""
    project = get_project_by_id(db, project_id)
    if not project:
        return None
    
    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    return project

def delete_project(db: Session, project_id: int) -> bool:
    """Delete a project."""
    project = get_project_by_id(db, project_id)
    if not project:
        return False
    
    db.delete(project)
    db.commit()
    return True