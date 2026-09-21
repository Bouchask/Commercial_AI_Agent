from backend.database.connection import SessionLocal
from backend.models.service import Service
from backend.models.quote import Quote, QuoteItem
from backend.database.catalogue import seed_catalogue

db = SessionLocal()
try:
    print("Deleting all quote items...")
    db.query(QuoteItem).delete()
    print("Deleting all quotes...")
    db.query(Quote).delete()
    print(f"Deleting {db.query(Service).count()} existing services...")
    db.query(Service).delete()
    db.commit()
    print("Seeding new catalogue...")
    created = seed_catalogue(db)
    print(f"Catalogue seeded with {created} services.")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
