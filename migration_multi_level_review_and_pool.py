"""
Migration: Multi-Level Review and Resource Pool

This migration adds support for:
1. Multi-level reviewer chain (review_level in project_assignments)
2. Current review level tracking in annotations
3. Resource pool functionality (pool_status, locking)
4. Enhanced queue tracking (review_level, reviewer_id)

Run with: python migration_multi_level_review_and_pool.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the migration to add multi-level review and pool features."""
    db = SessionLocal()
    
    try:
        # ========================================
        # 1. Add review_level to project_assignments
        # ========================================
        logger.info("Adding review_level column to project_assignments...")
        try:
            db.execute(text("""
                ALTER TABLE project_assignments 
                ADD COLUMN IF NOT EXISTS review_level INTEGER NULL
            """))
            logger.info("✓ review_level column added to project_assignments")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ review_level column already exists in project_assignments")
            else:
                raise

        # ========================================
        # 2. Add current_review_level to text_annotations
        # ========================================
        logger.info("Adding current_review_level column to text_annotations...")
        try:
            db.execute(text("""
                ALTER TABLE text_annotations 
                ADD COLUMN IF NOT EXISTS current_review_level INTEGER DEFAULT 0
            """))
            logger.info("✓ current_review_level column added to text_annotations")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ current_review_level column already exists in text_annotations")
            else:
                raise

        # ========================================
        # 3. Add current_review_level to image_annotations
        # ========================================
        logger.info("Adding current_review_level column to image_annotations...")
        try:
            db.execute(text("""
                ALTER TABLE image_annotations 
                ADD COLUMN IF NOT EXISTS current_review_level INTEGER DEFAULT 0
            """))
            logger.info("✓ current_review_level column added to image_annotations")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ current_review_level column already exists in image_annotations")
            else:
                raise

        # ========================================
        # 4. Add pool_status, locked_by_user_id, locked_at to text_resources
        # ========================================
        logger.info("Adding pool columns to text_resources...")
        try:
            db.execute(text("""
                ALTER TABLE text_resources 
                ADD COLUMN IF NOT EXISTS pool_status VARCHAR(20) DEFAULT 'available'
            """))
            logger.info("✓ pool_status column added to text_resources")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ pool_status column already exists in text_resources")
            else:
                raise

        try:
            db.execute(text("""
                ALTER TABLE text_resources 
                ADD COLUMN IF NOT EXISTS locked_by_user_id INTEGER NULL REFERENCES users(id)
            """))
            logger.info("✓ locked_by_user_id column added to text_resources")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ locked_by_user_id column already exists in text_resources")
            else:
                raise

        try:
            db.execute(text("""
                ALTER TABLE text_resources 
                ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP NULL
            """))
            logger.info("✓ locked_at column added to text_resources")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ locked_at column already exists in text_resources")
            else:
                raise

        # ========================================
        # 5. Add pool_status, locked_by_user_id, locked_at to image_resources
        # ========================================
        logger.info("Adding pool columns to image_resources...")
        try:
            db.execute(text("""
                ALTER TABLE image_resources 
                ADD COLUMN IF NOT EXISTS pool_status VARCHAR(20) DEFAULT 'available'
            """))
            logger.info("✓ pool_status column added to image_resources")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ pool_status column already exists in image_resources")
            else:
                raise

        try:
            db.execute(text("""
                ALTER TABLE image_resources 
                ADD COLUMN IF NOT EXISTS locked_by_user_id INTEGER NULL REFERENCES users(id)
            """))
            logger.info("✓ locked_by_user_id column added to image_resources")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ locked_by_user_id column already exists in image_resources")
            else:
                raise

        try:
            db.execute(text("""
                ALTER TABLE image_resources 
                ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP NULL
            """))
            logger.info("✓ locked_at column added to image_resources")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ locked_at column already exists in image_resources")
            else:
                raise

        # ========================================
        # 6. Add review_level, reviewer_id to text_annotation_queue
        # ========================================
        logger.info("Adding review tracking columns to text_annotation_queue...")
        try:
            db.execute(text("""
                ALTER TABLE text_annotation_queue 
                ADD COLUMN IF NOT EXISTS review_level INTEGER NULL
            """))
            logger.info("✓ review_level column added to text_annotation_queue")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ review_level column already exists in text_annotation_queue")
            else:
                raise

        try:
            db.execute(text("""
                ALTER TABLE text_annotation_queue 
                ADD COLUMN IF NOT EXISTS reviewer_id INTEGER NULL REFERENCES users(id)
            """))
            logger.info("✓ reviewer_id column added to text_annotation_queue")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ reviewer_id column already exists in text_annotation_queue")
            else:
                raise

        # ========================================
        # 7. Add review_level, reviewer_id to image_annotation_queue
        # ========================================
        logger.info("Adding review tracking columns to image_annotation_queue...")
        try:
            db.execute(text("""
                ALTER TABLE image_annotation_queue 
                ADD COLUMN IF NOT EXISTS review_level INTEGER NULL
            """))
            logger.info("✓ review_level column added to image_annotation_queue")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ review_level column already exists in image_annotation_queue")
            else:
                raise

        try:
            db.execute(text("""
                ALTER TABLE image_annotation_queue 
                ADD COLUMN IF NOT EXISTS reviewer_id INTEGER NULL REFERENCES users(id)
            """))
            logger.info("✓ reviewer_id column added to image_annotation_queue")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ reviewer_id column already exists in image_annotation_queue")
            else:
                raise

        # ========================================
        # 8. Add reviewer_level to review_corrections
        # ========================================
        logger.info("Adding reviewer_level column to review_corrections...")
        try:
            db.execute(text("""
                ALTER TABLE review_corrections 
                ADD COLUMN IF NOT EXISTS reviewer_level INTEGER NULL
            """))
            logger.info("✓ reviewer_level column added to review_corrections")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ reviewer_level column already exists in review_corrections")
            else:
                raise

        # ========================================
        # 9. Add reviewer_level to image_review_corrections
        # ========================================
        logger.info("Adding reviewer_level column to image_review_corrections...")
        try:
            db.execute(text("""
                ALTER TABLE image_review_corrections 
                ADD COLUMN IF NOT EXISTS reviewer_level INTEGER NULL
            """))
            logger.info("✓ reviewer_level column added to image_review_corrections")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✓ reviewer_level column already exists in image_review_corrections")
            else:
                raise

        # ========================================
        # 10. Create indexes for new columns
        # ========================================
        logger.info("Creating indexes for new columns...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_project_assignments_review_level ON project_assignments(review_level)",
            "CREATE INDEX IF NOT EXISTS idx_text_annotations_review_level ON text_annotations(current_review_level)",
            "CREATE INDEX IF NOT EXISTS idx_image_annotations_review_level ON image_annotations(current_review_level)",
            "CREATE INDEX IF NOT EXISTS idx_text_resources_pool_status ON text_resources(pool_status)",
            "CREATE INDEX IF NOT EXISTS idx_text_resources_locked_by ON text_resources(locked_by_user_id)",
            "CREATE INDEX IF NOT EXISTS idx_image_resources_pool_status ON image_resources(pool_status)",
            "CREATE INDEX IF NOT EXISTS idx_image_resources_locked_by ON image_resources(locked_by_user_id)",
            "CREATE INDEX IF NOT EXISTS idx_text_queue_review_level ON text_annotation_queue(review_level)",
            "CREATE INDEX IF NOT EXISTS idx_text_queue_reviewer ON text_annotation_queue(reviewer_id)",
            "CREATE INDEX IF NOT EXISTS idx_image_queue_review_level ON image_annotation_queue(review_level)",
            "CREATE INDEX IF NOT EXISTS idx_image_queue_reviewer ON image_annotation_queue(reviewer_id)",
        ]
        
        for idx_sql in indexes:
            try:
                db.execute(text(idx_sql))
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")
        
        logger.info("✓ Indexes created")

        # ========================================
        # 11. Set default review_level=1 for existing reviewers
        # ========================================
        logger.info("Setting default review_level=1 for existing reviewers...")
        db.execute(text("""
            UPDATE project_assignments 
            SET review_level = 1 
            WHERE role = 'reviewer' AND review_level IS NULL
        """))
        logger.info("✓ Default review levels set for existing reviewers")

        # ========================================
        # 12. Update existing annotation statuses
        # ========================================
        # Map 'pending' to 'draft', 'under_review' to 'in_review'
        logger.info("Updating existing annotation statuses...")
        db.execute(text("""
            UPDATE text_annotations 
            SET status = 'draft' 
            WHERE status = 'pending'
        """))
        db.execute(text("""
            UPDATE text_annotations 
            SET status = 'in_review' 
            WHERE status = 'under_review'
        """))
        db.execute(text("""
            UPDATE image_annotations 
            SET status = 'draft' 
            WHERE status = 'pending'
        """))
        db.execute(text("""
            UPDATE image_annotations 
            SET status = 'in_review' 
            WHERE status = 'under_review'
        """))
        logger.info("✓ Annotation statuses updated")

        # Commit all changes
        db.commit()
        
        logger.info("=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Changes made:")
        logger.info("  - Added review_level to project_assignments")
        logger.info("  - Added current_review_level to text_annotations")
        logger.info("  - Added current_review_level to image_annotations")
        logger.info("  - Added pool_status, locked_by_user_id, locked_at to text_resources")
        logger.info("  - Added pool_status, locked_by_user_id, locked_at to image_resources")
        logger.info("  - Added review_level, reviewer_id to text_annotation_queue")
        logger.info("  - Added review_level, reviewer_id to image_annotation_queue")
        logger.info("  - Added reviewer_level to review_corrections")
        logger.info("  - Added reviewer_level to image_review_corrections")
        logger.info("  - Created indexes for new columns")
        logger.info("  - Set default review_level=1 for existing reviewers")
        logger.info("  - Updated annotation statuses (pending->draft, under_review->in_review)")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()