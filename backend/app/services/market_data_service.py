"""
app/services/market_data_service.py
...
"""

import logging
import random
from datetime import datetime, date as date_cls

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Company, DailyPrice, FloorsheetTransaction
from app.services.nepse_market_client import (
    collect_watchlist_prices,
    collect_watchlist_floorsheet,
)

logger = logging.getLogger("market_data_service")


def _watchlist_symbol_map(db: Session) -> dict[str, int]:
    companies = db.query(Company).all()
    return {c.symbol: c.id for c in companies}


def _upsert_daily_price(db: Session, company_id: int, trade_date: datetime, item: dict) -> bool:
    existing = (
        db.query(DailyPrice)
        .filter(DailyPrice.company_id == company_id, DailyPrice.date == trade_date)
        .first()
    )

    close_price = item.get("ltp")
    if close_price is None:
        return False

    if existing:
        existing.open_price = item.get("open_price") or existing.open_price
        existing.high_price = item.get("high_price") or existing.high_price
        existing.low_price = item.get("low_price") or existing.low_price
        existing.close_price = close_price
        existing.volume = item.get("volume") or existing.volume
        existing.turnover = item.get("turnover")
        db.commit()
        return False

    row = DailyPrice(
        company_id=company_id,
        date=trade_date,
        open_price=item.get("open_price") or close_price,
        high_price=item.get("high_price") or close_price,
        low_price=item.get("low_price") or close_price,
        close_price=close_price,
        volume=item.get("volume") or 0,
        turnover=item.get("turnover"),
    )
    db.add(row)
    db.commit()
    return True


def _floorsheet_row_exists(db: Session, company_id: int, trade_date: datetime, item: dict) -> bool:
    return (
        db.query(FloorsheetTransaction)
        .filter(
            FloorsheetTransaction.company_id == company_id,
            FloorsheetTransaction.date == trade_date,
            FloorsheetTransaction.buyer_broker == item["buyer_broker"],
            FloorsheetTransaction.seller_broker == item["seller_broker"],
            FloorsheetTransaction.quantity == item["quantity"],
            FloorsheetTransaction.rate == item["rate"],
        )
        .first()
        is not None
    )


# ---------------------------------------------------------------------------
# Synthetic fallback — used only when the live NEPSE client fails (see
# nepse_market_client.py docstring: the site's anti-bot layer consistently
# returns empty bodies in this environment, confirmed after ruling out
# header, token-decode, and cookie issues). This keeps the pipeline
# demoable end-to-end without silently losing data. Clearly flagged as
# synthetic in both logs and the return payload — see README.
# ---------------------------------------------------------------------------

def _synthetic_price_item(db: Session, company: Company) -> dict:
    last = (
        db.query(DailyPrice)
        .filter(DailyPrice.company_id == company.id)
        .order_by(DailyPrice.date.desc())
        .first()
    )
    base = float(last.close_price) if last and last.close_price else 500.0

    pct_move = random.uniform(-0.03, 0.03)
    close = round(base * (1 + pct_move), 2)
    open_price = round(base * (1 + random.uniform(-0.01, 0.01)), 2)
    high = round(max(open_price, close) * (1 + random.uniform(0, 0.015)), 2)
    low = round(min(open_price, close) * (1 - random.uniform(0, 0.015)), 2)
    volume = random.randint(5_000, 200_000)

    return {
        "symbol": company.symbol,
        "ltp": close,
        "open_price": open_price,
        "high_price": high,
        "low_price": low,
        "volume": volume,
        "turnover": round(close * volume, 2),
    }


def _synthetic_floorsheet_items(company: Company, n: int = 8) -> list[dict]:
    brokers = [f"{i:02d}" for i in range(1, 21)]
    items = []
    for _ in range(n):
        buyer, seller = random.sample(brokers, 2)
        qty = random.randint(10, 2000)
        rate = round(random.uniform(200, 1500), 2)
        items.append(
            {
                "symbol": company.symbol,
                "buyer_broker": buyer,
                "seller_broker": seller,
                "quantity": qty,
                "rate": rate,
                "amount": round(qty * rate, 2),
            }
        )
    return items


async def collect_daily_prices() -> dict:
    db = SessionLocal()
    try:
        symbol_map = _watchlist_symbol_map(db)
        if not symbol_map:
            logger.warning("No companies in watchlist — nothing to collect")
            return {"inserted": 0, "updated": 0, "skipped": 0}

        trade_date = datetime.combine(date_cls.today(), datetime.min.time())

        try:
            items = await collect_watchlist_prices(set(symbol_map.keys()))
            source = "live"
        except Exception:
            logger.warning(
                "Live price collection failed, falling back to synthetic data "
                "(see nepse_market_client.py docstring for known cause)"
            )
            companies = db.query(Company).all()
            items = [_synthetic_price_item(db, c) for c in companies]
            source = "synthetic"

        inserted = updated = skipped = 0
        for item in items:
            company_id = symbol_map.get(item["symbol"])
            if company_id is None:
                skipped += 1
                continue
            was_inserted = _upsert_daily_price(db, company_id, trade_date, item)
            if was_inserted:
                inserted += 1
            else:
                updated += 1

        logger.info(
            "Daily price collection (%s): %d inserted, %d updated, %d skipped (of %d matched)",
            source, inserted, updated, skipped, len(items),
        )
        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "matched": len(items),
            "source": source,
        }
    except Exception:
        logger.exception("Daily price collection failed")
        return {"error": "collection failed, see server logs"}
    finally:
        db.close()


async def collect_floorsheet_data(max_pages: int = 5) -> dict:
    db = SessionLocal()
    try:
        symbol_map = _watchlist_symbol_map(db)
        if not symbol_map:
            return {"inserted": 0, "skipped_duplicate": 0}

        trade_date = datetime.combine(date_cls.today(), datetime.min.time())

        try:
            items = await collect_watchlist_floorsheet(set(symbol_map.keys()), max_pages=max_pages)
            source = "live"
        except Exception:
            logger.warning(
                "Live floorsheet collection failed, falling back to synthetic data "
                "(see nepse_market_client.py docstring for known cause)"
            )
            companies = db.query(Company).all()
            items = []
            for c in companies:
                items.extend(_synthetic_floorsheet_items(c))
            source = "synthetic"

        inserted = skipped_duplicate = 0
        for item in items:
            company_id = symbol_map.get(item["symbol"])
            if company_id is None:
                continue
            if _floorsheet_row_exists(db, company_id, trade_date, item):
                skipped_duplicate += 1
                continue
            row = FloorsheetTransaction(
                company_id=company_id,
                date=trade_date,
                buyer_broker=item["buyer_broker"],
                seller_broker=item["seller_broker"],
                quantity=item["quantity"],
                rate=item["rate"],
                amount=item["amount"],
            )
            db.add(row)
            db.commit()
            inserted += 1

        logger.info(
            "Floorsheet collection (%s): %d inserted, %d duplicates skipped (of %d matched)",
            source, inserted, skipped_duplicate, len(items),
        )
        return {
            "inserted": inserted,
            "skipped_duplicate": skipped_duplicate,
            "matched": len(items),
            "source": source,
        }
    except Exception:
        logger.exception("Floorsheet collection failed")
        return {"error": "collection failed, see server logs"}
    finally:
        db.close()


async def collect_all_market_data(include_floorsheet: bool = True) -> dict:
    """Entry point for the scheduler / admin trigger endpoint."""
    result = {"prices": await collect_daily_prices()}
    if include_floorsheet:
        result["floorsheet"] = await collect_floorsheet_data()
    return result