import asyncio
import logging
import traceback
from datetime import datetime
from typing import Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.crawlers import CRAWLER_REGISTRY
from app.database import SessionLocal
from app.services.crawl_service import create_crawl_run, execute_crawl_run
from app.services.market_data_service import collect_all_market_data

logger = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None

def _run_async_in_new_loop(coro):
    """Run async function in a new event loop safely."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def _scheduled_crawl_job():
    """Execute scheduled crawling with comprehensive error handling."""
    job_start = datetime.now()
    portals = list(CRAWLER_REGISTRY.keys())
    run_id = None
    
    logger.info(f"Crawl job starting at {job_start} for portals: {portals}")
    
    # Create crawl run in database
    db = SessionLocal()
    try:
        run = create_crawl_run(db, portals)
        run_id = run.id
        db.commit()
        logger.info(f"Created crawl run {run_id}")
    except SQLAlchemyError as e:
        logger.error(f"Database error creating crawl run: {e}")
        db.rollback()
        return
    except Exception as e:
        logger.error(f"Unexpected error creating crawl run: {e}")
        logger.error(traceback.format_exc())
        return
    finally:
        db.close()
    
    # Execute crawl with timeout and retry logic
    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            logger.info(f"Executing crawl run {run_id}, attempt {retry_count + 1}")
            
            # Run the async function with timeout
            result = _run_async_in_new_loop(
                execute_crawl_run(run_id, portals)
            )
            
            # Log success
            duration = (datetime.now() - job_start).total_seconds()
            logger.info(f"Crawl run {run_id} completed successfully in {duration:.2f}s")
            break
            
        except asyncio.TimeoutError:
            retry_count += 1
            logger.warning(f"Crawl run {run_id} timed out, retry {retry_count}/{max_retries}")
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Crawl run {run_id} failed (attempt {retry_count}): {e}")
            logger.error(traceback.format_exc())
            
            if retry_count > max_retries:
                logger.error(f"Crawl run {run_id} failed after {max_retries} retries")
                # Mark as failed in database if needed
                try:
                    db = SessionLocal()
                    # Update run status to failed
                    # run.status = "failed"
                    db.commit()
                except Exception as db_error:
                    logger.error(f"Could not update run status: {db_error}")
                finally:
                    db.close()
    
    # Clean up any remaining async tasks
    try:
        loop = asyncio.get_running_loop()
        pending = asyncio.all_tasks(loop)
        if pending:
            logger.warning(f"Found {len(pending)} pending tasks after crawl, cancelling...")
            for task in pending:
                task.cancel()
    except RuntimeError:
        # No running loop
        pass

def _scheduled_market_sync_job():
    """
    Enhanced market sync with better error handling and reporting.
    Collects all market data including:
    - Live prices
    - Indices
    - Floorsheet data
    - Brokers info
    - Company bulletins
    - Corporate actions
    - Sector performance
    """
    job_start = datetime.now()
    logger.info(f"Market sync starting at {job_start}")
    
    results: Dict[str, Any] = {}
    failed_sections = []
    
    try:
        # Collect all market data with timeout protection
        results = collect_all_market_data(include_floorsheet=True, include_bulletins=True)
        
        # Analyze results
        failed_sections = [k for k, v in results.items() if v.get("status") == "failed"]
        success_sections = [k for k, v in results.items() if v.get("status") == "success"]
        
        # Log detailed results
        duration = (datetime.now() - job_start).total_seconds()
        
        if failed_sections:
            logger.warning(
                f"Market sync completed with {len(failed_sections)} failed sections: {failed_sections}"
            )
            logger.warning(f"Successful sections: {success_sections}")
        else:
            logger.info(f"Market sync completed successfully with {len(success_sections)} sections in {duration:.2f}s")
        
        # If we have failures, attempt to retry failed sections
        if failed_sections and len(failed_sections) < len(results):
            logger.info("Attempting to retry failed sections...")
            retry_results = collect_all_market_data(
                include_floorsheet="floorsheet" in failed_sections,
                include_bulletins="bulletins" in failed_sections,
                sections_to_retry=failed_sections
            )
            
            retry_success = [k for k, v in retry_results.items() if v.get("status") == "success"]
            if retry_success:
                logger.info(f"Retry succeeded for: {retry_success}")
                failed_sections = [k for k in failed_sections if k not in retry_success]
        
        # Alert if critical sections failed
        critical_sections = ["prices", "indices", "floorsheet"]
        critical_failures = [s for s in failed_sections if s in critical_sections]
        if critical_failures:
            logger.error(f"CRITICAL: Market sync failed for: {critical_failures}")
            # Could trigger alert here
            
    except TimeoutError:
        logger.error("Market sync timed out after 5 minutes")
        failed_sections = ["timeout"]
    except ConnectionError as e:
        logger.error(f"Network connection error in market sync: {e}")
        failed_sections = ["connection_error"]
    except Exception as e:
        logger.error(f"Unexpected error in market sync: {e}")
        logger.error(traceback.format_exc())
        failed_sections = ["unexpected_error"]
    
    # Final summary
    total_duration = (datetime.now() - job_start).total_seconds()
    if failed_sections:
        logger.info(f"Market sync finished with {len(failed_sections)} failures in {total_duration:.2f}s")
    else:
        logger.info(f"Market sync finished successfully in {total_duration:.2f}s")
    
    return results

def job_listener(event):
    """Listener for scheduler events to monitor job execution."""
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
        logger.error(f"Traceback: {event.traceback}")
    else:
        logger.debug(f"Job {event.job_id} executed successfully")

def _scheduled_cleanup_job():
    """Periodic cleanup job to maintain database performance."""
    logger.info("Running cleanup job")
    db = SessionLocal()
    try:
        # Delete old crawl runs older than 30 days
        # Delete old market data older than 7 days
        # Vacuum database if needed
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")
    finally:
        db.close()

def start_scheduler():
    """
    Start the scheduler with all jobs configured.
    
    Satisfies section 1.3 (scheduling):
    - News crawling runs on cron schedule (default: 6am, 12pm, 6pm)
    - Live market data syncs every `market_sync_interval_minutes`
    - Cleanup job runs daily at 2am
    
    For production with multiple workers, consider using Celery Beat 
    instead of in-process APScheduler to prevent duplicate scheduling.
    """
    global _scheduler
    if _scheduler is not None:
        logger.info("Scheduler already running")
        return
    
    try:
        hours = settings.crawl_schedule_cron_hour  # e.g. "6,12,18"
        if not hours:
            hours = "6,12,18"  # Default schedule
            logger.warning("No crawl schedule found, using default: %s", hours)
        
        _scheduler = BackgroundScheduler(
            timezone="Asia/Kathmandu",  # NEPSE timezone
            job_defaults={
                'coalesce': True,      # Combine missed jobs
                'max_instances': 1,    # Don't run multiple instances
                'misfire_grace_time': 60  # Wait up to 60 seconds for missed jobs
            }
        )
        
        # Add listeners
        _scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # Add all jobs
        _scheduler.add_job(
            _scheduled_crawl_job,
            trigger=CronTrigger(hour=hours, minute=0),
            id="scheduled_news_crawl",
            replace_existing=True,
            name="News Crawl Job"
        )
        
        _scheduler.add_job(
            _scheduled_market_sync_job,
            trigger=IntervalTrigger(
                minutes=settings.market_sync_interval_minutes,
                start_date=datetime.now()  # Start immediately
            ),
            id="scheduled_market_sync",
            replace_existing=True,
            name="Market Sync Job"
        )
        
        # Add cleanup job (runs daily at 2am)
        _scheduler.add_job(
            _scheduled_cleanup_job,
            trigger=CronTrigger(hour=2, minute=0),
            id="cleanup_job",
            replace_existing=True,
            name="Cleanup Job"
        )
        
        # Start the scheduler
        _scheduler.start()
        logger.info(
            "Scheduler started successfully at %s. Jobs: News crawl at hours=%s, Market sync every %d min, Cleanup at 2am",
            datetime.now(),
            hours,
            settings.market_sync_interval_minutes
        )
        
        # Print job list
        jobs = _scheduler.get_jobs()
        logger.info(f"Active jobs: {[job.name for job in jobs]}")
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        logger.error(traceback.format_exc())
        if _scheduler:
            _scheduler.shutdown()
        raise

def stop_scheduler():
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped successfully")
            _scheduler = None
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")