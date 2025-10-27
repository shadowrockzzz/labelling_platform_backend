from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserCreate, UserRead
from app.crud.user import get_user_by_email, create_user
from app.core.security import verify_password, token_provider
from app.schemas.user import UserBase

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/signup", response_model=UserRead)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(db, user_in)
    return user

@router.post("/login")
def login(form_data: UserBase, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email=form_data.email)
    if not user or not verify_password(form_data.password, user.hashed_password):  # adjust schema accordingly
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = token_provider.create_token(subject=user.email)
    return {"access_token": token, "token_type": "bearer"}
