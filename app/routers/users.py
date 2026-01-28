from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user, get_user_company

router = APIRouter()

@router.post("/auth/join")
def join_organization(
    invite_code: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Join an organization using an Invite Code.
    """
    code = invite_code.strip()
    company = db.query(models.Company).filter(models.Company.invitation_code == code).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Invalid Invitation Code")
        
    user_id = current_user["id"]
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    # If user doesn't exist yet (first login via join?), create them
    if not db_user:
        db_user = models.User(
            id=user_id,
            email=current_user["email"],
            role=models.UserRole.STAFF.value # Joining users are Staff by default
        )
        db.add(db_user)
        
    # Update Membership
    db_user.company_id = company.id
    db_user.role = models.UserRole.STAFF.value # Ensure they become Staff
    
    db.commit()
    return {"status": "success", "company_name": company.name}

@router.get("/admin/team")
def get_team_members(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_user_company)
):
    """
    List all members of the organization. Admin only.
    """
    # Verify Admin Role
    db_user = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if not db_user or db_user.role != models.UserRole.ADMIN.value:
         raise HTTPException(status_code=403, detail="Admin access required")
         
    members = db.query(models.User).filter(models.User.company_id == company_id).all()
    
    # Get Company Info for Invite Code
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    
    result = []
    for m in members:
        # Calculate Total Spent (Simple logic for now)
        total_spent = 0
        try:
             # This might be slow if many users/reports, ideally aggregation query.
             # But for < 50 users it's instant.
             total_spent = db.query(models.Report).filter(
                 models.Report.user_id == m.id, 
                 models.Report.company_id == company_id
             ).with_entities(models.Report.amount).all()
             total_spent = sum([x[0] or 0 for x in total_spent])
        except:
            pass
            
        result.append({
            "id": m.id,
            "email": m.email,
            "full_name": m.full_name,
            "role": m.role,
            "status": "Active" if m.is_active else "Inactive",
            "total_spent": total_spent
        })
        
    return {
        "company_name": company.name,
        "invitation_code": company.invitation_code,
        "members": result
    }

@router.patch("/admin/deactivate/{user_id}")
def deactivate_member(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_user_company)
):
    # Verify Admin
    admin_user = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if admin_user.role != models.UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin only")
        
    target_user = db.query(models.User).filter(
        models.User.id == user_id, 
        models.User.company_id == company_id
    ).first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found in your company")
        
    target_user.is_active = False 
    # Also maybe clear company_id? Or just keep them inactive so they can't login/upload.
    # For now toggle active.
    
    db.commit()
    return {"status": "success"}

@router.post("/admin/users")
def create_user_manual(
    user_data: schemas.UserCreateAdmin,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_user_company)
):
    """
    Manually provision a user. 
    Useful if invite codes are not desired.
    User will claim this account upon first login/signup with matching email.
    """
    # 1. Verify Admin
    admin_user = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if not admin_user or admin_user.role != models.UserRole.ADMIN.value:
         raise HTTPException(status_code=403, detail="Admin access required")
         
    # 2. Check if user exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        if existing_user.company_id == company_id:
            raise HTTPException(status_code=400, detail="El usuario ya pertenece a esta empresa")
        elif existing_user.company_id:
             raise HTTPException(status_code=400, detail="El usuario ya pertenece a otra empresa")
        else:
            # Add to company
            existing_user.company_id = company_id
            existing_user.role = user_data.role
            db.commit()
            return {"status": "success", "message": "Usuario existente añadido a la empresa"}
            
    # 3. Create pre-provisioned user
    new_user = models.User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        company_id=company_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"status": "success", "user": new_user}
