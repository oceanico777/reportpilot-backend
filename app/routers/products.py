from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(
    prefix="/products",
    tags=["products"],
)

# Schema for Product (Insumo)
from pydantic import BaseModel
class ProductBase(BaseModel):
    name: str
    unit: str = "unit" # kg, lb, unit
    provider_id: str
    last_price: float = 0.0

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: str
    company_id: str
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[Product])
def get_products(
    provider_id: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    query = db.query(models.Product).filter(models.Product.company_id == current_user.company_id)
    if provider_id:
        query = query.filter(models.Product.provider_id == provider_id)
    return query.all()

@router.post("/", response_model=Product)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Verify provider exists
    if product.provider_id:
        provider = db.query(models.Provider).filter(models.Provider.id == product.provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

    new_product = models.Product(
        **product.dict(),
        company_id=current_user.company_id
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product
