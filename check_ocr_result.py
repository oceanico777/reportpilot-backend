import sqlite3
import pandas as pd

db_path = "v2.db"

def check_db():
    conn = sqlite3.connect(db_path)
    print("--- Receipts Status ---")
    receipts = pd.read_sql_query("SELECT id, status, filename FROM receipts ORDER BY id DESC LIMIT 5", conn)
    print(receipts)
    
    print("\n--- Parsed Data ---")
    parsed = pd.read_sql_query("SELECT id, receipt_id, vendor, amount, date FROM parsed_data ORDER BY id DESC LIMIT 5", conn)
    print(parsed)
    
    conn.close()

if __name__ == "__main__":
    check_db()
