from app.database import SessionLocal
from app import models
import sys
import os

print(f"Check script running from: {os.getcwd()}")
db = SessionLocal()
count = db.query(models.Report).count()
print(f"Total Reports in DB: {count}")

reports = db.query(models.Report).limit(5).all()
for r in reports:
    print(f"- {r.tour_id}: {r.category} ({r.amount})")
