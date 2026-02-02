# LabelBox Clone - Complete Setup Guide

This guide will help you set up complete annotation platform with role-based authentication system.

## Prerequisites

- **Backend Requirements**:
  - Python 3.9+
  - PostgreSQL 12+
  - pip or poetry
  - Docker (for MinIO S3 storage)

- **Frontend Requirements**:
  - Node.js 18+
  - npm or yarn

## Quick Start

### Step 1: Backend Setup

```bash
cd labelling_platform_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and generate a SECRET_KEY

# Generate SECRET_KEY
openssl rand -hex 32

# Run database migration
python migration.py

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### Step 1.5: Set Up S3/MinIO Storage (Required for Text Annotation)

For text annotation features to work properly, you need to set up MinIO (S3-compatible storage):

```bash
# From backend directory
cd labelling_platform_backend

# Start MinIO using Docker Compose
docker-compose up -d
```

**What this does:**
- Starts MinIO server on port 9000 (S3 API)
- Starts MinIO Console on port 9001 (Web UI)
- Creates `labelling-platform-files` bucket automatically
- Stores uploaded files and annotation outputs

**For detailed setup instructions, see:**
- `labelling_platform_backend/docs/QUICK_START.md` - Quick setup guide
- `labelling_platform_backend/docs/S3_SETUP_GUIDE.md` - Complete documentation

**Important:** MinIO must be running for text annotation file uploads to work properly!

### Step 2: Frontend Setup

Open a new terminal:

```bash
cd labelling_platform_frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Initial Admin User Setup

Since registration endpoint is admin-only, you need to create first admin user directly in database:

```bash
# Connect to your PostgreSQL database
psql -U your_user -d labelling_platform

# Insert admin user (password: Admin123!)
INSERT INTO users (email, hashed_password, full_name, role, is_active, created_at, modified_at)
VALUES (
  'admin@example.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4l5qV0J7uOqVYUqW',  # bcrypt hash of "Admin123!"
  'Admin User',
  'admin',
  true,
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);

\q
```

Now you can:
1. Login at `http://localhost:5173/login`
2. Email: `admin@example.com`
3. Password: `Admin123!`

## Creating Additional Users

After logging in as admin, you can create users through API:

### Option 1: Use User Management Page (when implemented)
Navigate to `/admin/users` in application

### Option 2: Use API Documentation
1. Go to `http://localhost:8000/docs`
2. Find `POST /api/v1/auth/register` endpoint
3. Click "Try it out"
4. Enter user details
5. Click "Execute"

### Option 3: Use cURL
```bash
# First login as admin to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "Admin123!"}'

# Use returned access_token to register new users
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "email": "manager@example.com",
    "password": "Manager123!",
    "full_name": "Project Manager",
    "role": "project_manager"
  }'
```

## Project Management Flow

### 1. Admin Creates Project Manager
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "email": "manager@example.com",
    "password": "Manager123!",
    "full_name": "John Manager",
    "role": "project_manager"
  }'
```

### 2. Project Manager Creates Project
Login as project manager and create a project through UI or API:
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "name": "Image Annotation Project",
    "description": "Annotate product images"
  }'
```

### 3. Assign Team Members
Add reviewers and annotators to project:
```bash
# Add reviewers
curl -X POST http://localhost:8000/api/v1/projects/1/reviewers \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "user_ids": [2, 3]
  }'

# Add annotators
curl -X POST http://localhost:8000/api/v1/projects/1/annotators \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -d '{
    "user_ids": [4, 5]
  }'
```

## Role-Based Permissions

### Admin
- ✓ Create and manage all users
- ✓ Create and manage all projects
- ✓ Assign project managers
- ✓ Full system access

### Project Manager
- ✓ Create and manage assigned projects
- ✓ Assign reviewers (0 to unlimited)
- ✓ Assign annotators
- ✓ View project analytics
- ✗ Cannot manage other managers or admins

### Reviewer
- ✓ Review submitted annotations
- ✓ Approve/reject annotations
- ✓ Add review comments
- ✓ View project details (read-only)
- ✗ Cannot create or edit annotations

### Annotator
- ✓ Create new annotations
- ✓ Edit own annotations (before review)
- ✓ View assigned projects
- ✓ Submit annotations for review
- ✗ Cannot review others' annotations

