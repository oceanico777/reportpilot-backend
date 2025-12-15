import requests
import json
import uuid

API_URL = "http://localhost:8000"

def test_create_report_with_new_fields():
    print("Testing report creation with new fields...")
    
    payload = {
        "company_id": "demo-company-123",
        "month": 12,
        "year": 2025,
        "tour_id": "TOUR-2025-TEST",
        "client_name": "Test Client",
        "source_file_path": "uploads/test_file.pdf",
        "extracted_data": {
            "vendor": "Test Vendor",
            "date": "2025-12-15",
            "amount": 123.45,
            "currency": "$",
            "category": "Meals"
        }
    }
    
    try:
        # 1. Create Report
        headers = {"Authorization": "Bearer fake-jwt-token-for-auth"}
        res = requests.post(f"{API_URL}/reports/generate", json=payload, headers=headers)
        if res.status_code != 200:
            print(f"❌ Failed to create report: {res.text}")
            return
            
        data = res.json()
        report_id = data['id']
        print(f"✅ Report created with ID: {report_id}")
        
        # Verify returned data has new fields
        assert data['tour_id'] == "TOUR-2025-TEST", f"Expected tour_id 'TOUR-2025-TEST', got {data.get('tour_id')}"
        assert data['client_name'] == "Test Client", f"Expected client_name 'Test Client', got {data.get('client_name')}"
        assert data['vendor'] == "Test Vendor", f"Expected vendor 'Test Vendor', got {data.get('vendor')}"
        assert data['amount'] == 123.45 or data['amount'] == '123.45', f"Expected amount 123.45, got {data.get('amount')}"
        
        print("✅ Report creation response contains correct new fields")

        # 2. Fetch Reports and verify persistence
        res = requests.get(f"{API_URL}/reports/?limit=1", headers=headers)
        if res.status_code != 200:
            print(f"❌ Failed to fetch reports: {res.text}")
            return
            
        reports = res.json()
        if not reports:
            print("❌ No reports found")
            return
            
        latest_report = reports[0]
        # In list view, we might verify if we updated the list endpoint schema too?
        # Yes, schemas.Report is used for list too.
        
        print("Latest report from DB:", latest_report)
        assert latest_report['tour_id'] == "TOUR-2025-TEST", "Persisted tour_id incorrect"
        assert latest_report['category'] == "Meals", "Persisted category incorrect"
        
        print("✅ Verification Successful: Fields are persisting correctly.")
        
    except Exception as e:
        print(f"❌ Exception during test: {e}")

if __name__ == "__main__":
    test_create_report_with_new_fields()
