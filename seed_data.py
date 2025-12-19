import random
from datetime import datetime, timedelta
import uuid
from app.database import SessionLocal, engine
from app import models

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    
    print("🌱 Seeding data for Bogotá Tours...")

    # 1. Get or Create Demo Company (Using the HARDCODED ID from auth.py to ensure frontend visibility)
    # ID from auth.py: e9821814-c159-42b7-8742-167812035978
    user_id = "e9821814-c159-42b7-8742-167812035978"
    user_email = "guide@reportpilot.com"

    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        user = models.User(id=user_id, email=user_email, full_name="Report Pilot Guide")
        db.add(user)
        db.commit()
    
    company = db.query(models.Company).filter(models.Company.user_id == user.id).first()
    if not company:
        company = models.Company(id=str(uuid.uuid4()), user_id=user.id, name="Bogotá Travel Experts")
        db.add(company)
        db.commit()

    cid = company.id
    print(f"🏢 Using Company: {company.name} (User: {user.email}) Company ID: {cid}")

    # CLEAN UP OLD DATA FOR THIS COMPANY
    # We delete anything linked to this company to remove "Food", "Entertainment" etc.
    deleted = db.query(models.Report).filter(models.Report.company_id == cid).delete()
    db.commit()
    print(f"🧹 Cleared {deleted} old reports to ensure clean categories.")

    # 2. Define Tour Templates (Bogotá Specific)
    tours = [
        {
            "name": "Tour a Monserrate",
            "expenses": [
                ("💰 Anticipo de Caja", 300000, "ANTICIPO_RECIBIDO"), # Advance!
                ("Teleférico Tiquetes", 29000, "📦 Otros"),
                ("Guía Privado", 80000, "Atractivos"),
                ("Refrigerio Tamal", 35000, "Comida"),
                ("Transporte Hotel-Cerro", 45000, "📦 Otros")
            ]
        },
        {
            "name": "Tour La Candelaria",
            "expenses": [
                ("💰 Anticipo de Caja", 250000, "ANTICIPO_RECIBIDO"),
                ("Entrada Museo Oro", 5000, "Atractivos"),
                ("Guía Histórico", 120000, "Atractivos"),
                ("Chicha en el Chorro", 15000, "Snacks"),
                ("Almuerzo Ajiaco", 45000, "Comida")
            ]
        },
        {
            "name": "Tour de Graffiti",
            "expenses": [
                 ("💰 Anticipo de Caja", 400000, "ANTICIPO_RECIBIDO"),
                 ("💵 Venta Souvenir", 50000, "RECAUDO_CLIENTE"), # New!
                ("Aporte Artista Local", 50000, "Atractivos"),
                ("Guía Urbano", 90000, "Atractivos"),
                ("Kit de Aerosoles Taller", 60000, "Materiales"), 
                ("Refrigerio Frutas", 20000, "Snacks")
            ]
        },
        {
            "name": "Cata de Café",
            "expenses": [
                ("💰 Anticipo de Caja", 350000, "ANTICIPO_RECIBIDO"),
                ("💵 Venta Café Grano", 120000, "RECAUDO_CLIENTE"), # New!
                ("Experiencia Barista", 150000, "Atractivos"),
                ("Muestras de Café", 80000, "Snacks"),
                ("Maridaje Postres", 40000, "Snacks"),
                ("Certificado Asistencia", 10000, "Atractivos")
            ]
        },
        {
            "name": "Tour Centro Histórico",
             "expenses": [
                ("💰 Recarga Anticipo", 150000, "ANTICIPO_RECIBIDO"),
                ("💵 Upgrade Privado", 80000, "RECAUDO_CLIENTE"), # New!
                ("Entrada Museo Botero", 0, "Atractivos"),
                ("Guía Cultural", 100000, "Atractivos"),
                ("Oblea callejera", 12000, "Snacks"),
                ("Taxi Regreso", 25000, "📦 Otros")
            ]
        }
    ]

    # 3. Generate History (Last 3 months)
    reports_created = 0

    for _ in range(3): # Simulate 3 months of activity
        for tour in tours:
            # Simulate 2-3 instances of each tour per "batch"
            for i in range(random.randint(2, 4)):
                
                # Tour Date (Random in last 90 days)
                days_ago = random.randint(1, 90)
                tour_date = datetime.now() - timedelta(days=days_ago)
                
                # Create expenses for this specific tour instance
                for item_name, base_price, category in tour["expenses"]:
                    # Advances/Collections usually rounded and specific
                    if category == "ANTICIPO_RECIBIDO":
                        final_price = base_price
                        vendor_name = "Tesorería Agencia"
                    elif category == "RECAUDO_CLIENTE":
                        final_price = base_price
                        vendor_name = "Cliente Directo"
                    else:
                        # Add some variance to price (+- 10%)
                        variance = random.uniform(0.9, 1.1)
                        final_price = round(base_price * variance, -2) # Round to nearest 100
                        vendor_name = f"Proveedor {item_name.split()[0]}"

                    report = models.Report(
                        id=str(uuid.uuid4()),
                        company_id=cid,
                        month=tour_date.month,
                        year=tour_date.year,
                        tour_id=tour["name"], # Grouping ID
                        client_name=f"Familia {random.choice(['González', 'Smith', 'Pérez', 'Müller', 'Takahashi'])}",
                        vendor=vendor_name,
                        amount=final_price,
                        currency="COP",
                        category=category,
                        summary_text=f"{item_name} para {tour['name']}",
                        status="PROCESSED",
                        created_at=tour_date
                    )
                    db.add(report)
                    reports_created += 1

    db.commit()
    print(f"✅ Successfully seeded {reports_created} reports (Includes ANTICIPOS)!")
    print("   Refresh the app to see the data.")

if __name__ == "__main__":
    seed()
