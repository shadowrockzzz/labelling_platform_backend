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
from app.schemas.assignment import AssignmentWithUser, TeamMemberResponse
from app.models.user import User
from app.models.project import Project
from app.crud.user import get_user_by_id
from app.crud.project import get_project_by_id

def get_project_team(db: Session, project_id: int) -> TeamMemberResponse:
    """Get all team members for a project."""
    team_data = get_team_members(db, project_id)
    
    team_members = [
        AssignmentWithUser(
            id=row.id,
            project_id=row.project_id,
            user_id=row.user_id,
            role=row.role,
            created_at=row.created_at,
            user_email=row.user_email,
            user_full_name=row.user_full_name
        )
        for row in team_data
    ]
    
    return TeamMemberResponse(success=True, data=team_members)

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