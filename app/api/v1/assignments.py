from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.assignment import (
    AddTeamMembersRequest, 
    TeamMemberResponse, 
    SuccessResponse, 
    ProjectTeamResponse,
    AddReviewerRequest,
    AddReviewersRequest,
    UpdateReviewerLevelRequest,
    ReviewerWithLevel
)
from app.services.assignment_service import (
    get_project_team,
    add_reviewers,
    add_annotators,
    remove_team_member,
    add_project_manager
)
from app.crud.assignment import (
    get_reviewer_levels,
    get_max_review_level,
    create_assignment,
    update_assignment_review_level,
    reassign_reviewer_levels
)
from app.crud.user import get_user_by_id
from app.utils.dependencies import require_admin, require_project_manager, require_annotator, get_current_active_user

router = APIRouter(tags=["Project Assignments"])


def verify_project_access(project_id: int, db: Session, current_user):
    """Helper to verify user has access to the project."""
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
    
    return project


def verify_project_management(project_id: int, db: Session, current_user):
    """Helper to verify user can manage the project (admin or owner)."""
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
            detail="Only project owner or admin can perform this action"
        )
    
    return project


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
    verify_project_access(project_id, db, current_user)
    return get_project_team(db, project_id)


@router.get("/projects/{project_id}/reviewers", response_model=List[ReviewerWithLevel])
def get_project_reviewers_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_annotator)
):
    """
    Get all reviewers for a project with their review levels.
    Returns reviewers ordered by level (1, 2, 3...).
    """
    verify_project_access(project_id, db, current_user)
    reviewers = get_reviewer_levels(db, project_id)
    return reviewers


@router.post("/projects/{project_id}/reviewers")
def add_reviewers_endpoint(
    project_id: int,
    request: AddTeamMembersRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Add reviewers to a project (Admin/Manager only).
    This endpoint adds reviewers with default level assignment.
    For explicit level control, use /projects/{project_id}/reviewers/with-levels
    """
    verify_project_management(project_id, db, current_user)
    return add_reviewers(db, project_id, request.user_ids)


@router.post("/projects/{project_id}/reviewers/with-levels")
def add_reviewers_with_levels_endpoint(
    project_id: int,
    request: AddReviewersRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Add reviewers with explicit review levels.
    Each reviewer is assigned a specific level (1, 2, 3...).
    Level 1 is the first reviewer (closest to annotator).
    """
    verify_project_management(project_id, db, current_user)
    
    added_reviewers = []
    for reviewer_req in request.reviewers:
        # Validate level is positive
        if reviewer_req.review_level < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Review level must be >= 1, got {reviewer_req.review_level}"
            )
        
        # Check if user exists
        from app.crud.user import get_user_by_id
        user = get_user_by_id(db, reviewer_req.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {reviewer_req.user_id} not found"
            )
        
        # Create assignment with level
        assignment = create_assignment(
            db, 
            project_id, 
            reviewer_req.user_id, 
            "reviewer",
            review_level=reviewer_req.review_level
        )
        added_reviewers.append({
            "user_id": reviewer_req.user_id,
            "review_level": reviewer_req.review_level,
            "assignment_id": assignment.id
        })
    
    return {
        "success": True,
        "message": f"Added {len(added_reviewers)} reviewer(s) with levels",
        "reviewers": added_reviewers
    }


