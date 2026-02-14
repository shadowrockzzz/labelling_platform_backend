"""
Database Migration: Add Image Annotation Tables

Run this script to add image annotation tables to the database:
    python migration_add_image_annotation.py

Tables added:
- image_resources: Image files for annotation
- image_annotations: Annotations on images
- image_review_corrections: Review correction suggestions
- image_annotation_queue: Queue for annotation tasks
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine, Base

# Import parent models first so SQLAlchemy can resolve foreign keys
from app.models.user import User
from app.models.project import Project

# Import image annotation models
from app.annotations.image.models import (
    ImageResource,
    ImageAnnotation,
    ImageReviewCorrection,
    ImageAnnotationQueue
)


def upgrade():
    """Create image annotation tables."""
    print("Creating image annotation tables...")
    
    try:
        # Create tables
        Base.metadata.create_all(bind=engine, tables=[
            ImageResource.__table__,
            ImageAnnotation.__table__,
            ImageReviewCorrection.__table__,
            ImageAnnotationQueue.__table__,
        ])
        print("✅ Successfully created image annotation tables!")
        
        # Print created tables
        print("\nCreated tables:")
        print("  - image_resources")
        print("  - image_annotations")
        print("  - image_review_corrections")
        print("  - image_annotation_queue")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)


def downgrade():
    """Drop image annotation tables."""
    print("Dropping image annotation tables...")
    
    try:
        with engine.connect() as conn:
            # Drop in reverse order due to foreign key constraints
            conn.execute(text("DROP TABLE IF EXISTS image_annotation_queue CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS image_review_corrections CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS image_annotations CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS image_resources CASCADE"))
            conn.commit()
        print("✅ Successfully dropped image annotation tables!")
        
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Image annotation tables migration")
    parser.add_argument("--downgrade", action="store_true", help="Drop tables instead of creating")
    args = parser.parse_args()
    
    if args.downgrade:
        downgrade()
    else:
        upgrade()