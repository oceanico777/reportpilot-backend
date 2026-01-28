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
                Analiza esta imagen de factura/recibo de compra y extrae la siguiente información en formato JSON:
                
                {
                    "vendor": "nombre del proveedor/comercio",
                    "vendor_nit": "NIT/RUT si existe",
                    "date": "YYYY-MM-DD",
                    "amount": 1234.56,
                    "currency": "COP",
                    "category": "Categoría sugerida (Ej: Carnes, Frutas, Bebidas, Aseo, Mantenimiento)",
                    "invoice_number": "Número de factura si existe",
                    "confidence_score": 0.95,
                    "items": [
                        {
                            "name": "nombre producto detallado", 
                            "qty": 1.0, 
                            "unit": "kg/lb/unid (detectar si existe)", 
                            "price": 1000.0, 
                            "total": 1000.0
                        }
                    ]
                }
                
                Instrucciones Clave:
                1. Extrae TODOS los items de compra posibles.
                2. Si la cantidad no es explícita, asume 1.
                3. 'price' es el precio unitario. 'total' es precio * cantidad.
                4. Solo responde con el objeto JSON puro.
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
                break
    
    # Fallback
    return {
        "vendor": "Comercio no detectado",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "amount": 0.0,
        "currency": "COP",
        "category": "📦 Otros",
        "confidence_score": 0.1,
        "items": []
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

    try:
        receipt.status = "PROCESSING"
        db.commit()
    except Exception as e:
        logger.error(f"Failed to set status: {e}")

    try:
        # Load file bytes
        file_path = receipt.storage_path or receipt.file_url
        from ..services.storage import storage_service
        file_bytes = storage_service.download_file(file_path)
        
        if not file_bytes and os.path.exists(file_path):
             with open(file_path, "rb") as f:
                 file_bytes = f.read()

        if not file_bytes:
             raise Exception("File bytes extraction failed")

        extracted_data = process_receipt_with_gemini(file_bytes)
        
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
            confidence_score=float(extracted_data.get("confidence_score", 0.0)),
            items=json.dumps(extracted_data.get("items", []))
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
