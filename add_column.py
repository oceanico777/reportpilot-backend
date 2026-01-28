import sqlite3
import os

DB_PATH = "reportpilot.db"

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Adding vendor_nit to reports ---")
    try:
        cursor.execute("ALTER TABLE reports ADD COLUMN vendor_nit VARCHAR")
        conn.commit()
        print("Success: Column added.")
    except Exception as e:
        print(f"Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    add_column()
