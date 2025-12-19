from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date
from enum import Enum

class ReceiptStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class ReportStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DRAFT = "DRAFT"
    FAILED = "FAILED"

# User Schemas
class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: str
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

# Report Schemas
class ReportBase(BaseModel):
    month: int
    year: int
    tour_id: Optional[str] = None
    client_name: Optional[str] = None

class ReportCreate(ReportBase):
    company_id: str
    source_file_path: Optional[str] = None
    extracted_data: Optional[dict] = None  # New field to pass OCR data
    category: Optional[str] = None # Manual category override

class Report(ReportBase):
    id: str
    company_id: str
    summary_text: Optional[str] = None
    vendor: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    source_file_path: Optional[str] = None
    file_url: Optional[str] = None
    status: str
    created_at: datetime
    is_duplicate: bool = False
    potential_duplicate_of: Optional[str] = None
    class Config:
        from_attributes = True

# Tour Budget Schemas
class TourBudgetBase(BaseModel):
    tour_id: str
    category: str
    budget_amount: float

class TourBudgetCreate(TourBudgetBase):
    pass

class TourBudget(TourBudgetBase):
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

