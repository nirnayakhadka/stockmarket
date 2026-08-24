# NEPSE Stock Market Application

## Project Overview

AI-powered NEPSE platform for news, market, broker, and behavior analysis.

## Features

- Multi-portal news crawling
- Multi-label news categorization with confidence scores
- Manual news correction
- OHLCV market data
- VWAP and buy/sell pressure analysis
- Volume anomaly detection
- Buyer/seller broker activity
- News-price correlation
- Company-wise and cross-company analysis
- JWT authentication
- Admin, Analyst, and Viewer roles
- Responsive stock market dashboard

## Tech Stack

### Backend
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- APScheduler
- BeautifulSoup
- HTTPX
- JWT

### Frontend
- React
- TypeScript
- Tailwind CSS
- Vite

## Data Sources

- Merolagani
- ShareSansar
- NEPSE Alpha
- Bizmandu
- NEPSE market/floorsheet data

## Architecture

News Sources → Crawler → PostgreSQL
                       ↓
                Categorization
                       ↓
                Market Analysis
                       ↓
React Dashboard ← FastAPI API
API Documentation

FastAPI Swagger documentation:

/docs

RBAC
Admin: Manage users, crawling, and administration
Analyst: View and analyze data, correct news categorization
Viewer: Read-only access
Limitations

Some historical market data used for development/testing is seeded data.
News-price correlation is exploratory and is not a validated trading signal.