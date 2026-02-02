# Getting Started Guide

**Last Updated:** February 2, 2026

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture](#architecture)
4. [Project Summary](#project-summary)
5. [Quick Start](#quick-start)
6. [User Roles & Permissions](#user-roles--permissions)
7. [Database Schema](#database-schema)

---

## System Overview

The Labeling Platform is a complete, production-ready annotation system with role-based authentication, featuring a Python FastAPI backend and React frontend.

### Key Features

- ✅ Complete authentication system with JWT tokens
- ✅ Role-based access control (Admin, Project Manager, Reviewer, Annotator)
- ✅ Team management capabilities
- ✅ Text annotation system with multiple annotation types
- ✅ Modern, professional UI
- ✅ Production-ready code structure

---

## Technology Stack

### Backend
- **Framework:** FastAPI 0.104.1
- **Database:** PostgreSQL 12+
- **ORM:** SQLAlchemy 2.0.23
- **Authentication:** JWT (python-jose)
- **Password Hashing:** bcrypt
- **API Documentation:** Auto-generated Swagger UI

### Frontend
- **Framework:** React 18.2.0
- **Routing:** React Router DOM v6.20.0
- **Styling:** Tailwind CSS 3.3.6
- **HTTP Client:** Axios 1.6.0
- **Forms:** React Hook Form 7.48.0
- **Build Tool:** Vite 5.0.8
- **UI Notifications:** React Hot Toast 2.4.1

---

## Architecture

### System Architecture Diagram

```
┌─────────────────┐         ┌─────────────────┐
│                 │         │                 │
│   Frontend      │◄──────►│   Backend API    │
│   (React)       │  HTTP   │   (FastAPI)     │
│                 │         │                 │
└─────────────────┘         └────────┬────────┘
                                    │
                                    │
                           ┌────────▼────────┐
                           │                │
                           │  PostgreSQL DB  │
                           │                │
                           └─────────────────┘
```

### Backend Directory Structure

```
labelling_platform_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── core/
│   │   ├── config.py              # Application configuration
│   │   ├── database.py            # Database connection setup
│   │   └── security.py           # JWT token handling
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── annotation.py
│   │   ├── dataset.py
│   │   └── project_assignment.py
│   ├── schemas/                   # Pydantic schemas (request/response)
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── assignment.py
│   │   ├── annotation.py
│   │   └── auth.py
│   ├── crud/                      # Database operations
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── assignment.py
│   │   └── annotation.py
│   ├── services/                  # Business logic
│   │   ├── user_service.py
│   │   ├── auth_service.py
│   │   └── assignment_service.py
│   ├── api/
│   │   ├── deps.py               # Dependency injection
│   │   └── v1/
│   │       ├── auth.py             # Authentication endpoints
│   │       ├── users.py            # User management endpoints
│   │       ├── projects.py         # Project management endpoints
│   │       ├── assignments.py      # User assignment endpoints
│   │       ├── datasets.py         # Dataset management endpoints
│   │       └── annotations.py     # Annotation endpoints
│   ├── annotations/              # Annotation framework
│   │   ├── base.py              # Base annotation classes
│   │   └── text/                # Text annotation implementation
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── crud.py
│   │       ├── service.py
│   │       └── router.py
│   └── utils/                    # Utility functions
│       ├── dependencies.py         # Role-based dependencies
│       ├── validators.py          # Input validation
│       └── s3_utils.py          # S3 storage integration
```

### Frontend Directory Structure

```
labelling_platform_frontend/
├── public/
│   └── index.html
├── src/
│   ├── main.jsx                  # React app entry point
│   ├── App.jsx                   # Root component with routing
│   ├── index.css                  # Global styles
│   ├── pages/                    # Page components
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── UserManagement.jsx
│   │   ├── ProjectList.jsx
│   │   ├── ProjectDetail.jsx
│   │   └── Profile.jsx
│   ├── components/
│   │   ├── auth/
│   │   │   ├── ProtectedRoute.jsx
│   │   │   └── RoleBasedRoute.jsx
│   │   ├── layout/
│   │   │   └── Layout.jsx
│   │   ├── common/
│   │   │   └── LoadingSpinner.jsx
│   │   └── text-annotation/     # Text annotation UI
│   ├── contexts/
│   │   └── AuthContext.jsx       # Global authentication state
│   ├── services/                  # API service layer
│   │   ├── api.jsx               # Axios instance configuration
│   │   ├── authService.jsx
│   │   ├── userService.js
│   │   ├── projectService.js
│   │   └── assignmentService.js
│   ├── features/
│   │   └── text-annotation/
│   │       └── constants.js
│   ├── hooks/                    # Custom React hooks
│   │   ├── useTextAnnotations.js
│   │   └── useTextResources.js
│   └── utils/
│       ├── constants.js
│       └── roleHelpers.jsx
```

### Application Layers

```
┌─────────────────────────────────────┐
│      API Layer (Routes)         │  ← app/api/v1/
│  - Request validation             │
│  - Response formatting            │
│  - Dependency injection          │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│     Service Layer                │  ← app/services/
│  - Business logic               │
│  - Authorization checks          │
│  - Data transformation          │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│      CRUD Layer                 │  ← app/crud/
│  - Database queries             │
│  - ORM operations              │
│  - Transaction management       │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│    Database (PostgreSQL)        │
│  - Tables: users, projects...  │
└─────────────────────────────────┘
```

---

## Project Summary

### What's Been Implemented

#### Backend (Python/FastAPI)

**Authentication System**
- JWT tokens (access + refresh)
- Password hashing with bcrypt
- Token expiry: 15 min (access), 7 days (refresh)
- Auto-logout mechanism
- Password strength validation

**User Management**
- Complete CRUD operations
- Role-based access control
- User activation/deactivation
- Role change functionality
- Admin-only registration

**Project Management**
- Create, read, update, delete projects
- Status tracking (active, completed, archived)
- Owner-based permissions
- Role-filtered project listing

**Team Management**
- Assign 0 to unlimited reviewers per project
- Assign annotators to projects
- View project team composition
- Remove team members
- Project assignment tracking

**Text Annotation System**
- Extensible annotation framework
- Multiple annotation types (General, NER, Classification, Sentiment)
- Resource management (file upload and URL-based ingestion)
- Annotation lifecycle: Draft → Submitted → Under Review → Approved/Rejected
- Queue system for background task processing
- S3-compatible storage with mock fallback

**API Endpoints (30+ total)**
- Authentication: login, logout, refresh, me, register
- Users: list, get, update, delete, change role, activate
- Projects: list, create, get, update, delete
- Assignments: get team, add/remove reviewers, add/remove annotators
- Text Annotation: resources, annotations, queue management

#### Frontend (React 18)

**Authentication Flow**
- Beautiful login page with gradient background
- Real-time form validation
- Password visibility toggle
- Remember me checkbox
- Error handling with toast notifications
- Auto-logout after 15 minutes inactivity
- Automatic token refresh

**User Interface**
- Modern, professional design
- Responsive layout (mobile, tablet, desktop)
- Role-based navigation sidebar
- Dashboard with statistics
- Loading states and spinners
- Smooth transitions and animations

**Components**
- ProtectedRoute (authentication guard)
- RoleBasedRoute (role-based guard)
- Layout with responsive sidebar
- User profile display with role badges
- Quick action cards
- Navigation menu

**State Management**
- AuthContext for authentication state
- Auto-refresh tokens
- Activity tracking
- User session management

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 12+
- npm or yarn

### Backend Setup

```bash
# Navigate to backend directory
cd labelling_platform_backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your database credentials
# Example:
# DATABASE_URL=postgresql://user:password@localhost:5432/labelling_platform
# SECRET_KEY=your-secret-key-here
# ALGORITHM=HS256
# ACCESS_TOKEN_EXPIRE_MINUTES=30
# REFRESH_TOKEN_EXPIRE_DAYS=7
# API_V1_STR=/api/v1
# BACKEND_CORS_ORIGINS=["http://localhost:5173"]
# DEBUG=True

# Run migrations
python migration.py
python migration_add_annotation_sub_type.py
python migration_add_config.py

# Start S3/MinIO (Required for text annotation)
docker-compose up -d

# Create MinIO bucket manually (if init script fails)
# Visit: http://localhost:9001
# Login: labelling_platform / labelling_platform_secret_key
# Create bucket: labelling-platform-files

# Start development server
uvicorn app.main:app --reload
```

Backend will run on: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

MinIO Console: `http://localhost:9001`

**Important:** MinIO (S3 storage) is required for text annotation features. Files will not upload/download without it.

### Frontend Setup

```bash
# Navigate to frontend directory (new terminal)
cd labelling_platform_frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run on: `http://localhost:5173`

### Default Admin User

```
Email: admin@example.com
Password: Admin123!
```

⚠️ **Important**: Change this password immediately after first login!

---

## User Roles & Permissions

### Admin (Highest Level)
- ✅ Full system access
- ✅ Create/manage all users
- ✅ Create/manage all projects
- ✅ Assign project managers
- ✅ Configure system settings
- ✅ View all projects
- ✅ Upload resources without project assignment
- ✅ Review annotations

### Project Manager
- ✅ Create/manage assigned projects
- ✅ Assign 0 to unlimited reviewers
- ✅ Assign annotators
- ✅ View project analytics
- ✅ Update project details
- ✅ Upload resources to owned projects
- ✅ Annotate data
- ✅ Review annotations
- ❌ Cannot manage other managers/admins
- ❌ Cannot delete projects

### Reviewer
- ✅ Review submitted annotations
- ✅ Approve/reject annotations
- ✅ Add review comments
- ✅ View project details (read-only)
- ✅ See assigned projects
- ✅ View all submitted annotations in project
- ❌ Cannot create annotations
- ❌ Cannot manage team
- ❌ Cannot upload resources

### Annotator
- ✅ Create new annotations
- ✅ Edit own annotations (before review)
- ✅ View assigned projects
- ✅ Submit annotations for review
- ✅ Upload resources to assigned projects
- ❌ Cannot review others' work
- ❌ Cannot manage team
- ❌ Cannot delete resources

### Permission Matrix

| Feature | Admin | Project Manager | Reviewer | Annotator |
|----------|--------|----------------|-----------|------------|
| View all users | ✅ | ❌ | ❌ | ❌ |
| Create user | ✅ | ❌ | ❌ | ❌ |
| Edit user | ✅ | ❌ | ❌ | ❌ |
| Delete user | ✅ | ❌ | ❌ | ❌ |
| View all projects | ✅ | ❌ | ❌ | ❌ |
| Create project | ✅ | ✅ | ❌ | ❌ |
| Edit own project | ✅ | ✅ | ❌ | ❌ |
| Delete project | ✅ | ❌ | ❌ | ❌ |
| Assign users | ✅ | ✅ | ❌ | ❌ |
| View assigned projects | ✅ | ✅ | ✅ | ✅ |
| Upload resources | ✅ | ✅ | ❌ | ✅ |
| Annotate data | ✅ | ✅ | ❌ | ✅ |
| Review annotations | ✅ | ✅ | ✅ | ❌ |

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'annotator',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP
);
```

**Roles:**
- `admin`: Full system access
- `project_manager`: Manage projects and assignments
- `reviewer`: Review annotated data
- `annotator`: Create and edit annotations

### Projects Table

```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id INTEGER REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'active',
    annotation_type VARCHAR(50),
    config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP
);
```

**Status Values:**
- `active`: Project is active and accepting annotations
- `completed`: Project is completed
- `archived`: Project is archived

### Project Assignments Table

```sql
CREATE TABLE project_assignments (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- 'annotator' or 'reviewer'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);
```

### Text Resources Table

```sql
CREATE TABLE text_resources (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    external_url TEXT,
    s3_key VARCHAR(255),
    content_preview TEXT,
    full_content TEXT,
    file_size INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Text Annotations Table

```sql
CREATE TABLE text_annotations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    resource_id INTEGER REFERENCES text_resources(id) ON DELETE CASCADE,
    annotator_id INTEGER REFERENCES users(id),
    reviewer_id INTEGER REFERENCES users(id),
    annotation_type VARCHAR(50) NOT NULL,
    label VARCHAR(255),
    span_start INTEGER,
    span_end INTEGER,
    annotation_sub_type VARCHAR(50),
    annotation_data JSONB,
    status VARCHAR(50) DEFAULT 'draft',
    review_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    reviewed_at TIMESTAMP
);
```

**Status Values:**
- `draft`: Annotation is being created
- `submitted`: Annotation submitted for review
- `under_review`: Annotation is being reviewed
- `approved`: Annotation approved by reviewer
- `rejected`: Annotation rejected by reviewer

**Annotation Types:**
- `general`: Simple label-based annotations
- `ner`: Named Entity Recognition
- `classification`: Categorical labeling
- `sentiment`: Sentiment analysis

### Text Annotation Queue Table

```sql
CREATE TABLE text_annotation_queue (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    resource_id INTEGER REFERENCES text_resources(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,
    metadata JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Task Types:**
- `upload`: File upload to S3
- `fetch_url`: Fetch content from URL
- `process`: Process resource content

---

## API Documentation

### Base URLs
- **Development:** `http://localhost:8000/api/v1`
- **Production:** Configurable in `app/core/config.py`

### Interactive Documentation
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Authentication Flow

1. User enters email/password on Login page
2. Frontend sends POST /auth/login
3. Backend validates credentials
4. Backend generates JWT tokens (access + refresh)
5. Backend returns tokens + user data
6. Frontend stores tokens in localStorage
7. Frontend updates AuthContext with user data
8. All subsequent requests include Bearer token in Authorization header
9. Backend validates token on each protected route
10. Tokens expire automatically (refresh token used to get new access token)

### JWT Token Structure

**Access Token (short-lived):**
- Validity: 15 minutes
- Used for API requests
- Contains user ID and role

**Refresh Token (long-lived):**
- Validity: 7 days
- Used to get new access tokens
- Stored securely in localStorage

---

## Next Steps

After completing the Quick Start, refer to:

- **FEATURE_GUIDE.md** - Detailed feature documentation
- **BUG_FIX_LOG.md** - Bug fixes and improvements
- **SETUP_GUIDE.md** - Detailed setup instructions

---

*Document consolidated from ARCHITECTURE_DOCUMENTATION.md and PROJECT_SUMMARY.md*