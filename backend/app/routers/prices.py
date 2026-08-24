from datetime import datetime, timedelta, date as date_cls
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, DailyPrice, FloorsheetTransaction
from app.schemas import DailyPriceResponse

router = APIRouter(prefix="/api/companies", tags=["prices"])


@router.get("/{company_id}/prices", response_model=List[DailyPriceResponse])
def get_prices(
    company_id: int,
    range_days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get daily price data for a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    cutoff_date = datetime.now() - timedelta(days=range_days)
    prices = db.query(DailyPrice).filter(
        DailyPrice.company_id == company_id,
        DailyPrice.date >= cutoff_date
    ).order_by(DailyPrice.date).all()

    return prices


@router.get("/{company_id}/floorsheet")
def get_floorsheet(
    company_id: int,
    date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today"),
    db: Session = Depends(get_db),
):
    """
    Floorsheet transactions for a single day (per assignment section 1.2 /
    API surface: GET /api/companies/:id/floorsheet?date=). Data is populated
    by market_data_service.collect_floorsheet_data() — the official NEPSE
    floorsheet endpoint only exposes the CURRENT trading day, so historical
    dates will return an empty list unless that day was collected while it
    was live. See README for the honesty note on this limitation.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be in YYYY-MM-DD format")
    else:
        target_date = datetime.combine(date_cls.today(), datetime.min.time())

    rows = (
        db.query(FloorsheetTransaction)
        .filter(
            FloorsheetTransaction.company_id == company_id,
            FloorsheetTransaction.date == target_date,
        )
        .order_by(FloorsheetTransaction.id)
        .all()
    )

    return {
        "company_id": company_id,
        "symbol": company.symbol,
        "date": target_date.strftime("%Y-%m-%d"),
        "transaction_count": len(rows),
        "transactions": [
            {
                "id": r.id,
                "buyer_broker": r.buyer_broker,
                "seller_broker": r.seller_broker,
                "quantity": r.quantity,
                "rate": float(r.rate),
                "amount": float(r.amount) if r.amount is not None else None,
            }
            for r in rows
        ],
    }