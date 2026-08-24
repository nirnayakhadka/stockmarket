from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Article, Company, NewsCategorization
from app.schemas import NewsCategorizationResponse, RecategorizeRequest
from app.services.ml_categorizer import MLCategorizer
from app.auth_dependencies import require_role

router = APIRouter(prefix="/api/categorization", tags=["categorization"])

@router.post(
    "/categorize-articles",
    dependencies=[Depends(require_role("admin"))],
)
def categorize_articles(
    article_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """
    Categorize articles by company
    """
    # Get articles to categorize
    query = db.query(Article)
    if article_ids:
        query = query.filter(Article.id.in_(article_ids))
    else:
        # Get uncategorized articles
        categorized_ids = db.query(NewsCategorization.article_id).distinct().subquery()
        query = query.filter(Article.id.notin_(categorized_ids))
    
    articles = query.limit(100).all()
    
    if not articles:
        return {"message": "No articles to categorize", "categorized": 0}
    
    # Categorize
    categorizer = MLCategorizer(db)
    count = categorizer.categorize_articles(articles)
    
    return {
        "message": f"Categorized {count} articles",
        "total_articles_processed": len(articles),
        "categorized": count
    }


@router.get("/article/{article_id}")
def get_article_categories(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Get categories for a specific article"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    categories = db.query(NewsCategorization).filter(
        NewsCategorization.article_id == article_id
    ).all()
    
    return {
        "article_id": article_id,
        "headline": article.headline,
        "categories": [
            {
                "company_id": c.company_id,
                "company_symbol": db.query(Company).filter(Company.id == c.company_id).first().symbol if c.company_id else None,
                "confidence": float(c.confidence_score),
                "method": c.method,
                "is_manual": c.is_manual_correction
            }
            for c in categories
        ]
    }


@router.post(
    "/recategorize/{article_id}",
    dependencies=[Depends(require_role("admin", "analyst"))],
)
def recategorize_article(
    article_id: int,
    request: RecategorizeRequest,
    db: Session = Depends(get_db)
):
    """Manually recategorize an article (Analyst/Admin only)"""
    # Check if article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Validate all company IDs exist
    invalid_companies = []
    for company_id in request.company_ids:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            invalid_companies.append(company_id)
    
    if invalid_companies:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid company IDs: {invalid_companies}. Valid IDs are 11-20."
        )
    
    # Remove existing categorizations
    db.query(NewsCategorization).filter(
        NewsCategorization.article_id == article_id
    ).delete()
    
    # Add new categorizations
    for company_id in request.company_ids:
        categorization = NewsCategorization(
            article_id=article_id,
            company_id=company_id,
            confidence_score=request.confidence_score,
            method="manual",
            is_manual_correction=True,
            corrected_at=datetime.utcnow()
        )
        db.add(categorization)
    
    db.commit()
    
    return {
        "message": "Article recategorized successfully",
        "article_id": article_id,
        "categories": request.company_ids
    }