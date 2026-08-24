# NEPSE News Crawler — FastAPI Backend (Section 1.1)

Scope note: this repo implements **section 1.1 (News crawling)** of the assignment only,
per your request — multi-portal crawling, headline/body/date/source/URL capture,
URL dedup, robots.txt compliance, and a configurable crawl delay — exposed through a
FastAPI service. Sections 2–7 (categorization, behavior analysis, RBAC dashboard) are
out of scope for this slice.

## Why FastAPI + httpx/BeautifulSoup instead of Scrapy

The assignment allows "Scrapy or an equivalent Python framework." I went with
`httpx` (async) + `BeautifulSoup` inside a small custom crawler base class rather
than Scrapy, because:

- It runs naturally inside FastAPI's async request/background-task model — no
  separate Scrapy process/Twisted reactor to bridge into the API layer.
- The politeness requirements (robots.txt, crawl delay, User-Agent) are a handful
  of lines with `urllib.robotparser` + `asyncio.sleep` — Scrapy's equivalent
  machinery (`AutoThrottle`, `ROBOTSTXT_OBEY`) is heavier than needed for 4 portals.
- Each portal is ~60 lines implementing 2 methods (`list_article_urls`,
  `parse_article`); all dedup/error-handling/rate-limiting is shared in `base.py`.

Trade-off: Scrapy would give you built-in retry/backoff policies, a request
scheduler, and easier horizontal scaling to many more portals. If the watchlist
grows past a handful of sources, Scrapy is the better long-term choice.

## Architecture

```
app/
├── main.py              FastAPI app, centralized exception handlers
├── config.py             All settings (env-var driven, no hard-coded secrets)
├── database.py           SQLAlchemy engine/session (SQLite by default, swap to Postgres via DATABASE_URL)
├── models.py              Article (raw crawled data) + CrawlRun (run tracking)
├── schemas.py             Pydantic request/response models
├── crawlers/
│   ├── base.py            Shared: robots.txt check, crawl delay, fetch/parse loop, error isolation
│   ├── merolagani.py       Portal-specific selectors only
│   ├── sharesansar.py
│   ├── nepsealpha.py
│   └── bizmandu.py
├── services/
│   └── crawl_service.py    Orchestrates crawlers, dedups by URL, persists, updates CrawlRun status
├── routers/
│   ├── news.py              GET /api/news, GET /api/news/{id}
│   └── admin.py              POST/GET /api/admin/crawl-runs
└── scheduler.py            Optional APScheduler cron job (section 1.3)
```

**Raw-data separation**: `Article` only stores what the crawler captured
(headline, body, url, source, timestamps). No categorization or analysis fields
live on this table — the assignment's later sections should add their own
tables referencing `Article.id` by foreign key, so raw crawl data is never
recomputed or mutated by downstream processing.

## Politeness / compliance (section 1.1 requirements)

- **robots.txt**: `BaseCrawler._load_robots()` fetches and parses each portal's
  `robots.txt` once per run (cached on the crawler instance) via
  `urllib.robotparser`. Every fetch goes through `_allowed()` first; disallowed
  URLs are skipped and logged, never fetched.
- **Crawl delay**: `CRAWL_DELAY_SECONDS` (default 2s) is applied via
  `asyncio.sleep` after *every* request — including robots.txt itself and
  failed requests — so a burst of errors can't turn into a burst of requests.
- **User-Agent**: a single identifiable `USER_AGENT` (configurable, include a
  contact email) is sent on every request — never spoofed as a browser.
- **Deduplication**: enforced at two levels — a DB `UNIQUE` constraint on
  `Article.url` (source of truth) and a pre-check in `crawl_service._save_articles`
  to avoid noisy constraint-violation churn on every re-crawl.
- **Failure handling**: `BaseCrawler.run()` never raises — a failed fetch,
  parse error, or fully-unreachable portal is caught, logged, and recorded in
  `CrawlRun.errors` as JSON; it never aborts the other portals in the same run
  or bubbles into a 500.

## ⚠️ Selector verification needed before real use

I don't have live network access to merolagani.com / sharesansar.com /
nepsealpha.com / bizmandu.com from this environment to inspect their current
DOM structure. Each crawler file has a docstring flagging this. The
`list_article_urls()` / `parse_article()` methods use each site's *typical*
structure (listing pages with anchor links to article detail pages; detail
pages with an `h1` headline and a content container), but **you should spot-check
2-3 live article pages per portal and adjust the CSS selectors** before relying
on this for real data. Everything else (robots.txt compliance, delay, dedup,
error isolation, run tracking) works regardless of selector accuracy — a wrong
selector just means 0 articles parsed from that portal, surfaced clearly via
`CrawlRun.articles_found`, not a crash.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adjust DATABASE_URL / USER_AGENT as needed
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive Swagger docs (satisfies the
API documentation requirement).

## Try it

```bash
# Trigger a crawl (omit "portals" to crawl all four)
curl -X POST http://localhost:8000/api/admin/crawl-runs \
  -H "Content-Type: application/json" \
  -d '{"portals": ["merolagani", "bizmandu"]}'

# Check run status
curl http://localhost:8000/api/admin/crawl-runs/1

# Read crawled news
curl http://localhost:8000/api/news?source_portal=merolagani
```

## Scheduling (section 1.3)

Set `ENABLE_SCHEDULER=true` and `CRAWL_SCHEDULE_CRON_HOUR` (comma-separated 24h
hours, e.g. `6,12,18`) in `.env`. `app/scheduler.py` runs an in-process
APScheduler cron job on startup. For a multi-worker production deployment,
swap this for Celery beat so scheduling isn't duplicated per worker — the
`execute_crawl_run()` function in `crawl_service.py` is already
worker-agnostic (opens its own DB session, takes no request context) so this
swap doesn't touch crawler or API code.

## What's deliberately left out (scope of this slice)

- Trading data (OHLCV/floorsheet) crawling — section 1.2.
- Categorization, RBAC dashboard, analysis endpoints — sections 2–7. `Article`
  and `CrawlRun` are designed so those can be added as new tables/routers
  without touching this crawling layer.
- Auth/role checks on the admin endpoints — noted inline in `routers/admin.py`.
