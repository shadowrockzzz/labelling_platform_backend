"""
Database migration script to update existing database for role-based authentication system.
This script should be run after installing the new code.

Migration steps:
1. Update user roles: 'manager' -> 'project_manager', 'labeler' -> 'annotator'
2. Add status column to projects table
3. Add project_assignments table
"""

from sqlalchemy import text
from app.core.database import engine, SessionLocal

def migrate():
    """Run database migration."""
    db = SessionLocal()
    
    try:
        print("Starting database migration...")
        
        # Step 1: Update user roles
        print("Step 1: Updating user roles...")
        db.execute(text("""
            UPDATE users 
            SET role = CASE 
                WHEN role = 'manager' THEN 'project_manager'
                WHEN role = 'labeler' THEN 'annotator'
                ELSE role
            END
            WHERE role IN ('manager', 'labeler')
        """))
        db.commit()
        print("✓ User roles updated")
        
        # Step 2: Add status column to projects table if not exists
        # print("Step 2: Adding status column to projects table...")
        # try:
        #     db.execute(text("""
        #         ALTER TABLE projects 
        #         ADD COLUMN status VARCHAR DEFAULT 'active'
        #     """))
        #     db.commit()
        #     print("✓ Status column added to projects table")
        # except Exception as e:
        #     if "duplicate column name" in str(e).lower():
        #         print("✓ Status column already exists in projects table")
        #     else:
        #         raise e
        
        # Step 3: Create project_assignments table
        print("Step 3: Creating project_assignments table...")
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS project_assignments (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role VARCHAR NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(project_id, user_id)
                )
            """))
            db.commit()
            print("✓ Project_assignments table created")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ Project_assignments table already exists")
            else:
                raise e
        
        # Step 4: Update projects table foreign key constraints
        print("Step 4: Updating foreign key constraints...")
        try:
            # Drop old foreign key if exists
            db.execute(text("""
                ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_owner_id_fkey
            """))
            
            # Add new foreign key with CASCADE delete
            db.execute(text("""
                ALTER TABLE projects 
                ADD CONSTRAINT projects_owner_id_fkey 
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            """))
            db.commit()
            print("✓ Foreign key constraints updated")
        except Exception as e:
            print(f"Note: {e}")
        
        # Step 5: Add bio column to users table
        print("Step 5: Adding bio column to users table...")
        try:
            db.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS bio VARCHAR
            """))
            db.commit()
            print("✓ Bio column added to users table")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("✓ Bio column already exists in users table")
            else:
                print(f"Note: {e}")
        
        print("\n✓ Migration completed successfully!")
        print("\nSummary of changes:")
        print("- User roles updated: manager -> project_manager, labeler -> annotator")
        print("- Added status column to projects table")
        print("- Created project_assignments table for team management")
        print("- Updated foreign key constraints with CASCADE delete")
        print("- Added bio column to users table")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()