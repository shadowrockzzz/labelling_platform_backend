from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from app.core.database import Base

class Dataset(Base):
    """
    Legacy Dataset model - NOT ACTIVELY USED.
    
    This model is kept for database migration compatibility only.
    The annotation module uses text_resources and image_resources tables instead.
    """
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Note: relationship removed - this model is not actively used
