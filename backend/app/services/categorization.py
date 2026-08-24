import re
import logging
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session

from app.models import Company, Article, NewsCategorization

logger = logging.getLogger(__name__)


class NewsCategorizer:
    """Categorize news articles by company using keyword matching"""
    
    def __init__(self, db: Session):
        self.db = db
        self.company_keywords = self._build_keyword_index()
        
    def _build_keyword_index(self) -> Dict[int, List[str]]:
        """Build a keyword index for all companies"""
        companies = self.db.query(Company).all()
        keyword_index = {}
        
        for company in companies:
            keywords = []
            # Add company symbol
            keywords.append(company.symbol.lower())
            # Add company name words
            name_words = company.name.lower().split()
            keywords.extend(name_words)
            # Add sector
            if company.sector:
                keywords.append(company.sector.lower())
            
            keyword_index[company.id] = keywords
        
        return keyword_index
    
    def categorize_article(self, article: Article) -> List[Tuple[int, float]]:
        """
        Categorize an article and return list of (company_id, confidence_score)
        """
        # Combine headline and body for matching
        text = (article.headline + " " + article.body_text).lower()
        
        matches = []
        for company_id, keywords in self.company_keywords.items():
            score = self._calculate_match_score(text, keywords)
            if score > 0:
                matches.append((company_id, score))
        
        # Sort by confidence and return
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Return only matches above threshold, limit to top 3
        threshold = 0.1
        return [m for m in matches if m[1] >= threshold][:3]
    
    def _calculate_match_score(self, text: str, keywords: List[str]) -> float:
        """
        Calculate match score based on keyword frequency
        """
        score = 0.0
        matched_keywords = []
        
        for keyword in keywords:
            # Count occurrences
            count = text.count(keyword)
            if count > 0:
                # Boost score for exact symbol matches
                if keyword == keywords[0]:  # First keyword is usually the symbol
                    count *= 3
                score += count * 0.1
                matched_keywords.append(keyword)
        
        # Normalize score
        if score > 0:
            score = min(score, 1.0)
        
        return score
    
    def categorize_articles(self, articles: List[Article]) -> int:
        """
        Categorize multiple articles and save results
        """
        categorized_count = 0
        
        for article in articles:
            # Check if already categorized
            existing = self.db.query(NewsCategorization).filter(
                NewsCategorization.article_id == article.id
            ).first()
            if existing:
                continue
            
            # Get matches
            matches = self.categorize_article(article)
            
            for company_id, score in matches:
                categorization = NewsCategorization(
                    article_id=article.id,
                    company_id=company_id,
                    confidence_score=score,
                    method="keyword_matching",
                    is_manual_correction=False
                )
                self.db.add(categorization)
                categorized_count += 1
        
        self.db.commit()
        return categorized_count