"""
app/routers/market.py

Public, read-only endpoints the frontend consumes instead of dummy data.
Everything served here is persisted by market_sync_service at startup /
on the scheduler interval - no live proxying, no seeded rows.
"""

from datetime import datetime, timedelta, date as date_cls
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    BrokerInfo,
    Company,
    DailyPrice,
    MarketIndexSnapshot,
    MarketStatus,
    NewsBulletinItem,
    TopTurnoverScrip,
)

router = APIRouter(prefix="/api/market", tags=["market"])


def _latest_trade_date(db: Session) -> Optional[datetime]:
    return db.query(sa_func.max(DailyPrice.date)).scalar()


def _serialize_index(row: MarketIndexSnapshot) -> dict:
    return {
        "index_name": row.index_name,
        "value": float(row.value) if row.value is not None else None,
        "point_change": float(row.point_change) if row.point_change is not None else None,
        "pct_change": float(row.pct_change) if row.pct_change is not None else None,
        "open": float(row.open_value) if row.open_value is not None else None,
        "high": float(row.high_value) if row.high_value is not None else None,
        "low": float(row.low_value) if row.low_value is not None else None,
        "prev_close": float(row.prev_close) if row.prev_close is not None else None,
        "turnover": float(row.turnover) if row.turnover is not None else None,
        "ceil": float(row.ceil) if row.ceil is not None else None,
        "floor": float(row.floor) if row.floor is not None else None,
        "business_date": row.business_date.strftime("%Y-%m-%d"),
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }


def _quote_row(price: DailyPrice) -> dict:
    prev = price.prev_close
    change_pct = (
        price.change_pct
        if price.change_pct is not None
        else (
            round((float(price.close_price) - float(prev)) / float(prev) * 100.0, 4)
            if prev
            else None
        )
    )
    point_change = float(price.close_price) - float(prev) if prev else None
    return {
        "price": float(price.close_price),
        "open": float(price.open_price),
        "high": float(price.high_price),
        "low": float(price.low_price),
        "prev_close": float(prev) if prev else None,
        "point_change": round(point_change, 2) if point_change is not None else None,
        "change_pct": float(change_pct) if change_pct is not None else None,
        "volume": int(price.volume or 0),
        "turnover": float(price.turnover) if price.turnover is not None else None,
        "transactions": int(price.transactions or 0),
        "date": price.date.strftime("%Y-%m-%d"),
    }


def _scrip_row(p: DailyPrice) -> dict:
    return {
        "company_id": p.company_id,
        "symbol": p.company.symbol if p.company else None,
        "name": p.company.name if p.company else None,
        "price": float(p.close_price),
        "prev_close": float(p.prev_close) if p.prev_close else None,
        "point_change": round(float(p.close_price) - float(p.prev_close), 2)
        if p.prev_close
        else None,
        "change_pct": float(p.change_pct) if p.change_pct is not None else None,
        "volume": int(p.volume or 0),
        "turnover": float(p.turnover) if p.turnover is not None else None,
    }


