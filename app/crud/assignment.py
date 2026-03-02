from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, asc
from app.models.project_assignment import ProjectAssignment
from app.models.project import Project
from app.models.user import User


def get_assignments_by_project(db: Session, project_id: int) -> List[ProjectAssignment]:
    """Get all assignments for a project."""
    return db.query(ProjectAssignment).filter(ProjectAssignment.project_id == project_id).all()


def get_assignments_by_user(db: Session, user_id: int) -> List[ProjectAssignment]:
    """Get all assignments for a user."""
    return db.query(ProjectAssignment).filter(ProjectAssignment.user_id == user_id).all()


def get_assignment(db: Session, project_id: int, user_id: int) -> Optional[ProjectAssignment]:
    """Get a specific assignment."""
    return db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user_id
    ).first()


def get_assignment_by_id(db: Session, assignment_id: int) -> Optional[ProjectAssignment]:
    """Get an assignment by its ID."""
    return db.query(ProjectAssignment).filter(ProjectAssignment.id == assignment_id).first()


def create_assignment(db: Session, project_id: int, user_id: int, role: str, review_level: Optional[int] = None) -> ProjectAssignment:
    """Create a new assignment.
    
    Args:
        db: Database session
        project_id: Project ID
        user_id: User ID
        role: Role ('project_manager', 'reviewer', 'annotator')
        review_level: For reviewers, the review level (1, 2, 3...)
    """
    assignment = ProjectAssignment(
        project_id=project_id,
        user_id=user_id,
        role=role,
        review_level=review_level
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def update_assignment_review_level(db: Session, assignment_id: int, review_level: int) -> Optional[ProjectAssignment]:
    """Update the review level for a reviewer assignment."""
    assignment = db.query(ProjectAssignment).filter(ProjectAssignment.id == assignment_id).first()
    if not assignment:
        return None
    
    assignment.review_level = review_level
    db.commit()
    db.refresh(assignment)
    return assignment


def delete_assignment(db: Session, project_id: int, user_id: int) -> bool:
    """Delete an assignment."""
    assignment = get_assignment(db, project_id, user_id)
    if not assignment:
        return False
    
    db.delete(assignment)
    db.commit()
    return True


def delete_assignment_by_id(db: Session, assignment_id: int) -> bool:
    """Delete an assignment by its ID."""
    assignment = db.query(ProjectAssignment).filter(ProjectAssignment.id == assignment_id).first()
    if not assignment:
        return False
    
    db.delete(assignment)
    db.commit()
    return True


def get_team_members(db: Session, project_id: int) -> List[dict]:
    """Get all team members for a project with user details."""
    return db.query(
        ProjectAssignment.id,
        ProjectAssignment.project_id,
        ProjectAssignment.user_id,
        ProjectAssignment.role,
        ProjectAssignment.review_level,
        ProjectAssignment.created_at,
        User.email.label("user_email"),
        User.full_name.label("user_full_name"),
        User.role.label("user_role")
    ).join(
        User, ProjectAssignment.user_id == User.id
    ).filter(
        ProjectAssignment.project_id == project_id
    ).all()


def get_project_counts(db: Session, project_id: int) -> dict:
    """Get count of reviewers and annotators for a project."""
    reviewer_count = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.role == "reviewer"
    ).count()
    
    annotator_count = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.role == "annotator"
    ).count()
    
    return {
        "reviewer_count": reviewer_count,
        "annotator_count": annotator_count
    }


# ============================================
# Multi-Level Review Helper Functions
# ============================================

