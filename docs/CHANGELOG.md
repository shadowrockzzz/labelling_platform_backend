# Changelog - Backend

All notable changes to the backend will be documented in this file.

## [2.0.0] - 2026-03-07

### Major Features Added

#### Multi-Level Review Workflow
- Added `review_level` column to `project_assignments` table for reviewer chain ordering
- Added `current_review_level` column to `text_annotations` and `image_annotations` tables
- Reviewers can be assigned to specific levels (1, 2, 3, etc.)
- Annotations flow through review chain: Level 1 → Level 2 → ... → Approved
- Rejection sends annotation back to previous level (or annotator if Level 1)

#### Resource Pool Management
- Added `pool_status`, `locked_by_user_id`, `locked_at` columns to resource tables
- Project config `resource_provider`: "annotator" or "project_manager"
- PM-provided resources: PM bulk-uploads, annotators claim from pool
- Resource locking mechanism with expiry (configurable, default 30 minutes)
- Pool statuses: available, locked, completed, skipped

#### Task Assignment System
- New `annotation_tasks` table for resource pool task tracking
- New `review_tasks` table for review task assignments by level
- Task status tracking: available, locked, completed

#### Review Task Locking
- Added `locked_by_reviewer_id` and `review_locked_at` to annotation tables
- Reviewers claim tasks exclusively to prevent conflicts
- Lock expiry mechanism for abandoned reviews

### Database Changes
- Unified migration script `init_database.py` replaces multiple migration files
- All tables created with correct schema in single script
- Comprehensive indexes for performance

### API Endpoints Added
- `GET /api/v1/tasks/text/projects/{id}/pool/next` - Get next annotation task
- `GET /api/v1/tasks/image/projects/{id}/pool/next` - Get next image annotation task
- `GET /api/v1/review/text/projects/{id}/next` - Get next review task
- `GET /api/v1/review/image/projects/{id}/next` - Get next image review task
- `POST /api/v1/review/text/projects/{id}/tasks/{taskId}/approve` - Approve review
- `POST /api/v1/review/text/projects/{id}/tasks/{taskId}/reject` - Reject review

### Removed
- Deleted individual migration files (consolidated into `init_database.py`)
- Removed `seed_existing_tasks.py` (functionality integrated)

## [1.0.0] - Initial Release

### Features
- User authentication with JWT tokens
- Role-based access control (admin, project_manager, reviewer, annotator)
- Project management with labels configuration
- Team assignments
- Text annotation with span-based labeling
- Image annotation with bounding boxes, polygons, keypoints, segmentation
- Single-level review workflow
- MinIO/S3 storage integration
- Redis Queue for background tasks