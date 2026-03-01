# Labelling Platform - Backend Documentation

**Last Updated:** March 1, 2026

---

## Welcome

Welcome to the Labelling Platform backend documentation. This documentation provides comprehensive information about the backend architecture, API endpoints, annotation systems, and deployment guides.

## Quick Links

| Document | Description |
|----------|-------------|
| [01-GETTING-STARTED.md](01-GETTING-STARTED.md) | Installation, setup, and quick start guide |
| [02-ARCHITECTURE.md](02-ARCHITECTURE.md) | System architecture and data models |
| [03-TEXT-ANNOTATION.md](03-TEXT-ANNOTATION.md) | Text annotation system documentation |
| [04-IMAGE-ANNOTATION.md](04-IMAGE-ANNOTATION.md) | Image annotation system documentation |
| [05-REVIEW-WORKFLOW.md](05-REVIEW-WORKFLOW.md) | Review, corrections, and editing workflows |
| [06-API-REFERENCE.md](06-API-REFERENCE.md) | Complete API endpoint reference |
| [07-DEPLOYMENT.md](07-DEPLOYMENT.md) | S3, Docker, and production deployment |
| [CHANGELOG.md](CHANGELOG.md) | Version history and bug fixes |

## Reading Order for New Developers

1. **Start Here:** [01-GETTING-STARTED.md](01-GETTING-STARTED.md)
2. **Understand the System:** [02-ARCHITECTURE.md](02-ARCHITECTURE.md)
3. **Learn Annotation Types:** [03-TEXT-ANNOTATION.md](03-TEXT-ANNOTATION.md) and [04-IMAGE-ANNOTATION.md](04-IMAGE-ANNOTATION.md)
4. **Review Workflows:** [05-REVIEW-WORKFLOW.md](05-REVIEW-WORKFLOW.md)
5. **API Reference:** [06-API-REFERENCE.md](06-API-REFERENCE.md)
6. **Deploy:** [07-DEPLOYMENT.md](07-DEPLOYMENT.md)

## Project Overview

The Labelling Platform is a full-stack annotation platform supporting:

- **Text Annotation** - NER, POS, Sentiment, Classification, and more
- **Image Annotation** - Bounding boxes, Polygons, Keypoints, Segmentation
- **Review Workflow** - Approve/Reject with correction suggestions
- **Role-Based Access** - Admin, Project Manager, Reviewer, Annotator

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Storage | S3/MinIO |
| Authentication | JWT |
| Migration | Alembic |

## Quick Start

```bash
# Navigate to backend directory
cd labelling_platform_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python migration.py

# Start the server
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Project Structure

```
labelling_platform_backend/
├── app/
│   ├── api/v1/           # API endpoints
│   ├── annotations/      # Annotation modules (text, image)
│   ├── core/            # Core configuration, database
│   ├── crud/            # Database operations
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── utils/           # Utilities
├── docs/                # Documentation (you are here)
├── migrations/          # Alembic migrations
└── tests/               # Test files
```

## Contributing

When adding new features:

1. Update the relevant documentation file
2. Add entries to CHANGELOG.md
3. Follow the existing code style
4. Write tests for new functionality

## Support

For issues and questions:
- Check the relevant documentation section
- Review the CHANGELOG.md for known issues
- Open an issue on the repository

---

*Documentation reorganized and consolidated on March 1, 2026*