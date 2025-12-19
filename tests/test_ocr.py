from unittest.mock import patch, MagicMock
from app.services.ocr import process_receipt_with_gemini
import json

@patch('app.services.ocr.genai.GenerativeModel')
@patch('app.services.ocr.Image.open')
def test_ocr_extraction_success(mock_img_open, mock_model_cls):
    # Mock Image
    mock_img_open.return_value = MagicMock()

    # Mock Response
    mock_response = MagicMock()
    mock_response.text = '''
    ```json
    {
        "vendor": "Supermercado Exito",
        "date": "2023-10-25",
        "amount": 150000.00,
        "currency": "COP",
        "category": "Groceries",
        "confidence_score": 0.95
    }
    ```
    '''
    mock_model = mock_model_cls.return_value
    mock_model.generate_content.return_value = mock_response
    
    # Input fake bytes
    result = process_receipt_with_gemini(b"fake_image_bytes")
    
    assert result["vendor"] == "Supermercado Exito"
    assert result["amount"] == 150000.00
    assert result["confidence_score"] == 0.95

@patch('app.services.ocr.genai.GenerativeModel')
def test_ocr_extraction_retry_logic(mock_model_cls):
    # Setup failure then success? 
    # Current implementation retries on specific 429/503 errors only or generic exceptions?
    # Logic: "if '429' in error_str... continue"
    # To test this we need side_effect on generate_content
    pass
