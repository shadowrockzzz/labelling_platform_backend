# Deployment Guide

**Last Updated:** March 1, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Docker Deployment](#docker-deployment)
3. [S3/MinIO Setup](#s3minio-setup)
4. [Production Deployment](#production-deployment)
5. [Environment Variables](#environment-variables)

---

## Overview

This guide covers deployment options for the Labelling Platform backend, from local development with Docker to production deployment.

### Deployment Options

| Option | Use Case | Complexity |
|--------|----------|------------|
| **Local/Docker** | Development | Low |
| **Docker Compose** | Staging/Testing | Medium |
| **Production** | Live Environment | High |

---

## Docker Deployment

### Using Docker Compose

The project includes a `docker-compose.yml` for easy deployment:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Services Included

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 8000 | FastAPI application |
| `postgres` | 5432 | PostgreSQL database |
| `minio` | 9000 | S3-compatible storage |
| `minio-console` | 9001 | MinIO web console |

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/labelling_db
      - AWS_S3_ENDPOINT=http://minio:9000
    depends_on:
      - postgres
      - minio

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=labelling_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=labelling_platform
      - MINIO_ROOT_PASSWORD=labelling_platform_secret_key
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
```

---

## S3/MinIO Setup

### MinIO (Development)

MinIO provides S3-compatible storage for local development.

#### Access MinIO Console

1. Open http://localhost:9001
2. Login with credentials:
   - Username: `labelling_platform`
   - Password: `labelling_platform_secret_key`

#### Create Bucket

```bash
# Using MinIO Client (mc)
mc alias set local http://localhost:9000 labelling_platform labelling_platform_secret_key
mc mb local/labelling-platform-files

# Or use the web console
```

#### Initialize Script

The project includes `minio-init.sh`:

```bash
#!/bin/bash
mc alias set local http://minio:9000 labelling_platform labelling_platform_secret_key
mc mb local/labelling-platform-files --ignore-existing
mc admin user add local labelling_platform labelling_platform_secret_key
mc admin policy set local readwrite user=labelling_platform
```

### AWS S3 (Production)

For production, switch to AWS S3:

```env
AWS_ACCESS_KEY_ID=<your_aws_access_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-production-bucket
AWS_S3_ENDPOINT=https://s3.amazonaws.com
```

#### S3 Bucket Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:user/labelling-platform"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-production-bucket",
        "arn:aws:s3:::your-production-bucket/*"
      ]
    }
  ]
}
```

---

## Production Deployment

### Prerequisites

- PostgreSQL 13+ database
- S3-compatible storage (AWS S3, Google Cloud Storage, etc.)
- SSL certificate for HTTPS
- Reverse proxy (nginx, traefik, etc.)

### Server Setup

#### 1. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3.10 python3.10-venv python3-pip -y

# Install PostgreSQL client
sudo apt install postgresql-client -y
```

#### 2. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd labelling_platform/labelling_platform_backend

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with production values
nano .env
```

#### 4. Run Migrations

```bash
python migration.py
python migration_add_config.py
python migration_add_annotation_sub_type.py
python migration_add_image_annotation.py
python migration_add_review_corrections.py
```

#### 5. Start with Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Start server
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service

Create `/etc/systemd/system/labelling-platform.service`:

```ini
[Unit]
Description=Labelling Platform API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/labelling_platform_backend
Environment="PATH=/var/www/labelling_platform_backend/venv/bin"
ExecStart=/var/www/labelling_platform_backend/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable labelling-platform
sudo systemctl start labelling-platform
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | JWT secret key | `openssl rand -hex 32` |
| `AWS_S3_BUCKET` | S3 bucket name | `labelling-platform-files` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_S3_ENDPOINT` | AWS S3 | Custom S3 endpoint |
| `AWS_ACCESS_KEY_ID` | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | - | AWS secret key |
| `AWS_REGION` | `us-east-1` | AWS region |
| `BACKEND_CORS_ORIGINS` | `[]` | Allowed CORS origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token expiration |

### Complete .env Example

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/labelling_db

# JWT
SECRET_KEY=your-super-secret-key-here-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# S3/MinIO
AWS_ACCESS_KEY_ID=labelling_platform
AWS_SECRET_ACCESS_KEY=labelling_platform_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=labelling-platform-files
AWS_S3_ENDPOINT=http://localhost:9000

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Optional
DEBUG=true
LOG_LEVEL=info
```

---

## Health Checks

### Backend Health

```bash
curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

### Database Health

```bash
curl http://localhost:8000/health/db
# Response: {"status": "healthy", "database": "connected"}
```

### S3 Health

```bash
curl http://localhost:8000/health/storage
# Response: {"status": "healthy", "storage": "connected"}
```

---

## Troubleshooting

### Common Issues

#### Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection
psql -U postgres -d labelling_db -c "SELECT 1"
```

#### S3 Upload Failed

```bash
# Check MinIO is running
docker ps | grep minio

# Test S3 connection
aws s3 ls --endpoint-url http://localhost:9000
```

#### CORS Errors

```bash
# Check CORS configuration
echo $BACKEND_CORS_ORIGINS

# Ensure frontend URL is included
export BACKEND_CORS_ORIGINS='["http://localhost:5173"]'
```

---

## Next Steps

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [06-API-REFERENCE.md](06-API-REFERENCE.md) - API documentation