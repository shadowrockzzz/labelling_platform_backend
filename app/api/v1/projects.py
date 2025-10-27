from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectRead
from app.crud.project import get_projects, create_project
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_projects(db)

@router.post("/", response_model=ProjectRead)
def create_new_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return create_project(db, project_in, owner_id=current_user.id)
