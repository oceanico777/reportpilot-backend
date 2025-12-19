import requests
import os

url = "http://127.0.0.1:8005/reports/upload"
# We need a token. Let's use the same one from the frontend if possible, 
# or just a fake one if RLS is bypassed or we use the dev secret.
# In reports.py, it uses get_user_company which depends on the token.
token = "fake-jwt-token-for-auth" # This matches the hardcoded check in storage.py for dev

headers = {
    "Authorization": f"Bearer {token}"
}

# Create a dummy file
file_path = "test_receipt.jpg"
with open(file_path, "wb") as f:
    f.write(b"dummy image content")

try:
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "image/jpeg")}
        print(f"Uploading to {url}...")
        response = requests.post(url, headers=headers, files=files)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
finally:
    if os.path.exists(file_path):
        os.remove(file_path)
