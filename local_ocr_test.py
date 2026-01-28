import os
import io
import json
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = "AIzaSyDM0Hea3BBFeqFs7hOkgrIkucIujZrBNXA"
genai.configure(api_key=api_key)

def test_ocr_locally(image_path):
    print(f"Testing OCR with image: {image_path}")
    
    try:
        with open(image_path, "rb") as f:
            file_data = f.read()
            
        # 1. Resize
        img = Image.open(io.BytesIO(file_data))
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024))
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img.format or 'JPEG')
            file_data = img_byte_arr.getvalue()
            print(f"Resized image to {img.size}")

        # 2. Try Gemini
        model_name = 'gemini-2.0-flash'
        print(f"Using model: {model_name}")
        model = genai.GenerativeModel(model_name)
        
        prompt = """
        Analiza esta imagen de recibo y extrae la siguiente información en formato JSON:
        {
            "vendor": "nombre del comercio o vendedor",
            "vendor_nit": "NIT o RUT del comercio si existe",
            "date": "fecha en formato YYYY-MM-DD",
            "amount": 1234.56,
            "currency": "COP",
            "category": "una de estas: Alimentación, Transporte, Alojamiento, Otros",
            "confidence_score": 0.95
        }
        Solo responde con el objeto JSON puro.
        """
        
        # Re-open for Gemini
        img_for_gemini = Image.open(io.BytesIO(file_data))
        response = model.generate_content([prompt, img_for_gemini])
        
        print("Response received from Gemini:")
        print(response.text)
        
        # 3. Clean and Parse JSON
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        parsed = json.loads(text.strip())
        print("\nSUCCESSFULLY PARSED:")
        print(json.dumps(parsed, indent=2))

    except Exception as e:
        print(f"\nERROR DURING LOCAL TEST: {e}")

if __name__ == "__main__":
    # The user provided two images in the metadata.
    # UPLOADED_IMAGE_1_1766152509844.jpg seems to be the one from the screenshot.
    target_image = r"C:/Users/USUARIO/.gemini/antigravity/brain/d8e8bba0-235d-4ca2-b76e-8ddeca525ac1/uploaded_image_1_1766152509844.jpg"
    test_ocr_locally(target_image)
