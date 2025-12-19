from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..services.report_generator import generate_clearance_act
# from ..services.gcs import upload_file_to_storage # REMOVED
# Assuming storage service exists or using local storage for now if GCS not set up.
# Let's check imports in reports.py. It seems they use supabase directly or some service.
# I'll implement a simple storage helper here for now or look for existing one.
import shutil
import base64
import os
import uuid
from datetime import datetime
# from ..routers.reports import get_tour_summary_data # REMOVED

router = APIRouter(
    prefix="/tours",
    tags=["tours"],
    responses={404: {"description": "Not found"}},
)

UPLOAD_DIR = "uploads/signatures"
os.makedirs(UPLOAD_DIR, exist_ok=True)
PDF_DIR = "uploads/actas"
os.makedirs(PDF_DIR, exist_ok=True)

@router.post("/{tour_id}/close")
async def close_tour(
    tour_id: str,
    signature: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Check if already closed
    existing = db.query(models.TourClosure).filter(models.TourClosure.tour_id == tour_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tour already closed")

    # 2. Get Tour Financial Data & Company Info
    reports = db.query(models.Report).filter(models.Report.tour_id == tour_id).all()
    if not reports:
        raise HTTPException(status_code=404, detail="No reports found for this tour. Cannot close empty tour.")
    
    company_id = reports[0].company_id
    guide_name = reports[0].client_name or "Guía"

    # 3. Setup Signature
    from ..services.storage import storage_service
    sig_filename = f"{tour_id}_sig_{uuid.uuid4()}.png"
    sig_path = os.path.join(UPLOAD_DIR, sig_filename)
    
    content = await signature.read()
    with open(sig_path, "wb") as buffer:
        buffer.write(content)
    
    # Upload Signature to Supabase
    sig_storage_data = storage_service.upload_bytes(content, sig_filename, "image/png", company_id)
    cloud_sig_path = sig_storage_data.get("storage_path", sig_path)
    
    # Absolute path for WeasyPrint template
    abs_sig_path = os.path.abspath(sig_path)
    abs_sig_path_uri = f"file:///{abs_sig_path.replace(os.sep, '/')}"

    # 4. Calculate Financials
    total_advances = 0
    total_collections = 0
    total_expenses = 0
    
    for r in reports:
        amount = r.amount or 0
        if r.category == "ANTICIPO_RECIBIDO":
            total_advances += amount
        elif r.category == "RECAUDO_CLIENTE":
            total_collections += amount
        else:
            total_expenses += amount
            
    final_balance = (total_advances + total_collections) - total_expenses
    
    # Get Company Name
    company_name = "Empresa de Turismo"
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if company: company_name = company.name

    tour_data = {
        "company_name": company_name,
        "tour_id": tour_id,
        "guide_name": guide_name,
        "total_advances": total_advances,
        "total_collections": total_collections,
        "total_expenses": total_expenses,
        "closed_at": datetime.now()
    }

    # 5. Generate PDF
    pdf_bytes = generate_clearance_act(tour_data, abs_sig_path_uri)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="Failed to generate PDF")
        
    pdf_filename = f"Acta_{tour_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
            
    # Upload PDF to Supabase
    pdf_storage_data = storage_service.upload_bytes(pdf_bytes, pdf_filename, "application/pdf", company_id)
    cloud_pdf_path = pdf_storage_data.get("storage_path", pdf_path)

    # 6. Create Closure Record
    closure = models.TourClosure(
        tour_id=tour_id,
        company_id=company_id,
        closed_by_email="guide@reportpilot.com", # Mock for now
        signature_url=cloud_sig_path,
        pdf_url=cloud_pdf_path,
        final_balance=final_balance
    )
    
    db.add(closure)
    db.commit()

    return {"status": "success", "message": "Tour closed successfully", "pdf_url": pdf_path}
