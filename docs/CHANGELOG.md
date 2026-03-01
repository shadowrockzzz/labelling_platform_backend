# Changelog

All notable changes to the Labelling Platform backend will be documented in this file.

---

## [Unreleased]

### Added
- Comprehensive documentation restructure

### Changed
- **Reviewer Edit Permissions**: Reviewers can now directly edit annotations (both text and image)
  - Previously, only the original annotator could edit their annotations
  - Reviewers can now update shapes, spans, and full annotations
  - When a reviewer edits an annotation, the status is reset to draft for re-review workflow

---

## [2026.03] - March 2026

### Added

#### Redis Queue System
- **Redis-backed job queue** using `rq` (Redis Queue)
- **Unified AnnotationQueue class** supporting all annotation types (text, image)
- **PostgreSQL audit logging** for all queue operations
- **Docker Compose integration** for Redis and rq-worker services
- **Management commands** for running background workers

#### New Files
- `app/core/redis_client.py` - Generic Redis connection manager
- `app/core/queue.py` - Unified `AnnotationQueue` class
- `app/workers/annotation_tasks.py` - rq job functions
- `run_worker.py` - Script to start rq workers

#### Configuration
- Added `REDIS_URL` environment variable
- Added `rq` and `redis` to requirements.txt
- Added `rq_job_id` column to queue tables

#### Docker Services
- `redis` - Redis server container
- `rq-worker` - Background worker container

### Migration
- `migration_add_rq_job_id.py` - Adds `rq_job_id` column to text_annotation_queue

---

## [2026.02] - February 2026

### Bug Fixes

#### Text Annotation Fixes
- **Fixed:** Single-span text annotations not saving correctly
- **Fixed:** Batch annotation validation allowing overlapping spans
- **Fixed:** Edit annotation form not loading existing spans
- **Fixed:** Review panel not displaying annotation data

#### Image Annotation Fixes
- **Fixed:** Bounding box coordinates not persisting
- **Fixed:** Polygon points not saving correctly
- **Fixed:** Image upload failing for large files
- **Fixed:** Shape deletion not working in edit mode

#### Authentication Fixes
- **Fixed:** Token refresh not returning new refresh token
- **Fixed:** Password validation too strict
- **Fixed:** User activation endpoint not working

#### General Fixes
- **Fixed:** CORS errors with frontend
- **Fixed:** Database connection pooling issues
- **Fixed:** S3 upload timeout for large files

---

## [2026.01] - January 2026

### Added

#### Review Corrections Feature
- Reviewers can suggest corrections to annotations
- Annotators can accept or reject corrections
- Full audit trail of all correction attempts
- New `review_corrections` table and endpoints

#### Single Annotation Model
- Migrated from multi-record to single-annotation model
- One annotation per resource with multiple spans/shapes
- Improved performance with fewer database queries
- Atomic save operations

#### Image Annotation System
- Bounding box annotations
- Polygon annotations
- Keypoint annotations
- Segmentation mask support
- S3 storage for images

#### Custom Labels
- Project-specific custom labels
- Custom colors for labels
- Label palette component

### Changed

#### Annotation Schema
- Added `annotation_sub_type` field
- Changed from individual span records to array of spans
- Added `shapes` field for image annotations

#### Project Configuration
- Added `config` JSON field for dynamic settings
- Support for `textSubType`, `classificationType`, `customLabels`

### Fixed

#### Annotation Editing
- Fixed editing reviewed annotations now resets status to draft
- Fixed clearing review fields when editing
- Fixed annotation version tracking

---

## [2025.12] - December 2025

### Added

#### Text Annotation System
- Named Entity Recognition (NER)
- Part-of-Speech Tagging (POS)
- Sentiment Analysis
- Document Classification
- Relation Extraction
- Span Labeling
- Dependency Parsing
- Coreference Resolution

#### Batch Workflow
- Accumulate multiple spans locally
- Submit all spans in one request
- Validation for overlapping spans

#### Queue System
- Task queue for asynchronous processing
- Queue isolation by project and annotation type
- Status tracking for queue items

#### User Management
- Role-based access control (admin, project_manager, reviewer, annotator)
- User activation/deactivation
- Profile management

#### Project Management
- Create, update, delete projects
- Project assignments
- Project configuration

### Security

#### Authentication
- JWT-based authentication
- Access and refresh tokens
- Token expiration and renewal

#### Authorization
- Role-based route protection
- Project-level permissions
- Annotation ownership validation

---

## Migration History

| Migration | Description |
|-----------|-------------|
| `migration.py` | Initial database schema |
| `migration_add_config.py` | Added project config field |
| `migration_add_annotation_sub_type.py` | Added annotation_sub_type |
| `migration_add_image_annotation.py` | Image annotation tables |
| `migration_add_review_corrections.py` | Review corrections table |
| `migration_add_rq_job_id.py` | Added rq_job_id for Redis queue |

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 2026.03 | Mar 2026 | Redis queue system |
| 2026.02 | Feb 2026 | Bug fixes and stability |
| 2026.01 | Jan 2026 | Major features (review, image) |
| 2025.12 | Dec 2025 | Initial release |
