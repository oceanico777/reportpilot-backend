from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from pathlib import Path
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, UploadFile, File
from ..database import get_db
from .. import models, schemas
from ..services import report_generator
from ..auth import get_current_user, get_user_company

router = APIRouter()

@router.on_event("startup")
def startup_event():
    pass

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return initial status
        return {
            "id": unique_filename, # Use filename as temporary ID
            "status": "PROCESSING",
            "file_path": str(file_path),
            "extracted_data": None # OCR will happen later
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

@router.post("/generate", response_model=schemas.Report)
def generate_report(
    report: schemas.ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user or not db_user.company_id:
        raise HTTPException(status_code=403, detail="User not linked to a company. Please join an organization.")
    
    company_id = db_user.company_id
    
    summary = "Reporte pendiente de procesamiento"
    vendor = None
    amount = None
    currency = None
    category = report.category # Default to manual selection if present
    existing_duplicate = None
    
    # [Start] Read-Only Check for Closed Tours
    if report.tour_id:
        closed_tour = db.query(models.TourClosure).filter(
            models.TourClosure.tour_id == report.tour_id,
            models.TourClosure.company_id == company_id
        ).first()
        if closed_tour:
            raise HTTPException(
                status_code=400, 
                detail=f"El Tour {report.tour_id} está CERRADO y no admite nuevos reportes."
            )
    # [End] Read-Only Check

    if report.extracted_data:
        data = report.extracted_data
        vendor = data.get('vendor')
        amount = data.get('amount')
        currency = data.get('currency')
        # If no manual category, use AI suggested one
        if not category:
            category = data.get('category')
            
        summary = (
            f"Factura de {vendor} del {data.get('date', 'N/A')}. "
            f"Total: {currency} {amount}. "
            f"Categoría: {category}"
        )
        
        # Check for duplicates
        existing_duplicate = db.query(models.Report).filter(
            models.Report.company_id == company_id,
            models.Report.vendor == vendor,
            models.Report.amount == amount
        ).first()

    db_report = models.Report(
        company_id=company_id,
        user_id=user_id,
        month=report.month,
        year=report.year,
        tour_id=report.tour_id,
        client_name=report.client_name,
        vendor=vendor,
        amount=amount,
        currency=currency,
        category=category,
        source_file_path=report.source_file_path,
        status=models.ReportStatus.PENDING_REVIEW.value,
        summary_text=summary,
        is_duplicate=True if existing_duplicate else False,
        potential_duplicate_of=existing_duplicate.id if existing_duplicate else None
    )

    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # Always trigger report generation background task
    background_tasks.add_task(report_generator.create_report, db_report.id, db)
    
    return db_report

@router.get("/", response_model=List[schemas.Report])
def list_reports(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    tour_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    query = db.query(models.Report).filter(models.Report.company_id == company_id)
    if month: query = query.filter(models.Report.month == month)
    if year: query = query.filter(models.Report.year == year)
    if tour_id: query = query.filter(models.Report.tour_id == tour_id)
    return query.order_by(models.Report.created_at.desc()).all()

@router.patch("/{report_id}/approve", response_model=schemas.Report)
def approve_report(
    report_id: str,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    report = db.query(models.Report).filter(models.Report.id == report_id, models.Report.company_id == company_id).first()
    if not report: raise HTTPException(status_code=404, detail="Report not found")
    report.status = models.ReportStatus.APPROVED.value
    db.commit()
    db.refresh(report)
    return report

@router.patch("/{report_id}/reject", response_model=schemas.Report)
def reject_report(
    report_id: str,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    report = db.query(models.Report).filter(models.Report.id == report_id, models.Report.company_id == company_id).first()
    if not report: raise HTTPException(status_code=404, detail="Report not found")
    report.status = models.ReportStatus.REJECTED.value
    db.commit()
    db.refresh(report)
    return report

@router.get("/budget", response_model=dict)
def get_budget(
    tour_id: str = Query(...),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    budget = db.query(models.TourBudget).filter(
        models.TourBudget.tour_id == tour_id,
        models.TourBudget.company_id == company_id,
        models.TourBudget.category == "TOTAL"
    ).first()
    
    return {"amount": budget.budget_amount if budget else 0}

@router.post("/budget", response_model=dict)
def set_budget(
    budget_data: schemas.TourBudgetCreate,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    # Ensure category is TOTAL for this specific feature
    category = "TOTAL"
    
    existing = db.query(models.TourBudget).filter(
        models.TourBudget.tour_id == budget_data.tour_id,
        models.TourBudget.company_id == company_id,
        models.TourBudget.category == category
    ).first()
    
    if existing:
        existing.budget_amount = budget_data.budget_amount
        existing.updated_at = datetime.utcnow()
    else:
        new_budget = models.TourBudget(
            tour_id=budget_data.tour_id,
            company_id=company_id,
            category=category,
            budget_amount=budget_data.budget_amount
        )
        db.add(new_budget)
    
    db.commit()
    return {"status": "success", "tour_id": budget_data.tour_id, "amount": budget_data.budget_amount}

@router.get("/summary", response_model=dict)
def get_tour_summary(
    tour_id: str = Query(...),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    """
    Calculates the balance for a specific tour.
    Balance = (Budget + Total Collections) - Total Expenses
    """
    # 1. Get Budget
    budget_rec = db.query(models.TourBudget).filter(
        models.TourBudget.tour_id == tour_id,
        models.TourBudget.company_id == company_id,
        models.TourBudget.category == "TOTAL"
    ).first()
    budget = budget_rec.budget_amount if budget_rec else 0

    # 2. Get Reports
    reports = db.query(models.Report).filter(
        models.Report.company_id == company_id,
        models.Report.tour_id == tour_id
    ).all()

    total_advances = 0 # Legacy, kept for compatibility if needed elsewhere
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

    # Balance = (Budget + Collections) - Expenses
    # The user wants "Monto Asignado" to be the base responsibility.
    balance = (budget + total_collections) - total_expenses

    return {
        "tour_id": tour_id,
        "budget": int(budget),
        "total_advances": int(total_advances), # Shows extra manual advances if any
        "total_collections": int(total_collections),
        "total_expenses": int(total_expenses),
        "balance": int(balance),
        "currency": "COP"
    }

@router.get("/admin/summary")
def get_admin_summary(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    """
    Returns a list of all tours with their financial status for the accountant.
    """
    # 1. Get all unique tours for this company
    query = db.query(models.Report.tour_id).filter(models.Report.company_id == company_id)
    if month: query = query.filter(models.Report.month == month)
    if year: query = query.filter(models.Report.year == year)
    
    tours = [r[0] for r in query.distinct().all() if r[0]]
    
    summary_list = []
    
    for t_id in tours:
        # Get Budget (cat TOTAL)
        budget_rec = db.query(models.TourBudget).filter(
            models.TourBudget.tour_id == t_id,
            models.TourBudget.company_id == company_id,
            models.TourBudget.category == "TOTAL"
        ).first()
        budget = budget_rec.budget_amount if budget_rec else 0

        # Get stats
        reports = db.query(models.Report).filter(
            models.Report.tour_id == t_id,
            models.Report.company_id == company_id
        ).all()
        
        advances = 0
        collections = 0
        expenses = 0
        categories = {}
        client_name = "N/A"
        
        for r in reports:
            if r.client_name: client_name = r.client_name
            amount = r.amount or 0
            if r.category == "ANTICIPO_RECIBIDO":
                advances += amount
            elif r.category == "RECAUDO_CLIENTE":
                collections += amount
            else:
                expenses += amount
                cat = r.category or "📦 Otros"
                categories[cat] = categories.get(cat, 0) + amount
        
        summary_list.append({
            "tour_id": t_id,
            "client_name": client_name,
            "total_advances": int(budget), # We use budget as the main "advance/fund"
            "total_collections": int(collections),
            "total_expenses": int(expenses),
            "balance": int((budget + collections) - expenses),
            "categories": categories
        })
        
    return summary_list


@router.get("/dashboard-stats", response_model=dict)
def get_dashboard_stats(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    # Base query
    query = db.query(models.Report).filter(models.Report.company_id == company_id)
    
    if start_date:
        query = query.filter(models.Report.created_at >= start_date)
    if end_date:
        query = query.filter(models.Report.created_at <= datetime.combine(end_date, datetime.max.time()))
        
    reports = query.all()
    
    total_spent = 0
    total_advances = 0
    total_collections = 0
    total_reports = len(reports)
    
    monthly_data = {}
    category_data = {}
    client_data = {}
    
    for r in reports:
        amount = r.amount or 0
        
        # Handle Advances vs Recaudos vs Expenses
        if r.category == "ANTICIPO_RECIBIDO":
            total_advances += amount
            continue # Don't count as spent
        
        if r.category == "RECAUDO_CLIENTE":
            total_collections += amount
            continue # Don't count as spent
            
        total_spent += amount
        
        # Monthly Stats
        month_key = r.created_at.strftime("%b") # Jan, Feb
        monthly_data[month_key] = monthly_data.get(month_key, 0) + amount
        
        # Category Stats
        cat = r.category or "Uncategorized"
        category_data[cat] = category_data.get(cat, 0) + amount
        
        # Client Stats (Top Clients by Spend)
        client = r.client_name or "Unknown"
        client_data[client] = client_data.get(client, 0) + amount

    # Format for Charts
    monthly_stats = [{"month": k, "total": int(v)} for k, v in monthly_data.items()]
    category_stats = [{"name": k, "value": int(v)} for k, v in category_data.items()]
    client_stats = [{"name": k, "value": int(v)} for k, v in client_data.items()]
    
    # Sort
    client_stats.sort(key=lambda x: x['value'], reverse=True)
    client_stats = client_stats[:5] # Top 5
    
    recent_activity = []
    for r in reports[:5]: # Just take first 5 from query result (ideally sort by date desc first)
         recent_activity.append({
             "id": r.id,
             "tour_id": r.tour_id,
             "created_at": r.created_at.isoformat(),
             "amount": int(r.amount) if r.amount else 0,
             "category": r.category
         })

    return {
        "total_reports": total_reports,
        "total_spent": int(total_spent),
        "total_advances": int(total_advances),
        "total_collections": int(total_collections),
        "monthly_stats": monthly_stats,
        "client_stats": client_stats,
        "recent_activity": recent_activity,
        "category_stats": category_stats
    }
