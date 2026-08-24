import re
from datetime import datetime
from typing import List, Optional

import httpx

from app.crawlers.base import BaseCrawler, CrawledArticle


class MeroLaganiCrawler(BaseCrawler):
    """
    Crawler for merolagani.com's news section.

    NOTE ON SELECTORS: merolagani.com (like the other portals here) changes
    its markup periodically and this environment has no outbound network
    access to the live site to verify selectors at write time. The
    discovery/parsing logic below follows the site's *typical* structure
    (a news listing with anchor cards linking to `/news/...` detail pages,
    each detail page having an `h1` headline, a `.news-details`/article body
    container, and a date near the top). Before running against production,
    do a quick `view-source` check on a couple of live pages and adjust the
    CSS selectors in `list_article_urls` / `parse_article` — the robots.txt
    compliance, dedup, delay, and error handling around them do not need to
    change.
    """

    source_portal = "merolagani"
    base_url = "https://merolagani.com"
    listing_paths = ["/News.aspx", "/NewsList.aspx"]

    async def list_article_urls(self, client: httpx.AsyncClient) -> List[str]:
        urls: set[str] = set()
        for path in self.listing_paths:
            html = await self._fetch(self._abs_url(path))
            if not html:
                continue
            soup = self._soup(html)
            for a in soup.select("a[href*='NewsDetail'], a[href*='/news/']"):
                href = a.get("href")
                if href:
                    urls.add(self._abs_url(href))
        return list(urls)

    def parse_article(self, html: str, url: str) -> Optional[CrawledArticle]:
        soup = self._soup(html)

        headline_el = soup.select_one("h1") or soup.select_one(".news-title") or soup.select_one("title")
        if not headline_el:
            return None
        headline = headline_el.get_text(strip=True)

        body_el = (
            soup.select_one(".news-details")
            or soup.select_one(".content-details")
            or soup.select_one("article")
        )
        body_text = body_el.get_text(" ", strip=True) if body_el else ""
        if not body_text:
            # Fallback: concatenate paragraph tags near the headline
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

        date_el = soup.select_one(".news-date, .date, .published-date")
        if date_el:
            text = date_el.get_text(strip=True)
            match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
            if match:
                try:
                    return datetime.strptime(match.group(1), "%Y-%m-%d")
                except ValueError:
                    return None
        return None
