from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, auth
from datetime import datetime, date
from sqlalchemy import func
from typing import List

router = APIRouter(
    prefix="/closures",
    tags=["closures"],
)

@router.get("/summary", response_model=schemas.DailyClosureSummary)
def get_daily_summary(
    date_str: str = None, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    target_date = date.today()
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass # Fallback to today

    # Calculate Total Expenses (Purchases for this date)
    total_expenses = db.query(func.sum(models.Purchase.amount)).filter(
        models.Purchase.company_id == current_user.company_id,
        models.Purchase.date == target_date
    ).scalar() or 0.0

    # Placeholders for Sales/Advances (Until we have sales module)
    total_sales = 0.0
    total_advances = 0.0
    total_collections = 0.0
    
    # Balance = (Sales + Collections) - (Expenses + Advances)
    # Adjust logic as per business rule. Usually Balance = Cash In Hand - System Calculated
    # For now, let's assume Balance = Sales - Expenses
    balance = total_sales - total_expenses 

    return schemas.DailyClosureSummary(
        date=target_date,
        total_sales=total_sales,
        total_collections=total_collections,
        total_expenses=total_expenses,
        total_advances=total_advances,
        balance=balance
    )

# ... (previous imports)
import os
import uuid
import shutil
from ..services.report_generator import generate_clearance_act
# Assuming simple local storage for now as seen in tours.py, or should use services.storage if available.
# Let's check services.storage first. It was in the file list.
from ..services.storage import storage_service

UPLOAD_DIR = "uploads/signatures"
os.makedirs(UPLOAD_DIR, exist_ok=True)
PDF_DIR = "uploads/actas"
os.makedirs(PDF_DIR, exist_ok=True)

@router.post("/close", response_model=schemas.DailyClosure)
async def close_day(
    date_str: str = Form(...), # Multipart form data
    signature: UploadFile = File(...),
    total_sales: float = Form(0.0), # Allow manual sales entry
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    try:
        closure_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # 1. Check if already closed
    existing = db.query(models.DailyClosure).filter(
        models.DailyClosure.company_id == current_user.company_id,
        models.DailyClosure.date == closure_date
    ).first()
    
    if existing:
         raise HTTPException(status_code=400, detail="Daily closure already exists for this date")

    # 2. Upload Signature
    sig_filename = f"sig_{closure_date}_{uuid.uuid4()}.png"
    sig_path = os.path.join(UPLOAD_DIR, sig_filename)
    
    content = await signature.read()
    with open(sig_path, "wb") as buffer:
        buffer.write(content)
        
    # Upload to Cloud/Storage Service
    sig_storage_data = storage_service.upload_bytes(content, sig_filename, "image/png", current_user.company_id)
    cloud_sig_path = sig_storage_data.get("storage_path", sig_path)
    
    # 3. Calculate Financials (Balance Logic)
    # Reusing logic from summary endpoint or calculating fresh
    total_expenses = db.query(func.sum(models.Purchase.amount)).filter(
        models.Purchase.company_id == current_user.company_id,
        models.Purchase.date == closure_date
    ).scalar() or 0.0
    
    # total_sales is already passed as argument
    # total_sales = 0.0 # Placeholder REMOVED
    
    balance = total_sales - total_expenses

    # 4. Generate PDF Act
    # Fetch detailed expenses for the PDF
    expenses_query = db.query(models.Purchase).filter(
        models.Purchase.company_id == current_user.company_id,
        models.Purchase.date == closure_date
    ).all()
    
    expense_details = [{
        "date": e.created_at.strftime("%Y-%m-%d"),
        "category": e.category or "General",
        "vendor": e.provider.name if e.provider else (e.category or "N/A"),
        "amount": e.amount
    } for e in expenses_query]

    closure_data = {
        "company_name": current_user.companies[0].name if current_user.companies else "Unknown Company",
        "date": str(closure_date),
        "owner_name": current_user.full_name,
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "balance": balance,
        "expense_details": expense_details
    }
    
    # Absolute path for signature for Weasyprint (needs file URI or http URL)
    abs_sig_path = os.path.abspath(sig_path)
    abs_sig_path_uri = f"file:///{abs_sig_path.replace(os.sep, '/')}"

    pdf_bytes = generate_clearance_act(closure_data, abs_sig_path_uri)
    
    pdf_filename = f"Acta_Cierre_{closure_date}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
        
    # Upload PDF
    pdf_storage_data = storage_service.upload_bytes(pdf_bytes, pdf_filename, "application/pdf", current_user.company_id)
    cloud_pdf_path = pdf_storage_data.get("storage_path", pdf_path)

    # Create DB Record
    new_closure = models.DailyClosure(
        company_id=current_user.company_id,
        date=closure_date,
        total_sales=total_sales, # Use the passed value
        total_expenses=total_expenses,
        cash_in_hand=balance,
        closed_by_email=current_user.email,
        # Save signature path if needed or just generate PDF
    )
    # Note: models.DailyClosure might need fields for signature/pdf url if not present.
    # Checking models.py... it has 'notes', but not explicit url fields.
    # I'll store the URLs in the notes for now or check models.py again.
    
    db.add(new_closure)
    db.commit()
    db.refresh(new_closure)
    return new_closure

@router.get("/", response_model=List[schemas.DailyClosure])
def list_closures(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    from typing import List # Ensure imported
    return db.query(models.DailyClosure).filter(
        models.DailyClosure.company_id == current_user.company_id
    ).order_by(models.DailyClosure.date.desc()).offset(skip).limit(limit).all()
