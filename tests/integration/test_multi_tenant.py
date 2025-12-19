from app import models
import pytest

def test_company_isolation_receipts(client, auth_headers, other_auth_headers, test_db):
    """
    Verify User A cannot see User B's receipts
    """
    # 1. Create Data for User A (handled by auth dependency implicitly on first call, but let's be explicit)
    # Call an endpoint to trigger company creation
    client.get("/receipts/", headers=auth_headers)
    
    # 2. Create Receipt for User A manually to ensure ID is known
    # Get A's company
    company_a = test_db.query(models.Company).filter(models.Company.owner.has(email="test@example.com")).first()
    receipt_a = models.Receipt(company_id=company_a.id, filename="user_a.jpg", status="PENDING", file_url="http://fake.url/a")
    test_db.add(receipt_a)
    test_db.commit()
    
    # 3. Create Data for User B
    client.get("/receipts/", headers=other_auth_headers)
    company_b = test_db.query(models.Company).filter(models.Company.owner.has(email="other@example.com")).first()
    receipt_b = models.Receipt(company_id=company_b.id, filename="user_b.jpg", status="PENDING", file_url="http://fake.url/b")
    test_db.add(receipt_b)
    test_db.commit()
    
    # 4. User A tries to get Reciept B -> Should be 404 Not Found (Isolation)
    response = client.get(f"/receipts/{receipt_b.id}", headers=auth_headers)
    assert response.status_code == 404
    
    # 5. User A tries to list receipts -> Should only see Receipt A
    response = client.get("/receipts/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == receipt_a.id

def test_company_isolation_reports(client, auth_headers, other_auth_headers, test_db):
    """
    Verify User A cannot see User B's reports
    """
    # Setup
    client.get("/reports/", headers=auth_headers) # Init Company A
    client.get("/reports/", headers=other_auth_headers) # Init Company B
    
    company_a = test_db.query(models.Company).filter(models.Company.owner.has(email="test@example.com")).first()
    company_b = test_db.query(models.Company).filter(models.Company.owner.has(email="other@example.com")).first()
    
    report_b = models.Report(company_id=company_b.id, client_name="Client B")
    test_db.add(report_b)
    test_db.commit()
    
    # Access Report B as User A
    response = client.delete(f"/reports/{report_b.id}", headers=auth_headers)
    assert response.status_code == 404 # Cannot find to delete
    
    # Verify it still exists
    assert test_db.query(models.Report).filter(models.Report.id == report_b.id).first() is not None