def get_reviewer_levels(db: Session, project_id: int) -> List[Dict[str, Any]]:
    """Get all reviewers for a project ordered by their review level.
    
    Returns a list of dicts with reviewer assignment info, ordered by review_level ascending.
    Level 1 is the first reviewer (closest to annotator).
    
    Returns:
        List of dicts: [{
            'assignment_id': int,
            'user_id': int,
            'user_email': str,
            'user_full_name': str,
            'review_level': int
        }, ...]
    """
    results = db.query(
        ProjectAssignment.id.label("assignment_id"),
        ProjectAssignment.user_id,
        ProjectAssignment.review_level,
        User.email.label("user_email"),
        User.full_name.label("user_full_name")
    ).join(
        User, ProjectAssignment.user_id == User.id
    ).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.role == "reviewer",
        ProjectAssignment.review_level.isnot(None)
    ).order_by(
        asc(ProjectAssignment.review_level)
    ).all()
    
    return [
        {
            "assignment_id": r.assignment_id,
            "user_id": r.user_id,
            "user_email": r.user_email,
            "user_full_name": r.user_full_name,
            "review_level": r.review_level
        }
        for r in results
    ]


def get_reviewer_for_level(db: Session, project_id: int, level: int) -> Optional[Dict[str, Any]]:
    """Get the reviewer assigned to a specific review level for a project.
    
    Args:
        db: Database session
        project_id: Project ID
        level: Review level (1, 2, 3...)
        
    Returns:
        Dict with reviewer info or None if no reviewer at that level
    """
    result = db.query(
        ProjectAssignment.id.label("assignment_id"),
        ProjectAssignment.user_id,
        ProjectAssignment.review_level,
        User.email.label("user_email"),
        User.full_name.label("user_full_name")
    ).join(
        User, ProjectAssignment.user_id == User.id
    ).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.role == "reviewer",
        ProjectAssignment.review_level == level
    ).first()
    
    if not result:
        return None
    
    return {
        "assignment_id": result.assignment_id,
        "user_id": result.user_id,
        "user_email": result.user_email,
        "user_full_name": result.user_full_name,
        "review_level": result.review_level
    }


def get_max_review_level(db: Session, project_id: int) -> int:
    """Get the maximum review level for a project.
    
    Returns 0 if there are no reviewers.
    """
    from sqlalchemy import func
    
    result = db.query(
        func.max(ProjectAssignment.review_level)
    ).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.role == "reviewer"
    ).scalar()
    
    return result or 0


def is_user_reviewer_for_level(db: Session, project_id: int, user_id: int, level: int) -> bool:
    """Check if a user is the reviewer for a specific level.
    
    Args:
        db: Database session
        project_id: Project ID
        user_id: User ID
        level: Review level to check
        
    Returns:
        True if the user is assigned as reviewer for that level
    """
    assignment = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user_id,
        ProjectAssignment.role == "reviewer",
        ProjectAssignment.review_level == level
    ).first()
    
    return assignment is not None


def get_user_review_level(db: Session, project_id: int, user_id: int) -> Optional[int]:
    """Get the review level for a user in a project.
    
    Returns None if the user is not a reviewer for this project.
    """
    assignment = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user_id,
        ProjectAssignment.role == "reviewer"
    ).first()
    
    return assignment.review_level if assignment else None


def get_reviewers_by_user(db: Session, user_id: int) -> List[ProjectAssignment]:
    """Get all reviewer assignments for a user across all projects."""
    return db.query(ProjectAssignment).filter(
        ProjectAssignment.user_id == user_id,
        ProjectAssignment.role == "reviewer"
    ).all()


def reassign_reviewer_levels(db: Session, project_id: int, reviewer_levels: List[Dict[str, int]]) -> bool:
    """Reassign reviewer levels for a project.
    
    Args:
        db: Database session
        project_id: Project ID
        reviewer_levels: List of dicts with 'user_id' and 'review_level'
        
    Returns:
        True if successful
    """
    try:
        for item in reviewer_levels:
            assignment = db.query(ProjectAssignment).filter(
                ProjectAssignment.project_id == project_id,
                ProjectAssignment.user_id == item['user_id'],
                ProjectAssignment.role == "reviewer"
            ).first()
            
            if assignment:
                assignment.review_level = item['review_level']
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e