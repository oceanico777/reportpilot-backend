from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models
from .ocr import process_receipt_with_gemini
from .storage import storage_service
import logging
from datetime import datetime
import zipfile
import io
import os

logger = logging.getLogger(__name__)

def export_receipts_zip(company_id: str, month: int, year: int, user_id: str = None):
    """
    Exports receipts for a given period/user matches to a zip file.
    """
    db: Session = SessionLocal()
    try:
        query = db.query(models.Report).filter(
            models.Report.company_id == company_id,
            models.Report.month == month,
            models.Report.year == year
        )
        if user_id:
            query = query.filter(models.Report.user_id == user_id)
        
        reports = query.all()
        if not reports:
            return {"status": "failed", "message": "No reports found"}

        # Create Zip in Memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            system_client = storage_service.get_system_client()
            
            for report in reports:
                if not report.source_file_path:
                    continue
                    
                try:
                    # Download file
                    # source_file_path is essentially "bucket_path" in many cases or local path in dev?
                    # The Model says: source_file_path = Column(String) # Points to receipt storage path 
                    # Let's assume it stores the storage path (e.g., "receipts/abc.jpg")
                    
                    file_data = system_client.storage.from_(storage_service.bucket).download(report.source_file_path)
                    
                    # Add to zip
                    # Filename: {date}_{vendor}_{amount}.ext
                    ext = os.path.splitext(report.source_file_path)[1] or ".bin"
                    vendor_safe = "".join(x for x in (report.vendor or "unknown") if x.isalnum())
                    filename = f"Tour{report.tour_id}_{vendor_safe}_{report.amount}{ext}"
                    zip_file.writestr(filename, file_data)
                    
                except Exception as e:
                    logger.error(f"Failed to zip report {report.id}: {e}")
        
        zip_buffer.seek(0)
        
        # Upload Zip
        zip_filename = f"exports/{company_id}/{year}_{month}_audit.zip"
        # Since UploadFile expects a file-like object with more attrs, we might need a workaround or use Supabase-py upload directly
        # storage_service.upload_file expects FastAPI UploadFile. 
        # let's use system_client directly for bytes upload
        
        system_client.storage.from_(storage_service.bucket).upload(
            zip_filename, 
            zip_buffer.getvalue(),
            {"content-type": "application/zip", "upsert": "true"}
        )
        
        # Get Public URL (or signed URL)
        # Using public URL for simplicity if bucket is public, else create_signed_url
        res = system_client.storage.from_(storage_service.bucket).create_signed_url(zip_filename, 3600) # 1 hour
        
        return {"status": "success", "download_url": res["signedURL"]}
        
    except Exception as e:
        logger.error(f"Export task failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def process_receipt_async(receipt_id: str, file_content: bytes = None):
    """
    Celery task to process receipt OCR asynchronously.
    """
    db: Session = SessionLocal()
    try:
        receipt = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return

        logger.info(f"Starting async OCR for receipt {receipt_id}")
        
        # If file_content is passed (small files), use it.
        # Otherwise, download from storage using storage_path.
        # For simplicity in this step, we assume bytes might be passed or we need to download.
        # Since passing bytes to Celery (Redis) is bad for large files, let's download if not present.
        
        data_to_process = file_content
        
        if not data_to_process and receipt.storage_path:
            # Download from Supabase
            # Use system client to bypass RLS in background task
            try:
                system_client = storage_service.get_system_client()
                data_to_process = system_client.storage.from_(storage_service.bucket).download(receipt.storage_path)
            except Exception as e:
                logger.error(f"Failed to download from storage: {e}")
                raise e

        if not data_to_process:
             raise ValueError("No file content available for processing")

        # Update status to PROCESSING (if not already)
        receipt.status = models.ReceiptStatus.PROCESSING.value
        db.commit()

        # Perform OCR
        extracted_data = process_receipt_with_gemini(data_to_process)
        
        # Parse date
        date_obj = None
        if extracted_data.get("date"):
            try:
                date_obj = datetime.strptime(extracted_data["date"], "%Y-%m-%d").date()
            except:
                pass

        # Save Results
        parsed = models.ParsedData(
            receipt_id=receipt.id,
            vendor=extracted_data.get("vendor"),
            date=date_obj,
            amount=float(extracted_data.get("amount") or 0),
            currency=extracted_data.get("currency"),
            category=extracted_data.get("category"),
            confidence_score=float(extracted_data.get("confidence_score") or 0)
        )
        db.add(parsed)
        
        receipt.status = models.ReceiptStatus.COMPLETED.value
        receipt.processed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully processed receipt {receipt_id}")
        
        return {"status": "success", "receipt_id": receipt_id}

    except Exception as e:
        logger.error(f"Task failed: {e}")
        if receipt:
            receipt.status = models.ReceiptStatus.FAILED.value
            db.commit()
        if receipt:
            receipt.status = models.ReceiptStatus.FAILED.value
            db.commit()
            
    finally:
        db.close()
