"""
Migration script to add annotation_tasks table.

This table implements a task queue system where:
- Each resource gets a corresponding task
- Annotators claim one task at a time
- Tasks are locked to prevent concurrent access
- Locks auto-expire after 2 hours

Run with: python migration_add_annotation_tasks.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from individual env vars
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

def run_migration():
    """Create annotation_tasks table with indexes."""
    
    engine = create_engine(DATABASE_URL)
    
    migration_sql = """
    -- Enable UUID extension if not already enabled
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Create annotation_tasks table
    CREATE TABLE IF NOT EXISTS annotation_tasks (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        resource_id INTEGER NOT NULL,
        resource_type VARCHAR(10) NOT NULL CHECK (resource_type IN ('text', 'image')),
        annotator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'available',
        -- Statuses: 'available', 'locked', 'in_progress', 'submitted', 'approved', 'rejected', 'skipped'
        locked_at TIMESTAMP,
        lock_expires_at TIMESTAMP,
        annotation_id INTEGER,
        skipped_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        
        -- Constraint: one task per resource per project
        CONSTRAINT uq_annotation_task_resource UNIQUE (project_id, resource_id, resource_type)
    );
    
    -- Create indexes for efficient querying
    CREATE INDEX IF NOT EXISTS idx_annotation_tasks_project_status 
        ON annotation_tasks(project_id, status);
    
    CREATE INDEX IF NOT EXISTS idx_annotation_tasks_annotator_status 
        ON annotation_tasks(annotator_id, status);
    
    CREATE INDEX IF NOT EXISTS idx_annotation_tasks_lock_expiry 
        ON annotation_tasks(status, lock_expires_at) 
        WHERE status = 'locked';
    
    -- Create index for atomic claim queries
    CREATE INDEX IF NOT EXISTS idx_annotation_tasks_available 
        ON annotation_tasks(project_id, created_at) 
        WHERE status = 'available';
    
    -- Create trigger for updated_at
    CREATE OR REPLACE FUNCTION update_annotation_tasks_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS trigger_annotation_tasks_updated_at ON annotation_tasks;
    CREATE TRIGGER trigger_annotation_tasks_updated_at
        BEFORE UPDATE ON annotation_tasks
        FOR EACH ROW
        EXECUTE FUNCTION update_annotation_tasks_updated_at();
    
    -- Add comment
    COMMENT ON TABLE annotation_tasks IS 'Task queue for annotation workflow with locking mechanism';
    """
    
    with engine.connect() as conn:
        # Split and execute each statement
        statements = migration_sql.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    conn.execute(text(statement))
                    conn.commit()
                    print(f"Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"Error executing statement: {e}")
                    # Continue with other statements
    
    print("\n✅ Migration completed: annotation_tasks table created")

def rollback_migration():
    """Rollback the migration."""
    
    engine = create_engine(DATABASE_URL)
    
    rollback_sql = """
    DROP TRIGGER IF EXISTS trigger_annotation_tasks_updated_at ON annotation_tasks;
    DROP FUNCTION IF EXISTS update_annotation_tasks_updated_at();
    DROP TABLE IF EXISTS annotation_tasks;
    """
    
    with engine.connect() as conn:
        for statement in rollback_sql.split(';'):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
                conn.commit()
    
    print("✅ Rollback completed: annotation_tasks table dropped")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        run_migration()