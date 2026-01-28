@router.get("/admin/transactions", response_model=List[schemas.Report])
def list_admin_transactions(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_user_company)
):
    """
    Returns a flat list of ALL transactions for the company, filtered by period.
    Designed for the 'Sábana de Datos' view in Accountant Dashboard.
    """
    query = db.query(models.Report).filter(models.Report.company_id == company_id)
    
    if month:
        query = query.filter(models.Report.month == month)
    if year:
        query = query.filter(models.Report.year == year)
        
    return query.order_by(models.Report.created_at.desc()).offset(skip).limit(limit).all()
