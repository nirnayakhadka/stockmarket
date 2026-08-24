from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.models import Company
from app.schemas import CompanyResponse

# Add redirect_slashes=False to prevent automatic redirects
router = APIRouter(prefix="/api/companies", tags=["companies"], redirect_slashes=False)
logger = logging.getLogger(__name__)


@router.get("")  # No slash here - handles /api/companies
@router.get("/")  # Also handles /api/companies/
def get_companies(db: Session = Depends(get_db)):
    """Get all tracked companies"""
    print("=" * 60)
    print("🚀 GET /api/companies/ endpoint called!")
    try:
        companies = db.query(Company).all()
        print(f"📊 Found {len(companies)} companies in database")
        for c in companies:
            print(f"  - {c.id}: {c.symbol} - {c.name}")
        print("=" * 60)
        return companies
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    """Get a specific company by ID"""
    print(f"🚀 GET /api/companies/{company_id} called")
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            print(f"❌ Company {company_id} not found")
            raise HTTPException(status_code=404, detail="Company not found")
        print(f"✅ Found company: {company.symbol} - {company.name}")
        return company
    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))