from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas

router = APIRouter()

@router.post("/login")
def login(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Mock login: just return a dummy token and create user if not exists
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user:
        user = models.User(email=user_data.email, full_name=user_data.full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create a default company for the user
        company = models.Company(user_id=user.id, name=f"{user.full_name or 'User'}'s Company")
        db.add(company)
        db.commit()
    
    return {"access_token": "mock_token", "token_type": "bearer", "user_id": user.id}
