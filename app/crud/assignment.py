from typing import List, Optional
from sqlalchemy.orm import Session
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

def create_assignment(db: Session, project_id: int, user_id: int, role: str) -> ProjectAssignment:
    """Create a new assignment."""
    assignment = ProjectAssignment(
        project_id=project_id,
        user_id=user_id,
        role=role
    )
    db.add(assignment)
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

def get_team_members(db: Session, project_id: int) -> List[dict]:
    """Get all team members for a project with user details."""
    return db.query(
        ProjectAssignment.id,
        ProjectAssignment.project_id,
        ProjectAssignment.user_id,
        ProjectAssignment.role,
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