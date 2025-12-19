import os
import time
from datetime import datetime
from supabase import create_client, Client, ClientOptions
from fastapi import UploadFile, HTTPException
import logging
from jose import jwt

logger = logging.getLogger(__name__)

class SupabaseStorageService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not set. Storage service will fail.")
            self.client = None
        else:
            self.client: Client = create_client(self.url, self.key)
            
        self.bucket = "receipts"

    def upload_file(self, file: UploadFile, company_id: str, file_type: str = "receipt", token: str = None) -> dict:
        """
        Uploads a file to Supabase Storage.
        Structure: {company_id}/{year}/{month}/{timestamp}_{filename}
        """
        if not self.client:
            raise HTTPException(status_code=500, detail="Storage service not configured")

        # Determine which client to use (Anon/Service or User Scoped)
        active_client = self.client
        if token:
            # DEV FIX: If using the fake frontend token, generate a REAL signed token for Supabase
            if token == "fake-jwt-token-for-auth":
                try:
                    secret = os.getenv("SUPABASE_JWT_SECRET")
                    if secret:
                        payload = {
                            "aud": "authenticated",
                            "exp": int(time.time()) + 3600,
                            "sub": "e9821814-c159-42b7-8742-167812035978",
                            "email": "guide@reportpilot.com",
                            "role": "authenticated"
                        }
                        token = jwt.encode(payload, secret, algorithm="HS256")
                        logger.info("Generated dev JWT for Supabase storage")
                except Exception as e:
                    logger.error(f"Failed to sign dev token: {e}")

            try:
                # Create a temporary client with the user's token headers to bypass RLS via Auth
                active_client = create_client(
                    self.url, 
                    self.key, 
                    options=ClientOptions(headers={"Authorization": f"Bearer {token}"})
                )
            except Exception as e:
                logger.error(f"Failed to create scoped client: {e}")
                # Fallback to default client
                active_client = self.client

        try:
            # Generate path
            now = datetime.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")
            timestamp = int(time.time())
            
            # Sanitize filename
            filename = "".join(c for c in file.filename if c.isalnum() or c in "._-")
            file_path = f"{company_id}/{year}/{month}/{timestamp}_{filename}"
            
            # Read file content
            file_content = file.file.read()
            
            # Upload
            active_client.storage.from_(self.bucket).upload(
                file=file_content,
                path=file_path,
                file_options={"content-type": file.content_type}
            )
            
            # Get public URL (or signed URL if private)
            # For this implementation we assume private bucket and generate signed URLs on retrieval, 
            # but for simplicity in MVP we might use public URL if bucket is public.
            # Let's assume we want secure access:
            
            return {
                "storage_path": file_path,
                "bucket": self.bucket,
                "filename": filename,
                "content_type": file.content_type,
                "size": len(file_content)
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file to Supabase: {str(e)}")
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

    def upload_bytes(self, file_content: bytes, filename: str, content_type: str, company_id: str) -> dict:
        """Uploads raw bytes to Supabase Storage"""
        if not self.client:
            # Return Mock if no client
            return {"storage_path": f"local/{filename}", "file_url": f"/mock/{filename}"}

        try:
            # Generate path
            now = datetime.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")
            timestamp = int(time.time())
            
            # Sanitize filename
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            file_path = f"{company_id}/{year}/{month}/{timestamp}_{safe_filename}"
            
            # Upload
            self.client.storage.from_(self.bucket).upload(
                file=file_content,
                path=file_path,
                file_options={"content-type": content_type}
            )
            
            return {
                "storage_path": file_path,
                "bucket": self.bucket,
                "filename": safe_filename,
                "content_type": content_type,
                "size": len(file_content)
            }
        except Exception as e:
            logger.error(f"Failed to upload bytes to Supabase: {str(e)}")
            # Return mock on failure to avoid blocking flow
            return {"storage_path": f"failed_upload/{filename}", "error": str(e)}

    def get_system_client(self) -> Client:
        """Creates a client with service_role privileges for background tasks"""
        if not self.url or not self.key:
             return None
        
        try:
            secret = os.getenv("SUPABASE_JWT_SECRET")
            if not secret:
                logger.error("SUPABASE_JWT_SECRET not set, cannot create system client")
                return self.client

            payload = {
                "aud": "authenticated", 
                "exp": int(time.time()) + 3600,
                "sub": "system-worker",
                "role": "service_role"
            }
            token = jwt.encode(payload, secret, algorithm="HS256")
            
            return create_client(
                self.url,
                self.key,
                options=ClientOptions(headers={"Authorization": f"Bearer {token}"})
            )
        except Exception as e:
            logger.error(f"Failed to create system client: {e}")
            return self.client
            
    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Generates a signed URL for a file"""
        if not self.client:
            return ""
            
        try:
            response = self.client.storage.from_(self.bucket).create_signed_url(file_path, expires_in)
            # Supabase returns dict usually {'signedURL': '...'}
            if isinstance(response, dict) and "signedURL" in response:
                return response["signedURL"]
            return str(response)
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            return ""

    def delete_file(self, file_path: str) -> bool:
        """Deletes a file from storage"""
        if not self.client:
            return False
            
        try:
            self.client.storage.from_(self.bucket).remove([file_path])
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False

# Singleton instance
storage_service = SupabaseStorageService()
