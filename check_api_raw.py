import requests
import os

API_KEY = "AIzaSyCZL03al6zrPwwnoaKdtDMkblXc1kEMpt4"
URL = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

print(f"Querying {URL.replace(API_KEY, 'API_KEY')}...")
try:
    response = requests.get(URL)
    print(f"Status Code: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
