import pytest
from app import models
from app.models import ReceiptStatus, ReportStatus

def test_receipt_status_enum():
    assert ReceiptStatus.PENDING.value == "PENDING"
    assert ReceiptStatus.PROCESSING.value == "PROCESSING"
    assert ReceiptStatus.COMPLETED.value == "COMPLETED"
    assert ReceiptStatus.FAILED.value == "FAILED"

def test_create_user_model():
    user = models.User(id="u1", email="test@test.com", full_name="Test User")
    assert user.email == "test@test.com"
    assert user.full_name == "Test User"

def test_create_company_model():
    company = models.Company(id="c1", user_id="u1", name="Test Co")
    assert company.name == "Test Co"
    
def test_create_receipt_defaults():
    receipt = models.Receipt(company_id="c1", status=ReceiptStatus.PENDING.value)
    assert receipt.status == ReceiptStatus.PENDING.value
