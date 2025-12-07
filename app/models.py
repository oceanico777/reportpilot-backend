from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Enum, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime
from .database import Base

class ReceiptStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class ReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    companies = relationship("Company", back_populates="owner")

class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    name = Column(String)
    settings = Column(Text) # JSON string for simplicity in SQLite
    
    owner = relationship("User", back_populates="companies")
    receipts = relationship("Receipt", back_populates="company")
    reports = relationship("Report", back_populates="company")

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    file_url = Column(String)
    status = Column(String, default=ReceiptStatus.PENDING.value)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="receipts")
    parsed_data = relationship("ParsedData", back_populates="receipt", uselist=False)

class ParsedData(Base):
    __tablename__ = "parsed_data"

    id = Column(String, primary_key=True, default=generate_uuid)
    receipt_id = Column(String, ForeignKey("receipts.id"))
    vendor = Column(String)
    date = Column(Date)
    amount = Column(Float)
    currency = Column(String)
    category = Column(String)
    confidence_score = Column(Float)

    receipt = relationship("Receipt", back_populates="parsed_data")

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    month = Column(Integer)
    year = Column(Integer)
    summary_text = Column(Text)
    source_file_path = Column(String)
    file_url = Column(String)
    status = Column(String, default=ReportStatus.DRAFT.value)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="reports")
