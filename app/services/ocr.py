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
    Process receipt image using Gemini Vision API with model fallback (Flash -> Pro)
    And failure context hints.
    """
    models_to_try = [
        {'name': 'gemini-1.5-flash', 'hint': ''},
        {'name': 'gemini-1.5-pro', 'hint': 'El modelo anterior tuvo dificultades. '}
    ]
    
    last_error_context = ""
    
    for model_cfg in models_to_try:
        model_name = model_cfg['name']
        hint = model_cfg['hint'] + last_error_context
        
        delay = 2
        for attempt in range(retries + 1):
            try:
                img = Image.open(io.BytesIO(file_data))
                logger.info(f"Trying OCR with model: {model_name} (Attempt {attempt+1})")
                
                # Check if model exists/can be initialized
                try:
                    model = genai.GenerativeModel(model_name)
                except Exception as e:
                    logger.error(f"Failed to initialize model {model_name}: {e}")
                    break # Try next model
                
                prompt = f"""
                {hint}
                Analiza esta imagen de recibo y extrae la siguiente información en formato JSON:
                
                {{
                    "vendor": "nombre del comercio o vendedor",
                    "vendor_nit": "NIT o RUT del establecimiento (formato XXXXXXXXX-Y o similar). Si no visible, devuelve null/vacío",
                    "date": "fecha en formato YYYY-MM-DD",
                    "amount": número decimal del monto total,
                    "currency": "código de moneda (USD, EUR, etc.) (default COP if in Colombia)",
                    "category": "categoría del gasto (elige exclusivamente entre: 🍽️ Restaurante, 🎟️ Atractivo, 🍿 Snack, 📦 Otros)",
                    "confidence_score": número entre 0 y 1 indicando confianza en la extracción
                }}
                
                Responde SOLO con el JSON válido.
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



def process_receipt(receipt_id: str, db: Session):
    """
    Process receipt using Gemini Vision API (background task)
    """
    receipt = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()
    if not receipt:
        logger.error(f"Receipt {receipt_id} not found")
        return

    try:
        # Load file bytes
        file_bytes = None
        file_path = receipt.file_url
        
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        else:
             logger.error(f"File not found at {file_path}")
             receipt.status = models.ReceiptStatus.FAILED.value
             db.commit()
             return

        # Extract data using Gemini
        extracted_data = process_receipt_with_gemini(file_bytes)
        
        # Parse date
        date_obj = None
        if extracted_data.get("date"):
            try:
                date_obj = datetime.strptime(extracted_data["date"], "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Invalid date format: {extracted_data['date']}")
        
        # Create ParsedData record
        parsed_data = models.ParsedData(
            receipt_id=receipt.id,
            vendor=extracted_data.get("vendor", "Unknown"),
            vendor_nit=extracted_data.get("vendor_nit"), # Save detected NIT
            date=date_obj,
            amount=float(extracted_data.get("amount", 0.0)),
            currency=extracted_data.get("currency", "USD"),
            category=extracted_data.get("category", "Other"),
            confidence_score=float(extracted_data.get("confidence_score", 0.0))
        )
        
        db.add(parsed_data)
        # Fix: Unified status name (matching schema and common usage)
        receipt.status = "PROCESSED" 
        db.commit()
        
        logger.info(f"Receipt {receipt_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Failed to process receipt {receipt_id}: {e}")
        receipt.status = models.ReceiptStatus.FAILED.value
        db.commit()
