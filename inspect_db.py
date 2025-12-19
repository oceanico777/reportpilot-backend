from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Receipt, ParsedData
from app.database import SessionLocal, engine

# engine = create_engine(DATABASE_URL) # Already in app.database
# SessionLocal = ...
db = SessionLocal()

receipt_id = "258a455a-04ba-409b-90f9-f10dd4432dac"

print(f"Checking Receipt: {receipt_id}")
receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()

if receipt:
    print(f"Receipt Found. ID: {receipt.id}, Status: {receipt.status}")
    if receipt.parsed_data:
        pd = receipt.parsed_data
        print(f"ParsedData Found. ID: {pd.id}")
        print(f"  Vendor: {pd.vendor}")
        print(f"  Date: {pd.date} (Type: {type(pd.date)})")
        print(f"  Amount: {pd.amount}")
    else:
        print("ParsedData is NULL")
else:
    print("Receipt NOT found")

db.close()