@router.get("/status")
def market_status(db: Session = Depends(get_db)):
    """Official market open/closed flag (mirrored from nepalstock.com.np)."""
    row = db.get(MarketStatus, 1)
    if row is None:
        return {
            "is_open": False,
            "is_open_raw": None,
            "as_of": None,
            "updated_at": None,
        }
    return {
        "is_open": row.is_open,
        "is_open_raw": row.is_open_raw,
        "as_of": row.as_of,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/indices")
def market_indices(
    history_days: int = Query(90, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Latest snapshot of every NEPSE index plus per-index history series
    (one entry per business date) for charting.
    """
    latest_dates = (
        db.query(
            MarketIndexSnapshot.index_name,
            sa_func.max(MarketIndexSnapshot.business_date).label("max_date"),
        )
        .group_by(MarketIndexSnapshot.index_name)
        .all()
    )
    name_to_latest = {name: d for name, d in latest_dates if d}

    cutoff = datetime.combine(date_cls.today(), datetime.min.time()) - timedelta(
        days=history_days
    )
    history_map: dict[str, list] = {}
    hist_rows = (
        db.query(MarketIndexSnapshot)
        .filter(MarketIndexSnapshot.business_date >= cutoff)
        .order_by(MarketIndexSnapshot.index_name, MarketIndexSnapshot.business_date)
        .all()
    )

    indices = []
    latest_set = {(n, d) for n, d in name_to_latest.items()}
    for row in hist_rows:
        entry = _serialize_index(row)
        history_map.setdefault(row.index_name, []).append(entry)
        if (row.index_name, row.business_date) in latest_set:
            indices.append(entry)

    return {"indices": indices, "history": history_map}


@router.get("/quotes")
def market_quotes(
    sparkline_days: int = Query(30, ge=2, le=90),
    db: Session = Depends(get_db),
):
    """
    One request powering Home/Companies: every tracked company with its
    latest quote + recent closes (for sparklines), straight from the DB.
    """
    companies = db.query(Company).order_by(Company.symbol).all()
    latest_sq = (
        db.query(DailyPrice.company_id, sa_func.max(DailyPrice.date).label("max_date"))
        .group_by(DailyPrice.company_id)
        .subquery()
    )
    quotes = (
        db.query(DailyPrice)
        .join(
            latest_sq,
            (DailyPrice.company_id == latest_sq.c.company_id)
            & (DailyPrice.date == latest_sq.c.max_date),
        )
        .options(joinedload(DailyPrice.company))
        .all()
    )
    by_company = {q.company_id: q for q in quotes}

    cutoff = datetime.combine(date_cls.today(), datetime.min.time()) - timedelta(
        days=sparkline_days
    )
    hist_rows = (
        db.query(
            DailyPrice.company_id,
            DailyPrice.date,
            DailyPrice.close_price,
            DailyPrice.volume,
        )
        .filter(DailyPrice.date >= cutoff)
        .order_by(DailyPrice.company_id, DailyPrice.date)
        .all()
    )
    history_map: dict[int, list] = {}
    for company_id, d, close, vol in hist_rows:
        history_map.setdefault(company_id, []).append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "close": float(close),
                "volume": int(vol or 0),
            }
        )

    out = []
    for c in companies:
        price = by_company.get(c.id)
        out.append(
            {
                "company_id": c.id,
                "symbol": c.symbol,
                "name": c.name,
                "sector": c.sector,
                "quote": _quote_row(price) if price else None,
                "history": history_map.get(c.id, []),
            }
        )
    return {"count": len(out), "quotes": out}


@router.get("/summary")
def market_summary(db: Session = Depends(get_db)):
    """
    Dashboard payload: status + headline indices + breadth + top movers +
    turnover/volume leaders, computed from synced daily prices.
    """
    trade_date = _latest_trade_date(db)

    status_row = db.get(MarketStatus, 1)
    status = {
        "is_open": bool(status_row.is_open) if status_row else False,
        "updated_at": (
            status_row.updated_at.isoformat()
            if status_row and status_row.updated_at
            else None
        ),
    }

    latest_idx_dates = (
        db.query(
            MarketIndexSnapshot.index_name,
            sa_func.max(MarketIndexSnapshot.business_date).label("md"),
        )
        .group_by(MarketIndexSnapshot.index_name)
        .subquery()
    )
    idx_rows = (
        db.query(MarketIndexSnapshot)
        .join(
            latest_idx_dates,
            (MarketIndexSnapshot.index_name == latest_idx_dates.c.index_name)
            & (MarketIndexSnapshot.business_date == latest_idx_dates.c.md),
        )
        .all()
    )
    indices = [_serialize_index(r) for r in idx_rows]

    gainers: list = []
    losers: list = []
    turnover_leaders: list = []
    volume_leaders: list = []
    advancers = decliners = unchanged = 0
    total_turnover = 0.0
    total_volume = 0

    if trade_date:
        day_prices = (
            db.query(DailyPrice)
            .filter(DailyPrice.date == trade_date)
            .options(joinedload(DailyPrice.company))
            .all()
        )
        with_change = [p for p in day_prices if p.prev_close]
        with_change.sort(
            key=lambda p: p.change_pct if p.change_pct is not None else -9999.0,
            reverse=True,
        )
        gainers = [_scrip_row(p) for p in with_change[:10]]
        losers = [_scrip_row(p) for p in reversed(with_change[-10:])]

        turnover_leaders = [
            _scrip_row(p)
            for p in sorted(
                day_prices, key=lambda p: float(p.turnover or 0), reverse=True
            )[:10]
        ]
        volume_leaders = [
            _scrip_row(p)
            for p in sorted(day_prices, key=lambda p: int(p.volume or 0), reverse=True)[
                :10
            ]
        ]

        advancers = sum(
            1 for p in with_change if float(p.close_price) > float(p.prev_close)
        )
        decliners = sum(
            1 for p in with_change if float(p.close_price) < float(p.prev_close)
        )
        unchanged = len(with_change) - advancers - decliners
        total_turnover = sum(float(p.turnover or 0) for p in day_prices)
        total_volume = sum(int(p.volume or 0) for p in day_prices)

    top_scrips = (
        db.query(TopTurnoverScrip)
        .order_by(TopTurnoverScrip.business_date.desc(), TopTurnoverScrip.rank)
        .limit(10)
        .all()
    )

    return {
        "status": status,
        "trade_date": trade_date.strftime("%Y-%m-%d") if trade_date else None,
        "indices": indices,
        "breadth": {
            "advancers": advancers,
            "decliners": decliners,
            "unchanged": unchanged,
            "total_turnover": round(total_turnover, 2),
            "total_volume": total_volume,
        },
        "gainers": gainers,
        "losers": losers,
        "turnover_leaders": turnover_leaders,
        "volume_leaders": volume_leaders,
        "official_top_turnover_scrips": [
            {
                "symbol": s.symbol,
                "ltp": float(s.ltp) if s.ltp is not None else None,
                "pct_change": float(s.pct_change) if s.pct_change is not None else None,
                "amount": float(s.amount) if s.amount is not None else None,
                "rank": s.rank,
                "business_date": s.business_date.strftime("%Y-%m-%d"),
            }
            for s in top_scrips
        ],
    }


@router.get("/news-bulletins")
def news_bulletins(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Official NEPSE market announcements."""
    rows = (
        db.query(NewsBulletinItem)
        .order_by(NewsBulletinItem.published_on.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "published_on": r.published_on.isoformat() if r.published_on else None,
            "source_url": r.source_url,
        }
        for r in rows
    ]


@router.get("/brokers")
def brokers(db: Session = Depends(get_db)):
    """NEPSE trading members (synced from the official /member endpoint)."""
    rows = db.query(BrokerInfo).order_by(BrokerInfo.broker_code).all()
    return [
        {
            "broker_code": r.broker_code,
            "name": r.name,
            "city": r.city,
        }
        for r in rows
    ]
