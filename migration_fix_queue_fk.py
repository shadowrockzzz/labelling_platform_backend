"""
Migration: Fix text_annotation_queue FK constraint

The text_annotation_queue table has a foreign key constraint on resource_id
that references text_resources. This causes issues when tracking image
annotations because the resource_id points to image_resources instead.

This migration drops the FK constraint, allowing resource_id to be a simple
integer that can reference different resource tables based on annotation_type.

Run with: python migration_fix_queue_fk.py
"""

import asyncio
from sqlalchemy import text
from app.core.database import engine


def run_migration():
    """Drop the foreign key constraint on text_annotation_queue.resource_id"""
    
    with engine.connect() as conn:
        print("Checking for foreign key constraint...")
        
        # Check if the constraint exists
        result = conn.execute(text("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'text_annotation_queue' 
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name LIKE '%resource_id%'
        """))
        
        constraints = result.fetchall()
        
        if not constraints:
            # Try to find any FK constraint on resource_id column
            result = conn.execute(text("""
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = 'text_annotation_queue'
                AND tc.constraint_type = 'FOREIGN KEY'
                AND kcu.column_name = 'resource_id'
            """))
            constraints = result.fetchall()
        
        if constraints:
            for constraint in constraints:
                constraint_name = constraint[0]
                print(f"Dropping constraint: {constraint_name}")
                conn.execute(text(f"""
                    ALTER TABLE text_annotation_queue 
                    DROP CONSTRAINT IF EXISTS {constraint_name}
                """))
            conn.commit()
            print("✓ Foreign key constraint dropped successfully!")
        else:
            print("No foreign key constraint found on resource_id column.")
            print("The migration may have already been applied.")
        
        # Verify the change
        result = conn.execute(text("""
            SELECT constraint_name 
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'text_annotation_queue'
            AND tc.constraint_type = 'FOREIGN KEY'
            AND kcu.column_name = 'resource_id'
        """))
        
        remaining = result.fetchall()
        if remaining:
            print(f"Warning: Still found FK constraints: {remaining}")
        else:
            print("✓ Verified: No FK constraint on resource_id column.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Fix text_annotation_queue FK constraint")
    print("=" * 60)
    run_migration()
    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)