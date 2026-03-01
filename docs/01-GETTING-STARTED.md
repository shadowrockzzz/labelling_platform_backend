# Getting Started Guide

**Last Updated:** March 1, 2026

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Database Setup](#database-setup)
5. [Running the Server](#running-the-server)
6. [Verification](#verification)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have the following installed:

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.10+ | Runtime environment |
| PostgreSQL | 13+ | Primary database |
| Redis | 7+ | Job queue (optional, for background tasks) |
| Docker | 20+ | Container runtime (optional) |
| Docker Compose | 2+ | Multi-container setup (optional) |

### Verify Prerequisites

```bash
# Check Python version
python --version  # Should be 3.10 or higher

# Check PostgreSQL
psql --version

# Check Docker (optional)
docker --version
docker-compose --version
```

---

## Installation

### Option 1: Standard Installation

```bash
# 1. Navigate to backend directory
cd labelling_platform_backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Option 2: Docker Installation

```bash
# 1. Navigate to backend directory
cd labelling_platform_backend

# 2. Build and start containers
docker-compose up -d

# 3. Check container status
docker-compose ps
```

---

## Configuration

### Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/labelling_db

# JWT Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# S3/MinIO Storage
AWS_ACCESS_KEY_ID=labelling_platform
AWS_SECRET_ACCESS_KEY=labelling_platform_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=labelling-platform-files
AWS_S3_ENDPOINT=http://localhost:9000

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Redis (for background job queue)
REDIS_URL=redis://localhost:6379

# Optional: Email Settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
```

### Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `SECRET_KEY` | Yes | - | JWT secret key (generate with `openssl rand -hex 32`) |
| `AWS_S3_BUCKET` | Yes | - | S3 bucket name for file storage |
| `AWS_S3_ENDPOINT` | No | AWS S3 | Custom S3 endpoint (MinIO) |
| `BACKEND_CORS_ORIGINS` | Yes | `[]` | List of allowed CORS origins |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection URL for job queue |

---

## Database Setup

### Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE labelling_db;

# Create user (optional)
CREATE USER labelling_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE labelling_db TO labelling_user;

# Exit
\q
```

### Run Migrations

```bash
# Run main migration
python migration.py

# Run additional migrations
python migration_add_config.py
python migration_add_annotation_sub_type.py
python migration_add_image_annotation.py
python migration_add_review_corrections.py
```

### Verify Database

```bash
# Connect to database
psql -U postgres -d labelling_db

# List tables
\dt

# Check users table
SELECT * FROM users;

# Exit
\q
```

---

## Running the Server

### Development Mode

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Start development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Start production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

---

## Verification

### Check Server Health

```bash
# Health check endpoint
curl http://localhost:8000/health

# Expected response
{"status": "healthy"}
```

### Access API Documentation

Open your browser and navigate to:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Create First Admin User

```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Admin123!@#",
    "full_name": "Admin User",
    "role": "admin"
  }'
```

### Test Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=Admin123!@#"

# Expected response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## Development Workflow

### Project Structure

```
labelling_platform_backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   └── v1/              # API version 1 endpoints
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── projects.py
│   │       └── ...
│   ├── annotations/         # Annotation modules
│   │   ├── text/           # Text annotation
│   │   └── image/          # Image annotation
│   ├── core/
│   │   ├── config.py       # Configuration settings
│   │   ├── database.py     # Database connection
│   │   └── security.py     # Authentication utilities
│   ├── crud/               # Database CRUD operations
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic layer
│   └── utils/              # Utility functions
├── docs/                   # Documentation
├── tests/                  # Test files
└── migrations/             # Database migrations
```

### Adding New Features

1. **Create Model** in `app/models/`
2. **Create Schema** in `app/schemas/`
3. **Create CRUD** in `app/crud/`
4. **Create Router** in `app/api/v1/`
5. **Register Router** in `app/main.py`
6. **Write Tests** in `tests/`
7. **Update Documentation**

### Code Style

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint
flake8 app/

# Type check
mypy app/
```

---

## Troubleshooting

### Common Issues

#### Database Connection Error

```
Error: Could not connect to database
```

**Solution:**
1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Check DATABASE_URL in `.env`
3. Verify database exists: `psql -U postgres -l`

#### Import Errors

```
Error: ModuleNotFoundError: No module named 'app'
```

**Solution:**
1. Ensure you're in the `labelling_platform_backend` directory
2. Activate virtual environment
3. Install dependencies: `pip install -r requirements.txt`

#### CORS Errors

```
Error: CORS policy blocked
```

**Solution:**
1. Add frontend URL to `BACKEND_CORS_ORIGINS` in `.env`
2. Restart the server

#### S3/MinIO Connection Error

```
Error: Could not connect to S3
```

**Solution:**
1. Verify MinIO is running: `docker-compose ps`
2. Check S3 credentials in `.env`
3. Verify bucket exists: Check MinIO console at http://localhost:9001

### Useful Commands

```bash
# Check running processes
ps aux | grep uvicorn

# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Reset database (CAUTION: Destroys all data)
dropdb labelling_db && createdb labelling_db
python migration.py

# View logs
tail -f logs/app.log
```

---

## Next Steps

- Read [02-ARCHITECTURE.md](02-ARCHITECTURE.md) to understand the system design
- Review [03-TEXT-ANNOTATION.md](03-TEXT-ANNOTATION.md) for text annotation features
- Check [07-DEPLOYMENT.md](07-DEPLOYMENT.md) for production deployment

---

## Getting Help

- **API Documentation:** http://localhost:8000/docs
- **GitHub Issues:** Open an issue on the repository
- **Documentation:** Check other files in the `docs/` folder