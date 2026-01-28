from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/providers",
    tags=["providers"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[schemas.Provider])
def read_providers(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    providers = db.query(models.Provider).filter(models.Provider.company_id == current_user.company_id).offset(skip).limit(limit).all()
    return providers

@router.post("/", response_model=schemas.Provider)
def create_provider(
    provider: schemas.ProviderCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_provider = models.Provider(**provider.dict(), company_id=current_user.company_id)
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider

@router.put("/{provider_id}", response_model=schemas.Provider)
def update_provider(
    provider_id: str,
    provider_update: schemas.ProviderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_provider = db.query(models.Provider).filter(
        models.Provider.id == provider_id,
        models.Provider.company_id == current_user.company_id
    ).first()
    
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    for key, value in provider_update.dict(exclude_unset=True).items():
        setattr(db_provider, key, value)
    
    db.commit()
    db.refresh(db_provider)
    return db_provider

@router.delete("/{provider_id}")
def delete_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_provider = db.query(models.Provider).filter(
        models.Provider.id == provider_id,
        models.Provider.company_id == current_user.company_id
    ).first()
    
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    db.delete(db_provider)
    db.commit()
    return {"ok": True}
