"""
app/routers/broker_activity.py

  - POST /api/admin/analysis/compute-broker-activity  (admin-only trigger)
  - GET  /api/companies/{id}/broker-activity?date=     (read, any logged-in role)
"""

from datetime import datetime, date as date_cls
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company
from app.auth_dependencies import require_role
from app.services.broker_analysis_service import compute_broker_activity_all, get_broker_activity

router = APIRouter(tags=["analysis"])


@router.post("/api/admin/analysis/compute-broker-activity", dependencies=[Depends(require_role("admin"))])
def trigger_broker_activity_computation(date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today")):
    """
    Aggregates today's (or a given date's) floorsheet_transactions into
    broker_activity_summaries for every tracked company. Run this after
    collecting floorsheet data (see market_data_admin.collect), or wire
    it into the scheduler right after collect_floorsheet_data().
    """
    if date:
        try:
            trade_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        trade_date = None

    return compute_broker_activity_all(trade_date)


@router.get(
    "/api/companies/{company_id}/broker-activity",
    dependencies=[Depends(require_role("admin", "analyst", "viewer"))],
)
def read_broker_activity(
    company_id: int,
    date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today"),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if date:
        try:
            trade_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        trade_date = datetime.combine(date_cls.today(), datetime.min.time())

    result = get_broker_activity(db, company_id, trade_date)
    result["company_id"] = company_id
    result["symbol"] = company.symbol
    return result