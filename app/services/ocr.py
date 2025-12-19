from sqlalchemy.orm import Session
from .. import models
import os
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

import time

import io

def process_receipt_with_gemini(file_data: bytes, retries=1) -> dict:
    """
    Process receipt image using Gemini Vision API with model fallback.
    Includes image resizing to save memory on Render.
    """
    # 1. OPTIMIZE IMAGE (Resize if large to save RAM on Render)
    try:
        img = Image.open(io.BytesIO(file_data))
        # Max dimension 1024px is plenty for OCR and saves tons of RAM
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024))
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img.format or 'JPEG')
            file_data = img_byte_arr.getvalue()
            logger.info(f"Resized image to {img.size} for memory efficiency")
    except Exception as e:
        logger.warning(f"Could not resize image: {e}")

    # 2. MODELS TO TRY (Robust naming)
    models_to_try = [
        'gemini-2.0-flash',
        'gemini-flash-latest',
        'gemini-1.5-flash',
        'gemini-pro-latest'
    ]
    
    for model_name in models_to_try:
        delay = 2
        for attempt in range(retries + 1):
            try:
                # Re-open image for each attempt to be safe
                img = Image.open(io.BytesIO(file_data))
                logger.info(f"Trying OCR with model: {model_name} (Attempt {attempt+1})")
                
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
                
                Solo responde con el objeto JSON puro, sin markdown ni explicaciones.
                Si no detectas el comercio, usa "Comercio no detectado".
                Si no detectas el monto, usa 0.
                """
                
                response = model.generate_content([prompt, img])
                if not response or not response.text:
                    raise Exception("Empty response from Gemini")
                    
                response_text = response.text.strip()
                
                # Clean JSON markdown
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                extracted_data = json.loads(response_text.strip())
                return extracted_data
                
            except Exception as e:
                logger.error(f"Gemini error with {model_name} on attempt {attempt+1}: {e}")
                last_error_context = f"Error previo: {str(e)}. "
                if attempt < retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                # If we exhausted retries for this model, we move to the next model in models_to_try
                break
    
    # If all models fail, return fallback mock
    return {
        "vendor": "Comercio no detectado",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "amount": 0.0,
        "currency": "COP",
        "category": "📦 Otros",
        "confidence_score": 0.1
    }



def process_receipt(receipt_id: str):
    """
    Process receipt using Gemini Vision API (background task)
    """
    from ..database import SessionLocal
    db = SessionLocal()
    
    logger.info(f"--- START OCR TASK for {receipt_id} ---")
    
    receipt = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()
    if not receipt:
        logger.error(f"Receipt {receipt_id} not found")
        db.close()
        return

    # 1. Update status to PROCESSING immediately
    try:
        receipt.status = "PROCESSING"
        db.commit()
        logger.info(f"Status set to PROCESSING for {receipt_id}")
    except Exception as e:
        logger.error(f"Failed to set initial status for {receipt_id}: {e}")

    try:
        # Load file bytes
        file_bytes = None
        file_path = receipt.file_url
        
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        else:
             # Try signed URL if local file is missing (e.g. cloud only)
             logger.warning(f"Local file not found at {file_path}, can only process if local path is correct.")
             receipt.status = "FAILED"
             db.commit()
             return

        # 2. Extract data using Gemini (Optimized model list)
        extracted_data = process_receipt_with_gemini(file_bytes)
        
        # 3. Parse and save result
        date_obj = None
        if extracted_data.get("date"):
            try:
                date_obj = datetime.strptime(extracted_data["date"], "%Y-%m-%d").date()
            except Exception:
                pass
        
        parsed_data = models.ParsedData(
            receipt_id=receipt.id,
            vendor=extracted_data.get("vendor", "Comercio no detectado"),
            vendor_nit=extracted_data.get("vendor_nit"),
            date=date_obj,
            amount=float(extracted_data.get("amount", 0.0)),
            currency=extracted_data.get("currency", "COP"),
            category=extracted_data.get("category", "📦 Otros"),
            confidence_score=float(extracted_data.get("confidence_score", 0.0))
        )
        
        db.add(parsed_data)
        receipt.status = "PROCESSED" 
        db.commit()
        logger.info(f"Receipt {receipt_id} PROCESSED successfully")
        
    except Exception as e:
        logger.error(f"Critical error processing receipt {receipt_id}: {e}")
        receipt.status = "FAILED"
        db.commit()
    finally:
        db.close()
