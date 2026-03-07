#!/usr/bin/env python3
"""
Database Initialization Script for Labelling Platform

This script creates all database tables with the correct schema for:
- Multi-level review workflow
- Resource pool management
- Annotation tasks
- Review tasks

Run this script to initialize a fresh database:
    python init_database.py

WARNING: This script will DROP all existing tables and recreate them.
All data will be lost. Use with caution on production databases.
"""

import sys
from sqlalchemy import text, inspect
from app.core.database import engine, SessionLocal
from app.core.config import settings


def drop_all_tables(db):
    """Drop all tables in the database."""
    print("Dropping all existing tables...")
    
    # List of tables to drop in reverse dependency order
    tables_to_drop = [
        # Task tables
        "review_tasks",
        "annotation_tasks",
        # Queue tables  
        "text_annotation_queue",
        "image_annotation_queue",
        # Review corrections
        "text_review_corrections",
        "image_review_corrections",
        # Annotations
        "text_annotations",
        "image_annotations",
        # Resources
        "text_resources",
        "image_resources",
        # Assignments
        "project_assignments",
        # Labels
        "labels",
        # Projects
        "projects",
        # Users
        "users",
    ]
    
    for table in tables_to_drop:
        try:
            db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            print(f"  ✓ Dropped table: {table}")
        except Exception as e:
            print(f"  ! Error dropping {table}: {e}")
    
    db.commit()
    print("✓ All tables dropped\n")


