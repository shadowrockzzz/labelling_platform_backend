from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1 import users, projects, datasets, annotations, auth, assignments
from app.annotations.text.router import router as text_annotation_router

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
