from app.database import SessionLocal
from app import models
import json

db = SessionLocal()
try:
    failed_receipts = db.query(models.Receipt).filter(models.Receipt.status == "FAILED").order_by(models.Receipt.created_at.desc()).limit(5).all()
    print(f"Found {len(failed_receipts)} failed receipts.")
    for r in failed_receipts:
        print(f"Receipt ID: {r.id}, Filename: {r.filename}, Local Path: {r.file_url}")
        # Check if parsed data exists but status is failed?
        pd = db.query(models.ParsedData).filter(models.ParsedData.receipt_id == r.id).first()
        if pd:
            print(f"  ParsedData exists! Vendor: {pd.vendor}, Amount: {pd.amount}")
        else:
            print("  No ParsedData found.")
finally:
    db.close()
