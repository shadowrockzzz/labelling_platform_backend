# System Architecture

**Last Updated:** March 1, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Database Models](#database-models)
4. [Annotation Data Model](#annotation-data-model)
5. [Authentication & Authorization](#authentication--authorization)
6. [File Storage](#file-storage)
7. [Queue System](#queue-system)

---

## Overview

The Labelling Platform is built on a modular, scalable architecture designed to support multiple annotation types (text, image, video, audio) with a consistent workflow pattern.

### Design Principles

- **Modularity**: Each annotation type has its own module with isolated logic
- **Scalability**: Horizontal scaling through stateless API servers
- **Extensibility**: Easy to add new annotation types
- **Security**: JWT-based authentication with role-based access control

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│                    http://localhost:5173                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway / CORS                        │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│                    http://localhost:8000                     │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │    Auth     │   Users     │  Projects   │ Annotations │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   PostgreSQL     │ │    S3/MinIO      │ │   Redis/Queue    │
│    Database      │ │     Storage      │ │   (Optional)     │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Module Structure

```
app/
├── main.py                    # FastAPI application entry
├── api/
│   ├── deps.py               # Dependency injection
│   └── v1/                   # API version 1
│       ├── auth.py           # Authentication endpoints
│       ├── users.py          # User management
│       ├── projects.py       # Project management
│       ├── assignments.py    # Project assignments
│       └── annotations.py    # Legacy annotation endpoints
├── annotations/              # Annotation modules
│   ├── base.py              # Base annotation class
│   ├── text/                # Text annotation module
│   │   ├── router.py        # Text annotation API
│   │   ├── crud.py          # Database operations
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── service.py       # Business logic
│   │   └── queue_stub.py    # Queue implementation
│   └── image/               # Image annotation module
│       ├── router.py
│       ├── crud.py
│       ├── models.py
│       ├── schemas.py
│       └── storage.py       # S3 storage operations
├── core/
│   ├── config.py            # Settings and configuration
│   ├── database.py          # Database connection
│   └── security.py          # JWT and password utilities
├── crud/                    # Core CRUD operations
├── models/                  # Core database models
├── schemas/                 # Core Pydantic schemas
├── services/                # Core business logic
└── utils/                   # Utility functions
```

---

## Database Models

### Core Models

#### Users

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="annotator")  # admin, project_manager, reviewer, annotator
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Projects

```python
class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="active")  # active, completed, archived
    annotation_type = Column(String)  # text, image, video, audio, custom
    config = Column(JSON)  # Dynamic configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Project Assignments

```python
class ProjectAssignment(Base):
    __tablename__ = "project_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)  # annotator, reviewer
    assigned_by = Column(Integer, ForeignKey("users.id"))
    assigned_at = Column(DateTime, default=datetime.utcnow)
```

### Annotation Models

#### Text Annotations

```python
class TextAnnotation(Base):
    __tablename__ = "text_annotations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    resource_id = Column(Integer, ForeignKey("text_resources.id"))
    annotator_id = Column(Integer, ForeignKey("users.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    annotation_type = Column(String, default="text")
    annotation_sub_type = Column(String, default="general")  # ner, pos, sentiment, etc.
    
    status = Column(String, default="draft")  # draft, submitted, approved, rejected
    label = Column(String)
    span_start = Column(Integer)
    span_end = Column(Integer)
    annotation_data = Column(JSON)  # Flexible data storage
    
    review_comment = Column(Text)
    submitted_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Text Resources

```python
class TextResource(Base):
    __tablename__ = "text_resources"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String, nullable=False)
    source_type = Column(String)  # file, url
    external_url = Column(String)
    s3_key = Column(String)  # S3 storage key
    content_preview = Column(Text)
    file_size = Column(Integer)
    status = Column(String, default="pending")  # pending, ready, error
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### Image Annotations

```python
class ImageAnnotation(Base):
    __tablename__ = "image_annotations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    resource_id = Column(Integer, ForeignKey("image_resources.id"))
    annotator_id = Column(Integer, ForeignKey("users.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    annotation_type = Column(String, default="image")
    annotation_sub_type = Column(String)  # bounding_box, polygon, keypoint, segmentation
    
    status = Column(String, default="draft")
    shapes = Column(JSON)  # Array of shape objects
    label = Column(String)
    
    review_comment = Column(Text)
    submitted_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Entity Relationship Diagram

```
┌────────────┐       ┌────────────┐       ┌────────────────┐
│   Users    │       │  Projects  │       │ ProjectAssign  │
├────────────┤       ├────────────┤       ├────────────────┤
│ id         │◄──────│ owner_id   │       │ id             │
│ email      │       │ id         │◄──────│ project_id     │
│ role       │       │ name       │       │ user_id        │──────┐
│ is_active  │       │ status     │       │ role           │      │
└────────────┘       │ config     │       └────────────────┘      │
       │             └────────────┘                               │
       │                    │                                     │
       │                    │                                     │
       ▼                    ▼                                     │
┌────────────────┐   ┌────────────────┐                          │
│ TextAnnotation │   │ ImageAnnotation│                          │
├────────────────┤   ├────────────────┤                          │
│ id             │   │ id             │                          │
│ project_id     │   │ project_id     │                          │
│ resource_id    │   │ resource_id    │                          │
│ annotator_id   │───│ annotator_id   │◄─────────────────────────┘
│ reviewer_id    │   │ reviewer_id    │
│ status         │   │ status         │
│ annotation_data│   │ shapes         │
└────────────────┘   └────────────────┘
       │                    │
       ▼                    ▼
┌────────────────┐   ┌────────────────┐
│ TextResource   │   │ ImageResource  │
├────────────────┤   ├────────────────┤
│ id             │   │ id             │
│ project_id     │   │ project_id     │
│ name           │   │ name           │
│ s3_key         │   │ s3_key         │
│ status         │   │ dimensions     │
└────────────────┘   └────────────────┘
```

---

## Annotation Data Model

### Single-Annotation Model

The platform uses a **single-annotation model** where one resource has ONE annotation record containing multiple spans/shapes.

#### Text Annotation Data Structure

```json
{
  "id": 1,
  "resource_id": 100,
  "project_id": 10,
  "annotator_id": 5,
  "annotation_type": "text",
  "annotation_sub_type": "ner",
  "status": "submitted",
  "annotation_data": {
    "spans": [
      {
        "id": "span_abc123",
        "text": "John Doe",
        "label": "PERSON",
        "start": 0,
        "end": 8,
        "confidence": 0.95
      },
      {
        "id": "span_def456",
        "text": "Google",
        "label": "ORG",
        "start": 20,
        "end": 26
      }
    ]
  }
}
```

#### Image Annotation Data Structure

```json
{
  "id": 1,
  "resource_id": 100,
  "project_id": 10,
  "annotator_id": 5,
  "annotation_type": "image",
  "annotation_sub_type": "bounding_box",
  "status": "draft",
  "shapes": [
    {
      "id": "shape_001",
      "type": "bounding_box",
      "label": "person",
      "coordinates": {
        "x": 100,
        "y": 150,
        "width": 200,
        "height": 300
      }
    }
  ]
}
```

### Benefits of Single-Annotation Model

| Benefit | Description |
|---------|-------------|
| **Fewer Records** | One annotation per resource instead of one per span |
| **Better Performance** | Fewer database queries and joins |
| **Atomic Operations** | All spans saved together |
| **Simpler Review** | Reviewer sees complete annotation |
| **Version Control** | Single record can be versioned easily |

---

## Authentication & Authorization

### JWT Authentication Flow

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client  │         │  Server  │         │ Database │
└────┬─────┘         └────┬─────┘         └────┬─────┘
     │                    │                    │
     │ POST /auth/login   │                    │
     │ {email, password}  │                    │
     │───────────────────►│                    │
     │                    │ Verify credentials │
     │                    │───────────────────►│
     │                    │◄───────────────────│
     │                    │                    │
     │ Access + Refresh   │                    │
     │ Tokens             │                    │
     │◄───────────────────│                    │
     │                    │                    │
     │ GET /projects      │                    │
     │ Authorization:     │                    │
     │ Bearer <token>     │                    │
     │───────────────────►│                    │
     │                    │ Validate JWT       │
     │                    │───────────────────►│
     │                    │◄───────────────────│
     │                    │                    │
     │ Projects data      │                    │
     │◄───────────────────│                    │
```

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| **admin** | Full system access, user management, all projects |
| **project_manager** | Create/manage projects, assign team members |
| **reviewer** | Review and approve/reject annotations |
| **annotator** | Create and edit own annotations |

### Permission Checks

```python
# Dependency decorators for role-based access
@Depends(get_current_active_user)     # Any authenticated user
@Depends(require_annotator)           # Annotator and above
@Depends(require_reviewer)            # Reviewer and above
@Depends(require_project_manager)     # Project Manager and above
@Depends(require_admin)               # Admin only
```

---

## File Storage

### S3/MinIO Integration

Files are stored in S3-compatible storage (MinIO for development):

```
Bucket: labelling-platform-files
│
├── projects/
│   ├── 1/                          # Project ID
│   │   ├── resources/
│   │   │   ├── text/
│   │   │   │   ├── 1.txt          # Text resource
│   │   │   │   └── 2.json         # JSON resource
│   │   │   └── images/
│   │   │       ├── 1.png          # Image resource
│   │   │       └── 2.jpg
│   │   └── exports/
│   │       └── annotations.json
│   └── 2/
│       └── ...
```

### Storage Configuration

```env
# MinIO (Development)
AWS_ACCESS_KEY_ID=labelling_platform
AWS_SECRET_ACCESS_KEY=labelling_platform_secret_key
AWS_S3_BUCKET=labelling-platform-files
AWS_S3_ENDPOINT=http://localhost:9000

# AWS S3 (Production)
AWS_ACCESS_KEY_ID=<aws_access_key>
AWS_SECRET_ACCESS_KEY=<aws_secret_key>
AWS_S3_BUCKET=prod-labelling-platform
AWS_S3_ENDPOINT=https://s3.amazonaws.com
```

---

## Queue System

### Redis-Backed Queue Architecture

The platform uses a **Redis-backed queue** using `rq` (Redis Queue) for asynchronous task processing with PostgreSQL audit logging:

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              AnnotationQueue Class                       ││
│  │   - Enqueue tasks to Redis                               ││
│  │   - Track job status                                     ││
│  │   - Log to PostgreSQL                                    ││
│  └────────────────────────┬────────────────────────────────┘│
└───────────────────────────┼─────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│     Redis        │ │   rq-worker      │ │   PostgreSQL     │
│   Job Queue      │ │   (Background)   │ │   Audit Log      │
│                  │ │                  │ │                  │
│ rq:queue:default │ │ Processes jobs   │ │ text_annotation_ │
│ rq:job:<id>      │ │ from Redis       │ │ queue table      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Queue Components

| Component | File | Description |
|-----------|------|-------------|
| **Redis Client** | `app/core/redis_client.py` | Generic Redis connection manager |
| **Queue Class** | `app/core/queue.py` | Unified `AnnotationQueue` class |
| **Worker Tasks** | `app/workers/annotation_tasks.py` | rq job functions |
| **Worker Script** | `run_worker.py` | Script to start rq workers |

### AnnotationQueue Class

```python
from app.core.queue import AnnotationQueue

# Create queue for text annotations
queue = AnnotationQueue(db_session, annotation_type="text")

# Enqueue a task
job = queue.enqueue(
    project_id=1,
    task_type="resource_uploaded",
    payload={"resource_id": 123, "filename": "document.txt"}
)

# Check job status
status = queue.get_job_status(job.id)

# Get all tasks for a project
tasks = queue.get_all_tasks(project_id=1)
```

### Database Queue Table (PostgreSQL Audit)

```python
class TextAnnotationQueue(Base):
    __tablename__ = "text_annotation_queue"
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    annotation_type = Column(String)  # text, image, etc.
    resource_id = Column(Integer, nullable=True)
    annotation_id = Column(Integer, nullable=True)
    task_type = Column(String)  # resource_uploaded, annotation_submitted, etc.
    status = Column(String)  # pending, processing, done, failed
    payload = Column(JSON)
    rq_job_id = Column(String)  # Redis Queue job ID
    created_at = Column(DateTime)
    processed_at = Column(DateTime)
    error_message = Column(Text)
```

### Task Types

| Task Type | Description |
|-----------|-------------|
| `resource_uploaded` | New resource uploaded |
| `resource_url_added` | URL resource added |
| `annotation_submitted` | Annotation submitted for review |
| `annotation_reviewed` | Annotation approved/rejected |

### Queue Isolation

Queues are isolated by `(project_id, annotation_type)`:

```
Project 1 (text):   Queue where project_id=1 AND annotation_type='text'
Project 1 (image):  Queue where project_id=1 AND annotation_type='image'
Project 2 (text):   Queue where project_id=2 AND annotation_type='text'
```

### Running the Worker

```bash
# Start Redis (via Docker)
docker-compose up -d redis

# Start worker manually
python run_worker.py

# Or start via Docker
docker-compose up -d rq-worker

# Check worker status
docker-compose logs rq-worker
```

### Configuration

```env
# Redis connection URL
REDIS_URL=redis://localhost:6379
```

---

## Next Steps

- [03-TEXT-ANNOTATION.md](03-TEXT-ANNOTATION.md) - Text annotation features
- [04-IMAGE-ANNOTATION.md](04-IMAGE-ANNOTATION.md) - Image annotation features
- [06-API-REFERENCE.md](06-API-REFERENCE.md) - API endpoints