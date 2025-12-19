from unittest.mock import patch
import pytest
from app import models

@pytest.fixture
def mock_upload_service():
    with patch("app.routers.reports.storage_service") as mock_service:
        mock_service.upload_file.return_value = {"storage_path": "receipts/c1/test.jpg"}
        yield mock_service

@pytest.fixture
def mock_celery_task():
    with patch("app.routers.reports.process_receipt_async") as mock_task:
        yield mock_task

def test_upload_endpoint_success(client, auth_headers, test_db, mock_upload_service, mock_celery_task):
    """
    Test successful upload flow:
    1. Auth check passes
    2. File type valid
    3. Storage service called
    4. DB record created
    5. Celery task triggered
    """
    # Create company for user first (usually done in dependency, but let's ensure it exists)
    # Using the auth_headers ensures the dependency 'get_user_company' triggers and creates the company.
    
    files = {'file': ('test.jpg', b'fake-image-content', 'image/jpeg')}
    
    response = client.post("/reports/upload", headers=auth_headers, files=files)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "PROCESSING"
    assert "id" in data
    assert data["message"] == "Upload successful. Processing in background."
    
    # Verify DB
    receipt = test_db.query(models.Receipt).filter(models.Receipt.id == data["id"]).first()
    assert receipt is not None
    assert receipt.status == "PENDING" # Endpoint sets PENDING, worker sets PROCESSING. 
                                     # Wait, endpoint sets PENDING (Phase 4 change).
                                     # Let's check router code again. router sets PENDING.
    
    # Verify Celery called
    mock_celery_task.delay.assert_called_once_with(receipt.id)

def test_upload_invalid_file_type(client, auth_headers):
    files = {'file': ('test.exe', b'bad-content', 'application/x-msdownload')}
    response = client.post("/reports/upload", headers=auth_headers, files=files)
    
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]
