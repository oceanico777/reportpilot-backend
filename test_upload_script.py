import requests
import os

BASE_URL = "http://localhost:8000"
UPLOAD_URL = f"{BASE_URL}/reports/upload"

def test_upload_csv():
    print("Testing CSV Upload...")
    files = {'file': ('test.csv', b'col1,col2\nval1,val2', 'text/csv')}
    try:
        response = requests.post(UPLOAD_URL, files=files)
        if response.status_code == 200:
            print("✅ CSV Upload Success")
            print(response.json())
        else:
            print(f"❌ CSV Upload Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ CSV Upload Error: {e}")

def test_upload_pdf():
    print("\nTesting PDF Upload...")
    files = {'file': ('test.pdf', b'%PDF-1.4...', 'application/pdf')}
    try:
        response = requests.post(UPLOAD_URL, files=files)
        if response.status_code == 200:
            print("✅ PDF Upload Success")
            print(response.json())
        else:
            print(f"❌ PDF Upload Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ PDF Upload Error: {e}")

def test_upload_invalid():
    print("\nTesting Invalid File Upload (TXT)...")
    files = {'file': ('test.txt', b'Just some text', 'text/plain')}
    try:
        response = requests.post(UPLOAD_URL, files=files)
        if response.status_code == 400:
            print("✅ Invalid File Handled Correctly (400 Bad Request)")
            print(response.json())
        else:
            print(f"❌ Invalid File Test Failed: Expected 400, got {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Invalid File Upload Error: {e}")

if __name__ == "__main__":
    # check if server is up
    try:
        requests.get(BASE_URL)
        test_upload_csv()
        test_upload_pdf()
        test_upload_invalid()
    except requests.exceptions.ConnectionError:
        print("❌ Backend server is not running on http://localhost:8000")
