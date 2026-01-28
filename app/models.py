from sqlalchemy import Column, String, Integer, Float, ForeignKey, Boolean, DateTime, Date, Text, Index
from sqlalchemy.orm import relationship
from .database import Base
import uuid
import enum  # Added missing import
from datetime import datetime
from .database import Base

class ReceiptStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class PurchaseStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

def generate_uuid():
    return str(uuid.uuid4())

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN" # Owner/Manager
    STAFF = "STAFF" # Waiter/Chef

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
    purchases = relationship("Purchase", back_populates="company")
    providers = relationship("Provider", back_populates="company")
    products = relationship("Product", back_populates="company")

class Provider(Base):
    __tablename__ = "providers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False)
    contact_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    category = Column(String, nullable=True) # e.g., 'Meat', 'Vegetables'
    frequency = Column(String, nullable=True) # e.g., 'Weekly', 'Daily'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="providers")
    products = relationship("Product", back_populates="provider")
    purchases = relationship("Purchase", back_populates="provider")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=True)
    
    name = Column(String, nullable=False)
    unit = Column(String, default="unit") # kg, lb, lt, unit
    last_price = Column(Float, default=0.0)
    
    company = relationship("Company", back_populates="products")
    provider = relationship("Provider", back_populates="products")

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
    
    # Items extracted from receipt
    items = Column(Text, nullable=True) # JSON list of items found

    receipt = relationship("Receipt", back_populates="parsed_data")

class Purchase(Base):
    __tablename__ = "purchases" # Was reports

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True) # Who registered it
    provider_id = Column(String, ForeignKey("providers.id"), nullable=True)
    
    date = Column(Date, nullable=False) # Purchase date
    
    # Generative AI Data (Flattened)
    invoice_number = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    category = Column(String, nullable=True) # Expense category
    
    # Duplicate Detection
    is_duplicate = Column(Boolean, default=False)
    potential_duplicate_of = Column(String, nullable=True) 

    # Notes
    notes = Column(Text)
    
    # File Storage
    storage_path = Column(String, nullable=True) 
    file_url = Column(String, nullable=True)
    source_file_path = Column(String) # Points to receipt storage path
    
    status = Column(String, default=PurchaseStatus.DRAFT.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="purchases")
    provider = relationship("Provider", back_populates="purchases")
    
    __table_args__ = (
        Index('idx_purchase_company_date', 'company_id', 'date'),
    )
    
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    purchase_id = Column(String, ForeignKey("purchases.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String, nullable=True) # kg, lb, unit
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    purchase = relationship("Purchase", back_populates="items")

class Recipe(Base):
    __tablename__ = "recipes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"))
    name = Column(String)
    sale_price = Column(Float, default=0.0) # Price on Menu
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    items = relationship("RecipeItem", back_populates="recipe", cascade="all, delete-orphan")
    
class RecipeItem(Base):
    __tablename__ = "recipe_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipe_id = Column(String, ForeignKey("recipes.id"))
    product_id = Column(String, ForeignKey("products.id")) # Link to Inventory
    quantity = Column(Float, default=0.0) # Amount used (e.g. 0.2 kg)
    
    recipe = relationship("Recipe", back_populates="items")
    product = relationship("Product") # To get current price for cost calc
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # company = relationship("Company") # Removed: No FK and redundant (access via recipe.company)

class CategoryBudget(Base):
    __tablename__ = "category_budgets"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    period = Column(String, default="MONTHLY") # WEEKLY, MONTHLY
    category = Column(String, nullable=False)
    budget_amount = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")

class DailyClosure(Base):
    __tablename__ = "daily_closures" # Was TourClosure

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    date = Column(Date, nullable=False)
    closed_at = Column(DateTime, default=datetime.utcnow)
    closed_by_email = Column(String) 
    
    total_sales = Column(Float, default=0.0)
    total_expenses = Column(Float, default=0.0)
    cash_in_hand = Column(Float, default=0.0)
    
    notes = Column(Text, nullable=True)
    
    company = relationship("Company")

