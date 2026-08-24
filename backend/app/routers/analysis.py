from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import statistics
import math
import logging

from app.database import get_db
from app.models import Company, DailyPrice, BehaviorAnalysis, BrokerActivitySummary
from app.schemas import BehaviorAnalysisResponse

router = APIRouter(prefix="/api/companies", tags=["analysis"])
logger = logging.getLogger(__name__)


def calculate_vwap(prices):
    """Calculate Volume Weighted Average Price"""
    if not prices:
        return None
    try:
        total_value = sum(float(p.close_price) * float(p.volume) for p in prices)
        total_volume = sum(float(p.volume) for p in prices)
        return total_value / total_volume if total_volume > 0 else None
    except Exception as e:
        logger.error(f"Error calculating VWAP: {e}")
        return None


def calculate_pressure_indicator(price_change_pct, volume_change_pct):
    """Determine buy/sell pressure based on price and volume changes"""
    if price_change_pct is None or volume_change_pct is None:
        return "neutral", 0.0
    
    try:
        if price_change_pct > 0 and volume_change_pct > 0:
            return "strong_buy", min(1.0, (price_change_pct + volume_change_pct) / 10)
        elif price_change_pct > 0 and volume_change_pct < 0:
            return "weak_buy", min(0.5, price_change_pct / 5)
        elif price_change_pct < 0 and volume_change_pct > 0:
            return "strong_sell", max(-1.0, (price_change_pct - volume_change_pct) / 10)
        elif price_change_pct < 0 and volume_change_pct < 0:
            return "weak_sell", max(-0.5, price_change_pct / 5)
        else:
            return "neutral", 0.0
    except Exception as e:
        logger.error(f"Error calculating pressure: {e}")
        return "neutral", 0.0


def detect_volume_anomaly(volume, recent_volumes, threshold=2.0):
    """Detect if volume is anomalous using z-score"""
    try:
        if len(recent_volumes) < 5:
            return False, None, None
        
        mean_volume = statistics.mean(recent_volumes)
        std_volume = statistics.stdev(recent_volumes) if len(recent_volumes) > 1 else 1
        
        if std_volume == 0:
            return False, 0, None
        
        z_score = (volume - mean_volume) / std_volume
        is_anomaly = abs(z_score) > threshold
        
        return is_anomaly, z_score, threshold
    except Exception as e:
        logger.error(f"Error detecting anomaly: {e}")
        return False, None, None


