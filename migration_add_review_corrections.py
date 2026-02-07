"""
Migration: Add review_corrections table for annotation audit trail.

This migration creates a new table to store reviewer corrections
to annotations, maintaining an audit trail for the review workflow.
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from sqlalchemy import text


def upgrade():
    """Add review_corrections table."""
    conn = engine.connect()
    
    # Create review_corrections table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS review_corrections (
            id SERIAL PRIMARY KEY,
            annotation_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            original_data JSONB,
            corrected_data JSONB,
            comment TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            annotator_response TEXT,
            FOREIGN KEY (annotation_id) REFERENCES text_annotations(id) ON DELETE CASCADE,
            FOREIGN KEY (reviewer_id) REFERENCES users(id)
        );
    """))
    
    # Create indexes for performance
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_review_corrections_annotation 
        ON review_corrections(annotation_id);
    """))
    
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_review_corrections_reviewer 
        ON review_corrections(reviewer_id);
    """))
    
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_review_corrections_status 
        ON review_corrections(status);
    """))
    
    conn.commit()
    conn.close()
    print("✓ Created review_corrections table")


def downgrade():
    """Remove review_corrections table."""
    conn = engine.connect()
    
    # Drop indexes
    conn.execute(text("DROP INDEX IF EXISTS idx_review_corrections_status;"))
    conn.execute(text("DROP INDEX IF EXISTS idx_review_corrections_reviewer;"))
    conn.execute(text("DROP INDEX IF EXISTS idx_review_corrections_annotation;"))
    
    # Drop table
    conn.execute(text("DROP TABLE IF EXISTS review_corrections;"))
    
    conn.commit()
    conn.close()
    print("✓ Dropped review_corrections table")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration for review corrections")
    parser.add_argument("--downgrade", action="store_true", help="Rollback migration")
    
    args = parser.parse_args()
    
    if args.downgrade:
        print("Running downgrade...")
        downgrade()
    else:
        print("Running upgrade...")
        upgrade()