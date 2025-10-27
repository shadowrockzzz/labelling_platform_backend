from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.annotation import AnnotationCreate, AnnotationRead
from app.crud.annotation import get_annotations_by_dataset, create_annotation
from app.api.deps import get_current_user

router = APIRouter(prefix="/annotations", tags=["Annotations"])

@router.get("/{dataset_id}", response_model=list[AnnotationRead])
def list_annotations(dataset_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_annotations_by_dataset(db, dataset_id=dataset_id)

@router.post("/", response_model=AnnotationRead)
def create_new_annotation(annot_in: AnnotationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # optionally enforce labeler_id = current_user.id
    annot = create_annotation(db, annot_in)
    return annot
