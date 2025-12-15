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

def process_receipt_with_gemini(file_path: str, retries=3, initial_delay=2) -> dict:
    """
    Procesa imagen de recibo usando Gemini Vision API con retries
    
    Args:
        file_path: Ruta al archivo de imagen
        retries: Número de reintentos
        initial_delay: Delay inicial en segundos
        
    Returns:
        dict: Datos extraídos o error
    """
    delay = initial_delay
    last_error = None
    
    for attempt in range(retries + 1):
        try:
            # Load image
            img = Image.open(file_path)
            
            # Initialize Gemini model (Using 2.0 Flash as discovered)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Create structured prompt
            prompt = """
            Analiza esta imagen de recibo y extrae la siguiente información en formato JSON:
            
            {
                "vendor": "nombre del comercio o vendedor",
                "date": "fecha en formato YYYY-MM-DD",
                "amount": número decimal del monto total,
                "currency": "código de moneda (USD, EUR, etc.) (default COP if in Colombia)",
                "category": "categoría del gasto (elige entre: Office Supplies, Travel, Meals, Software, Entertainment, Other)",
                "items": ["lista de items comprados si están visibles"],
                "confidence_score": número entre 0 y 1 indicando confianza en la extracción
            }
            
            Si no puedes encontrar algún dato, usa null. Responde SOLO con el JSON, sin texto adicional.
            """
            
            # Generate content with image
            response = model.generate_content([prompt, img])
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Remove markdown
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            extracted_data = json.loads(response_text)
            
            logger.info(f"Successfully extracted data from receipt: {extracted_data}")
            return extracted_data
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            
            # Check for Rate Limit (429) or Service Unavailable (503)
            if "429" in error_str or "503" in error_str:
                if attempt < retries:
                    logger.warning(f"Gemini API rate limit hit. Retrying in {delay}s (Attempt {attempt+1}/{retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
            
            logger.error(f"Error processing receipt with Gemini (Attempt {attempt+1}): {e}")
            if attempt == retries:
                raise last_error

    return extracted_data


def process_receipt(receipt_id: str, db: Session):
    """
    Process receipt using Gemini Vision API (background task)
    """
    receipt = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()
    if not receipt:
        logger.error(f"Receipt {receipt_id} not found")
        return

    try:
        # Extract data using Gemini
        extracted_data = process_receipt_with_gemini(receipt.file_url)
        
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
            date=date_obj,
            amount=float(extracted_data.get("amount", 0.0)),
            currency=extracted_data.get("currency", "USD"),
            category=extracted_data.get("category", "Other"),
            confidence_score=float(extracted_data.get("confidence_score", 0.0))
        )
        
        db.add(parsed_data)
        receipt.status = models.ReceiptStatus.PROCESSED.value
        db.commit()
        
        logger.info(f"Receipt {receipt_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Failed to process receipt {receipt_id}: {e}")
        receipt.status = models.ReceiptStatus.FAILED.value
        db.commit()
