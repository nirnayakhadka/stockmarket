import sys
import os
from datetime import datetime, timedelta
import random
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Company, DailyPrice

def seed_prices():
    db = SessionLocal()
    try:
        # Get all companies
        companies = db.query(Company).all()
        print(f"Found {len(companies)} companies")
        
        # Generate 30 days of sample data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        total_added = 0
        
        for company in companies:
            # Start with a random base price
            base_price = random.uniform(100, 5000)
            print(f"Generating prices for {company.symbol} (base: {base_price:.2f})")
            
            for i in range(30):
                date = start_date + timedelta(days=i)
                # Skip weekends (Saturday=5, Sunday=6)
                if date.weekday() in [5, 6]:
                    continue
                    
                # Generate random price movement
                change = random.uniform(-0.05, 0.05)
                close = base_price * (1 + change)
                open_price = close * (1 + random.uniform(-0.02, 0.02))
                high = max(open_price, close) * (1 + random.uniform(0, 0.03))
                low = min(open_price, close) * (1 - random.uniform(0, 0.03))
                volume = random.randint(1000, 50000)
                turnover = close * volume
                
                price_data = DailyPrice(
                    company_id=company.id,
                    date=datetime.combine(date, datetime.min.time()),
                    open_price=round(open_price, 2),
                    high_price=round(high, 2),
                    low_price=round(low, 2),
                    close_price=round(close, 2),
                    volume=volume,
                    turnover=round(turnover, 2)
                )
                db.add(price_data)
                total_added += 1
                base_price = close  # Next day starts from previous close
        
        db.commit()
        print(f"✅ Added {total_added} price records for {len(companies)} companies")
        
        # Verify
        count = db.query(DailyPrice).count()
        print(f"📊 Total price records in DB: {count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_prices()
