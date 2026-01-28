import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Directory to store mock email logs
EMAIL_LOG_DIR = "uploads/emails"
os.makedirs(EMAIL_LOG_DIR, exist_ok=True)

class EmailService:
    def __init__(self):
        # Placeholder for real SMTP configuration
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.example.com")
        self.smtp_port = os.getenv("SMTP_PORT", "587")
        self.smtp_user = os.getenv("SMTP_USER", "user@example.com")
        self.smtp_pass = os.getenv("SMTP_PASSWORD", "password")

    def send_tour_closure_email(self, tour_id: str, recipient_email: str, pdf_path: str, guide_name: str):
        """
        Simulates sending an email with the Settlement PDF attached.
        Logs the content to a file for verification in the absence of real SMTP credentials.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"email_{tour_id}_{timestamp}.log"
        log_path = os.path.join(EMAIL_LOG_DIR, log_filename)
        
        email_content = f"""
Subject: Acta de Liquidación - Tour {tour_id}
To: {recipient_email}
From: ReportPilot <notifications@reportpilot.ai>

Estimado Contador,

Se ha completado el cierre del tour {tour_id} por el guía {guide_name}.
Adjunto encontrará el Acta de Liquidación en formato PDF.

Puede revisar los detalles completos y descargar los soportes originales en el siguiente enlace:
https://reportpilot-frontend.vercel.app/admin/dashboard?tour={tour_id}

Este es un mensaje automático, por favor no responda.

---
Attachment: {pdf_path} (PDF)
---
"""
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(email_content)
            
            logger.info(f"Email notification for tour {tour_id} logged to {log_path}")
            return {"status": "success", "log_path": log_path}
        except Exception as e:
            logger.error(f"Failed to log email for tour {tour_id}: {e}")
            return {"status": "error", "message": str(e)}

email_service = EmailService()
