
import logging
from datetime import datetime, date as date_cls
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import SessionLocal
from app.services.nepse_market_client import NepseMarketClientSync
from app.models import (
    BrokerInfo,
    Company,
    DailyPrice,
    FloorsheetTransaction,
    MarketIndexSnapshot,
    MarketStatus,
    NewsBulletinItem,
    TopTurnoverScrip,
)

logger = logging.getLogger("market_sync")


def _parse_date(value) -> Optional[datetime]:
    """Parse date from various formats."""
    if value is None:
        return None
    text_value = str(value).strip().split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text_value, fmt)
        except ValueError:
            continue
    return None


def _parse_datetime(value) -> Optional[datetime]:
    """Parse datetime from various formats."""
    parsed = _parse_date(value)
    if parsed is not None:
        return parsed
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except (ValueError, TypeError):
            continue
    return None


def _sync_status(db: Session, client: NepseMarketClientSync) -> str:
    """Sync market status."""
    try:
        status = client.fetch_market_open()
        row = db.get(MarketStatus, 1)
        if row is None:
            row = MarketStatus(id=1)
            db.add(row)
        row.is_open = bool(status.get("is_open", False))
        row.is_open_raw = status.get("is_open_raw", "CLOSE")
        row.as_of = status.get("as_of")
        row.updated_at = datetime.utcnow()
        db.commit()
        return f"open={row.is_open} ({row.is_open_raw})"
    except Exception as e:
        db.rollback()
        logger.error(f"Market status sync failed: {e}")
        raise


def _sync_companies(db: Session, client: NepseMarketClientSync) -> str:
    """Sync companies from listed securities."""
    try:
        securities = client.fetch_listed_securities()
        existing = {c.symbol: c for c in db.query(Company).all()}
        created = renamed = 0
        
        for sec in securities:
            symbol = sec.get("symbol")
            if not symbol or str(symbol).isdigit():
                continue
                
            # Clean symbol
            symbol = symbol.strip().upper()
            
            company = existing.get(symbol)
            if company is None:
                db.add(Company(
                    symbol=symbol, 
                    name=sec.get("name", symbol),
                ))
                created += 1
            elif company.name != sec.get("name", symbol):
                company.name = sec.get("name", symbol)
                renamed += 1
                
        db.commit()
        return f"{len(securities)} securities: {created} new, {renamed} renamed"
    except Exception as e:
        db.rollback()
        logger.error(f"Companies sync failed: {e}")
        raise


def _upsert_daily_price(
    db: Session, company_id: int, trade_date: datetime, item: dict
) -> bool:
    """Upsert daily price record."""
    close_price = item.get("ltp")
    if close_price is None:
        return False

    prev_close = item.get("prev_close")
    change_pct = None
    if prev_close:
        try:
            change_pct = round(
                (float(close_price) - float(prev_close)) / float(prev_close) * 100.0, 4
            )
        except (TypeError, ZeroDivisionError):
            change_pct = None

    existing = (
        db.query(DailyPrice)
        .filter(DailyPrice.company_id == company_id, DailyPrice.date == trade_date)
        .first()
    )
    
    if existing:
        existing.open_price = item.get("open_price") or existing.open_price or close_price
        existing.high_price = item.get("high_price") or existing.high_price or close_price
        existing.low_price = item.get("low_price") or existing.low_price or close_price
        existing.close_price = close_price
        existing.prev_close = prev_close
        existing.change_pct = change_pct
        existing.transactions = item.get("transactions")
        existing.volume = item.get("volume") or existing.volume or 0
        existing.turnover = item.get("turnover")
        return False

    db.add(
        DailyPrice(
            company_id=company_id,
            date=trade_date,
            open_price=item.get("open_price") or close_price,
            high_price=item.get("high_price") or close_price,
            low_price=item.get("low_price") or close_price,
            close_price=close_price,
            prev_close=prev_close,
            change_pct=change_pct,
            transactions=item.get("transactions"),
            volume=item.get("volume") or 0,
            turnover=item.get("turnover"),
        )
    )
    return True


