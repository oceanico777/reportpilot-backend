from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

security = HTTPBearer()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate Supabase JWT token and extract user information
    """
    token = credentials.credentials
    
    # Development Bypass
    if token == "fake-jwt-token-for-auth":
        return {
            "id": "e9821814-c159-42b7-8742-167812035978", # Mock user ID
            "email": "guide@reportpilot.com",
            "role": "user"
        }
    
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role", "user")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        
        return {
            "id": user_id,
            "email": email,
            "role": role
        }
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )

async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """
    Verify that the current user has admin role
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
    return current_user

from .database import get_db
from sqlalchemy.orm import Session
from . import models
import uuid

async def get_user_company(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> str:
    """
    Get the company_id for the current user.
    For MVP/Demo, if no company exists for the user, create one.
    """
    user_id = current_user["id"]
    
    # Check if user exists in DB (sync with Supabase Auth)
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    # Auto-create user if missing (First Login)
    if not db_user:
        db_user = models.User(
            id=user_id, 
            email=current_user["email"],
            full_name=current_user.get("user_metadata", {}).get("full_name"),
            role=models.UserRole.ADMIN.value # Default to Admin for first user
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    # 1. If user is already a member of a company, return that ID
    if db_user.company_id:
        return db_user.company_id

    # 2. If not a member, check if they OWN a company (Legacy 1-1 check)
    company = db.query(models.Company).filter(models.Company.user_id == user_id).first()
    
    if company:
        # Link them properly if not linked
        if not db_user.company_id:
            db_user.company_id = company.id
            db.add(db_user)
            db.commit()
        return company.id
        
    # 3. If no company and user is ADMIN (Default), Create New Company
    if db_user.role == models.UserRole.ADMIN.value:
        import random, string
        invite_code = "REPPILOT-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        company = models.Company(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=f"{current_user.get('email', 'User')}'s Organization",
            invitation_code=invite_code
        )
        db.add(company)
        db.flush() # Get ID
        
        # Link owner to company
        db_user.company_id = company.id
        db.add(db_user)
        
        db.commit()
        return company.id
    else:
        # User is a GUIDE but has no company? They need to join one.
        # Could return None or raise 403.
        # For now, let's allow them to exist without company but they can't do much.
        # Or simplistic fallback: Create a personal sandbox company? 
        # Let's enforce: Must join via Invite Code.
        raise HTTPException(
            status_code=403, 
            detail="You are not part of any organization. Please provide an Invitation Code."
        )
