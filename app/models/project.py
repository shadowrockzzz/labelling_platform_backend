from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Project(Base):
    """Project model with team management."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    status = Column(String, default="active")  # 'active', 'completed', 'archived'
    annotation_type = Column(String(50), nullable=True)  # 'text', 'image_classification', etc.
    config = Column(JSON, nullable=True)  # Dynamic configuration based on annotation_type
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="owned_projects", lazy="joined")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    assignments = relationship("ProjectAssignment", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"