def create_all_tables(db):
    """Create all tables with the complete schema."""
    print("Creating all tables...")
    
    # ==========================================
    # USERS TABLE
    # ==========================================
    print("  Creating users table...")
    db.execute(text("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            role VARCHAR(50) DEFAULT 'annotator',
            is_active BOOLEAN DEFAULT TRUE,
            bio VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # PROJECTS TABLE
    # ==========================================
    print("  Creating projects table...")
    db.execute(text("""
        CREATE TABLE projects (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            owner_id INTEGER REFERENCES users(id),
            status VARCHAR(50) DEFAULT 'active',
            annotation_type VARCHAR(50) DEFAULT 'text',
            config JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # LABELS TABLE
    # ==========================================
    print("  Creating labels table...")
    db.execute(text("""
        CREATE TABLE labels (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            color VARCHAR(7) DEFAULT '#3B82F6',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # PROJECT_ASSIGNMENTS TABLE
    # ==========================================
    print("  Creating project_assignments table...")
    db.execute(text("""
        CREATE TABLE project_assignments (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(50) NOT NULL DEFAULT 'annotator',
            review_level INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, user_id, role)
        )
    """))
    
    # ==========================================
    # TEXT_RESOURCES TABLE
    # ==========================================
    print("  Creating text_resources table...")
    db.execute(text("""
        CREATE TABLE text_resources (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            source_type VARCHAR(50) DEFAULT 'file',
            s3_key VARCHAR(500),
            external_url VARCHAR(1000),
            content_preview TEXT,
            status VARCHAR(50) DEFAULT 'available',
            pool_status VARCHAR(20) DEFAULT 'available',
            locked_by_user_id INTEGER REFERENCES users(id),
            locked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # IMAGE_RESOURCES TABLE
    # ==========================================
    print("  Creating image_resources table...")
    db.execute(text("""
        CREATE TABLE image_resources (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500),
            thumbnail VARCHAR(500),
            width INTEGER,
            height INTEGER,
            mime_type VARCHAR(100),
            is_archived BOOLEAN DEFAULT FALSE,
            pool_status VARCHAR(20) DEFAULT 'available',
            locked_by_user_id INTEGER REFERENCES users(id),
            locked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # TEXT_ANNOTATIONS TABLE
    # ==========================================
    print("  Creating text_annotations table...")
    db.execute(text("""
        CREATE TABLE text_annotations (
            id SERIAL PRIMARY KEY,
            resource_id INTEGER NOT NULL REFERENCES text_resources(id) ON DELETE CASCADE,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            annotator_id INTEGER NOT NULL REFERENCES users(id),
            reviewer_id INTEGER REFERENCES users(id),
            annotation_sub_type VARCHAR(50) DEFAULT 'span',
            status VARCHAR(50) DEFAULT 'draft',
            label VARCHAR(100),
            span_start INTEGER,
            span_end INTEGER,
            annotation_data JSONB DEFAULT '{}',
            review_comment TEXT,
            reviewed_at TIMESTAMP,
            current_review_level INTEGER DEFAULT 0,
            locked_by_reviewer_id INTEGER REFERENCES users(id),
            review_locked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # IMAGE_ANNOTATIONS TABLE
    # ==========================================
    print("  Creating image_annotations table...")
    db.execute(text("""
        CREATE TABLE image_annotations (
            id SERIAL PRIMARY KEY,
            resource_id INTEGER NOT NULL REFERENCES image_resources(id) ON DELETE CASCADE,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            annotator_id INTEGER NOT NULL REFERENCES users(id),
            reviewer_id INTEGER REFERENCES users(id),
            annotation_sub_type VARCHAR(50) DEFAULT 'bounding_box',
            status VARCHAR(50) DEFAULT 'draft',
            annotation_data JSONB DEFAULT '{}',
            review_comment TEXT,
            reviewed_at TIMESTAMP,
            current_review_level INTEGER DEFAULT 0,
            locked_by_reviewer_id INTEGER REFERENCES users(id),
            review_locked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # TEXT_ANNOTATION_QUEUE TABLE
    # ==========================================
    print("  Creating text_annotation_queue table...")
    db.execute(text("""
        CREATE TABLE text_annotation_queue (
            id SERIAL PRIMARY KEY,
            annotation_id INTEGER REFERENCES text_annotations(id) ON DELETE CASCADE,
            task_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            rq_job_id VARCHAR(100),
            review_level INTEGER,
            reviewer_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # IMAGE_ANNOTATION_QUEUE TABLE
    # ==========================================
    print("  Creating image_annotation_queue table...")
    db.execute(text("""
        CREATE TABLE image_annotation_queue (
            id SERIAL PRIMARY KEY,
            annotation_id INTEGER REFERENCES image_annotations(id) ON DELETE CASCADE,
            task_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            rq_job_id VARCHAR(100),
            review_level INTEGER,
            reviewer_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # TEXT_REVIEW_CORRECTIONS TABLE
    # ==========================================
    print("  Creating text_review_corrections table...")
    db.execute(text("""
        CREATE TABLE text_review_corrections (
            id SERIAL PRIMARY KEY,
            annotation_id INTEGER NOT NULL REFERENCES text_annotations(id) ON DELETE CASCADE,
            reviewer_id INTEGER NOT NULL REFERENCES users(id),
            original_data JSONB NOT NULL,
            corrected_data JSONB NOT NULL,
            comment TEXT,
            review_level INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # IMAGE_REVIEW_CORRECTIONS TABLE
    # ==========================================
    print("  Creating image_review_corrections table...")
    db.execute(text("""
        CREATE TABLE image_review_corrections (
            id SERIAL PRIMARY KEY,
            annotation_id INTEGER NOT NULL REFERENCES image_annotations(id) ON DELETE CASCADE,
            reviewer_id INTEGER NOT NULL REFERENCES users(id),
            original_data JSONB NOT NULL,
            corrected_data JSONB NOT NULL,
            comment TEXT,
            review_level INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # ANNOTATION_TASKS TABLE (Resource Pool Tasks)
    # ==========================================
    print("  Creating annotation_tasks table...")
    db.execute(text("""
        CREATE TABLE annotation_tasks (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            resource_id INTEGER NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            assigned_to_user_id INTEGER REFERENCES users(id),
            status VARCHAR(50) DEFAULT 'available',
            priority INTEGER DEFAULT 0,
            locked_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # ==========================================
    # REVIEW_TASKS TABLE
    # ==========================================
    print("  Creating review_tasks table...")
    db.execute(text("""
        CREATE TABLE review_tasks (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            annotation_id INTEGER NOT NULL,
            annotation_type VARCHAR(50) NOT NULL,
            review_level INTEGER NOT NULL DEFAULT 1,
            assigned_to_user_id INTEGER REFERENCES users(id),
            status VARCHAR(50) DEFAULT 'pending',
            locked_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    db.commit()
    print("✓ All tables created successfully!\n")


def create_indexes(db):
    """Create indexes for better query performance."""
    print("Creating indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
        "CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
        "CREATE INDEX IF NOT EXISTS idx_projects_annotation_type ON projects(annotation_type)",
        "CREATE INDEX IF NOT EXISTS idx_labels_project ON labels(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_project_assignments_project ON project_assignments(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_project_assignments_user ON project_assignments(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_project_assignments_role ON project_assignments(role)",
        "CREATE INDEX IF NOT EXISTS idx_project_assignments_review_level ON project_assignments(review_level)",
        "CREATE INDEX IF NOT EXISTS idx_text_resources_project ON text_resources(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_text_resources_pool_status ON text_resources(pool_status)",
        "CREATE INDEX IF NOT EXISTS idx_text_resources_locked_by ON text_resources(locked_by_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_image_resources_project ON image_resources(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_image_resources_pool_status ON image_resources(pool_status)",
        "CREATE INDEX IF NOT EXISTS idx_image_resources_locked_by ON image_resources(locked_by_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_text_annotations_project ON text_annotations(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_text_annotations_resource ON text_annotations(resource_id)",
        "CREATE INDEX IF NOT EXISTS idx_text_annotations_annotator ON text_annotations(annotator_id)",
        "CREATE INDEX IF NOT EXISTS idx_text_annotations_reviewer ON text_annotations(reviewer_id)",
        "CREATE INDEX IF NOT EXISTS idx_text_annotations_status ON text_annotations(status)",
        "CREATE INDEX IF NOT EXISTS idx_text_annotations_review_level ON text_annotations(current_review_level)",
        "CREATE INDEX IF NOT EXISTS idx_text_annotations_locked_by ON text_annotations(locked_by_reviewer_id)",
        "CREATE INDEX IF NOT EXISTS idx_image_annotations_project ON image_annotations(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_image_annotations_resource ON image_annotations(resource_id)",
        "CREATE INDEX IF NOT EXISTS idx_image_annotations_annotator ON image_annotations(annotator_id)",
        "CREATE INDEX IF NOT EXISTS idx_image_annotations_reviewer ON image_annotations(reviewer_id)",
        "CREATE INDEX IF NOT EXISTS idx_image_annotations_status ON image_annotations(status)",
        "CREATE INDEX IF NOT EXISTS idx_image_annotations_review_level ON image_annotations(current_review_level)",
        "CREATE INDEX IF NOT EXISTS idx_image_annotations_locked_by ON image_annotations(locked_by_reviewer_id)",
        "CREATE INDEX IF NOT EXISTS idx_text_queue_status ON text_annotation_queue(status)",
        "CREATE INDEX IF NOT EXISTS idx_text_queue_annotation ON text_annotation_queue(annotation_id)",
        "CREATE INDEX IF NOT EXISTS idx_image_queue_status ON image_annotation_queue(status)",
        "CREATE INDEX IF NOT EXISTS idx_image_queue_annotation ON image_annotation_queue(annotation_id)",
        "CREATE INDEX IF NOT EXISTS idx_annotation_tasks_project ON annotation_tasks(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_annotation_tasks_user ON annotation_tasks(assigned_to_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_annotation_tasks_status ON annotation_tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_review_tasks_project ON review_tasks(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_review_tasks_user ON review_tasks(assigned_to_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_review_tasks_status ON review_tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_review_tasks_level ON review_tasks(review_level)",
    ]
    
    for idx_sql in indexes:
        try:
            db.execute(text(idx_sql))
        except Exception as e:
            print(f"  ! Index creation note: {e}")
    
    db.commit()
    print("✓ Indexes created successfully!\n")


def print_summary():
    """Print a summary of the database schema."""
    print("=" * 60)
    print("DATABASE INITIALIZATION COMPLETE")
    print("=" * 60)
    print("""
Tables created:
  Core:
    - users                   (id, email, hashed_password, full_name, role, is_active, bio)
    - projects                (id, name, description, owner_id, status, annotation_type, config)
    - labels                  (id, project_id, name, color, description)
    - project_assignments     (id, project_id, user_id, role, review_level)
  
  Resources:
    - text_resources          (id, project_id, name, pool_status, locked_by_user_id, locked_at)
    - image_resources         (id, project_id, name, pool_status, locked_by_user_id, locked_at)
  
  Annotations:
    - text_annotations        (id, resource_id, project_id, annotator_id, reviewer_id, status,
                              current_review_level, locked_by_reviewer_id, review_locked_at)
    - image_annotations       (id, resource_id, project_id, annotator_id, reviewer_id, status,
                              current_review_level, locked_by_reviewer_id, review_locked_at)
  
  Queue/Audit:
    - text_annotation_queue   (id, annotation_id, task_type, status, rq_job_id, review_level, reviewer_id)
    - image_annotation_queue  (id, annotation_id, task_type, status, rq_job_id, review_level, reviewer_id)
  
  Review Corrections:
    - text_review_corrections (id, annotation_id, reviewer_id, original_data, corrected_data, review_level)
    - image_review_corrections(id, annotation_id, reviewer_id, original_data, corrected_data, review_level)
  
  Tasks:
    - annotation_tasks        (id, project_id, resource_id, resource_type, assigned_to_user_id, status)
    - review_tasks            (id, project_id, annotation_id, annotation_type, review_level, status)

Key features:
  ✓ Multi-level review workflow (review_level column)
  ✓ Resource pool management (pool_status, locked_by_user_id, locked_at)
  ✓ Review task locking (locked_by_reviewer_id, review_locked_at)
  ✓ Task assignment system (annotation_tasks, review_tasks)
  ✓ Queue tracking with review levels
""")
    print("=" * 60)


def init_database(drop_existing: bool = True):
    """Initialize the database with all tables."""
    print("\n" + "=" * 60)
    print("LABELLING PLATFORM - DATABASE INITIALIZATION")
    print("=" * 60)
    print(f"\nDatabase URL: {settings.DATABASE_URL}")
    print(f"Drop existing tables: {drop_existing}")
    print()
    
    db = SessionLocal()
    
    try:
        if drop_existing:
            drop_all_tables(db)
        
        create_all_tables(db)
        create_indexes(db)
        print_summary()
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Database initialization failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Parse command line arguments
    drop_existing = True
    if "--no-drop" in sys.argv or "--keep-data" in sys.argv:
        drop_existing = False
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("\nUsage: python init_database.py [OPTIONS]")
        print("\nOptions:")
        print("  --no-drop, --keep-data  Do not drop existing tables (add missing only)")
        print("  --help, -h              Show this help message")
        sys.exit(0)
    
    init_database(drop_existing=drop_existing)