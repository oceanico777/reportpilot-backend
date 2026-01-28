import sqlite3
import os

DB_PATH = "reportpilot.db"

def inspect_schema():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Table: reports ---")
    try:
        cursor.execute("PRAGMA table_info(reports)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
    except Exception as e:
        print(e)
        
    conn.close()

if __name__ == "__main__":
    inspect_schema()
