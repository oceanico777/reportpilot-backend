from sqlalchemy.orm import Session
from .. import models
import time
import random

def process_receipt(receipt_id: str, db: Session):
    # Simulate processing delay
    time.sleep(2)
    
    receipt = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()
    if not receipt:
        return

    # Mock OCR result
    # In real implementation, this would call OpenAI GPT-4o
    mock_data = {
        "vendor": "Mock Vendor Inc.",
        "date": "2023-10-25",
        "amount": round(random.uniform(10.0, 500.0), 2),
        "currency": "USD",
        "category": random.choice(["Office Supplies", "Travel", "Meals", "Software"]),
        "confidence_score": 0.98
    }
    
    parsed_data = models.ParsedData(
        receipt_id=receipt.id,
        vendor=mock_data["vendor"],
        date=datetime.strptime(mock_data["date"], "%Y-%m-%d").date(),
        amount=mock_data["amount"],
        currency=mock_data["currency"],
        category=mock_data["category"],
        confidence_score=mock_data["confidence_score"]
    )
    
    db.add(parsed_data)
    receipt.status = models.ReceiptStatus.PROCESSED.value
    db.commit()

from datetime import datetime
