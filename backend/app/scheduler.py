import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.crawlers import CRAWLER_REGISTRY
from app.database import SessionLocal
from app.services.crawl_service import create_crawl_run, execute_crawl_run
from app.services.market_data_service import collect_all_market_data

logger = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _scheduled_crawl_job():
    db = SessionLocal()
    try:
        portals = list(CRAWLER_REGISTRY.keys())
        run = create_crawl_run(db, portals)
    finally:
        db.close()

    logger.info("Scheduled crawl run %s starting for portals=%s", run.id, portals)
    asyncio.run(execute_crawl_run(run.id, portals))

    logger.info("Starting scheduled market data collection")
    try:
        asyncio.run(collect_all_market_data(include_floorsheet=True))
    except Exception:
        logger.exception("Scheduled market data collection failed")


def start_scheduler():
    """
    Satisfies section 1.3 (scheduling): runs the full crawl on a cron
    schedule so the dataset stays current without manual invocation.
    For a production deployment with multiple workers, prefer Celery beat
    over an in-process APScheduler instance so scheduling isn't duplicated
    per worker.
    """
    global _scheduler
    if _scheduler is not None:
        return

    hours = settings.crawl_schedule_cron_hour  # e.g. "6,12,18"
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _scheduled_crawl_job,
        trigger=CronTrigger(hour=hours, minute=0),
        id="scheduled_news_crawl",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started: crawling at hours=%s", hours)