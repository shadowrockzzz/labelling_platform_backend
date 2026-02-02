"""
Migration: Add config column to projects table
This script adds a JSON config column to store dynamic annotation settings
"""
from sqlalchemy import text
from app.core.database import engine

def migrate():
    """Add config column to projects table if it doesn't exist."""
    print("Starting migration: Add config column to projects table...")
    
    try:
        with engine.connect() as conn:
            # Check if config column exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'projects' 
                    AND column_name = 'config'
                );
            """))
            column_exists = result.scalar()
            
            if column_exists:
                print("Config column already exists in projects table. Skipping migration.")
                return
            
            # Add config column
            conn.execute(text("""
                ALTER TABLE projects 
                ADD COLUMN IF NOT EXISTS config JSON;
            """))
            conn.commit()
            
            print("✓ Successfully added config column to projects table")
            
            # Verify the column was added
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'projects' 
                AND column_name = 'config';
            """))
            column_info = result.fetchone()
            
            if column_info:
                print(f"  Column name: {column_info[0]}")
                print(f"  Data type: {column_info[1]}")
            
            print("\nMigration completed successfully!")
            
    except Exception as e:
        print(f"\n✗ Migration failed with error: {e}")
        raise

if __name__ == "__main__":
    migrate()