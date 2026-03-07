# Data Annotation Platform - Backend

A FastAPI-based backend for a multi-role data annotation platform supporting text and image annotation with multi-level review workflow.

## Features

- **Multi-Role System**: Admin, Project Manager, Reviewer, Annotator
- **Multi-Level Review Workflow**: Configurable review chain with multiple reviewer levels
- **Resource Pool Management**: PM-provided or annotator-provided resources with locking
- **Text Annotation**: Span-based annotations with labels
- **Image Annotation**: Bounding boxes, polygons, keypoints, segmentation
- **Task Assignment System**: Annotation and review task management
- **Background Job Processing**: Redis Queue (RQ) for async tasks

## Tech Stack

- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache/Queue**: Redis + RQ
- **Storage**: MinIO (S3-compatible)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/labelling_platform
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
SECRET_KEY=your-secret-key-here
```

### 3. Initialize Database

**WARNING**: This will drop all existing tables and recreate them.

```bash
cd labelling_platform_backend
python init_database.py
```

Options:
- `--no-drop` or `--keep-data`: Add missing tables without dropping existing ones
- `--help`: Show help message

### 4. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Run Background Worker (Optional)

```bash
python run_worker.py
```

## Database Schema

### Core Tables
- `users` - User accounts with roles (admin, project_manager, reviewer, annotator)
- `projects` - Annotation projects with configuration
- `labels` - Project-specific labels for annotations
- `project_assignments` - Team assignments with review levels

### Resource Tables
- `text_resources` - Text files for annotation with pool status
- `image_resources` - Images for annotation with pool status

### Annotation Tables
- `text_annotations` - Text annotations with review workflow
- `image_annotations` - Image annotations with review workflow

### Task Tables
- `annotation_tasks` - Resource pool task assignments
- `review_tasks` - Review task assignments by level

### Audit Tables
- `text_annotation_queue` - Annotation event log
- `image_annotation_queue` - Annotation event log
- `text_review_corrections` - Review correction history
- `image_review_corrections` - Review correction history

## API Structure

```
/api/v1/auth          - Authentication endpoints
/api/v1/users         - User management (admin)
/api/v1/projects      - Project CRUD
/api/v1/assignments   - Team assignments
/api/v1/annotations/text/projects/{id}/...    - Text annotation
/api/v1/annotations/image/projects/{id}/...   - Image annotation
/api/v1/review/text/projects/{id}/...         - Text review tasks
/api/v1/review/image/projects/{id}/...        - Image review tasks
/api/v1/tasks/text/projects/{id}/...          - Text annotation tasks
/api/v1/tasks/image/projects/{id}/...         - Image annotation tasks
```

## User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full system access, user management |
| `project_manager` | Create/manage projects, team assignment |
| `reviewer` | Review annotations at assigned level |
| `annotator` | Create and submit annotations |

## Review Workflow

1. Annotator creates annotation → Status: `draft`
2. Annotator submits → Status: `submitted`, goes to reviewer level 1
3. Reviewer approves → Goes to next level (or `approved` if final level)
4. Reviewer rejects → Goes back to previous level (or `rejected` if level 1)

### Annotation Statuses
- `draft` - Being created by annotator
- `submitted` - Submitted for review
- `approved` - Approved by all reviewers
- `rejected` - Rejected, needs correction

## Resource Pool

Projects can be configured for:
- **Annotator-provided resources**: Annotators upload their own files
- **PM-provided resources**: PM uploads resources to a shared pool

Pool statuses:
- `available` - Ready to be claimed
- `locked` - Claimed by a user
- `completed` - Annotation completed
- `skipped` - Skipped by user

## Project Structure

```
labelling_platform_backend/
├── app/
│   ├── api/v1/           # API route handlers
│   ├── annotations/      # Annotation modules (text, image, shared)
│   ├── core/             # Config, database, security
│   ├── crud/             # Database CRUD operations
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic services
│   ├── utils/            # Utilities
│   └── workers/          # Background task workers
├── docs/                 # Documentation
├── init_database.py      # Database initialization script
└── requirements.txt      # Python dependencies
```

## Docker Deployment

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis server
- MinIO storage
- API server
- Background worker

## License

MIT License