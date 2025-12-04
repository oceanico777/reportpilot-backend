from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas
from ..services import ocr

router = APIRouter()

@router.post("/upload", response_model=schemas.Receipt)
def upload_receipt(receipt: schemas.ReceiptCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # In a real app, we would handle file upload here or get a signed URL
    # For MVP, we assume the client uploads to Supabase Storage and sends us the URL
    db_receipt = models.Receipt(
        company_id=receipt.company_id,
        file_url=receipt.file_url,
        status=models.ReceiptStatus.PENDING.value
    )
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)
    
    # Trigger OCR in background
    background_tasks.add_task(ocr.process_receipt, db_receipt.id, db)
    
    return db_receipt

@router.get("/", response_model=List[schemas.Receipt])
def read_receipts(company_id: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    receipts = db.query(models.Receipt).filter(models.Receipt.company_id == company_id).offset(skip).limit(limit).all()
    return receipts

@router.get("/{receipt_id}", response_model=schemas.Receipt)
def read_receipt(receipt_id: str, db: Session = Depends(get_db)):
    receipt = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt
