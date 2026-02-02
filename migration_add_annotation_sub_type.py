"""
Migration script to add annotation_sub_type column to text_annotations table.

This migration:
1. Adds annotation_sub_type column (VARCHAR(50), nullable)
2. Migrates existing data: sets annotation_sub_type = annotation_type
3. No data loss, backward compatible

Run this migration with:
    python migration_add_annotation_sub_type.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings


def migrate():
    """Execute migration to add annotation_sub_type column."""
    
    # Create engine
    database_url = settings.db_url
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("Starting migration: Add annotation_sub_type column...")
        
        # Step 1: Add annotation_sub_type column
        print("Step 1: Adding annotation_sub_type column...")
        alter_table_sql = """
            ALTER TABLE text_annotations
            ADD COLUMN IF NOT EXISTS annotation_sub_type VARCHAR(50);
        """
        session.execute(text(alter_table_sql))
        session.commit()
        print("✓ annotation_sub_type column added")
        
        # Step 2: Migrate existing data - set annotation_sub_type = annotation_type
        print("\nStep 2: Migrating existing annotations...")
        
        # First, check if we need to migrate
        check_sql = """
            SELECT COUNT(*) as count
            FROM text_annotations
            WHERE annotation_sub_type IS NULL;
        """
        result = session.execute(text(check_sql)).fetchone()
        null_count = result[0] if result else 0
        
        if null_count > 0:
            print(f"Found {null_count} annotations to migrate...")
            
            # For existing annotations, map old annotation_type to annotation_sub_type
            # Old values: 'general', 'ner', 'classification', 'sentiment'
            # New values: 'general', 'ner', 'pos', 'sentiment', 'relation', 'span', 'classification', 'dependency', 'coreference'
            # Direct mappings: general->general, ner->ner, classification->classification, sentiment->sentiment
            
            migrate_sql = """
                UPDATE text_annotations
                SET annotation_sub_type = annotation_type
                WHERE annotation_sub_type IS NULL;
            """
            session.execute(text(migrate_sql))
            session.commit()
            print(f"✓ Migrated {null_count} annotations")
        else:
            print("✓ No annotations need migration (all already have annotation_sub_type)")
        
        # Step 3: Verify migration
        print("\nStep 3: Verifying migration...")
        verify_sql = """
            SELECT annotation_type, annotation_sub_type, COUNT(*) as count
            FROM text_annotations
            GROUP BY annotation_type, annotation_sub_type
            ORDER BY annotation_type;
        """
        results = session.execute(text(verify_sql)).fetchall()
        
        print("\nAnnotation types summary:")
        for row in results:
            annotation_type, annotation_sub_type, count = row
            print(f"  - annotation_type: {annotation_type}, annotation_sub_type: {annotation_sub_type}, count: {count}")
        
        print("\n✓ Migration completed successfully!")
        print("\nNote: The annotation_type column now always contains 'text' (module-level).")
        print("      The annotation_sub_type column contains the specific type: 'ner', 'pos', 'sentiment', etc.")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        session.rollback()
        sys.exit(1)
    
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    migrate()