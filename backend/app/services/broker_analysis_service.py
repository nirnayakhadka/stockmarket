"""
app/services/broker_analysis_service.py

Populates `broker_activity_summaries` from `floorsheet_transactions` —
this is the piece the assignment asks for under section 3: "the most
active buyer and seller brokers, and net buy/sell quantity per broker,
for the sampled days."

Computed once and stored (upsert on the existing unique constraint
company_id + date + broker_code), not recalculated per-request — matches
the architecture requirement to separate raw data from computed analysis.
"""

import logging
from datetime import datetime, date as date_cls
from collections import defaultdict

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Company, FloorsheetTransaction, BrokerActivitySummary

logger = logging.getLogger("broker_analysis_service")


def _upsert_broker_row(
    db: Session,
    company_id: int,
    trade_date: datetime,
    broker_code: str,
    buy_qty: int,
    sell_qty: int,
    buy_amount: float,
    sell_amount: float,
) -> None:
    existing = (
        db.query(BrokerActivitySummary)
        .filter(
            BrokerActivitySummary.company_id == company_id,
            BrokerActivitySummary.date == trade_date,
            BrokerActivitySummary.broker_code == broker_code,
        )
        .first()
    )

    net_qty = buy_qty - sell_qty

    if existing:
        existing.total_buy_quantity = buy_qty
        existing.total_sell_quantity = sell_qty
        existing.net_quantity = net_qty
        existing.total_buy_amount = buy_amount
        existing.total_sell_amount = sell_amount
    else:
        db.add(
            BrokerActivitySummary(
                company_id=company_id,
                date=trade_date,
                broker_code=broker_code,
                total_buy_quantity=buy_qty,
                total_sell_quantity=sell_qty,
                net_quantity=net_qty,
                total_buy_amount=buy_amount,
                total_sell_amount=sell_amount,
            )
        )
    db.commit()


def compute_broker_activity_for_company(
    db: Session, company_id: int, trade_date: datetime
) -> dict:
    """
    Aggregates floorsheet_transactions for one company on one date into
    per-broker buy/sell/net totals, and upserts into
    broker_activity_summaries. Returns a small summary dict for logging/
    API responses.
    """
    transactions = (
        db.query(FloorsheetTransaction)
        .filter(
            FloorsheetTransaction.company_id == company_id,
            FloorsheetTransaction.date == trade_date,
        )
        .all()
    )

    if not transactions:
        return {"company_id": company_id, "brokers": 0, "transactions": 0}

    # broker_code -> {buy_qty, sell_qty, buy_amount, sell_amount}
    stats: dict[str, dict] = defaultdict(lambda: {"buy_qty": 0, "sell_qty": 0, "buy_amt": 0.0, "sell_amt": 0.0})

    for t in transactions:
        amount = float(t.amount) if t.amount is not None else float(t.rate) * t.quantity

        stats[t.buyer_broker]["buy_qty"] += t.quantity
        stats[t.buyer_broker]["buy_amt"] += amount

        stats[t.seller_broker]["sell_qty"] += t.quantity
        stats[t.seller_broker]["sell_amt"] += amount

    for broker_code, s in stats.items():
        _upsert_broker_row(
            db,
            company_id=company_id,
            trade_date=trade_date,
            broker_code=broker_code,
            buy_qty=s["buy_qty"],
            sell_qty=s["sell_qty"],
            buy_amount=s["buy_amt"],
            sell_amount=s["sell_amt"],
        )

    return {"company_id": company_id, "brokers": len(stats), "transactions": len(transactions)}


def compute_broker_activity_all(trade_date: datetime | None = None) -> dict:
    """
    Entry point for the admin trigger / scheduler. Runs across every
    tracked company for the given date (defaults to today).
    """
    if trade_date is None:
        trade_date = datetime.combine(date_cls.today(), datetime.min.time())

    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        results = []
        for c in companies:
            result = compute_broker_activity_for_company(db, c.id, trade_date)
            if result["transactions"] > 0:
                results.append({**result, "symbol": c.symbol})

        logger.info(
            "Broker activity computed for %s: %d companies had floorsheet data",
            trade_date.strftime("%Y-%m-%d"), len(results),
        )
        return {"date": trade_date.strftime("%Y-%m-%d"), "companies_processed": len(results), "details": results}
    except Exception:
        logger.exception("Broker activity computation failed")
        return {"error": "computation failed, see server logs"}
    finally:
        db.close()


def get_broker_activity(db: Session, company_id: int, trade_date: datetime) -> dict:
    """
    Read path for the API endpoint — returns stored (precomputed) rows,
    sorted so most-active buyer/seller are easy to surface.
    """
    rows = (
        db.query(BrokerActivitySummary)
        .filter(
            BrokerActivitySummary.company_id == company_id,
            BrokerActivitySummary.date == trade_date,
        )
        .all()
    )

    brokers = [
        {
            "broker_code": r.broker_code,
            "buy_quantity": r.total_buy_quantity,
            "sell_quantity": r.total_sell_quantity,
            "net_quantity": r.net_quantity,
            "buy_amount": float(r.total_buy_amount) if r.total_buy_amount is not None else 0,
            "sell_amount": float(r.total_sell_amount) if r.total_sell_amount is not None else 0,
        }
        for r in rows
    ]

    most_active_buyer = max(brokers, key=lambda b: b["buy_quantity"], default=None)
    most_active_seller = max(brokers, key=lambda b: b["sell_quantity"], default=None)

    return {
        "date": trade_date.strftime("%Y-%m-%d"),
        "broker_count": len(brokers),
        "most_active_buyer": most_active_buyer,
        "most_active_seller": most_active_seller,
        "brokers": sorted(brokers, key=lambda b: b["buy_quantity"] + b["sell_quantity"], reverse=True),
    }