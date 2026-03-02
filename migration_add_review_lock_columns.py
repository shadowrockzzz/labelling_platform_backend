"""
Migration script to add review_locked_by and review_locked_at columns
to both image_annotations and text_annotations tables.

These columns are needed for the multi-level review workflow with resource pool.

Run with: python migration_add_review_lock_columns.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")

def run_migration():
    """Add review lock columns to annotation tables."""
    
    engine = create_engine(DATABASE_URL)
    
    migration_sql = """
    -- Add review lock columns to image_annotations table
    ALTER TABLE image_annotations 
    ADD COLUMN IF NOT EXISTS review_locked_by INTEGER REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS review_locked_at TIMESTAMP WITH TIME ZONE;
    
    -- Add review lock columns to text_annotations table
    ALTER TABLE text_annotations 
    ADD COLUMN IF NOT EXISTS review_locked_by INTEGER REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS review_locked_at TIMESTAMP WITH TIME ZONE;
    
    -- Create indexes for the new columns (optional but recommended)
    CREATE INDEX IF NOT EXISTS idx_image_annotations_review_locked_by ON image_annotations(review_locked_by);
    CREATE INDEX IF NOT EXISTS idx_text_annotations_review_locked_by ON text_annotations(review_locked_by);
    """
    
    with engine.connect() as conn:
        # Split and execute each statement
        statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
        
        for statement in statements:
            try:
                conn.execute(text(statement))
                conn.commit()
                print(f"✓ Executed: {statement[:80]}...")
            except Exception as e:
                # Check if it's a "column already exists" error
                if "already exists" in str(e).lower():
                    print(f"ℹ Skipped (already exists): {statement[:60]}...")
                else:
                    print(f"✗ Error: {e}")
                    print(f"  Statement: {statement[:100]}...")
    
    print("\n✅ Migration completed successfully!")
    print("   - Added review_locked_by and review_locked_at to image_annotations")
    print("   - Added review_locked_by and review_locked_at to text_annotations")

if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add review lock columns to annotation tables")
    print("=" * 60)
    print()
    
    run_migration()