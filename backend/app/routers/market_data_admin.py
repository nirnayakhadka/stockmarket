"""
app/routers/market_data_admin.py

Admin trigger for real trading-data collection (section 1.2).
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.services.market_data_service import collect_all_market_data
from app.auth_dependencies import require_role

router = APIRouter(prefix="/api/admin/market-data", tags=["admin", "market-data"])


@router.post("/collect", dependencies=[Depends(require_role("admin"))])
async def trigger_market_data_collection(
    background_tasks: BackgroundTasks,
    include_floorsheet: bool = True,
):
    """
    Triggers a real-data collection run against nepalstock.com.np for the
    watchlist. Runs in the background — call this once daily via the
    scheduler (see app/scheduler.py), or manually from here for testing/
    on-demand refresh.
    """
    background_tasks.add_task(_run_collection, include_floorsheet)
    return {"status": "collection started", "include_floorsheet": include_floorsheet}


async def _run_collection(include_floorsheet: bool):
    result = await collect_all_market_data(include_floorsheet=include_floorsheet)
    return result


@router.post("/collect-sync", dependencies=[Depends(require_role("admin"))])
async def trigger_market_data_collection_sync(include_floorsheet: bool = True):
    """
    Same as /collect but waits for the result and returns it directly —
    useful when testing from Swagger UI so you can see inserted/updated
    counts immediately instead of polling.
    """
    return await collect_all_market_data(include_floorsheet=include_floorsheet)