## Database Schema Overview

### Users Table
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  hashed_password VARCHAR NOT NULL,
  full_name VARCHAR,
  role VARCHAR NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP,
  modified_at TIMESTAMP
);
```

### Projects Table
```sql
CREATE TABLE projects (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL,
  description TEXT,
  owner_id INTEGER REFERENCES users(id),
  status VARCHAR DEFAULT 'active',
  created_at TIMESTAMP,
  modified_at TIMESTAMP
);
```

### Project Assignments Table
```sql
CREATE TABLE project_assignments (
  id SERIAL PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR NOT NULL,
  created_at TIMESTAMP,
  UNIQUE(project_id, user_id)
);
```

## Stopping All Services

When you're done working or need to restart services:

### Stop Backend Server

```bash
# Press Ctrl+C in the terminal where backend is running
# OR find and kill the process
ps aux | grep uvicorn
kill <process_id>
```

### Stop Frontend Server

```bash
# Press Ctrl+C in the terminal where frontend is running
# OR find and kill the process
ps aux | grep "vite"
kill <process_id>
```

### Stop MinIO and PostgreSQL Containers

```bash
# From backend directory
cd labelling_platform_backend

# Stop and remove containers
docker-compose down

# To stop but keep data (volumes)
docker-compose stop

# To stop and remove everything including volumes
docker-compose down -v
```

### Stop All Services at Once

```bash
# 1. Stop backend and frontend (Ctrl+C in their terminals)

# 2. Stop Docker services
cd labelling_platform_backend
docker-compose down

# Done! All services stopped.
```

### Restarting Services

```bash
# Restart Docker services
cd labelling_platform_backend
docker-compose up -d

# Restart backend (in backend terminal)
cd labelling_platform_backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Restart frontend (in frontend terminal)
cd labelling_platform_frontend
npm run dev
```

## Testing System

### 1. Test Admin Login
```
URL: http://localhost:5173/login
Email: admin@example.com
Password: Admin123!
```

### 2. Create Test Users
Create users for each role:
- Project Manager: manager@example.com
- Reviewer: reviewer@example.com
- Annotator: annotator@example.com

### 3. Test Role-Based Access
- Login as each role
- Verify correct navigation options
- Test access control on protected routes

### 4. Test Auto-Logout
- Login as any user
- Wait 15 minutes without activity
- Verify automatic logout

## Troubleshooting

### Backend Issues

**Database Connection Failed**
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Check database exists
psql -U postgres -l

# Verify credentials in .env
cat .env | grep DATABASE_URL
```

**Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend Issues

**CORS Errors**
- Ensure backend CORS includes frontend URL
- Check `BACKEND_CORS_ORIGINS` in backend .env

**Login Fails**
- Verify backend is running
- Check browser console for errors
- Verify API_URL in frontend .env

**Build Errors**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Production Deployment

### Backend Deployment

```bash
# Build Docker image
cd labelling_platform_backend
docker build -t labelbox-backend .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e SECRET_KEY=your-production-key \
  --env-file .env \
  labelbox-backend
```

### Frontend Deployment

```bash
# Build for production
cd labelling_platform_frontend
npm run build

# Deploy dist/ folder to your hosting provider
```

## Security Checklist

- [ ] Change default admin password immediately
- [ ] Use strong SECRET_KEY in production
- [ ] Enable HTTPS
- [ ] Set DEBUG=False in production
- [ ] Configure CORS properly
- [ ] Implement rate limiting
- [ ] Use environment variables for secrets
- [ ] Regular security updates
- [ ] Backup database regularly
- [ ] Monitor logs for suspicious activity

## Next Steps

After setup, consider:
1. Implement annotation interfaces
2. Add file upload functionality
3. Create review workflows
4. Build analytics dashboards
5. Add email notifications
6. Implement audit logging
7. Add bulk operations
8. Create export functionality

## Support

For issues:
- Backend: Check `labelling_platform_backend/README.md`
- Frontend: Check `labelling_platform_frontend/README.md`
- S3/MinIO: Check `labelling_platform_backend/docs/S3_SETUP_GUIDE.md`
- API Docs: `http://localhost:8000/docs`

## License

MIT