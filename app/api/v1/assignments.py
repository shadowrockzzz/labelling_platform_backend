from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.assignment import AddTeamMembersRequest, TeamMemberResponse, SuccessResponse, ProjectTeamResponse
from app.services.assignment_service import (
    get_project_team,
    add_reviewers,
    add_annotators,
    remove_team_member,
    add_project_manager
)
from app.utils.dependencies import require_admin, require_project_manager, require_annotator, get_current_active_user

router = APIRouter(tags=["Project Assignments"])

@router.get("/projects/{project_id}/team", response_model=ProjectTeamResponse)
def get_project_team_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_annotator)
):
    """
    Get all team members for a project.
    User must have access to the project.
    """
    # Check if user has access to project
    from app.crud.project import get_project_by_id
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
    
    return get_project_team(db, project_id)

@router.post("/projects/{project_id}/reviewers")
def add_reviewers_endpoint(
    project_id: int,
    request: AddTeamMembersRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Add reviewers to a project (Admin/Manager only).
    Can add 0 to unlimited reviewers.
    """
    # Verify project ownership/management
    from app.crud.project import get_project_by_id
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
            detail="Only project owner or admin can add reviewers"
        )
    
    return add_reviewers(db, project_id, request.user_ids)

@router.delete("/projects/{project_id}/reviewers/{user_id}")
def remove_reviewer_endpoint(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Remove a reviewer from a project (Admin/Manager only).
    """
    # Verify project ownership/management
    from app.crud.project import get_project_by_id
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
            detail="Only project owner or admin can remove reviewers"
        )
    
    return remove_team_member(db, project_id, user_id)

@router.post("/projects/{project_id}/annotators")
def add_annotators_endpoint(
    project_id: int,
    request: AddTeamMembersRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Add annotators to a project (Admin/Manager only).
    """
    # Verify project ownership/management
    from app.crud.project import get_project_by_id
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
            detail="Only project owner or admin can add annotators"
        )
    
    return add_annotators(db, project_id, request.user_ids)

@router.delete("/projects/{project_id}/annotators/{user_id}")
def remove_annotator_endpoint(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Remove an annotator from a project (Admin/Manager only).
    """
    # Verify project ownership/management
    from app.crud.project import get_project_by_id
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
            detail="Only project owner or admin can remove annotators"
        )
    
    return remove_team_member(db, project_id, user_id)