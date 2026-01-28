from app.services.ocr import process_receipt_with_gemini
import os
from dotenv import load_dotenv

# Load env to get API Key
load_dotenv()

# Image Paths from User
image_paths = [
    r"C:/Users/USUARIO/.gemini/antigravity/brain/e89ce639-0b34-4802-8f10-ddad6d48126c/uploaded_image_0_1766453616313.jpg",
    r"C:/Users/USUARIO/.gemini/antigravity/brain/e89ce639-0b34-4802-8f10-ddad6d48126c/uploaded_image_1_1766453616313.jpg",
    r"C:/Users/USUARIO/.gemini/antigravity/brain/e89ce639-0b34-4802-8f10-ddad6d48126c/uploaded_image_2_1766453616313.jpg"
]

results = []
print("--- Starting OCR Test on Real Receipts ---")
for path in image_paths:
    if not os.path.exists(path):
        print(f"File not found: {path}")
        continue
        
    print(f"\nProcessing: {os.path.basename(path)}")
    try:
        with open(path, "rb") as f:
            file_bytes = f.read()
            
        result = process_receipt_with_gemini(file_bytes)
        result['filename'] = os.path.basename(path)
        results.append(result)
        print("Vendor:", result.get("vendor"))
        print("Total:", result.get("amount"))
    except Exception as e:
        print(f"Error: {e}")

import json
with open("ocr_results.json", "w", encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("Saved results to ocr_results.json")
