# LabelBox Clone Backend

A FastAPI-based backend for an annotation platform with role-based authentication and team management.

## Features

- **Role-Based Access Control (RBAC)**
  - Admin: Full system access, user management, project management
  - Project Manager: Create/manage assigned projects, assign team members
  - Reviewer: Review and approve/reject annotations
  - Annotator: Create and submit annotations

- **JWT Authentication**
  - Access tokens (15 minute expiry)
  - Refresh tokens (7 day expiry)
  - Secure password hashing with bcrypt

- **Project Management**
  - Create, read, update, delete projects
  - Team member assignments (managers, reviewers, annotators)
  - Project status tracking (active, completed, archived)

- **Team Management**
  - Assign 0 to unlimited reviewers per project
  - Assign annotators to projects
  - View team composition by role

## Tech Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL with SQLAlchemy 2.0.23
- **Authentication**: JWT with python-jose
- **Password Hashing**: bcrypt via passlib
- **API Documentation**: Auto-generated with Swagger/OpenAPI

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- pip or poetry

### Setup Steps

1. **Clone the repository**
   ```bash
   cd labelling_platform_backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and secret key
   ```

5. **Generate SECRET_KEY** (if not set)
   ```bash
   openssl rand -hex 32
   ```

6. **Run database migration**
   ```bash
   python migration.py
   ```

7. **Start the server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Database Schema

### Users Table
- `id`: Primary key
- `email`: Unique email address
- `hashed_password`: Bcrypt hashed password
- `full_name`: User's full name (optional)
- `role`: One of: admin, project_manager, reviewer, annotator
- `is_active`: Account status
- `created_at`: Account creation timestamp
- `modified_at`: Last update timestamp

### Projects Table
- `id`: Primary key
- `name`: Project name
- `description`: Project description (optional)
- `owner_id`: Foreign key to users table
- `status`: One of: active, completed, archived
- `created_at`: Project creation timestamp
- `modified_at`: Last update timestamp

### Project Assignments Table
- `id`: Primary key
- `project_id`: Foreign key to projects table
- `user_id`: Foreign key to users table
- `role`: One of: project_manager, reviewer, annotator
- `created_at`: Assignment creation timestamp

## API Endpoints

### Authentication (`/api/v1/auth`)

- `POST /login` - Login and get JWT tokens
- `POST /refresh` - Refresh access token
- `POST /logout` - Logout (client-side token discard)
- `GET /me` - Get current user info
- `POST /register` - Register new user (Admin only)

### Users (`/api/v1/users`)

- `GET /` - List all users (Admin only)
- `GET /{id}` - Get user details (Admin/Manager)
- `PUT /{id}` - Update user (Admin only)
- `DELETE /{id}` - Deactivate user (Admin only)
- `PUT /{id}/role` - Change user role (Admin only)
- `PUT /{id}/activate` - Activate deactivated user (Admin only)

### Projects (`/api/v1/projects`)

- `GET /` - List projects (filtered by user role)
- `POST /` - Create project (Admin/Manager)
- `GET /{id}` - Get project details
- `PUT /{id}` - Update project (Admin/Manager or owner)
- `DELETE /{id}` - Delete project (Admin only)

### Project Assignments (`/api/v1`)

- `GET /projects/{id}/team` - Get project team
- `POST /projects/{id}/reviewers` - Add reviewers
- `DELETE /projects/{id}/reviewers/{user_id}` - Remove reviewer
- `POST /projects/{id}/annotators` - Add annotators
- `DELETE /projects/{id}/annotators/{user_id}` - Remove annotator

## Password Requirements

Passwords must meet the following criteria:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 number
- At least 1 special character

## Role Hierarchy

1. **Admin** (highest privilege)
   - Full system access
   - Create/manage all users
   - Create/manage all projects
   - Assign project managers
   - Configure system settings

2. **Project Manager**
   - Create/manage assigned projects
   - Assign annotators to projects
   - Assign 0 to unlimited reviewers per project
   - View project analytics
   - Cannot manage other managers or admins

3. **Reviewer** (0 to unlimited per project)
   - Review submitted annotations
   - Approve/reject annotations
   - Add review comments
   - View project details (read-only)

4. **Annotator**
   - Create new annotations
   - Edit own annotations (before review)
   - View assigned projects
   - Submit annotations for review

## Security Best Practices

1. **Never commit `.env` file** - Use `.env.example` as template
2. **Use strong SECRET_KEY** - Generate with `openssl rand -hex 32`
3. **Set DEBUG=False** in production
4. **Use HTTPS** in production
5. **Rotate refresh tokens** - Implement token blacklist in production
6. **Validate all inputs** - Pydantic models handle most validation
7. **Rate limiting** - Implement for auth endpoints in production

## Error Response Format

All API responses follow this format:

**Success:**
```json
{
  "success": true,
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error message",
  "details": { ... }
}
```

## Testing

Run tests (when implemented):
```bash
pytest
```

## Docker Deployment

Build and run with Docker:
```bash
docker build -t labelling-platform-backend .
docker run -p 8000:8000 --env-file .env labelling-platform-backend
```

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env file
- Verify database user has proper permissions

### Import Errors
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Migration Failures
- Check database connection
- Review migration script output
- Manually apply changes if needed

## Development

### Adding New Endpoints

1. Create route handler in `app/api/v1/`
2. Create service logic in `app/services/`
3. Create CRUD operations in `app/crud/`
4. Define schemas in `app/schemas/`
5. Update `app/main.py` to include new router

### Code Structure

```
app/
├── api/v1/          # API route handlers
├── core/             # Configuration and security
├── crud/             # Database operations
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # Business logic
└── utils/            # Helper functions
```

## License

MIT

## Support

For issues and questions, please open an issue on the repository.