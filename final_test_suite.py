import requests
import uuid
import time

API_URL = "http://localhost:8005"
headers = {"Authorization": "Bearer fake-jwt-token-for-auth"}

def run_test():
    print("🚀 Starting Final Test Suite...")
    
    # 1. Health Check
    try:
        requests.get(f"{API_URL}/health", timeout=2)
    except:
        print("❌ Error: Backend is not running on localhost:8005.")
        return

    # 2. Verify Organization Management (Force User/Company Creation)
    print("\n--- Testing Organization Management ---")
    res = requests.get(f"{API_URL}/admin/team", headers=headers)
    if res.status_code == 200:
        data = res.json()
        print(f"✅ Organization Found: {data.get('company_name', 'Unknown')}")
    else:
        print(f"❌ Failed to fetch team: {res.status_code} {res.text}")
        return

    # 3. Verify Tourism Specialization (Generate Report with Manual Override)
    print("\n--- Testing Tourism Report Generation ---")
    payload = {
        "month": 12,
        "year": 2025,
        "tour_id": "TOUR-TOURISM-001",
        "client_name": "Turista Feliz",
        "company_id": "demo-company-123",
        "source_file_path": "test_path.jpg",
        "category": "🍽️ Restaurante", # Confirmación manual
        "extracted_data": {
            "vendor": "Restaurante El Sol",
            "amount": 150000,
            "currency": "COP",
            "date": "2025-12-17",
            "category": "Alimentación" # Sugerencia de la IA
        }
    }
    res = requests.post(f"{API_URL}/reports/generate", headers=headers, json=payload)
    if res.status_code == 200:
        data = res.json()
        if data["category"] == "🍽️ Restaurante":
            print(f"✅ Manual category priority verified: {data['category']} used.")
        else:
            print(f"❌ Manual category priority FAILED: Used {data['category']}")
    else:
        print(f"❌ Report Generation failed: {res.status_code} {res.text}")

    # 4. Verify Excel Export
    print("\n--- Testing Excel Export ---")
    res = requests.get(f"{API_URL}/exports/gastos?format=xlsx", headers=headers)
    if res.status_code == 200:
        print("✅ Excel Export verified (received XLSX stream).")
    else:
        print(f"❌ Excel Export failed: {res.status_code} {res.text}")

    print("\n✨ FINAL TOURISM VERIFICATION COMPLETED ✨")

if __name__ == "__main__":
    run_test()
