from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime, date
from enum import Enum

class ReceiptStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class PurchaseStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DRAFT = "DRAFT"
    FAILED = "FAILED"

# User Schemas
class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: Optional[str] = "STAFF"

class UserCreateAdmin(UserCreate):
    role: str # Explicitly required for admin creation

class User(UserBase):
    id: str
    created_at: datetime
    company_id: Optional[str] = None
    role: str

    class Config:
        from_attributes = True

# Provider Schemas
class ProviderBase(BaseModel):
    name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    category: Optional[str] = None
    frequency: Optional[str] = None

class ProviderCreate(ProviderBase):
    pass

class Provider(ProviderBase):
    id: str
    company_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# Receipt Schemas
class ParsedDataBase(BaseModel):
    vendor: Optional[str] = None
    date: Optional[Any] = None # Relaxed validation
    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    confidence_score: Optional[float] = None
    items: Optional[str] = None # JSON string

class ParsedDataCreate(ParsedDataBase):
    pass

class ParsedData(ParsedDataBase):
    id: str
    receipt_id: str

    class Config:
        from_attributes = True

class ReceiptBase(BaseModel):
    file_url: Optional[str] = None

class ReceiptCreate(ReceiptBase):
    company_id: str

class Receipt(ReceiptBase):
    id: str
    company_id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    # Storage fields
    storage_path: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    
    parsed_data: Optional[ParsedData] = None

    class Config:
        from_attributes = True

# Purchase (was Report) Schemas
class PurchaseBase(BaseModel):
    date: date
    provider_id: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "COP"
    notes: Optional[str] = None
    invoice_number: Optional[str] = None

class PurchaseCreate(PurchaseBase):
    company_id: str
    source_file_path: Optional[str] = None
    extracted_data: Optional[dict] = None  # New field to pass OCR data
    
class Purchase(PurchaseBase):
    id: str
    company_id: str
    user_id: Optional[str] = None
    
    vendor: Optional[str] = None # Flattened from extracted data if no provider_id
    
    storage_path: Optional[str] = None 
    file_url: Optional[str] = None
    status: str
    created_at: datetime
    
    is_duplicate: bool = False
    potential_duplicate_of: Optional[str] = None
    
    provider: Optional[Provider] = None

    class Config:
        from_attributes = True

# Category Budget Schemas
class CategoryBudgetBase(BaseModel):
    category: str
    budget_amount: float
    period: str = "MONTHLY"

class CategoryBudgetCreate(CategoryBudgetBase):
    pass

class CategoryBudget(CategoryBudgetBase):
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Daily Closure Schemas
class DailyClosureBase(BaseModel):
    date: date
    total_sales: float
    total_expenses: float
    cash_in_hand: float
    notes: Optional[str] = None

class DailyClosureCreate(DailyClosureBase):
    pass

class DailyClosure(DailyClosureBase):
    id: str
    company_id: str
    closed_at: datetime
    closed_by_email: Optional[str] = None

    class Config:
        from_attributes = True

class DailyClosureSummary(BaseModel):
    date: date
    total_sales: float
    total_expenses: float
    total_advances: float = 0.0
    total_collections: float = 0.0
    balance: float
    
    class Config:
        from_attributes = True


