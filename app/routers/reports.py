from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from .. import models, schemas
from ..services import report_generator
from ..auth import get_current_user

router = APIRouter()

@router.post("/generate", response_model=schemas.Report)
def generate_report(
    report_request: schemas.ReportCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Check if report already exists? For now, just create new one
    db_report = models.Report(
        company_id=report_request.company_id,
        month=report_request.month,
        year=report_request.year,
        source_file_path=report_request.source_file_path,
        status=models.ReportStatus.DRAFT.value
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # Trigger generation in background
    background_tasks.add_task(report_generator.create_report, db_report.id, db)
    
    return db_report

from fastapi import UploadFile, File
import shutil
import os
import uuid

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.pdf', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV, PDF, and JPG are allowed.")
    
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("uploads", file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"file_path": file_path, "filename": file.filename}

@router.get("/", response_model=List[schemas.Report])
def read_reports(
    client: Optional[str] = Query(None, description="Filter by company/client ID"),
    from_date: Optional[str] = Query(None, alias="from", description="Filter reports from this date (ISO format or YYYY-MM)"),
    to_date: Optional[str] = Query(None, alias="to", description="Filter reports to this date (ISO format or YYYY-MM)"),
    search: Optional[str] = Query(None, description="Search in report summary text"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve reports with optional filtering:
    - client: Filter by company_id
    - from: Start date for filtering (YYYY-MM-DD or YYYY-MM)
    - to: End date for filtering (YYYY-MM-DD or YYYY-MM)
    - search: Search term to filter by summary text
    """
    # Start with base query
    query = db.query(models.Report)
    
    # Filter by client/company_id
    if client:
        query = query.filter(models.Report.company_id == client)
    
    # Filter by date range
    if from_date:
        try:
            # Parse date - support both YYYY-MM-DD and YYYY-MM formats
            if len(from_date) == 7:  # YYYY-MM format
                year, month = map(int, from_date.split('-'))
                query = query.filter(
                    models.Report.year >= year,
                    models.Report.month >= month if models.Report.year == year else True
                )
            else:  # Full date format
                from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
                query = query.filter(models.Report.created_at >= from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'from' date format. Use YYYY-MM-DD or YYYY-MM")
    
    if to_date:
        try:
            # Parse date - support both YYYY-MM-DD and YYYY-MM formats
            if len(to_date) == 7:  # YYYY-MM format
                year, month = map(int, to_date.split('-'))
                query = query.filter(
                    models.Report.year <= year,
                    models.Report.month <= month if models.Report.year == year else True
                )
            else:  # Full date format
                to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
                query = query.filter(models.Report.created_at <= to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'to' date format. Use YYYY-MM-DD or YYYY-MM")
    
    # Filter by search term in summary text
    if search:
        query = query.filter(models.Report.summary_text.ilike(f"%{search}%"))
    
    # Order by most recent first
    query = query.order_by(models.Report.created_at.desc())
    
    # Apply pagination
    reports = query.offset(skip).limit(limit).all()
    
    return reports
