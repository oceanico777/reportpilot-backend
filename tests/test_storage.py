from unittest.mock import MagicMock, patch
from app.services.storage import SupabaseStorageService
import pytest

@pytest.fixture
def mock_supabase():
    with patch("app.services.storage.create_client") as mock_client:
        yield mock_client

def test_upload_file(mock_supabase):
    # Setup
    service = SupabaseStorageService()
    service.client = MagicMock()
    service.bucket = "receipts"
    
    mock_file = MagicMock()
    mock_file.read.return_value = b"file_content"
    mock_file.content_type = "image/jpeg"
    
    # Mock storage.from_.upload
    service.client.storage.from_.return_value.upload.return_value = {"path": "test/path.jpg"}
    
    # Act
    result = service.upload_file(mock_file, "company_123")
    
    # Assert
    assert result["storage_path"]
    service.client.storage.from_.assert_called_with("receipts")
    # path should contain company_id
    # upload was called with kwargs: upload(file=..., path=..., ...)
    upload_call = service.client.storage.from_.return_value.upload.call_args
    # call_args is (args, kwargs)
    assert "company_123/" in upload_call.kwargs['path']

def test_get_file_url(mock_supabase):
    service = SupabaseStorageService()
    service.client = MagicMock()
    
    service.client.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "http://signed.url"}
    
    url = service.get_file_url("path/to/file.jpg", "company_123") # Mocked logic doesn't use company_id in call
    
    assert url == "http://signed.url"
    # Service calls create_signed_url("path/to/file.jpg", 3600)
    # verify call happened generally
    assert service.client.storage.from_.return_value.create_signed_url.called