def _sync_prices(db: Session, client: NepseMarketClientSync) -> str:
    """Sync today's prices."""
    try:
        items = client.fetch_today_price()
        
        # Log what symbols we got
        if items:
            symbols = [item.get("symbol") for item in items[:10] if item.get("symbol")]
            logger.info(f"Price symbols from data: {symbols}")
        
        # Get all companies
        companies = db.query(Company).all()
        symbol_map = {c.symbol.upper(): c.id for c in companies}
        
        # Create companies from price data if they don't exist
        created_count = 0
        for item in items:
            symbol = item.get("symbol")
            if not symbol or str(symbol).isdigit():
                continue
                
            clean_symbol = symbol.strip().upper()
            
            # Check if company already exists (case-insensitive)
            if clean_symbol not in symbol_map:
                try:
                    # Try to create the company
                    new_company = Company(symbol=clean_symbol, name=clean_symbol)
                    db.add(new_company)
                    db.flush()  # Get the ID
                    symbol_map[clean_symbol] = new_company.id
                    created_count += 1
                    logger.debug(f"Created company: {clean_symbol}")
                except IntegrityError:
                    # Company was created by another process or already exists
                    db.rollback()
                    # Refresh the symbol map
                    companies = db.query(Company).all()
                    symbol_map = {c.symbol.upper(): c.id for c in companies}
                    # Check again
                    if clean_symbol in symbol_map:
                        logger.debug(f"Company {clean_symbol} already exists (created by another process)")
                    else:
                        logger.warning(f"Could not create company {clean_symbol}")
                except Exception as e:
                    logger.warning(f"Could not create company {clean_symbol}: {e}")
                    db.rollback()
        
        # Commit any created companies
        if created_count > 0:
            db.commit()
            # Refresh symbol map
            companies = db.query(Company).all()
            symbol_map = {c.symbol.upper(): c.id for c in companies}
            logger.info(f"✅ Created {created_count} new companies from price data")
        
        # If still no companies, we can't sync
        if not symbol_map:
            logger.warning("No companies found in database, cannot sync prices")
            return "0 scrips: 0 inserted, 0 updated, 0 skipped (no companies)"
        
        trade_date = datetime.combine(date_cls.today(), datetime.min.time())
        inserted = updated = unmatched = skipped = 0
        
        for item in items:
            symbol = item.get("symbol")
            if not symbol or str(symbol).isdigit():
                skipped += 1
                continue
            
            clean_symbol = symbol.strip().upper()
            company_id = symbol_map.get(clean_symbol)
                
            if company_id is None:
                # Try to create the company one more time
                try:
                    new_company = Company(symbol=clean_symbol, name=clean_symbol)
                    db.add(new_company)
                    db.flush()
                    symbol_map[clean_symbol] = new_company.id
                    company_id = new_company.id
                    created_count += 1
                except IntegrityError:
                    db.rollback()
                    # Refresh and check again
                    companies = db.query(Company).all()
                    symbol_map = {c.symbol.upper(): c.id for c in companies}
                    company_id = symbol_map.get(clean_symbol)
                    if company_id is None:
                        unmatched += 1
                        continue
                except Exception as e:
                    logger.warning(f"Could not create company {clean_symbol}: {e}")
                    unmatched += 1
                    continue
                
            if item.get("ltp") is None:
                skipped += 1
                continue
                
            if _upsert_daily_price(db, company_id, trade_date, item):
                inserted += 1
            else:
                updated += 1
                
        db.commit()
        
        if created_count > 0:
            logger.info(f"✅ Created {created_count} total companies during price sync")

        # Backfill prev_close/change_pct from history
        for row in db.query(DailyPrice).filter(DailyPrice.date == trade_date).all():
            if row.prev_close is not None:
                continue
            prev = (
                db.query(DailyPrice)
                .filter(
                    DailyPrice.company_id == row.company_id,
                    DailyPrice.date < trade_date,
                )
                .order_by(DailyPrice.date.desc())
                .first()
            )
            if prev and prev.close_price:
                row.prev_close = prev.close_price
                try:
                    row.change_pct = round(
                        (float(row.close_price) - float(prev.close_price))
                        / float(prev.close_price) * 100.0,
                        4,
                    )
                except ZeroDivisionError:
                    pass
                    
        db.commit()
        return (
            f"{len(items)} scrips: {inserted} inserted, {updated} updated, "
            f"{skipped} skipped, {unmatched} unmatched"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Prices sync failed: {e}")
        raise


def _upsert_index_snapshot(
    db: Session,
    name: str,
    business_date: datetime,
    values: dict,
) -> bool:
    """Upsert index snapshot."""
    snapshot = (
        db.query(MarketIndexSnapshot)
        .filter(
            MarketIndexSnapshot.index_name == name,
            MarketIndexSnapshot.business_date == business_date,
        )
        .one_or_none()
    )
    
    if snapshot is None:
        snapshot = MarketIndexSnapshot(index_name=name, business_date=business_date)
        db.add(snapshot)
        
    changed = False
    for field, key in (
        ("value", "value"),
        ("point_change", "point_change"),
        ("pct_change", "pct_change"),
        ("open_value", "open_value"),
        ("high_value", "high_value"),
        ("low_value", "low_value"),
        ("prev_close", "prev_close"),
        ("turnover", "turnover"),
        ("ceil", "ceil"),
        ("floor", "floor"),
    ):
        if values.get(key) is not None and getattr(snapshot, field) != values[key]:
            setattr(snapshot, field, values[key])
            changed = True
            
    snapshot.captured_at = datetime.utcnow()
    return changed


def _sync_indices(db: Session, client: NepseMarketClientSync) -> str:
    """Sync indices data."""
    try:
        # Get index bounds
        ceil_floor = {}
        try:
            ceil_floor = client.fetch_index_ceil_floor()
        except Exception as e:
            logger.info("index-ceil-floor unavailable: %s", e)

        # Get indices
        indices = client.fetch_indices()
        default_bd = datetime.combine(date_cls.today(), datetime.min.time())
        written = 0
        
        for idx in indices:
            if not idx.get("name"):
                continue
                
            business_date = _parse_date(idx.get("business_date")) or default_bd
            bounds = ceil_floor.get(idx["name"], {})
            values = {
                "value": idx.get("value"),
                "point_change": idx.get("point_change"),
                "pct_change": idx.get("pct_change"),
                "open_value": idx.get("open"),
                "high_value": idx.get("high"),
                "low_value": idx.get("low"),
                "prev_close": idx.get("prev_close"),
                "turnover": idx.get("turnover"),
                "ceil": bounds.get("ceil"),
                "floor": bounds.get("floor"),
            }
            if _upsert_index_snapshot(db, idx["name"], business_date, values):
                written += 1
                
        db.commit()

        # History backfill
        try:
            history = client.fetch_nepse_price_history()
            backfilled = 0
            for row in history:
                bd = _parse_date(row.get("business_date"))
                if bd is None or row.get("value") is None:
                    continue
                    
                existing = (
                    db.query(MarketIndexSnapshot.id)
                    .filter(
                        MarketIndexSnapshot.index_name == row.get("name", "NEPSE Index"),
                        MarketIndexSnapshot.business_date == bd,
                    )
                    .first()
                )
                if existing:
                    continue
                    
                db.add(
                    MarketIndexSnapshot(
                        index_name=row.get("name", "NEPSE Index"),
                        value=row.get("value"),
                        point_change=row.get("point_change"),
                        turnover=row.get("turnover"),
                        business_date=bd,
                        captured_at=datetime.utcnow(),
                    )
                )
                backfilled += 1
                
            db.commit()
        except Exception as e:
            logger.warning("nepse-price history backfill failed: %s", e)
            backfilled = 0

        return f"{written} index snapshots updated, {backfilled} history rows added"
    except Exception as e:
        db.rollback()
        logger.error(f"Indices sync failed: {e}")
        raise


def _sync_top_scrips(db: Session, client: NepseMarketClientSync) -> str:
    """Sync top turnover scrips."""
    try:
        scrips = client.fetch_top_ten_turnover_scrips()
        today = datetime.combine(date_cls.today(), datetime.min.time())
        seen = 0
        skipped = 0
        updated = 0
        
        # Get all companies for symbol lookup
        companies = db.query(Company).all()
        symbol_map = {c.id: c.symbol for c in companies}
        symbol_lookup = {c.symbol.upper(): c.id for c in companies}
        
        # Track processed symbols to avoid duplicates in this batch
        processed_symbols = set()
        
        for i, s in enumerate(scrips):
            rank = s.get("rank") or (i + 1)
            symbol = s.get("symbol")
            
            # Skip invalid symbols
            if not symbol:
                skipped += 1
                continue
                
            # If symbol is a number string, try to find actual symbol from company list
            if str(symbol).isdigit():
                company_id = int(symbol)
                if company_id in symbol_map:
                    symbol = symbol_map[company_id]
                else:
                    skipped += 1
                    continue
            
            # Clean symbol
            clean_symbol = str(symbol).strip().upper()
            
            # Skip if symbol is still numeric or empty
            if not clean_symbol or clean_symbol.isdigit():
                skipped += 1
                continue
            
            # Skip duplicates in this batch
            if clean_symbol in processed_symbols:
                skipped += 1
                continue
            processed_symbols.add(clean_symbol)
                
            # Check if already exists for today
            exists = (
                db.query(TopTurnoverScrip)
                .filter(
                    TopTurnoverScrip.symbol == clean_symbol,
                    TopTurnoverScrip.business_date == today,
                )
                .first()
            )
            
            if exists:
                # Update existing record
                exists.ltp = s.get("ltp")
                exists.point_change = s.get("point_change")
                exists.pct_change = s.get("pct_change")
                exists.amount = s.get("amount")
                exists.rank = rank
                exists.captured_at = datetime.utcnow()
                updated += 1
                seen += 1
                continue
                
            # Create new record
            db.add(
                TopTurnoverScrip(
                    symbol=clean_symbol,
                    ltp=s.get("ltp"),
                    point_change=s.get("point_change"),
                    pct_change=s.get("pct_change"),
                    amount=s.get("amount"),
                    rank=rank,
                    business_date=today,
                    captured_at=datetime.utcnow(),
                )
            )
            seen += 1
            
        db.commit()
        return f"{seen} processed ({updated} updated), {skipped} skipped of {len(scrips)} scrips"
    except Exception as e:
        db.rollback()
        logger.error(f"Top scrips sync failed: {e}")
        raise


def _sync_brokers(db: Session, client: NepseMarketClientSync) -> str:
    """Sync broker info."""
    try:
        members = client.fetch_members()
        existing = {b.broker_code: b for b in db.query(BrokerInfo).all()}
        created = updated = 0
        
        for m in members:
            code = m.get("code")
            if not code or str(code).isdigit():
                continue
                
            broker = existing.get(code)
            if broker is None:
                db.add(
                    BrokerInfo(
                        broker_code=code, 
                        name=m.get("name", f"Broker {code}"), 
                        city=m.get("city")
                    )
                )
                created += 1
            else:
                if m.get("city") and broker.city != m.get("city"):
                    broker.city = m.get("city")
                    updated += 1
                    
        db.commit()
        return f"{len(members)} brokers: {created} new, {updated} updated"
    except Exception as e:
        db.rollback()
        logger.error(f"Brokers sync failed: {e}")
        raise


def _sync_bulletins(db: Session, client: NepseMarketClientSync) -> str:
    """Sync news bulletins."""
    try:
        bulletins = client.fetch_news_bulletin()
        added = 0
        
        for b in bulletins:
            title = b.get("title")
            if not title:
                continue
                
            exists = (
                db.query(NewsBulletinItem.id)
                .filter(NewsBulletinItem.title == title)
                .first()
            )
            if exists:
                continue
                
            published = _parse_datetime(b.get("published_on"))
            db.add(
                NewsBulletinItem(
                    title=title,
                    published_on=published,
                    source_url=b.get("url"),
                )
            )
            added += 1
            
        db.commit()
        return f"{added} new of {len(bulletins)} bulletins"
    except Exception as e:
        db.rollback()
        logger.error(f"Bulletins sync failed: {e}")
        raise


def _sync_floorsheet(db: Session, client: NepseMarketClientSync, max_pages: int) -> str:
    """Sync floorsheet data."""
    try:
        symbol_map = {c.symbol.upper(): c.id for c in db.query(Company).all()}
        today = datetime.combine(date_cls.today(), datetime.min.time())
        inserted = duplicate = 0

        for page in range(max_pages):
            raw = client.fetch_floorsheet(page=page)
            content = raw.get("content", [])
            if not content:
                break
                
            for f in content:
                symbol = f.get("symbol") or f.get("stockSymbol")
                if not symbol or str(symbol).isdigit():
                    continue
                    
                clean_symbol = symbol.strip().upper()
                company_id = symbol_map.get(clean_symbol)
                if company_id is None:
                    continue
                    
                item = {
                    "buyer_broker": str(f.get("buyerMemberId") or f.get("buyerBroker") or ""),
                    "seller_broker": str(f.get("sellerMemberId") or f.get("sellerBroker") or ""),
                    "quantity": int(float(f.get("contractQuantity") or f.get("quantity") or 0)),
                    "rate": float(f.get("contractRate") or f.get("rate") or 0),
                    "amount": float(f.get("contractAmount") or f.get("amount") or 0),
                }
                
                # Check for duplicate
                dup = (
                    db.query(FloorsheetTransaction.id)
                    .filter(
                        FloorsheetTransaction.company_id == company_id,
                        FloorsheetTransaction.date == today,
                        FloorsheetTransaction.buyer_broker == item["buyer_broker"],
                        FloorsheetTransaction.seller_broker == item["seller_broker"],
                        FloorsheetTransaction.quantity == item["quantity"],
                        FloorsheetTransaction.rate == item["rate"],
                    )
                    .first()
                )
                if dup:
                    duplicate += 1
                    continue
                    
                db.add(FloorsheetTransaction(company_id=company_id, date=today, **item))
                inserted += 1
                
            db.commit()
            if len(content) < 500:
                break
                
        return f"{inserted} inserted, {duplicate} duplicates ({max_pages} pages)"
    except Exception as e:
        db.rollback()
        logger.error(f"Floorsheet sync failed: {e}")
        raise


def sync_all_market_data(
    include_floorsheet: bool = True,
    max_floorsheet_pages: Optional[int] = None,
) -> Dict[str, Dict]:
    """
    Entry point for startup + scheduler + admin trigger. Fetches every
    market data source and persists it.
    
    Returns:
        {
            "market_status": {"status": "ok"|"failed", "detail": "..."},
            "companies": {"status": "ok"|"failed", "detail": "..."},
            ...
        }
    """
    pages = max_floorsheet_pages or getattr(settings, "floorsheet_max_pages", 5)
    result: Dict[str, Dict] = {}

    # Use the synchronous client
    client = NepseMarketClientSync()
    db = SessionLocal()
    
    try:
        # Define steps in order
        steps: List[tuple[str, callable]] = [
            ("market_status", lambda: _sync_status(db, client)),
            ("companies", lambda: _sync_companies(db, client)),
            ("prices", lambda: _sync_prices(db, client)),
            ("indices", lambda: _sync_indices(db, client)),
            ("top_scrips", lambda: _sync_top_scrips(db, client)),
            ("brokers", lambda: _sync_brokers(db, client)),
            ("news_bulletins", lambda: _sync_bulletins(db, client)),
        ]
        
        if include_floorsheet:
            steps.append(("floorsheet", lambda: _sync_floorsheet(db, client, pages)))

        # Execute each step with proper error handling
        for name, fn in steps:
            try:
                detail = fn()
                result[name] = {"status": "ok", "detail": detail}
                logger.info("market sync [%s]: %s", name, detail)
            except Exception as exc:
                logger.exception("market sync [%s] failed", name)
                result[name] = {"status": "failed", "error": str(exc)}
                # Rollback the session after each failed step
                try:
                    db.rollback()
                except:
                    pass
                
    finally:
        db.close()
        client.close()

    return result


def sync_all_market_data_async(
    include_floorsheet: bool = True,
    max_floorsheet_pages: Optional[int] = None,
) -> Dict[str, Dict]:
    """
    Async wrapper for sync_all_market_data.
    Use this if you need async compatibility.
    """
    return sync_all_market_data(include_floorsheet, max_floorsheet_pages)


# ============ Helper Functions for Scheduler ============

def get_market_summary() -> Dict[str, Any]:
    """
    Get a summary of current market data.
    Useful for health checks and monitoring.
    """
    client = NepseMarketClientSync()
    try:
        status = client.fetch_market_open()
        top_scrips = client.fetch_top_ten_turnover_scrips()
        
        return {
            "market_open": status.get("is_open", False),
            "last_updated": status.get("as_of"),
            "top_scrips": top_scrips[:5] if top_scrips else [],
            "total_scrips": len(client.fetch_listed_securities()),
        }
    finally:
        client.close()


def check_market_health() -> Dict[str, bool]:
    """
    Check if all market data sources are working.
    """
    client = NepseMarketClientSync()
    try:
        results = {
            "market_status": bool(client.fetch_market_open()),
            "prices": bool(client.fetch_today_price()),
            "companies": bool(client.fetch_listed_securities()),
            "indices": bool(client.fetch_indices()),
            "members": bool(client.fetch_members()),
            "top_scrips": bool(client.fetch_top_ten_turnover_scrips()),
        }
        return results
    finally:
        client.close()