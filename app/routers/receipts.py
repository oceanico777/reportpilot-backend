from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas
from ..services import ocr

router = APIRouter()

from ..auth import get_user_company

from pathlib import Path
import shutil
import uuid
import os

@router.post("/upload", response_model=schemas.Receipt)
def upload_receipt(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    # 1. Cloud Storage Integration
    from ..services.storage import storage_service
    
    # 2. Upload to Cloud (Supabase)
    # We pass company_id to organize files in the bucket
    storage_data = storage_service.upload_file(file, company_id)
    cloud_path = storage_data.get("storage_path")
    
    # 3. Save File Locally (Fallback/Cache)
    UPLOAD_DIR = "uploads/receipts"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    local_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Reset file pointer after storage_service read it
    file.file.seek(0)
    with open(local_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 4. Create Receipt Record
    db_receipt = models.Receipt(
        company_id=company_id,
        file_url=local_path,       # Keep local path for immediate background processing
        storage_path=cloud_path,   # Permanent cloud path
        filename=file.filename,
        content_type=file.content_type,
        status=models.ReceiptStatus.PENDING.value
    )
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)
    
    # 5. Trigger OCR (Background)
    # The OCR service will use the local_path for speed, but cloud_path is stored for permanence
    background_tasks.add_task(ocr.process_receipt, db_receipt.id, db)
    
    return db_receipt

@router.get("/", response_model=List[schemas.Receipt])
def read_receipts(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    from ..services.storage import storage_service
    receipts = db.query(models.Receipt).filter(models.Receipt.company_id == company_id).offset(skip).limit(limit).all()
    
    # Enrich with signed URLs if they are in cloud
    for r in receipts:
        if r.storage_path and not r.storage_path.startswith("uploads/"):
            signed_url = storage_service.get_file_url(r.storage_path)
            if signed_url:
                r.file_url = signed_url
                
    return receipts

@router.get("/{receipt_id}", response_model=schemas.Receipt)
def read_receipt(
    receipt_id: str, 
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    from ..services.storage import storage_service
    receipt = db.query(models.Receipt).filter(
        models.Receipt.id == receipt_id,
        models.Receipt.company_id == company_id
    ).first()
    
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
        
    # Enrich with signed URL
    if receipt.storage_path and not receipt.storage_path.startswith("uploads/"):
        signed_url = storage_service.get_file_url(receipt.storage_path)
        if signed_url:
            receipt.file_url = signed_url
            
    return receipt
