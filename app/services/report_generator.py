from sqlalchemy.orm import Session
from .. import models
import time

import pytesseract
from PIL import Image
from pypdf import PdfReader
import magic
import os
import io
import platform

# Set Tesseract path for Windows
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def process_text_with_llm(text: str):
    # Placeholder for LLM processing
    # In a real app, this would send 'text' to OpenAI/Gemini to extract structured data
    return f"Processed Text (Length: {len(text)} chars). Content Preview: {text[:100]}..."

def create_report(report_id: str, db: Session):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        return

    try:
        # 1. Read the file
        file_path = report.source_file_path
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            contents = f.read()

        # 2. Detect file type
        # Note: python-magic might need system dependencies. 
        # Fallback to extension if magic fails or returns generic type could be added.
        try:
            file_type = magic.from_buffer(contents, mime=True)
        except Exception as e:
            print(f"Magic failed: {e}, falling back to extension")
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.csv': file_type = 'text/csv'
            elif ext == '.pdf': file_type = 'application/pdf'
            elif ext in ['.jpg', '.jpeg']: file_type = 'image/jpeg'
            elif ext == '.png': file_type = 'image/png'
            else: file_type = 'unknown'

        text_data = ""

        # 3. Extract Text
        if file_type == 'application/pdf':
            text_data = extract_text_from_pdf(contents)

        elif file_type == 'text/csv' or file_type == 'text/plain':
            text_data = contents.decode('utf-8')

        elif file_type in ['image/jpeg', 'image/png']:
            try:
                image = Image.open(io.BytesIO(contents))
                text_data = pytesseract.image_to_string(image)
            except Exception as e:
                raise Exception(f"OCR Failed: {str(e)}")
        
        else:
            raise Exception(f"Unsupported file type: {file_type}")

        if not text_data:
            raise Exception("No text extracted from file.")

        # 4. Process with LLM (Mock)
        processed_summary = process_text_with_llm(text_data)
        
        # 5. Update Report
        report.summary_text = processed_summary
        report.file_url = f"https://example.com/reports/{report.id}.pdf" # Mock URL
        report.status = models.ReportStatus.SENT.value # Success
        
    except Exception as e:
        print(f"Error generating report {report_id}: {e}")
        report.status = models.ReportStatus.FAILED.value
        report.summary_text = f"Error: {str(e)}"
    
    finally:
        db.commit()
