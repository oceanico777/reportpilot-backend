import sys
import os

# Add the project root to sys.path to allow importing from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import SessionLocal
from app import models

db = SessionLocal()
receipt_id = "bb9ab9b3-1252-4274-ab7f-3b80998a5ad3" # Corrected from screenshot
receipt = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()

if not receipt:
    print(f"Receipt {receipt_id} NOT found in DB.")
else:
    print(f"Receipt ID: {receipt.id}")
    print(f"Status: {receipt.status}")
    print(f"Created At: {receipt.created_at}")
    print(f"Storage Path: {receipt.storage_path}")
    
    parsed = db.query(models.ParsedData).filter(models.ParsedData.receipt_id == receipt_id).first()
    if parsed:
        print("--- Parsed Data ---")
        print(f"Vendor: {parsed.vendor}")
        print(f"Amount: {parsed.amount}")
        print(f"Category: {parsed.category}")
    else:
        print("No parsed data found yet.")

db.close()
