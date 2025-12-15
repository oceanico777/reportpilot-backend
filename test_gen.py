import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def test_model(model_name):
    print(f"Testing model: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, world!")
        print(f"✅ Success with {model_name}")
        print(response.text)
        return True
    except Exception as e:
        print(f"❌ Failed with {model_name}: {e}")
        return False

# Test priority
if not test_model('gemini-1.5-flash'):
    test_model('gemini-pro')
