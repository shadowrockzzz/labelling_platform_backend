#!/usr/bin/env python3
"""
Seed annotation_tasks for existing resources.

This script creates annotation tasks for resources that were uploaded
before the task-based workflow was implemented.

Run with: python seed_existing_tasks.py
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text as sql_text
from app.core.database import SessionLocal
from app.annotations.text.models import TextResource
from app.annotations.image.models import ImageResource
from app.annotations.shared.task_models import AnnotationTask
from app.models.project import Project


def seed_text_resources(db):
    """Create tasks for existing text resources in PM-provided projects."""
    # Get all PM-provided text projects using raw SQL for JSON query
    result = db.execute(
        sql_text("""
            SELECT id FROM projects 
            WHERE annotation_type = 'text' 
            AND config->>'resource_provider' = 'project_manager'
        """)
    )
    pm_project_ids = [row[0] for row in result.fetchall()]
    
    if not pm_project_ids:
        print("No PM-provided text projects found.")
        return 0
    
    # Get all text resources in these projects
    resources = db.query(TextResource).filter(
        TextResource.project_id.in_(pm_project_ids)
    ).all()
    
    created_count = 0
    for resource in resources:
        # Check if task already exists
        existing = db.query(AnnotationTask).filter(
            AnnotationTask.project_id == resource.project_id,
            AnnotationTask.resource_id == resource.id,
            AnnotationTask.resource_type == 'text'
        ).first()
        
        if not existing:
            task = AnnotationTask(
                project_id=resource.project_id,
                resource_id=resource.id,
                resource_type='text',
                status='available'
            )
            db.add(task)
            created_count += 1
            print(f"Created task for text resource {resource.id}: {resource.name}")
    
    db.commit()
    return created_count


def seed_image_resources(db):
    """Create tasks for existing image resources in PM-provided projects."""
    # Get all PM-provided image projects using raw SQL for JSON query
    result = db.execute(
        sql_text("""
            SELECT id FROM projects 
            WHERE annotation_type = 'image' 
            AND config->>'resource_provider' = 'project_manager'
        """)
    )
    pm_project_ids = [row[0] for row in result.fetchall()]
    
    if not pm_project_ids:
        print("No PM-provided image projects found.")
        return 0
    
    # Get all image resources in these projects
    resources = db.query(ImageResource).filter(
        ImageResource.project_id.in_(pm_project_ids)
    ).all()
    
    created_count = 0
    for resource in resources:
        # Check if task already exists
        existing = db.query(AnnotationTask).filter(
            AnnotationTask.project_id == resource.project_id,
            AnnotationTask.resource_id == resource.id,
            AnnotationTask.resource_type == 'image'
        ).first()
        
        if not existing:
            task = AnnotationTask(
                project_id=resource.project_id,
                resource_id=resource.id,
                resource_type='image',
                status='available'
            )
            db.add(task)
            created_count += 1
            print(f"Created task for image resource {resource.id}: {resource.name}")
    
    db.commit()
    return created_count


def main():
    """Main entry point."""
    print("Seeding annotation tasks for existing resources...")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # First, update projects that don't have config set using raw SQL
        db.execute(
            sql_text("""
                UPDATE projects 
                SET config = '{"resource_provider": "annotator"}'::jsonb 
                WHERE config IS NULL
            """)
        )
        result = db.execute(sql_text("SELECT id, name FROM projects WHERE config IS NULL"))
        null_projects = result.fetchall()
        for row in null_projects:
            print(f"Checked project {row[0]}: {row[1]}")
        
        db.commit()
        
        # Seed text resources
        print("\nSeeding text resources...")
        text_count = seed_text_resources(db)
        print(f"Created {text_count} text annotation tasks")
        
        # Seed image resources
        print("\nSeeding image resources...")
        image_count = seed_image_resources(db)
        print(f"Created {image_count} image annotation tasks")
        
        print("\n" + "=" * 50)
        print(f"Total tasks created: {text_count + image_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()