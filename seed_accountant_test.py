from backend.app.database import SessionLocal
from backend.app import models
import uuid

def seed_test():
    db = SessionLocal()
    try:
        # 1. Get a company or create a test one
        company = db.query(models.Company).first()
        if not company:
            # Create a company if none exists
            company = models.Company(name="Test Org", id="test-company-123")
            db.add(company)
            db.commit()
            db.refresh(company)
        
        company_id = company.id
        tour_id = "TOUR-VERIFICACION-001"
        
        # 2. Assign some budget (Anticipo)
        # Category 'TOTAL' is used by the logic to represent the main fund
        existing_budget = db.query(models.TourBudget).filter(
            models.TourBudget.tour_id == tour_id,
            models.TourBudget.company_id == company_id,
            models.TourBudget.category == "TOTAL"
        ).first()
        
        if existing_budget:
            existing_budget.budget_amount = 500000.0
        else:
            new_budget = models.TourBudget(
                tour_id=tour_id,
                company_id=company_id,
                category="TOTAL",
                budget_amount=500000.0
            )
            db.add(new_budget)
        
        # 3. Create a Report (Gasto) of 50.000 for that tour
        new_report = models.Report(
            company_id=company_id,
            tour_id=tour_id,
            client_name="Prueba de Auditoría",
            vendor="Restaurante Test",
            amount=50000.0,
            currency="COP",
            category="🍽️ Restaurante",
            month=12,
            year=2025,
            status=models.ReportStatus.APPROVED.value, # Approved gasto
            summary_text="Gasto de prueba de 50k"
        )
        db.add(new_report)
        
        db.commit()
        print(f"Success! Data seeded for {tour_id}")
        print(f"Anticipo: 500,000 | Gasto: 50,000 | Diferencia esperada: 450,000")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_test()