@router.get("/{company_id}/behavior-summary")
def get_behavior_summary(
    company_id: int,
    range_days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get behavior analysis summary for a company"""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        cutoff_date = datetime.now() - timedelta(days=range_days)
        prices = db.query(DailyPrice).filter(
            DailyPrice.company_id == company_id,
            DailyPrice.date >= cutoff_date
        ).order_by(DailyPrice.date).all()
        
        if len(prices) < 2:
            return {
                "company": company.symbol,
                "message": "Insufficient data for analysis",
                "data_points": len(prices)
            }
        
        analysis = {
            "company": company.symbol,
            "company_id": company_id,
            "data_points": len(prices),
            "date_range": {
                "start": prices[0].date.isoformat() if prices[0].date else None,
                "end": prices[-1].date.isoformat() if prices[-1].date else None
            }
        }
        
        vwap = calculate_vwap(prices)
        analysis["vwap"] = round(vwap, 2) if vwap else None
        analysis["current_price"] = float(prices[-1].close_price) if prices[-1].close_price else None
        analysis["vwap_vs_close"] = round(vwap - float(prices[-1].close_price), 2) if vwap and prices[-1].close_price else None
        
        price_changes = []
        volume_changes = []
        daily_analyses = []
        recent_volumes = [float(p.volume) for p in prices[-10:]]
        
        for i in range(1, len(prices)):
            prev = prices[i-1]
            curr = prices[i]
            
            prev_close = float(prev.close_price)
            curr_close = float(curr.close_price)
            prev_volume = float(prev.volume)
            curr_volume = float(curr.volume)
            
            price_change_pct = ((curr_close - prev_close) / prev_close) * 100 if prev_close != 0 else 0
            volume_change_pct = ((curr_volume - prev_volume) / prev_volume) * 100 if prev_volume != 0 else 0
            
            price_changes.append(price_change_pct)
            volume_changes.append(volume_change_pct)
            
            pressure, score = calculate_pressure_indicator(price_change_pct, volume_change_pct)
            is_anomaly, z_score, threshold = detect_volume_anomaly(curr_volume, recent_volumes[:10])
            
            daily_analyses.append({
                "date": curr.date.isoformat() if curr.date else None,
                "close": curr_close,
                "volume": curr_volume,
                "price_change_pct": round(price_change_pct, 2),
                "volume_change_pct": round(volume_change_pct, 2),
                "pressure": pressure,
                "pressure_score": round(score, 2),
                "is_volume_anomaly": is_anomaly,
                "volume_z_score": round(z_score, 2) if z_score else None
            })
        
        analysis["price_trend"] = {
            "total_change_pct": round(((float(prices[-1].close_price) - float(prices[0].close_price)) / float(prices[0].close_price)) * 100, 2) if prices[0].close_price else 0,
            "avg_daily_change": round(statistics.mean(price_changes), 2) if price_changes else 0,
            "max_daily_gain": round(max(price_changes), 2) if price_changes else 0,
            "max_daily_loss": round(min(price_changes), 2) if price_changes else 0
        }
        
        analysis["volume_trend"] = {
            "avg_volume": int(statistics.mean([float(p.volume) for p in prices])),
            "max_volume": int(max([float(p.volume) for p in prices])),
            "min_volume": int(min([float(p.volume) for p in prices]))
        }
        
        anomalies = [d for d in daily_analyses if d["is_volume_anomaly"]]
        analysis["anomalies"] = {
            "count": len(anomalies),
            "details": anomalies
        }
        
        pressure_counts = {}
        for d in daily_analyses:
            p = d["pressure"]
            pressure_counts[p] = pressure_counts.get(p, 0) + 1
        
        analysis["pressure_summary"] = pressure_counts
        analysis["recent_days"] = daily_analyses[-10:]
        
        return analysis
        
    except Exception as e:
        print(f"❌ ERROR in behavior-summary: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}/news-price-correlation")
def get_news_price_correlation(
    company_id: int,
    range_days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Analyze correlation between news volume and price movement"""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        cutoff_date = datetime.now() - timedelta(days=range_days)
        prices = db.query(DailyPrice).filter(
            DailyPrice.company_id == company_id,
            DailyPrice.date >= cutoff_date
        ).order_by(DailyPrice.date).all()
        
        if len(prices) < 3:
            return {"message": "Insufficient data for correlation analysis"}
        
        correlation_data = []
        for i in range(2, len(prices)):
            curr = prices[i]
            prev = prices[i-1]
            price_change = ((float(curr.close_price) - float(prev.close_price)) / float(prev.close_price)) * 100
            correlation_data.append({
                "date": curr.date.isoformat() if curr.date else None,
                "price_change_pct": round(price_change, 2),
                "news_count": 0,
                "next_day_return": None
            })
        
        return {
            "company": company.symbol,
            "data_points": len(correlation_data),
            "correlation": correlation_data,
            "note": "News correlation data will be available after news categorization is implemented"
        }
        
    except Exception as e:
        print(f"❌ ERROR in news-price-correlation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============ BROKER ACTIVITY ENDPOINTS ============

@router.get("/{company_id}/broker-activity")
def get_broker_activity(
    company_id: int,
    date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today"),
    db: Session = Depends(get_db)
):
    """
    Get broker activity summary for a company on a specific date.
    Shows most active buyers and sellers, and net buy/sell quantity per broker.
    """
    try:
        from datetime import date as date_cls
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        if date:
            trade_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            trade_date = datetime.combine(date_cls.today(), datetime.min.time())
        
        rows = db.query(BrokerActivitySummary).filter(
            BrokerActivitySummary.company_id == company_id,
            BrokerActivitySummary.date == trade_date
        ).all()
        
        if not rows:
            return {
                "company_id": company_id,
                "symbol": company.symbol,
                "date": trade_date.strftime("%Y-%m-%d"),
                "broker_count": 0,
                "most_active_buyer": None,
                "most_active_seller": None,
                "brokers": [],
                "message": "No broker activity found for this date"
            }
        
        brokers = []
        for r in rows:
            brokers.append({
                "broker_code": r.broker_code,
                "buy_quantity": r.total_buy_quantity,
                "sell_quantity": r.total_sell_quantity,
                "net_quantity": r.net_quantity,
                "buy_amount": float(r.total_buy_amount) if r.total_buy_amount else 0,
                "sell_amount": float(r.total_sell_amount) if r.total_sell_amount else 0,
            })
        
        most_active_buyer = max(brokers, key=lambda b: b["buy_quantity"])
        most_active_seller = max(brokers, key=lambda b: b["sell_quantity"])
        
        return {
            "company_id": company_id,
            "symbol": company.symbol,
            "date": trade_date.strftime("%Y-%m-%d"),
            "broker_count": len(brokers),
            "most_active_buyer": most_active_buyer,
            "most_active_seller": most_active_seller,
            "brokers": sorted(brokers, key=lambda b: b["buy_quantity"] + b["sell_quantity"], reverse=True)
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error getting broker activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/compute-broker-activity")
def compute_broker_activity(
    date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today")
):
    """
    Compute broker activity from floorsheet transactions for all companies.
    """
    try:
        from datetime import date as date_cls
        from app.services.broker_analysis_service import compute_broker_activity_all
        
        if date:
            trade_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            trade_date = datetime.combine(date_cls.today(), datetime.min.time())
        
        return compute_broker_activity_all(trade_date)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error computing broker activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))