import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, 
    UniqueConstraint, Index, Float, ForeignKey, JSON,
    Boolean, Table, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# --- Existing Models ---
class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("url", name="uq_articles_url"),
        Index("ix_articles_source_published", "source_portal", "published_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    headline = Column(String(512), nullable=False)
    body_text = Column(Text, nullable=False)
    url = Column(String(1024), nullable=False, unique=True, index=True)
    source_portal = Column(String(64), nullable=False, index=True)
    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    categorizations = relationship("NewsCategorization", back_populates="article", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Article id={self.id} source={self.source_portal} url={self.url!r}>"


class CrawlRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(CrawlRunStatus), default=CrawlRunStatus.pending, nullable=False)
    portals = Column(String(256), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    articles_found = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    articles_duplicate = Column(Integer, default=0)
    errors = Column(Text, nullable=True)


# --- Company & Trading Data Models ---

class Company(Base):
    """Tracked NEPSE-listed companies"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    sector = Column(String(100), nullable=True)
    listed_date = Column(DateTime, nullable=True)
    
    # Relationships
    daily_prices = relationship("DailyPrice", back_populates="company", cascade="all, delete-orphan")
    floorsheet_transactions = relationship("FloorsheetTransaction", back_populates="company", cascade="all, delete-orphan")
    behavior_analyses = relationship("BehaviorAnalysis", back_populates="company", cascade="all, delete-orphan")
    categorizations = relationship("NewsCategorization", back_populates="company")
    
    def __repr__(self):
        return f"<Company symbol={self.symbol} name={self.name}>"


class DailyPrice(Base):
    """Daily OHLCV trading data"""
    __tablename__ = "daily_prices"
    __table_args__ = (
        UniqueConstraint("company_id", "date", name="uq_company_date"),
        Index("ix_daily_prices_company_date", "company_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    open_price = Column(DECIMAL(20, 4), nullable=False)
    high_price = Column(DECIMAL(20, 4), nullable=False)
    low_price = Column(DECIMAL(20, 4), nullable=False)
    close_price = Column(DECIMAL(20, 4), nullable=False)
    prev_close = Column(DECIMAL(20, 4), nullable=True)
    change_pct = Column(DECIMAL(10, 4), nullable=True)
    transactions = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=False)
    turnover = Column(DECIMAL(20, 2), nullable=True)

    # Relationships
    company = relationship("Company", back_populates="daily_prices")


class FloorsheetTransaction(Base):
    """Floorsheet-level transaction data"""
    __tablename__ = "floorsheet_transactions"
    __table_args__ = (
        Index("ix_floorsheet_company_date", "company_id", "date"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    buyer_broker = Column(String(20), nullable=False)
    seller_broker = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    rate = Column(DECIMAL(20, 4), nullable=False)
    amount = Column(DECIMAL(20, 2), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="floorsheet_transactions")


# --- Categorization Models ---

class NewsCategorization(Base):
    """Categorization of news articles to companies"""
    __tablename__ = "news_categorizations"
    __table_args__ = (
        UniqueConstraint("article_id", "company_id", name="uq_article_company"),
        Index("ix_categorization_company", "company_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    confidence_score = Column(DECIMAL(5, 4), nullable=False)
    method = Column(String(50), nullable=False)
    is_manual_correction = Column(Boolean, default=False)
    corrected_at = Column(DateTime, nullable=True)
    corrected_by_user_id = Column(Integer, nullable=True)
    original_confidence = Column(DECIMAL(5, 4), nullable=True)
    
    # Relationships
    article = relationship("Article", back_populates="categorizations")
    company = relationship("Company", back_populates="categorizations")


# --- Behavior Analysis Models ---

class BehaviorAnalysis(Base):
    """Computed behavior analysis per company per day"""
    __tablename__ = "behavior_analyses"
    __table_args__ = (
        UniqueConstraint("company_id", "analysis_date", name="uq_behavior_company_date"),
        Index("ix_behavior_company_date", "company_id", "analysis_date"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    analysis_date = Column(DateTime, nullable=False)
    
    # VWAP
    vwap = Column(DECIMAL(20, 4), nullable=True)
    vwap_vs_close = Column(DECIMAL(10, 4), nullable=True)
    
    # Price/Volume trends
    price_change_pct = Column(DECIMAL(10, 4), nullable=True)
    volume_change_pct = Column(DECIMAL(10, 4), nullable=True)
    
    # Buy/Sell Pressure
    pressure_indicator = Column(String(20), nullable=True)
    pressure_score = Column(DECIMAL(5, 4), nullable=True)
    
    # Volume Anomaly
    is_volume_anomaly = Column(Boolean, default=False)
    anomaly_threshold = Column(DECIMAL(10, 4), nullable=True)
    volume_z_score = Column(DECIMAL(10, 4), nullable=True)
    
    # News correlation
    news_count_previous_day = Column(Integer, default=0)
    news_count_prev_2_days = Column(Integer, default=0)
    avg_sentiment_score = Column(DECIMAL(5, 4), nullable=True)
    
    # Computed at timestamp
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="behavior_analyses")


class BrokerActivitySummary(Base):
    """Aggregated broker activity per company per day"""
    __tablename__ = "broker_activity_summaries"
    __table_args__ = (
        UniqueConstraint("company_id", "date", "broker_code", name="uq_broker_activity"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    broker_code = Column(String(20), nullable=False)
    
    total_buy_quantity = Column(Integer, default=0)
    total_sell_quantity = Column(Integer, default=0)
    net_quantity = Column(Integer, default=0)
    total_buy_amount = Column(DECIMAL(20, 2), default=0)
    total_sell_amount = Column(DECIMAL(20, 2), default=0)
    
    # Relationships
    company = relationship("Company")


# --- Live Market Models (populated from nepalstock.com.np NOTS API) ---

class MarketIndexSnapshot(Base):
    """Snapshot of a NEPSE index captured at each market-data sync.

    One row per index per sync (and, on first startup, one row per
    business date from the /nepse-price history endpoint so index charts
    have data immediately).
    """
    __tablename__ = "market_index_snapshots"
    __table_args__ = (
        UniqueConstraint("index_name", "business_date", name="uq_market_index_name_date"),
        Index("ix_market_index_captured", "captured_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    index_name = Column(String(120), nullable=False)
    value = Column(DECIMAL(20, 4), nullable=True)
    point_change = Column(DECIMAL(20, 4), nullable=True)
    pct_change = Column(DECIMAL(10, 4), nullable=True)
    open_value = Column(DECIMAL(20, 4), nullable=True)
    high_value = Column(DECIMAL(20, 4), nullable=True)
    low_value = Column(DECIMAL(20, 4), nullable=True)
    prev_close = Column(DECIMAL(20, 4), nullable=True)
    turnover = Column(DECIMAL(24, 2), nullable=True)
    ceil = Column(DECIMAL(20, 4), nullable=True)
    floor = Column(DECIMAL(20, 4), nullable=True)
    business_date = Column(DateTime, nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MarketStatus(Base):
    """Single-row (id=1) mirror of the official market-open flag."""
    __tablename__ = "market_status"

    id = Column(Integer, primary_key=True, index=True)
    is_open = Column(Boolean, default=False, nullable=False)
    is_open_raw = Column(String(20), nullable=True)
    as_of = Column(String(64), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TopTurnoverScrip(Base):
    """Rows of the official top-ten-turnover-scrips endpoint."""
    __tablename__ = "top_turnover_scrips"
    __table_args__ = (
        UniqueConstraint("symbol", "business_date", name="uq_top_scrip_symbol_date"),
        Index("ix_top_scrip_date", "business_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    ltp = Column(DECIMAL(20, 4), nullable=True)
    point_change = Column(DECIMAL(20, 4), nullable=True)
    pct_change = Column(DECIMAL(10, 4), nullable=True)
    amount = Column(DECIMAL(24, 2), nullable=True)
    rank = Column(Integer, nullable=True)
    business_date = Column(DateTime, nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NewsBulletinItem(Base):
    """Official NEPSE news bulletins (market announcements)."""
    __tablename__ = "news_bulletin_items"
    __table_args__ = (
        UniqueConstraint("title", "published_on", name="uq_bulletin_title_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    published_on = Column(DateTime, nullable=True)
    source_url = Column(String(1024), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BrokerInfo(Base):
    """NEPSE trading members (brokers) from the /member endpoint."""
    __tablename__ = "broker_infos"

    id = Column(Integer, primary_key=True, index=True)
    broker_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# --- User & RBAC Models ---
class UserRole(str, enum.Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


class User(Base):
    """User model for RBAC"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.viewer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit trail for important actions"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)