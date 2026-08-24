import re
from datetime import datetime
from typing import List, Optional

import httpx

from app.crawlers.base import BaseCrawler, CrawledArticle


class ShareSansarCrawler(BaseCrawler):
    """
    Crawler for sharesansar.com's news section.
    See the selector note in merolagani.py — same caveat applies here:
    verify `list_article_urls`/`parse_article` selectors against the live
    DOM before production use; the surrounding compliance/dedup/error
    handling is portal-agnostic and reusable as-is.
    """

    source_portal = "sharesansar"
    base_url = "https://www.sharesansar.com"
    listing_paths = ["/category/latest", "/category/news"]

    async def list_article_urls(self, client: httpx.AsyncClient) -> List[str]:
        urls: set[str] = set()
        for path in self.listing_paths:
            html = await self._fetch(self._abs_url(path))
            if not html:
                continue
            soup = self._soup(html)
            for a in soup.select("a.newsblog-list-content, .news-caption a, h4 a, h3 a"):
                href = a.get("href")
                if href:
                    urls.add(self._abs_url(href))
        return list(urls)

    def parse_article(self, html: str, url: str) -> Optional[CrawledArticle]:
        soup = self._soup(html)

        headline_el = soup.select_one("h1") or soup.select_one(".page-title")
        if not headline_el:
            return None
        headline = headline_el.get_text(strip=True)

        body_el = soup.select_one(".detail-news-content") or soup.select_one("article")
        body_text = body_el.get_text(" ", strip=True) if body_el else ""
        if not body_text:
            paras = soup.select("p")
            body_text = " ".join(p.get_text(" ", strip=True) for p in paras[:15])

        published_at = self._extract_date(soup)

        return CrawledArticle(
            headline=headline,
            body_text=body_text,
            url=url,
            source_portal=self.source_portal,
            published_at=published_at,
        )

    @staticmethod
    def _extract_date(soup) -> Optional[datetime]:
        date_el = soup.select_one(".news-post-meta, .date, .posted-date")
        if date_el:
            text = date_el.get_text(strip=True)
            match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
            if match:
                try:
                    return datetime.strptime(match.group(1), "%Y-%m-%d")
                except ValueError:
                    return None
        return None
