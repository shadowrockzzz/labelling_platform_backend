from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectResponse, ProjectListResponse
from app.crud.project import (
    get_projects, create_project, get_project_by_id, 
    update_project as update_project_crud, 
    delete_project as delete_project_crud
)
from app.crud.assignment import get_project_counts
from app.utils.dependencies import require_admin, require_project_manager, require_annotator, get_current_active_user
from app.models.project import Project

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=ProjectListResponse)
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(require_annotator)
):
    """
    List projects based on user role.
    - Admin: All projects
    - Manager: Projects they own or are assigned to
    - Reviewer/Annotator: Projects they are assigned to
    """
    if current_user.role == "admin":
        # Admin sees all projects
        projects = get_projects(db, skip=skip, limit=limit)
    elif current_user.role == "project_manager":
        # Manager sees owned projects
        projects = db.query(Project).filter(
            or_(
                Project.owner_id == current_user.id, 
                Project.id.in_([a.project_id for a in current_user.assignments])
            )
        ).offset(skip).limit(limit).all()
    else:
        # Reviewer/Annotator see assigned projects
        assigned_project_ids = [a.project_id for a in current_user.assignments]
        projects = db.query(Project).filter(
            Project.id.in_(assigned_project_ids)
        ).offset(skip).limit(limit).all()
    
    # Add team counts to each project
    projects_with_counts = []
    for project in projects:
        counts = get_project_counts(db, project.id)
        project_dict = ProjectRead.model_validate(project).model_dump()
        project_dict['reviewer_count'] = counts['reviewer_count']
        project_dict['annotator_count'] = counts['annotator_count']
        projects_with_counts.append(ProjectRead(**project_dict))
    
    return ProjectListResponse(success=True, data=projects_with_counts)

@router.post("", response_model=ProjectResponse)
def create_new_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Create a new project (Admin/Manager only).
    """
    project = create_project(db, project_in, owner_id=current_user.id)
    return ProjectResponse(success=True, data=project)

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_annotator)
):
    """
    Get project details.
    User must have access to the project (owner or assigned).
    """
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check access
    if current_user.role != "admin" and project.owner_id != current_user.id:
        has_assignment = any(a.project_id == project_id for a in current_user.assignments)
        if not has_assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
    
    # Add team counts
    counts = get_project_counts(db, project_id)
    project_dict = ProjectRead.model_validate(project).model_dump()
    project_dict['reviewer_count'] = counts['reviewer_count']
    project_dict['annotator_count'] = counts['annotator_count']
    
    return ProjectResponse(success=True, data=ProjectRead(**project_dict))

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Update project details.
    User must be owner or an admin.
    Only admins can change the project owner.
    """
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check access (admin or owner)
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner or admin can update this project"
        )
    
    # Only admins can change the owner
    if project_update.owner_id is not None and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change the project owner"
        )
    
    project = update_project_crud(db, project_id, project_update)
    
    # Add team counts
    counts = get_project_counts(db, project_id)
    project_dict = ProjectRead.model_validate(project).model_dump()
    project_dict['reviewer_count'] = counts['reviewer_count']
    project_dict['annotator_count'] = counts['annotator_count']
    
    return ProjectResponse(success=True, data=ProjectRead(**project_dict))

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Delete a project (Admin only).
    This will cascade delete all related data.
    """
    success = delete_project_crud(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return {"success": True, "message": "Project deleted successfully"}
