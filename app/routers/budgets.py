from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from ..database import get_db
from .. import models, schemas
from ..auth import get_user_company

router = APIRouter()

@router.post("/", response_model=schemas.TourBudget)
def create_or_update_budget(
    budget_in: schemas.TourBudgetCreate,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    # Check if exists
    existing = db.query(models.TourBudget).filter(
        models.TourBudget.company_id == company_id,
        models.TourBudget.tour_id == budget_in.tour_id,
        models.TourBudget.category == budget_in.category
    ).first()

    if existing:
        existing.budget_amount = budget_in.budget_amount
        db.commit()
        db.refresh(existing)
        return existing
    
    new_budget = models.TourBudget(
        **budget_in.dict(),
        company_id=company_id
    )
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    return new_budget

@router.get("/", response_model=List[schemas.TourBudget])
def list_budgets(
    tour_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    query = db.query(models.TourBudget).filter(models.TourBudget.company_id == company_id)
    if tour_id:
        query = query.filter(models.TourBudget.tour_id == tour_id)
    return query.all()

@router.get("/consolidated")
def get_budget_comparison(
    tour_id: str = Query(...),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    """
    Compares Planned Budget vs Actual Spend for a specific tour.
    """
    # 1. Get Budgets
    budgets = db.query(models.TourBudget).filter(
        models.TourBudget.company_id == company_id,
        models.TourBudget.tour_id == tour_id
    ).all()
    
    # 2. Get Actual Spend per category
    actuals = db.query(
        models.Report.category,
        func.sum(models.Report.amount).label("total_spent")
    ).filter(
        models.Report.company_id == company_id,
        models.Report.tour_id == tour_id,
        models.Report.status == models.ReportStatus.APPROVED.value # Only count approved expenses
    ).group_by(models.Report.category).all()
    
    actual_map = {category: amount for category, amount in actuals}
    
    comparison = []
    for b in budgets:
        spent = actual_map.get(b.category, 0.0)
        comparison.append({
            "category": b.category,
            "budget": b.budget_amount,
            "actual": spent,
            "diff": b.budget_amount - spent,
            "percent": (spent / b.budget_amount * 100) if b.budget_amount > 0 else 0
        })
        
    return {
        "tour_id": tour_id,
        "comparison": comparison
    }
