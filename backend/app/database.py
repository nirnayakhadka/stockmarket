from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# PostgreSQL doesn't need special connect_args
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _ensure_daily_price_columns()


def _ensure_daily_price_columns():
    """
    Lightweight migration: Base.metadata.create_all only creates missing
    tables — it never alters existing ones. These columns were added when
    seeding was replaced by live NEPSE sync; add them to pre-existing
    daily_prices tables and ignore failures (fresh DBs already have them).
    """
    from sqlalchemy import text
    statements = [
        "ALTER TABLE daily_prices ADD COLUMN prev_close NUMERIC(20,4)",
        "ALTER TABLE daily_prices ADD COLUMN change_pct NUMERIC(10,4)",
        "ALTER TABLE daily_prices ADD COLUMN transactions INTEGER",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass