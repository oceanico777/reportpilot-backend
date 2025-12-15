import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

models_to_test = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-flash-001',
    'gemini-1.5-pro',
    'gemini-1.5-pro-latest',
    'gemini-pro',
    'gemini-1.0-pro'
]

print("Starting model tests...")

for model_name in models_to_test:
    print(f"\nTrying {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hi")
        print(f"✅ SUCCESS: {model_name} works!")
        break
    except Exception as e:
        print(f"❌ FAILED {model_name}: {str(e)[:100]}...")
