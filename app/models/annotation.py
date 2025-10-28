from sqlalchemy import Column, Integer, ForeignKey, JSON, DateTime, func
from app.core.database import Base

class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    labeler_id = Column(Integer, ForeignKey("users.id"))
    annotation_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), onupdate=func.now())
