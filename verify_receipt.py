import requests
import json
import os

# Configuration
API_URL = "http://127.0.0.1:8000/reports/upload"
IMAGE_PATH = r"C:/Users/USUARIO/.gemini/antigravity/brain/582487c0-a8c5-4665-ab18-98223e7eac1d/uploaded_image_1765734266413.jpg"

def test_ocr():
    print(f"Testing OCR with image: {IMAGE_PATH}")
    
    if not os.path.exists(IMAGE_PATH):
        print("Error: Image file not found!")
        return

    try:
        with open(IMAGE_PATH, 'rb') as f:
            files = {'file': (os.path.basename(IMAGE_PATH), f, 'image/jpeg')}
            response = requests.post(API_URL, files=files)
            
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Upload Successful!")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Validation logic
            extracted = data.get('extracted_data', {})
            print("\n--- Extracted Data Analysis ---")
            print(f"Vendor: {extracted.get('vendor')}")
            print(f"Date: {extracted.get('date')}")
            print(f"Amount: {extracted.get('currency')} {extracted.get('amount')}")
            print(f"Category: {extracted.get('category')}")
            print(f"Confidence: {extracted.get('confidence_score')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_ocr()
