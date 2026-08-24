from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Company Schemas ---
class CompanyBase(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int
    
    class Config:
        from_attributes = True


# --- Categorization Schemas ---
class NewsCategorizationBase(BaseModel):
    company_id: int
    confidence_score: float
    method: str


class NewsCategorizationCreate(NewsCategorizationBase):
    article_id: int


class NewsCategorizationResponse(NewsCategorizationBase):
    id: int
    article_id: int
    is_manual_correction: bool
    corrected_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# --- Article Schemas ---
class ArticleBase(BaseModel):
    headline: str
    body_text: str
    url: str
    source_portal: str
    published_at: Optional[datetime] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleResponse(ArticleBase):
    id: int
    crawled_at: datetime
    categorizations: List[NewsCategorizationResponse] = []
    
    class Config:
        from_attributes = True


# For compatibility with news.py
ArticleOut = ArticleResponse
ArticleListOut = List[ArticleResponse]


# --- Crawl Run Schemas ---
class CrawlRunBase(BaseModel):
    portals: str


class CrawlRunCreate(CrawlRunBase):
    pass


class CrawlRunOut(BaseModel):
    id: int
    status: str
    portals: str
    started_at: datetime
    finished_at: Optional[datetime]
    articles_found: int
    articles_new: int
    articles_duplicate: int
    errors: Optional[str]
    
    class Config:
        from_attributes = True


class CrawlStatusResponse(BaseModel):
    id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    articles_found: int
    articles_new: int
    errors: Optional[str]
    
    class Config:
        from_attributes = True


# --- Daily Price Schemas ---
class DailyPriceBase(BaseModel):
    date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    turnover: Optional[float] = None


class DailyPriceResponse(DailyPriceBase):
    id: int
    company_id: int
    
    class Config:
        from_attributes = True


# --- Behavior Analysis Schemas ---
class BehaviorAnalysisResponse(BaseModel):
    company_id: int
    analysis_date: datetime
    vwap: Optional[float]
    vwap_vs_close: Optional[float]
    price_change_pct: Optional[float]
    volume_change_pct: Optional[float]
    pressure_indicator: Optional[str]
    pressure_score: Optional[float]
    is_volume_anomaly: bool
    volume_z_score: Optional[float]
    news_count_previous_day: int
    
    class Config:
        from_attributes = True


# --- Broker Activity Schemas ---
class BrokerActivityResponse(BaseModel):
    broker_code: str
    total_buy_quantity: int
    total_sell_quantity: int
    net_quantity: int
    
    class Config:
        from_attributes = True


# --- User Schemas (RBAC) ---
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# --- Recategorization Schemas ---
class RecategorizeRequest(BaseModel):
    company_ids: List[int]
    confidence_score: float = 1.0


# --- Crawl Trigger Schema ---
class CrawlTriggerRequest(BaseModel):
    portals: Optional[List[str]] = None


