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
    # Print received data for debugging
    print(f"Generate Report Request: {report_request}")
    try:
        # HANDLING DEMO COMPANY ID
        cid = report_request.company_id
        if cid == 'demo-company-123':
            # Try to find any company
            existing_company = db.query(models.Company).first()
            if existing_company:
                cid = existing_company.id
            else:
                # Create a demo company
                demo_user = db.query(models.User).filter(models.User.email == "guide@reportpilot.com").first()
                if not demo_user:
                    demo_user = models.User(id=str(uuid.uuid4()), email="guide@reportpilot.com", full_name="Report Pilot Guide")
                    db.add(demo_user)
                    db.commit()
                
                new_company = models.Company(id=cid, user_id=demo_user.id, name="Demo Company")
                # cid is 'demo-company-123' here unless we want a uuid. 
                # If we use the string 'demo-company-123' as ID, it works if UUID validation isn't strict.
                # But models.py uses String for ID. So we can insert it.
                db.add(new_company)
                db.commit()
        
        # Prepare summary from extracted data if available
        # Prepare summary from extracted data if available
        summary = None
        vendor = None
        amount = None
        currency = None
        category = None

        if report_request.extracted_data:
            data = report_request.extracted_data
            summary = (
                f"Receipt from {data.get('vendor')} on {data.get('date')}. "
                f"Total: {data.get('currency', '$')} {data.get('amount')}. "
                f"Category: {data.get('category')}"
            )
            vendor = data.get('vendor')
            amount = data.get('amount')
            currency = data.get('currency')
            category = data.get('category')

        # Check if report already exists? For now, just create new one
        db_report = models.Report(
            company_id=cid,
            month=report_request.month,
            year=report_request.year,
            tour_id=report_request.tour_id,
            client_name=report_request.client_name,
            vendor=vendor,
            amount=amount,
            currency=currency,
            category=category,
            source_file_path=report_request.source_file_path,
            status=models.ReportStatus.SENT.value if summary else models.ReportStatus.DRAFT.value,
            summary_text=summary
        )
        db.add(db_report)
        db.commit()
    except Exception as e:
        print(f"Error creating report in DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    db.refresh(db_report)
    
    # Trigger generation in background
    background_tasks.add_task(report_generator.create_report, db_report.id, db)
    
    return db_report

from fastapi import UploadFile, File
import shutil
import os
import uuid
from ..services.ocr import process_receipt_with_gemini
import logging

logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload receipt file (JPG/PNG/PDF) and extract data using Gemini OCR
    """
    # Validate file type
    if not file.filename.lower().endswith(('.csv', '.pdf', '.jpg', '.jpeg', '.png')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV, PDF, JPG, and PNG are allowed.")
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("uploads", file_name)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process image files with Gemini OCR
    extracted_data = None
    if file_extension.lower() in ['.jpg', '.jpeg', '.png']:
        try:
            logger.info(f"Processing image {file_name} with Gemini OCR")
            extracted_data = process_receipt_with_gemini(file_path)
            logger.info(f"Successfully extracted data: {extracted_data}")
        except Exception as e:
            logger.error(f"Failed to process image with Gemini: {e}")
            # Don't fail the upload, just return without extracted data
            extracted_data = {"error": str(e)}
    
    response = {
        "file_path": file_path,
        "filename": file.filename
    }
    
    # Include extracted data if available
    if extracted_data:
        response["extracted_data"] = extracted_data
        
    return response

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

@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a report by ID
    """
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Optional: Check ownership
    # if report.company_id != current_user_company_id: ...

    db.delete(report)
    db.commit()
    return None

@router.get("/prediction")
def get_prediction_data(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get predictive data based on historical tours.
    Groups expenses by tour_id to calculate averages.
    """
    reports = db.query(models.Report).filter(models.Report.tour_id.isnot(None)).all()
    
    if not reports:
        return {
            "average_total": 0,
            "sample_size": 0,
            "by_category": {}
        }

    # Group by Tour ID
    tour_costs = {}
    for r in reports:
        tid = r.tour_id
        if tid not in tour_costs:
            tour_costs[tid] = {"total": 0, "categories": {}}
        
        # Add to total
        amount = r.amount or 0
        tour_costs[tid]["total"] += amount

        # Add to category
        cat = r.category or "Uncategorized"
        tour_costs[tid]["categories"][cat] = tour_costs[tid]["categories"].get(cat, 0) + amount

    # Calculate Global Averages
    total_cost_sum = 0
    category_sums = {}
    sample_size = len(tour_costs)

    if sample_size == 0:
        return {
            "average_total": 0,
            "sample_size": 0,
            "by_category": {}
        }

    for tid, data in tour_costs.items():
        total_cost_sum += data["total"]
        for cat, amount in data["categories"].items():
            category_sums[cat] = category_sums.get(cat, 0) + amount

    avg_total = total_cost_sum / sample_size
    
    avg_by_category = {}
    for cat, total_amount in category_sums.items():
        avg_by_category[cat] = total_amount / sample_size

    return {
        "average_total": round(avg_total, 2),
        "sample_size": sample_size,
        "by_category": {k: round(v, 2) for k, v in avg_by_category.items()}
    }

@router.get("/dashboard-stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get aggregated statistics for the dashboard.
    - Monthly activity (last 6 months)
    - Total reports count
    - Recent activity (latest 5 reports)
    """
    # 1. Total Count
    total_count = db.query(models.Report).count()

    # 2. Recent Reports
    recent_reports = db.query(models.Report).order_by(models.Report.created_at.desc()).limit(5).all()

    # 3. Monthly Activity (Last 6 months)
    # Group by year-month. 
    # Since we are using SQLite/standard SQL, we might do this in python for simplicity if data is small, 
    # or simple SQL group by. given the seed is ~200 rows, python aggregation is fine and safer for cross-db compatibility in MVP.
    
    # Get all dates (lightweight)
    all_dates = db.query(models.Report.created_at).all()
    
    from collections import defaultdict
    stats_map = defaultdict(int)
    
    for (d,) in all_dates:
        if d:
            key = d.strftime("%Y-%m") # 2023-10
            stats_map[key] += 1
            
    # Format for graph (sort by date)
    sorted_keys = sorted(stats_map.keys())[-6:] # Last 6 months
    monthly_stats = []
    for k in sorted_keys:
        # k is YYYY-MM
        # Convert to readable "Oct" or "Nov"
        dt = datetime.strptime(k, "%Y-%m")
        month_name = dt.strftime("%b")
        monthly_stats.append({"month": month_name, "total": stats_map[k]})
        
    # 4. Distribution by Category (All time)
    category_totals = {}
    reports = db.query(models.Report).all()
    for r in reports:
        cat = r.category or "Sin Categoría"
        category_totals[cat] = category_totals.get(cat, 0) + (r.amount or 0)
    
    category_stats = [{"name": k, "value": v} for k, v in category_totals.items()]

    return {
        "total_reports": total_count,
        "recent_activity": recent_reports,
        "monthly_stats": monthly_stats,
        "category_stats": category_stats
    }
