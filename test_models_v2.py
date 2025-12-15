import google.generativeai as genai
import sys

# Hardcoded key for testing
API_KEY = "AIzaSyCZL03al6zrPwwnoaKdtDMkblXc1kEMpt4"
genai.configure(api_key=API_KEY)

models_to_test = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-pro',
    'gemini-pro',
    'gemini-1.0-pro'
]

print(f"Testing with key: {API_KEY[:5]}...")

for model_name in models_to_test:
    print(f"\nTrying {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hi")
        print(f"✅ SUCCESS: {model_name} works!")
        # Stop after first success
        break
    except Exception as e:
        print(f"❌ FAILED {model_name}: {str(e)}")
