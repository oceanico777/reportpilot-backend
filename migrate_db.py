import sqlalchemy
from sqlalchemy import create_engine, text
from app.database import engine

print("Starting migration...")
# engine = create_engine(DATABASE_URL) # Already exists

commands = [
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS vendor VARCHAR;",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS amount FLOAT;",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS currency VARCHAR;",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS category VARCHAR;"
]

with engine.connect() as conn:
    for cmd in commands:
        try:
            print(f"Executing: {cmd}")
            conn.execute(text(cmd))
            print("OK")
        except Exception as e:
            print(f"Error executing {cmd}: {e}")
            
    conn.commit()

print("Migration completed.")
