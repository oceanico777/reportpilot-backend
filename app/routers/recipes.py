from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from .. import models, schemas, auth
import uuid  # Add this import

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)

# Pydantic Schemas
from pydantic import BaseModel

class RecipeItemCreate(BaseModel):
    product_id: str
    quantity: float

class RecipeCreate(BaseModel):
    name: str
    sale_price: float = 0.0

class RecipeItemOut(BaseModel):
    id: str
    product_name: str
    quantity: float
    unit: str
    unit_price: float
    total_cost: float

class RecipeOut(BaseModel):
    id: str
    name: str
    sale_price: float
    total_cost: float
    margin: float
    items: List[RecipeItemOut] = []

@router.get("/", response_model=List[RecipeOut])
def get_recipes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    recipes = db.query(models.Recipe).filter(models.Recipe.company_id == current_user.company_id).all()
    
    results = []
    for r in recipes:
        # Calculate cost dynamically based on current inventory price
        total_cost = 0
        items_out = []
        for item in r.items:
            # item.product.last_price is the cost per unit
            cost = item.quantity * (item.product.last_price if item.product else 0)
            total_cost += cost
            
            items_out.append({
                "id": item.id,
                "product_name": item.product.name if item.product else "Unknown",
                "quantity": item.quantity,
                "unit": item.product.unit if item.product else "-",
                "unit_price": item.product.last_price if item.product else 0,
                "total_cost": cost
            })
            
        margin = 0
        if r.sale_price > 0:
            margin = ((r.sale_price - total_cost) / r.sale_price) * 100
            
        results.append({
            "id": r.id,
            "name": r.name,
            "sale_price": r.sale_price,
            "total_cost": total_cost,
            "margin": margin,
            "items": items_out
        })
        
    return results

@router.post("/", response_model=dict)
def create_recipe(
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    new_recipe = models.Recipe(
        company_id=current_user.company_id,
        name=recipe.name,
        sale_price=recipe.sale_price
    )
    db.add(new_recipe)
    db.commit()
    return {"id": new_recipe.id, "name": new_recipe.name}

@router.post("/{recipe_id}/items", response_model=dict)
def add_recipe_item(
    recipe_id: str,
    item: RecipeItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Verify ownership
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id, models.Recipe.company_id == current_user.company_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    # Check if product exists
    product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_item = models.RecipeItem(
        recipe_id=recipe_id,
        product_id=item.product_id,
        quantity=item.quantity
    )
    db.add(new_item)
    db.commit()
    return {"status": "added"}

@router.delete("/{recipe_id}/items/{item_id}")
def delete_recipe_item(
    recipe_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Verify ownership
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id, models.Recipe.company_id == current_user.company_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    item = db.query(models.RecipeItem).filter(models.RecipeItem.id == item_id, models.RecipeItem.recipe_id == recipe_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    db.delete(item)
    db.commit()
    return {"status": "deleted"}
