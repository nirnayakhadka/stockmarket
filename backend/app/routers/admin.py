from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crawlers import CRAWLER_REGISTRY
from app.database import get_db
from app.models import CrawlRun
from app.schemas import CrawlTriggerRequest, CrawlRunOut
from app.services.crawl_service import create_crawl_run, execute_crawl_run
from app.auth_dependencies import require_role

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post(
    "/crawl-runs",
    response_model=CrawlRunOut,
    status_code=202,
    dependencies=[Depends(require_role("admin"))],
)
def trigger_crawl_run(
    payload: CrawlTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    portals = payload.portals or list(CRAWLER_REGISTRY.keys())
    unknown = [p for p in portals if p not in CRAWLER_REGISTRY]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown portal(s): {unknown}")

    run = create_crawl_run(db, portals)
    background_tasks.add_task(_run_async, run.id, portals)
    return run


def _run_async(run_id: int, portals: list[str]):
    import asyncio

    asyncio.run(execute_crawl_run(run_id, portals))


@router.get(
    "/crawl-runs/{run_id}",
    response_model=CrawlRunOut,
    dependencies=[Depends(require_role("admin", "analyst", "viewer"))],
)
def get_crawl_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(CrawlRun).filter(CrawlRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Crawl run not found")
    return run


@router.get(
    "/crawl-runs",
    response_model=list[CrawlRunOut],
    dependencies=[Depends(require_role("admin", "analyst", "viewer"))],
)
def list_crawl_runs(db: Session = Depends(get_db), limit: int = 20):
    return db.query(CrawlRun).order_by(CrawlRun.id.desc()).limit(limit).all()