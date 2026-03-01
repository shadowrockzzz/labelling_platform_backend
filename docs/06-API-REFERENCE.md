# API Reference

**Last Updated:** March 1, 2026

---

## Table of Contents

1. [Authentication](#authentication)
2. [Users](#users)
3. [Projects](#projects)
4. [Assignments](#assignments)
5. [Text Annotations](#text-annotations)
6. [Image Annotations](#image-annotations)

---

## Authentication

### Base URL
```
http://localhost:8000/api/v1
```

### Headers
```http
Content-Type: application/json
Authorization: Bearer <access_token>
```

### Endpoints

#### Register User
```http
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "Password123!",
  "full_name": "John Doe",
  "role": "annotator"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "annotator",
    "is_active": true
  }
}
```

#### Login
```http
POST /auth/login
```

**Request Body (form-data):**
```
username: user@example.com
password: Password123!
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Refresh Token
```http
POST /auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

#### Get Current User
```http
GET /auth/me
```

---

## Users

### Endpoints

#### List Users
```http
GET /users
GET /users?skip=0&limit=100
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "annotator",
      "is_active": true,
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "total": 50,
    "skip": 0,
    "limit": 100
  }
}
```

#### Get User
```http
GET /users/{id}
```

#### Update User
```http
PUT /users/{id}
```

**Request Body:**
```json
{
  "full_name": "Jane Doe",
  "role": "reviewer"
}
```

#### Delete User
```http
DELETE /users/{id}
```

#### Activate/Deactivate User
```http
PUT /users/{id}/activate
```

**Request Body:**
```json
{
  "is_active": true
}
```

---

## Projects

### Endpoints

#### Create Project
```http
POST /projects
```

**Request Body:**
```json
{
  "name": "NER Project",
  "description": "Named Entity Recognition dataset",
  "annotation_type": "text",
  "config": {
    "textSubType": "ner",
    "classificationType": "multi_class",
    "customLabels": [
      {"name": "PERSON", "color": "#FF5733"},
      {"name": "ORG", "color": "#33FF57"}
    ]
  }
}
```

#### List Projects
```http
GET /projects
GET /projects?status=active&annotation_type=text
```

#### Get Project
```http
GET /projects/{id}
```

#### Update Project
```http
PUT /projects/{id}
```

#### Delete Project
```http
DELETE /projects/{id}
```

---

## Assignments

### Endpoints

#### Create Assignment
```http
POST /assignments
```

**Request Body:**
```json
{
  "project_id": 1,
  "user_id": 5,
  "role": "annotator"
}
```

#### List Assignments
```http
GET /assignments
GET /assignments?project_id=1&role=annotator
```

#### Get User Assignments
```http
GET /assignments/my-assignments
```

#### Delete Assignment
```http
DELETE /assignments/{id}
```

---

## Text Annotations

### Resources

#### Upload Text Resource
```http
POST /annotations/text/projects/{project_id}/resources/upload
```

**Request Body (form-data):**
```
file: <text_file>
```

#### Add URL Resource
```http
POST /annotations/text/projects/{project_id}/resources/url
```

**Request Body:**
```json
{
  "name": "Article 1",
  "url": "https://example.com/article.txt"
}
```

#### List Resources
```http
GET /annotations/text/projects/{project_id}/resources
```

#### Get Resource
```http
GET /annotations/text/projects/{project_id}/resources/{resource_id}
```

#### Delete Resource
```http
DELETE /annotations/text/projects/{project_id}/resources/{resource_id}
```

### Annotations

#### Create Annotation
```http
POST /annotations/text/projects/{project_id}/annotations
```

**Request Body:**
```json
{
  "resource_id": 1,
  "annotation_type": "text",
  "annotation_sub_type": "ner",
  "spans": [
    {
      "text": "John Doe",
      "label": "PERSON",
      "start": 0,
      "end": 8
    }
  ]
}
```

#### List Annotations
```http
GET /annotations/text/projects/{project_id}/annotations
GET /annotations/text/projects/{project_id}/annotations?resource_id=1&status=submitted
```

#### Get Annotation
```http
GET /annotations/text/projects/{project_id}/annotations/{annotation_id}
```

#### Update Annotation
```http
PUT /annotations/text/projects/{project_id}/annotations/{annotation_id}
```

#### Delete Annotation
```http
DELETE /annotations/text/projects/{project_id}/annotations/{annotation_id}
```

#### Submit for Review
```http
POST /annotations/text/projects/{project_id}/annotations/{annotation_id}/submit
```

#### Review Annotation
```http
POST /annotations/text/projects/{project_id}/annotations/{annotation_id}/review
```

**Request Body:**
```json
{
  "action": "approve",
  "comment": "Great work!"
}
```

### Corrections

#### Create Correction
```http
POST /annotations/text/projects/{project_id}/annotations/{annotation_id}/corrections
```

**Request Body:**
```json
{
  "corrected_data": {
    "spans": [...]
  },
  "comment": "Please fix this"
}
```

#### List Corrections
```http
GET /annotations/text/projects/{project_id}/annotations/{annotation_id}/corrections
```

#### Accept Correction
```http
POST /annotations/text/projects/{project_id}/corrections/{correction_id}/accept?annotator_response=Thanks
```

#### Reject Correction
```http
POST /annotations/text/projects/{project_id}/corrections/{correction_id}/reject?annotator_response=Disagree
```

---

## Image Annotations

### Resources

#### Upload Image
```http
POST /annotations/image/projects/{project_id}/resources/upload
```

**Request Body (form-data):**
```
file: <image_file>
```

#### List Images
```http
GET /annotations/image/projects/{project_id}/resources
```

#### Get Image
```http
GET /annotations/image/projects/{project_id}/resources/{resource_id}
```

#### Delete Image
```http
DELETE /annotations/image/projects/{project_id}/resources/{resource_id}
```

### Annotations

#### Create Annotation
```http
POST /annotations/image/projects/{project_id}/annotations
```

**Request Body:**
```json
{
  "resource_id": 1,
  "annotation_type": "image",
  "annotation_sub_type": "bounding_box",
  "shapes": [
    {
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

#### List/Get/Update/Delete
Same pattern as text annotations.

---

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## Next Steps

- [07-DEPLOYMENT.md](07-DEPLOYMENT.md) - Deployment guide
- [CHANGELOG.md](CHANGELOG.md) - Version history