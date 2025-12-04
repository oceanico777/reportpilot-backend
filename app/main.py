from fastapi import FastAPI
from .database import engine, Base
from .routers import receipts, reports, auth

# Create tables
Base.metadata.create_all(bind=engine)

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
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(receipts.router, prefix="/receipts", tags=["Receipts"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])

@app.get("/")
def read_root():
    return {"message": "Welcome to ReportPilot AI API"}
