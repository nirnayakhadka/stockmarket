from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Article
from app.schemas import ArticleResponse, ArticleListOut

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/", response_model=List[ArticleResponse])
def get_news(
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get news articles, optionally filtered by company"""
    query = db.query(Article)
    
    # If company_id is provided, filter by company
    if company_id:
        from app.models import NewsCategorization
        query = query.join(NewsCategorization).filter(NewsCategorization.company_id == company_id).distinct()
    
    articles = query.offset(skip).limit(limit).all()
    return articles


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a specific article by ID"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article