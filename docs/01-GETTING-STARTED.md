# Getting Started - Backend

## Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 6+
- MinIO (or S3-compatible storage)

## Installation

### 1. Clone and Install Dependencies

```bash
cd labelling_platform_backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file from example:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/labelling_platform

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO/S3
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=annotations
MINIO_SECURE=false

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# App Settings
LOCK_EXPIRY_MINUTES=30
```

### 3. Initialize Database

**Fresh Installation (drops all existing tables):**

```bash
python init_database.py
```

**Add missing tables only (keeps data):**

```bash
python init_database.py --no-drop
```

### 4. Start Services

Using Docker Compose:

```bash
docker-compose up -d
```

Or manually start:
- PostgreSQL
- Redis
- MinIO

### 5. Run the API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run Background Worker

```bash
python run_worker.py
```

## Creating an Admin User

After initializing the database, create an admin user:

```bash
python -c "
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
user = User(
    email='admin@example.com',
    hashed_password=get_password_hash('admin123'),
    full_name='Admin User',
    role='admin',
    is_active=True
)
db.add(user)
db.commit()
print('Admin user created: admin@example.com / admin123')
db.close()
"
```

## API Documentation

Once the server is running, access:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Project Configuration

Projects support the following configuration options:

```json
{
  "resource_provider": "annotator",  // or "project_manager"
  "labels": [
    {"name": "Label1", "color": "#FF0000", "description": "..."}
  ]
}
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1"

# Create database if not exists
psql -U postgres -c "CREATE DATABASE labelling_platform"
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping
```

### MinIO Connection Issues

```bash
# Check MinIO is accessible
curl http://localhost:9000/minio/health/live