# NEPSE Pulse — FastAPI Backend

A comprehensive NEPSE (Nepal Stock Exchange) data aggregation and analysis platform with news crawling, market data sync, and behavioral analysis.

## 🚀 Features

### 1. News Crawling (Section 1.1)
- Multi-portal crawling from 4 NEPSE news sources:
  - Merolagani
  - Sharesansar
  - NEPSE Alpha
  - Bizmandu
- Headline, body, date, source, URL capture
- URL deduplication (database-level unique constraint)
- robots.txt compliance with crawl delay
- Configurable user-agent with contact email

### 2. Market Data Sync (Section 1.3)
- **Multiple data sources** with automatic failover:
  - Sharesansar HTML parsing (primary)
  - MeroLagani API
  - NEPSE Alpha API
  - Mock data generator (fallback)
- **Live market data**:
  - Stock prices (LTP, Open, High, Low, Volume, Turnover)
  - Market indices (NEPSE Index, Sensitive Index, Float Index)
  - Top turnover scrips (Top 10)
  - Broker information
  - Floorsheet transactions
  - News bulletins
- **Automatic company management**:
  - Creates companies from price data
  - Case-insensitive symbol matching
  - Duplicate handling with upsert logic

### 3. Scheduler (Section 1.3)
- **APScheduler** running in the background
- **Cron schedule** for news crawling (default: 6am, 12pm, 6pm)
- **Interval schedule** for market data sync (default: every 5 minutes)
- **Cleanup job** for database maintenance (daily at 2am)

### 4. API Endpoints
- **News**: GET /api/news, GET /api/news/{id}
- **Companies**: GET /api/companies, GET /api/companies/{id}
- **Prices**: GET /api/companies/{id}/prices
- **Market Status**: GET /api/market/status
- **Top Scrips**: GET /api/market/top-scrips
- **Indices**: GET /api/market/indices
- **Admin**: POST/GET /api/admin/crawl-runs


## 📦 Installation

### Prerequisites
- Python 3.12+
- PostgreSQL (or SQLite for development)

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# DATABASE_URL=postgresql://user:pass@localhost/nepse_db
# USER_AGENT=Mozilla/5.0 (compatible; NEPSE-Crawler/1.0; contact@example.com)
# CRAWL_DELAY_SECONDS=2
# CRAWL_SCHEDULE_CRON_HOUR=6,12,18
# MARKET_SYNC_INTERVAL_MINUTES=5

# Run migrations (if using Alembic)
# alembic upgrade head

# Start the server
uvicorn app.main:app --reload
