from sqlalchemy.orm import Session
from .. import models
import time

def create_report(report_id: str, db: Session):
    # Simulate processing delay
    time.sleep(3)
    
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        return

    # Mock Report Generation
    # In real implementation, this would query receipts for the month, 
    # generate a summary with AI, and create a PDF.
    
    report.summary_text = f"Executive Summary for {report.month}/{report.year}: Expenses were within budget. Top category: Software."
    report.file_url = f"https://example.com/reports/{report.id}.pdf"
    report.status = models.ReportStatus.SENT.value # Or DRAFT, depending on flow
    
    db.commit()
