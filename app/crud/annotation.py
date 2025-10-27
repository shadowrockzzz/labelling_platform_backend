from sqlalchemy.orm import Session
from app.models.annotation import Annotation
from app.schemas.annotation import AnnotationCreate

def get_annotations_by_dataset(db: Session, dataset_id: int):
    return db.query(Annotation).filter(Annotation.dataset_id == dataset_id).all()

def create_annotation(db: Session, annot_in: AnnotationCreate):
    annotation = Annotation(dataset_id=annot_in.dataset_id, labeler_id=annot_in.labeler_id, annotation_data=annot_in.annotation_data)
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation
