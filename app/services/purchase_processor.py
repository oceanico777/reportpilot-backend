from sqlalchemy.orm import Session
from .. import models
import time
import os
from datetime import datetime
import json

def process_purchase(purchase_id: str):
    """
    Refine Purchase details using more deep OCR or classification if needed.
    For now, this is a placeholder to ensure the background task architecture remains.
    In the future, this can link the Purchase to a specific Provider based on the extracted name.
    """
    from ..database import SessionLocal
    db = SessionLocal()
    
    try:
        purchase = db.query(models.Purchase).filter(models.Purchase.id == purchase_id).first()
        if not purchase:
            return

        # Simple Logic: Try to match Provider
        if purchase.vendor and not purchase.provider_id:
            # Fuzzy match or exact match logic here
            # For MVP: Exact match on name
            provider = db.query(models.Provider).filter(
                models.Provider.company_id == purchase.company_id,
                models.Provider.name == purchase.vendor
            ).first()
            
            if provider:
                purchase.provider_id = provider.id
                
        # Status update
        purchase.status = models.PurchaseStatus.PENDING_REVIEW.value
        db.commit()
        
    except Exception as e:
        print(f"Error processing purchase {purchase_id}: {e}")
    finally:
        db.close()
