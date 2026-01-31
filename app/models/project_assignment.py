from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ProjectAssignment(Base):
    """Model for project team assignments."""
    __tablename__ = "project_assignments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # 'project_manager', 'reviewer', 'annotator'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="assignments")
    user = relationship("User", back_populates="assignments")

    def __repr__(self):
        return f"<ProjectAssignment(project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"