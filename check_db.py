import sqlite3
import os

db_path = "v2.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, vendor, amount, category, status FROM reports ORDER BY created_at DESC LIMIT 5;")
    rows = cursor.fetchall()
    print("Last 5 reports:")
    for row in rows:
        print(row)
    conn.close()
else:
    print(f"DB {db_path} not found")
