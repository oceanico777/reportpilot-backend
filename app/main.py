from fastapi import FastAPI
from .database import engine, Base
from .routers import receipts, reports, auth, exports

# Create tables
Base.metadata.create_all(bind=engine)

import os
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app = FastAPI(
    title="ReportPilot AI API",
    description="Automated Receipt Processing & Reporting API",
    version="0.1.0"
)

from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://reportpilot-frontend.vercel.app",
    "https://reportpilot-frontend-8g9q033ks-oceanicos-projects-d2fe019f.vercel.app",
]

# Allow all Vercel preview deployments
import re
def is_vercel_domain(origin):
    return re.match(r"https://.*\.vercel\.app$", origin) is not None

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(receipts.router, prefix="/receipts", tags=["Receipts"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(exports.router, prefix="/exports", tags=["Exports"])

@app.get("/")
def read_root():
    return {"message": "Welcome to ReportPilot AI API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
