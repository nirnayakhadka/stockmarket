import logging
import threading

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.routers import news, admin, companies, prices, analysis, categorization,market_data_admin, auth, users, broker_activity, market

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nepse_crawler")

app = FastAPI(
    title="NEPSE News Crawler API",
    description=(
        "Section 1.1 of the assignment: multi-portal news crawling "
        "(merolagani, sharesansar, nepsealpha, bizmandu) with URL "
        "deduplication, robots.txt compliance, and a configurable crawl delay."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router)
app.include_router(admin.router)
app.include_router(companies.router)
app.include_router(prices.router)
app.include_router(analysis.router)
app.include_router(categorization.router)
app.include_router(market_data_admin.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(broker_activity.router)
app.include_router(market.router)

@app.on_event("startup")
def on_startup():
    init_db()
    if settings.enable_startup_market_sync:
        # Initial live-data sync in a background thread so the server
        # binds immediately while NEPSE data (companies, prices, indices,
        # floorsheet, brokers, bulletins...) populates the DB. This
        # replaces the old seeding step entirely.
        thread = threading.Thread(target=_startup_sync, name="market-sync-startup", daemon=True)
        thread.start()
    if settings.enable_scheduler:
        from app.scheduler import start_scheduler

        start_scheduler()


def _startup_sync():
    from app.services.market_sync_service import sync_all_market_data

    logger.info("Startup market data sync starting (replaces seeding)")
    try:
        result = sync_all_market_data(include_floorsheet=True)
        failed = [k for k, v in result.items() if v.get("status") == "failed"]
        for name, detail in result.items():
            logger.info("Startup sync [%s]: %s", name, detail.get("detail") or detail.get("error"))
        if failed:
            logger.warning(
                "Startup market sync completed with failures: %s "
                "(NEPSE API may be unreachable from this network; the "
                "scheduler will retry every %d minutes)",
                failed,
                settings.market_sync_interval_minutes,
            )
    except Exception:
        logger.exception("Startup market sync failed")


# --- Centralized error handling: no unhandled exception should ever
# bubble into a raw 500 without a consistent JSON shape. ---


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok"}
