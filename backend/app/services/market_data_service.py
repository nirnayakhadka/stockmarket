"""
app/services/market_data_service.py

Kept as the stable entry point for the scheduler and the admin trigger
endpoints. All collection logic now lives in market_sync_service, which
pulls exclusively from the official NEPSE API - the synthetic/dummy data
generators that used to live here were removed.
"""

from app.services.market_sync_service import sync_all_market_data


def collect_all_market_data(include_floorsheet: bool = True) -> dict:
    """Fetch every live market source and persist it. Blocking; safe to
    call from worker threads (the scheduler runs it via asyncio.run)."""
    return sync_all_market_data(include_floorsheet=include_floorsheet)
