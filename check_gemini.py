import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key found: {api_key[:5]}...{api_key[-5:] if api_key else 'NONE'}")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found")
    exit(1)

genai.configure(api_key=api_key)

print("Listing models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"FAILED to list models: {e}")

print("\nTesting simple generation...")
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content("Hola, dime 'OK' si recibes esto.")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"FAILED with gemini-2.5-flash: {e}")

try:
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content("Hola, dime 'OK' si recibes esto.")
    print(f"Response with gemini-flash-latest: {response.text}")
except Exception as e:
    print(f"FAILED with gemini-flash-latest: {e}")
