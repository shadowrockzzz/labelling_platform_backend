from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1 import users, projects, datasets, annotations, auth, assignments
from app.annotations.text.router import router as text_annotation_router
from app.annotations.image.router import router as image_annotation_router
from app.annotations.text.task_router import router as text_task_router
from app.annotations.image.task_router import router as image_task_router
from app.annotations.text import crud as text_crud
from app.annotations.image import crud as image_crud
from app.annotations.shared.review_router import create_review_router
from app.crud.assignment import get_max_review_level

# For dev: create tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(assignments.router, prefix=settings.API_V1_STR)
app.include_router(datasets.router, prefix=settings.API_V1_STR)
app.include_router(annotations.router, prefix=settings.API_V1_STR)
app.include_router(text_annotation_router, prefix=f"{settings.API_V1_STR}/annotations/text", tags=["Text Annotations"])
app.include_router(image_annotation_router, prefix=f"{settings.API_V1_STR}/annotations/image", tags=["Image Annotations"])
app.include_router(text_task_router, prefix=f"{settings.API_V1_STR}/annotations/text", tags=["Text Annotation Tasks"])
app.include_router(image_task_router, prefix=f"{settings.API_V1_STR}/annotations/image", tags=["Image Annotation Tasks"])

# Create and include review routers for text and image annotations
# Text review router
text_review_router = create_review_router(
    annotation_type="text",
    get_annotation_by_id_func=text_crud.get_annotation_by_id,
    get_resource_by_annotation_func=text_crud.get_resource_for_annotation,
    update_annotation_func=text_crud.update_annotation_data,
    get_max_review_level_func=get_max_review_level
)
app.include_router(text_review_router, prefix=f"{settings.API_V1_STR}/annotations/text", tags=["Text Review Tasks"])

# Image review router
image_review_router = create_review_router(
    annotation_type="image",
    get_annotation_by_id_func=image_crud.get_annotation_by_id,
    get_resource_by_annotation_func=image_crud.get_resource_for_annotation,
    update_annotation_func=image_crud.update_annotation_data,
    get_max_review_level_func=get_max_review_level
)
app.include_router(image_review_router, prefix=f"{settings.API_V1_STR}/annotations/image", tags=["Image Review Tasks"])

# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "details": {"message": str(exc)} if settings.DEBUG else {}
        }
    )

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "success": True,
        "message": "LabelBox Clone API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "success": True,
        "status": "healthy"
    }
