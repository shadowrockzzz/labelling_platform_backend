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
    Optionally accepts reviewer_chain to set up multi-level review on creation.
    """
    from app.crud.assignment import create_assignment
    
    # Create the project
    project = create_project(db, project_in, owner_id=current_user.id)
    
    # If reviewer_chain is provided, create the assignments
    if project_in.reviewer_chain and len(project_in.reviewer_chain) > 0:
        # Validate levels are consecutive starting from 1
        levels = sorted([r.review_level for r in project_in.reviewer_chain])
        expected_levels = list(range(1, len(levels) + 1))
        if levels != expected_levels:
            # Rollback project creation
            db.delete(project)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Review levels must be consecutive starting from 1. Got: {levels}"
            )
        
        # Create reviewer assignments
        for reviewer_item in project_in.reviewer_chain:
            # Check if user exists
            from app.crud.user import get_user_by_id
            user = get_user_by_id(db, reviewer_item.user_id)
            if not user:
                db.delete(project)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User {reviewer_item.user_id} not found"
                )
            
            # Create assignment with level
            create_assignment(
                db,
                int(project.id),
                reviewer_item.user_id,
                "reviewer",
                review_level=reviewer_item.review_level
            )
        
        db.commit()
    
    # Add team counts
    counts = get_project_counts(db, int(project.id))
    project_dict = ProjectRead.model_validate(project).model_dump()
    project_dict['reviewer_count'] = counts['reviewer_count']
    project_dict['annotator_count'] = counts['annotator_count']
    
    return ProjectResponse(success=True, data=ProjectRead(**project_dict))

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


@router.put("/{project_id}/manager")
def update_project_manager(
    project_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Update project manager (Admin only).
    Changes the project owner_id to a new user.
    """
    from app.models.user import User
    
    new_manager_id = body.get("user_id")
    if not new_manager_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required"
        )
    
    # Check project exists
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check new manager exists and has appropriate role
    new_manager = db.query(User).filter(User.id == new_manager_id).first()
    if not new_manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if new_manager.role not in ["admin", "project_manager"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must have admin or project_manager role"
        )
    
    # Update owner
    project.owner_id = new_manager_id
    db.commit()
    db.refresh(project)
    
    # Add team counts
    counts = get_project_counts(db, project_id)
    project_dict = ProjectRead.model_validate(project).model_dump()
    project_dict['reviewer_count'] = counts['reviewer_count']
    project_dict['annotator_count'] = counts['annotator_count']
    
    return ProjectResponse(success=True, data=ProjectRead(**project_dict))
