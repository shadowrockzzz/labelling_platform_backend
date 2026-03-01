"""
Migration: Add rq_job_id column to text_annotation_queue table.

This migration adds support for Redis Queue job tracking while maintaining
the PostgreSQL table as an audit log.

Run with: python migration_add_rq_job_id.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings


def run_migration():
    """Add rq_job_id column to text_annotation_queue table."""
    
    print(f"Connecting to database: {settings.db_url}")
    
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'text_annotation_queue' 
            AND column_name = 'rq_job_id'
        """))
        
        if result.fetchone():
            print("Column rq_job_id already exists. Skipping migration.")
            return
        
        # Add the column
        print("Adding rq_job_id column to text_annotation_queue...")
        conn.execute(text("""
            ALTER TABLE text_annotation_queue 
            ADD COLUMN rq_job_id VARCHAR(255) NULL
        """))
        
        # Create index on the new column
        print("Creating index on rq_job_id...")
        conn.execute(text("""
            CREATE INDEX idx_queue_rq_job_id 
            ON text_annotation_queue(rq_job_id)
        """))
        
        conn.commit()
        print("Migration completed successfully!")


def rollback():
    """Remove rq_job_id column from text_annotation_queue table."""
    
    print(f"Connecting to database: {settings.db_url}")
    
    with engine.connect() as conn:
        # Drop index first
        print("Dropping index on rq_job_id...")
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_queue_rq_job_id
        """))
        
        # Drop column
        print("Dropping rq_job_id column...")
        conn.execute(text("""
            ALTER TABLE text_annotation_queue 
            DROP COLUMN IF EXISTS rq_job_id
        """))
        
        conn.commit()
        print("Rollback completed successfully!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration: Add rq_job_id column")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()
    
    if args.rollback:
        rollback()
    else:
        run_migration()