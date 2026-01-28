from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from ..database import get_db
from .. import models, schemas
from ..auth import get_user_company

router = APIRouter(
    prefix="/budgets",
    tags=["budgets"],
)

@router.post("/", response_model=schemas.CategoryBudget)
def create_or_update_budget(
    budget_in: schemas.CategoryBudgetCreate,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    # Check if exists (Category + Period)
    existing = db.query(models.CategoryBudget).filter(
        models.CategoryBudget.company_id == company_id,
        models.CategoryBudget.category == budget_in.category,
        models.CategoryBudget.period == budget_in.period
    ).first()

    if existing:
        existing.budget_amount = budget_in.budget_amount
        db.commit()
        db.refresh(existing)
        return existing
    
    new_budget = models.CategoryBudget(
        **budget_in.dict(),
        company_id=company_id
    )
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    return new_budget

@router.get("/", response_model=List[schemas.CategoryBudget])
def list_budgets(
    period: str = "MONTHLY",
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    query = db.query(models.CategoryBudget).filter(
        models.CategoryBudget.company_id == company_id,
        models.CategoryBudget.period == period
    )
    return query.all()

@router.get("/status")
def get_budget_status(
    period: str = "MONTHLY",
    month: int = Query(default=None), 
    year: int = Query(default=None),
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    """
    Compares Budget vs Actual Spend for the current period.
    """
    if not month:
        from datetime import datetime
        month = datetime.now().month
    if not year:
        from datetime import datetime
        year = datetime.now().year

    # 1. Get Budgets for the period type
    budgets = db.query(models.CategoryBudget).filter(
        models.CategoryBudget.company_id == company_id,
        models.CategoryBudget.period == period
    ).all()
    
    # 2. Get Actual Spend per category for the specific time range
    # Assuming period="MONTHLY" implies getting spend for the specific month/year logic
    # We need to filter Purchases by date range.
    
    # Calculate start/end date for month
    from calendar import monthrange
    from datetime import date
    try:
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
    except Exception:
        return {"error": "Invalid date"}

    actuals = db.query(
        models.Purchase.category,
        func.sum(models.Purchase.amount).label("total_spent")
    ).filter(
        models.Purchase.company_id == company_id,
        models.Purchase.date >= start_date,
        models.Purchase.date <= end_date,
        models.Purchase.status != models.PurchaseStatus.REJECTED.value 
    ).group_by(models.Purchase.category).all()
    
    actual_map = {category: amount for category, amount in actuals}
    
    comparison = []
    # Include all budgeted categories
    for b in budgets:
        spent = actual_map.get(b.category, 0.0)
        comparison.append({
            "category": b.category,
            "budget": b.budget_amount,
            "actual": spent,
            "remaining": b.budget_amount - spent,
            "percent": (spent / b.budget_amount * 100) if b.budget_amount > 0 else 0
        })
        
    # Include unbudgeted spend
    budgeted_cats = [b.category for b in budgets]
    for cat, amount in actual_map.items():
        if cat not in budgeted_cats:
            comparison.append({
                "category": cat,
                "budget": 0,
                "actual": amount,
                "remaining": -amount,
                "percent": 100
            })
        
    return {
        "period": period,
        "month": month,
        "year": year,
        "comparison": comparison
    }
