from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.assignment import (
    get_team_members,
    create_assignment,
    delete_assignment,
    get_assignment,
    get_project_counts
)
from app.schemas.assignment import AssignmentWithUser, TeamMemberResponse, ProjectTeamResponse
from app.models.user import User
from app.models.project import Project
from app.crud.user import get_user_by_id
from app.crud.project import get_project_by_id

def get_project_team(db: Session, project_id: int) -> ProjectTeamResponse:
    """Get all team members for a project, separated by role."""
    team_data = get_team_members(db, project_id)
    
    # Get project owner as manager
    from app.models.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    manager = None
    if project:
        from app.crud.user import get_user_by_id
        owner = get_user_by_id(db, project.owner_id)
        if owner:
            manager = {
                'id': owner.id,
                'full_name': owner.full_name,
                'email': owner.email,
                'role': owner.role
            }
    
    # Separate members by role
    reviewers = []
    annotators = []
    
    for row in team_data:
        member = {
            'id': row.user_id,
            'full_name': row.user_full_name,
            'email': row.user_email,
            'role': row.user_role,
            'assignment_role': row.role
        }
        
        if row.role == 'reviewer':
            reviewers.append(member)
        elif row.role == 'annotator':
            annotators.append(member)
    
    return ProjectTeamResponse(
        success=True,
        data={
            'manager': manager,
            'reviewers': reviewers,
            'annotators': annotators
        }
    )

def add_reviewers(db: Session, project_id: int, user_ids: List[int]) -> dict:
    """Add multiple reviewers to a project."""
    # Verify project exists
    project = get_project_by_id(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    added_count = 0
    for user_id in user_ids:
        # Verify user exists
        user = get_user_by_id(db, user_id=user_id)
        if not user:
            continue
        
        # Check if already assigned
        existing = get_assignment(db, project_id, user_id)
        if existing:
            continue
        
        # Create assignment
        create_assignment(db, project_id, user_id, "reviewer")
        added_count += 1
    
    return {
        "success": True,
        "message": f"Added {added_count} reviewer(s) to project"
    }

def add_annotators(db: Session, project_id: int, user_ids: List[int]) -> dict:
    """Add multiple annotators to a project."""
    # Verify project exists
    project = get_project_by_id(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    added_count = 0
    for user_id in user_ids:
        # Verify user exists
        user = get_user_by_id(db, user_id=user_id)
        if not user:
            continue
        
        # Check if already assigned
        existing = get_assignment(db, project_id, user_id)
        if existing:
            continue
        
        # Create assignment
        create_assignment(db, project_id, user_id, "annotator")
        added_count += 1
    
    return {
        "success": True,
        "message": f"Added {added_count} annotator(s) to project"
    }

def remove_team_member(db: Session, project_id: int, user_id: int) -> dict:
    """Remove a team member from a project."""
    success = delete_assignment(db, project_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    return {
        "success": True,
        "message": "Team member removed successfully"
    }

def add_project_manager(db: Session, project_id: int, user_id: int) -> dict:
    """Add a project manager to a project."""
    # Verify project exists
    project = get_project_by_id(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Verify user exists
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already assigned
    existing = get_assignment(db, project_id, user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already assigned to this project"
        )
    
    # Create assignment
    create_assignment(db, project_id, user_id, "project_manager")
    
    return {
        "success": True,
        "message": "Project manager added successfully"
    }