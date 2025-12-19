from fastapi import FastAPI, Request
from .database import engine, Base
from .routers import receipts, reports, auth, exports, users, budgets, tours
import time
import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from .services.logging_config import setup_logging

# Setup Logging
logger = setup_logging()

# Setup Sentry
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "development")
    )

# Create tables
Base.metadata.create_all(bind=engine)

import os
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app = FastAPI(
    title="ReportPilot AI API",
    description="""
    ## 🚀 Automated Receipt Processing & Reporting API
    
    ### Features
    - 📸 OCR receipt processing with Google Gemini AI
    - 📊 Automated expense report generation
    - 🔐 Multi-tenant with company-level isolation
    - 📁 Secure file storage with Supabase
    
    ### Authentication
    All endpoints (except `/health`) require Bearer token authentication.
    Use your Supabase JWT token in the Authorization header.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

from fastapi.middleware.cors import CORSMiddleware


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get("origin")
    print(f"DEBUG: Incoming {request.method} request to {request.url.path} from origin: {origin}")
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info("request_completed", extra={
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 2)
    })
    return response

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(receipts.router, prefix="/receipts", tags=["Receipts"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(exports.router, prefix="/exports", tags=["Exports"])
app.include_router(users.router, tags=["Users"])
app.include_router(budgets.router, prefix="/budgets", tags=["Budgets"])
app.include_router(tours.router, tags=["Tours"])

@app.get("/")
def read_root():
    return {"message": "Welcome to ReportPilot AI API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