@router.put("/projects/{project_id}/reviewers/{user_id}/level")
def update_reviewer_level_endpoint(
    project_id: int,
    user_id: int,
    request: UpdateReviewerLevelRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Update a reviewer's review level.
    """
    verify_project_management(project_id, db, current_user)
    
    from app.crud.assignment import get_assignment
    assignment = get_assignment(db, project_id, user_id)
    
    if not assignment or assignment.role != "reviewer":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reviewer assignment not found"
        )
    
    if request.review_level < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review level must be >= 1"
        )
    
    updated = update_assignment_review_level(db, assignment.id, request.review_level)
    
    return {
        "success": True,
        "message": f"Updated reviewer level to {request.review_level}",
        "assignment_id": updated.id
    }


@router.put("/projects/{project_id}/reviewers/reorder")
def reorder_reviewers_endpoint(
    project_id: int,
    reviewer_levels: List[dict],
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Reorder reviewer levels.
    Body: [{"user_id": 1, "review_level": 1}, {"user_id": 2, "review_level": 2}, ...]
    """
    verify_project_management(project_id, db, current_user)
    
    try:
        reassign_reviewer_levels(db, project_id, reviewer_levels)
        return {
            "success": True,
            "message": "Reviewer levels reordered successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


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
    verify_project_management(project_id, db, current_user)
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
    verify_project_management(project_id, db, current_user)
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
    verify_project_management(project_id, db, current_user)
    return remove_team_member(db, project_id, user_id)


@router.put("/projects/{project_id}/manager")
def update_project_manager_endpoint(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Update the project manager (owner). Admin only.
    """
    from app.models.project import Project
    
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Verify new manager exists and is a project_manager
    new_manager = get_user_by_id(db, user_id)
    if not new_manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if new_manager.role != 'project_manager' and new_manager.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be a project_manager or admin to be assigned as manager"
        )
    
    # Update project owner
    project.owner_id = user_id
    db.commit()
    
    return {
        "success": True,
        "message": f"Project manager updated to {new_manager.full_name}",
        "manager": {
            "id": new_manager.id,
            "full_name": new_manager.full_name,
            "email": new_manager.email,
            "role": new_manager.role
        }
    }


@router.get("/projects/{project_id}/max-review-level")
def get_max_review_level_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_annotator)
):
    """
    Get the maximum review level for a project.
    Returns 0 if there are no reviewers.
    """
    verify_project_access(project_id, db, current_user)
    max_level = get_max_review_level(db, project_id)
    return {
        "project_id": project_id,
        "max_review_level": max_level
    }


@router.get("/projects/{project_id}/reviewers/chain")
def get_reviewer_chain_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_annotator)
):
    """
    Get the full reviewer chain for a project with user details.
    Returns reviewers ordered by level (1, 2, 3...).
    """
    verify_project_access(project_id, db, current_user)
    reviewers = get_reviewer_levels(db, project_id)
    
    # Format response with user details
    # get_reviewer_levels returns dicts, not ORM objects
    chain = []
    for reviewer in reviewers:
        chain.append({
            "user_id": reviewer["user_id"],
            "review_level": reviewer["review_level"],
            "user": {
                "id": reviewer["user_id"],
                "email": reviewer["user_email"],
                "full_name": reviewer["user_full_name"]
            }
        })
    
    return {"success": True, "data": chain}


@router.put("/projects/{project_id}/reviewers/chain")
def update_reviewer_chain_endpoint(
    project_id: int,
    request: AddReviewersRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_project_manager)
):
    """
    Update the full reviewer chain for a project.
    This replaces all existing reviewer assignments with the new chain.
    
    Body: {"reviewers": [{"user_id": 1, "review_level": 1}, {"user_id": 2, "review_level": 2}, ...]}
    """
    verify_project_management(project_id, db, current_user)
    
    from app.models.project_assignment import ProjectAssignment
    
    # Validate levels are consecutive starting from 1
    levels = sorted([r.review_level for r in request.reviewers])
    expected_levels = list(range(1, len(levels) + 1))
    if levels != expected_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Review levels must be consecutive starting from 1. Got: {levels}"
        )
    
    # Remove existing reviewer assignments
    db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.role == "reviewer"
    ).delete()
    
    # Add new reviewer assignments
    added_reviewers = []
    for reviewer_req in request.reviewers:
        # Check if user exists
        from app.crud.user import get_user_by_id
        user = get_user_by_id(db, reviewer_req.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {reviewer_req.user_id} not found"
            )
        
        # Create assignment with level
        assignment = create_assignment(
            db, 
            project_id, 
            reviewer_req.user_id, 
            "reviewer",
            review_level=reviewer_req.review_level
        )
        added_reviewers.append({
            "user_id": reviewer_req.user_id,
            "review_level": reviewer_req.review_level,
            "assignment_id": assignment.id
        })
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Updated reviewer chain with {len(added_reviewers)} reviewer(s)",
        "reviewers": added_reviewers
    }
