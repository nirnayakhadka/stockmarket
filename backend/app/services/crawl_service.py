import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crawlers import CRAWLER_REGISTRY
from app.database import SessionLocal
from app.models import Article, CrawlRun, CrawlRunStatus

logger = logging.getLogger("crawl_service")


def create_crawl_run(db: Session, portals: List[str]) -> CrawlRun:
    run = CrawlRun(
        status=CrawlRunStatus.pending,
        portals=",".join(portals),
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _save_articles(db: Session, portal_articles: list) -> tuple[int, int]:
    """
    Insert new articles, skip existing ones (dedup by URL — the unique
    constraint on Article.url is the source of truth; this pre-check just
    avoids noisy IntegrityErrors on every duplicate).
    Returns (new_count, duplicate_count).
    """
    new_count = 0
    duplicate_count = 0

    for item in portal_articles:
        exists = db.query(Article).filter(Article.url == item["url"]).first()
        if exists:
            duplicate_count += 1
            continue

        article = Article(
            headline=item["headline"][:512],
            body_text=item["body_text"],
            url=item["url"],
            source_portal=item["source_portal"],
            published_at=item.get("published_at"),
        )
        db.add(article)
        try:
            db.commit()
            new_count += 1
        except Exception:
            # Race with another writer inserting the same URL concurrently
            db.rollback()
            duplicate_count += 1

    return new_count, duplicate_count


async def _run_portal(name: str) -> tuple[str, list, Optional[str]]:
    crawler_cls = CRAWLER_REGISTRY.get(name)
    if crawler_cls is None:
        return name, [], f"Unknown portal: {name}"

    crawler = crawler_cls()
    try:
        articles = await crawler.run()
        return name, articles, None
    except Exception as exc:
        logger.exception("Crawler for %s failed", name)
        return name, [], str(exc)


async def execute_crawl_run(run_id: int, portals: List[str]) -> None:
    """
    The actual crawl execution, meant to be scheduled as a background task
    (FastAPI BackgroundTasks, or an APScheduler job — see main.py). Opens
    its own DB session since it runs outside the request lifecycle.
    """
    db = SessionLocal()
    try:
        run = db.query(CrawlRun).filter(CrawlRun.id == run_id).first()
        if not run:
            return
        run.status = CrawlRunStatus.running
        db.commit()

        results = await asyncio.gather(*[_run_portal(p) for p in portals])

        total_found = 0
        total_new = 0
        total_duplicate = 0
        errors = []

        for portal_name, articles, error in results:
            if error:
                errors.append({"portal": portal_name, "error": error})
                continue
            total_found += len(articles)
            new_count, dup_count = _save_articles(db, articles)
            total_new += new_count
            total_duplicate += dup_count

        run.status = CrawlRunStatus.failed if errors and total_found == 0 else CrawlRunStatus.completed
        run.finished_at = datetime.utcnow()
        run.articles_found = total_found
        run.articles_new = total_new
        run.articles_duplicate = total_duplicate
        run.errors = json.dumps(errors) if errors else None
        db.commit()
    except Exception:
        logger.exception("Crawl run %s crashed", run_id)
        run = db.query(CrawlRun).filter(CrawlRun.id == run_id).first()
        if run:
            run.status = CrawlRunStatus.failed
            run.finished_at = datetime.utcnow()
            run.errors = json.dumps([{"portal": "*", "error": "run crashed, see server logs"}])
            db.commit()
    finally:
        db.close()
