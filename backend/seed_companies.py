import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Company

# List of 10 NEPSE companies across sectors
companies_data = [
    # Banking
    {"symbol": "NABIL", "name": "Nabil Bank Limited", "sector": "Banking"},
    {"symbol": "NICA", "name": "NIC Asia Bank Limited", "sector": "Banking"},
    {"symbol": "GBIME", "name": "Global IME Bank Limited", "sector": "Banking"},
    
    # Insurance
    {"symbol": "NLIC", "name": "Nepal Life Insurance Company", "sector": "Insurance"},
    {"symbol": "SIC", "name": "Siddhartha Insurance Company", "sector": "Insurance"},
    
    # Hydropower
    {"symbol": "CHCL", "name": "Chilime Hydropower Company", "sector": "Hydropower"},
    {"symbol": "SHPC", "name": "Sanima Mai Hydropower", "sector": "Hydropower"},
    
    # Manufacturing
    {"symbol": "HDL", "name": "Himalayan Distillery Limited", "sector": "Manufacturing"},
    {"symbol": "UNL", "name": "Unilever Nepal Limited", "sector": "Manufacturing"},
    
    # Hotels & Tourism
    {"symbol": "SHL", "name": "Soaltee Hotel Limited", "sector": "Hotels & Tourism"},
]

def seed_companies():
    db = SessionLocal()
    try:
        # Clear existing companies
        db.query(Company).delete()
        db.commit()
        
        # Insert companies
        for data in companies_data:
            company = Company(**data)
            db.add(company)
        
        db.commit()
        print(f"✅ Added {len(companies_data)} companies to database")
        
        # Verify
        companies = db.query(Company).all()
        print("\n📋 Companies in database:")
        for c in companies:
            print(f"  - {c.symbol}: {c.name} ({c.sector})")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_companies()
