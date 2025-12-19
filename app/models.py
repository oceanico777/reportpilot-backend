from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Enum, Text, Date, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime
from .database import Base

class ReceiptStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class ReportStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DRAFT = "DRAFT"
    FAILED = "FAILED"

def generate_uuid():
    return str(uuid.uuid4())

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    GUIDE = "GUIDE"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Membership
    company_id = Column(String, ForeignKey("companies.id"), nullable=True) 
    role = Column(String, default=UserRole.ADMIN.value)
    is_active = Column(Boolean, default=True)

    companies = relationship("Company", back_populates="owner", foreign_keys="Company.user_id")
    company_membership = relationship("Company", foreign_keys=[company_id], back_populates="members")

class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id")) # Owner
    name = Column(String)
    settings = Column(Text) # JSON string
    invitation_code = Column(String, unique=True, nullable=True)
    
    owner = relationship("User", back_populates="companies", foreign_keys=[user_id])
    members = relationship("User", back_populates="company_membership", foreign_keys="User.company_id")
    
    receipts = relationship("Receipt", back_populates="company")
    reports = relationship("Report", back_populates="company")

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Storage fields
    storage_path = Column(String, nullable=True) # Path in Supabase bucket
    file_url = Column(String, nullable=True) # Kept for backward compat or public URLs
    filename = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    
    status = Column(String, default=ReceiptStatus.PENDING.value)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="receipts")
    parsed_data = relationship("ParsedData", back_populates="receipt", uselist=False)

    __table_args__ = (
        Index('idx_receipt_company_date', 'company_id', 'created_at'),
    )

class ParsedData(Base):
    __tablename__ = "parsed_data"

    id = Column(String, primary_key=True, default=generate_uuid)
    receipt_id = Column(String, ForeignKey("receipts.id"))
    vendor = Column(String)
    vendor_nit = Column(String, nullable=True) # Tax ID
    date = Column(Date)
    amount = Column(Float)
    currency = Column(String)
    category = Column(String)
    confidence_score = Column(Float)

    receipt = relationship("Receipt", back_populates="parsed_data")

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True) # Guide who created the report
    
    month = Column(Integer)
    year = Column(Integer)
    tour_id = Column(String)
    client_name = Column(String)
    
    # Generative AI Data (Flattened for easier reporting)
    vendor = Column(String, nullable=True)
    vendor_nit = Column(String, nullable=True) # Tax ID
    amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    category = Column(String, nullable=True)
    
    # Duplicate Detection
    is_duplicate = Column(Boolean, default=False)
    potential_duplicate_of = Column(String, nullable=True) # ID of the original report

    # Generative AI Summary
    summary_text = Column(Text)
    
    # File Storage
    storage_path = Column(String, nullable=True) # If generating PDF report
    file_url = Column(String, nullable=True)
    source_file_path = Column(String) # Points to receipt storage path if 1-to-1, or just metadata
    
    status = Column(String, default=ReportStatus.DRAFT.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="reports")
    
    __table_args__ = (
        Index('idx_report_company_date', 'company_id', 'created_at'),
    )

class TourBudget(Base):
    __tablename__ = "tour_budgets"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    tour_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    budget_amount = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")

    __table_args__ = (
        Index('idx_tour_budget_company_tour', 'company_id', 'tour_id'),
    )

class TourClosure(Base):
    __tablename__ = "tour_closures"

    tour_id = Column(String, primary_key=True) # Manually entered Tour ID
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    closed_at = Column(DateTime, default=datetime.utcnow)
    closed_by_email = Column(String) # Snapshot of who closed it
    
    signature_url = Column(String, nullable=True) # Path to signature image
    pdf_url = Column(String, nullable=True) # Path to generated Acta
    
    final_balance = Column(Float, default=0.0)
    
    company = relationship("Company")
