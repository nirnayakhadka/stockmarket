"""
app/routers/market_data_admin.py

Admin trigger for real trading-data collection.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.services.market_sync_service import sync_all_market_data
from app.auth_dependencies import require_role

router = APIRouter(prefix="/api/admin/market-data", tags=["admin", "market-data"])


@router.post("/collect", dependencies=[Depends(require_role("admin"))])
def trigger_market_data_collection(
    background_tasks: BackgroundTasks,
    include_floorsheet: bool = True,
):
    """
    Triggers a full live-data sync against nepalstock.com.np in the
    background. The same sync runs at startup and on the scheduler
    interval; this endpoint exists for manual/on-demand refreshes.
    """
    background_tasks.add_task(sync_all_market_data, include_floorsheet)
    return {"status": "collection started", "include_floorsheet": include_floorsheet}


@router.post("/collect-sync", dependencies=[Depends(require_role("admin"))])
def trigger_market_data_collection_sync(include_floorsheet: bool = True):
    """
    Same as /collect but waits and returns per-source results directly -
    useful from Swagger UI to see inserted/updated counts immediately.
    """
    return sync_all_market_data(include_floorsheet=include_floorsheet)
