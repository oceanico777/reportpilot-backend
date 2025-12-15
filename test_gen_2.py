import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model_name = 'gemini-1.5-flash-latest'
print(f"Testing model: {model_name}...")
try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Hello")
    print(f"✅ Success with {model_name}")
except Exception as e:
    print(f"❌ Failed with {model_name}: {e}")
