from app.database import engine, Base
from app import models
import sys

def reset_schema():
    print("WARNING: This will drop all tables in the database.")
    try:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Schema reset execution complete.")
    except Exception as e:
        print(f"❌ Error resetting schema: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_schema()
