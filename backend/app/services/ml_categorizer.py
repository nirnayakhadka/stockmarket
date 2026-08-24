import re
import logging
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session

from app.models import Company, Article, NewsCategorization

logger = logging.getLogger(__name__)


class MLCategorizer:
    """
    News categorizer using keyword matching and ML techniques
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.companies = db.query(Company).all()
        self.company_names = [c.name.lower() for c in self.companies]
        self.company_symbols = [c.symbol.lower() for c in self.companies]
        self.company_keywords = self._build_keyword_index()
        
    def _build_keyword_index(self) -> Dict[int, List[str]]:
        """Build comprehensive keyword index"""
        keyword_index = {}
        for company in self.companies:
            keywords = []
            # Company symbol
            keywords.append(company.symbol.lower())
            # Company name parts
            name_parts = company.name.lower().replace('limited', '').replace('ltd', '').strip().split()
            keywords.extend(name_parts)
            # Common abbreviations
            if company.symbol == "NABIL":
                keywords.extend(["nabil bank", "nabil"])
            elif company.symbol == "NICA":
                keywords.extend(["nic asia", "nic"])
            elif company.symbol == "GBIME":
                keywords.extend(["global ime", "ime"])
            # Sector
            if company.sector:
                keywords.append(company.sector.lower())
            
            # Remove duplicates and short words
            keyword_index[company.id] = list(set([k for k in keywords if len(k) > 2]))
        
        return keyword_index
    
    def _keyword_match_score(self, text: str, company_id: int) -> float:
        """Calculate keyword-based match score"""
        score = 0.0
        keywords = self.company_keywords.get(company_id, [])
        
        for keyword in keywords:
            # Count occurrences with word boundaries
            count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text.lower()))
            if count > 0:
                # Boost exact symbol matches
                if keyword.upper() in [s.upper() for s in self.company_symbols]:
                    score += count * 0.3
                else:
                    score += count * 0.1
        
        return min(score, 1.0)
    
    def categorize_article(self, article: Article) -> List[Tuple[int, float, str]]:
        """
        Categorize an article using keyword matching
        Returns: [(company_id, confidence, method), ...]
        """
        text = (article.headline + " " + article.body_text)[:10000]
        
        results = {}
        methods_used = []
        
        # Keyword matching
        for company in self.companies:
            score = self._keyword_match_score(text, company.id)
            if score > 0.1:
                results[company.id] = results.get(company.id, 0) + score * 0.4
        methods_used.append("keyword")
        
        # Normalize and filter
        final_results = []
        for company_id, score in results.items():
            normalized_score = min(score, 1.0)
            if normalized_score >= 0.15:  # Threshold
                final_results.append((
                    company_id,
                    round(normalized_score, 4),
                    "+".join(methods_used)
                ))
        
        # Sort by confidence
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        return final_results[:3]  # Max 3 companies
    
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
            
            for company_id, score, method in matches:
                categorization = NewsCategorization(
                    article_id=article.id,
                    company_id=company_id,
                    confidence_score=score,
                    method=method,
                    is_manual_correction=False
                )
                self.db.add(categorization)
                categorized_count += 1
        
        self.db.commit()
        return categorized_count