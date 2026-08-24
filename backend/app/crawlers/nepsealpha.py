import re
from datetime import datetime
from typing import List, Optional

import httpx

from app.crawlers.base import BaseCrawler, CrawledArticle


class NepseAlphaCrawler(BaseCrawler):
    """
    Crawler for nepsealpha.com's news section.
    Same selector-verification caveat as the other portal crawlers — see
    merolagani.py for details.
    """

    source_portal = "nepsealpha"
    base_url = "https://nepsealpha.com"
    listing_paths = ["/news"]

    async def list_article_urls(self, client: httpx.AsyncClient) -> List[str]:
        urls: set[str] = set()
        for path in self.listing_paths:
            html = await self._fetch(self._abs_url(path))
            if not html:
                continue
            soup = self._soup(html)
            for a in soup.select("a[href*='/news/']"):
                href = a.get("href")
                if href and href.rstrip("/") != "/news":
                    urls.add(self._abs_url(href))
        return list(urls)

    def parse_article(self, html: str, url: str) -> Optional[CrawledArticle]:
        soup = self._soup(html)

        headline_el = soup.select_one("h1")
        if not headline_el:
            return None
        headline = headline_el.get_text(strip=True)

        body_el = soup.select_one("article") or soup.select_one(".news-content")
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
        time_el = soup.select_one("time")
        if time_el and time_el.get("datetime"):
            try:
                return datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
            except ValueError:
                pass
        text = soup.get_text(" ", strip=True)
        match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                return None
        return None
