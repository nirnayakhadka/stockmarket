import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, TypedDict
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger("crawler")


class CrawledArticle(TypedDict):
    headline: str
    body_text: str
    url: str
    source_portal: str
    published_at: Optional[datetime]


class RobotsDisallowed(Exception):
    """Raised when robots.txt forbids fetching a given URL."""


class BaseCrawler(ABC):
    """
    Shared plumbing for every portal crawler:
      - robots.txt compliance (checked once per host, cached)
      - a fixed crawl delay between requests (politeness, not just speed)
      - a consistent, identifiable User-Agent
      - graceful handling of request failures/timeouts (never raises out
        of `run()` — caller collects `errors` and moves on to the next portal)

    Subclasses only implement `list_article_urls()` (find links on a
    listing/section page) and `parse_article(html, url)` (extract headline/
    body/date from a single article page). This keeps each portal's
    site-specific selectors isolated and easy to read/maintain independently.
    """

    source_portal: str = "unknown"
    base_url: str = ""
    listing_paths: List[str] = []  # section/listing pages to discover article links from
    max_articles_per_run: int = 40

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._robots: Optional[RobotFileParser] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": settings.user_agent},
                timeout=settings.request_timeout_seconds,
                follow_redirects=True,
            )
        return self._client

    async def _load_robots(self) -> RobotFileParser:
        if self._robots is not None:
            return self._robots

        parsed = urlparse(self.base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            client = await self._get_client()
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                # No robots.txt (or inaccessible) => treat as "allow all" per RFC convention
                rp.parse([])
        except httpx.HTTPError:
            logger.warning("Could not fetch robots.txt for %s; defaulting to allow", self.base_url)
            rp.parse([])

        self._robots = rp
        return rp

    async def _allowed(self, url: str) -> bool:
        rp = await self._load_robots()
        return rp.can_fetch(settings.user_agent, url)

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch a URL respecting robots.txt and the configured crawl delay."""
        if not await self._allowed(url):
            logger.info("robots.txt disallows %s — skipping", url)
            raise RobotsDisallowed(url)

        client = await self._get_client()
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Fetch failed for %s: %s", url, exc)
            return None
        finally:
            # Politeness delay applies after every request, success or fail
            await asyncio.sleep(settings.crawl_delay_seconds)

        return resp.text

    def _abs_url(self, href: str) -> str:
        return urljoin(self.base_url, href)

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    async def list_article_urls(self, client: httpx.AsyncClient) -> List[str]:
        """Return candidate article URLs discovered from this portal's listing pages."""
        raise NotImplementedError

    @abstractmethod
    def parse_article(self, html: str, url: str) -> Optional[CrawledArticle]:
        """Parse a single article page into a CrawledArticle, or None if unparseable."""
        raise NotImplementedError

    async def run(self) -> List[CrawledArticle]:
        """
        Full crawl for this portal: discover links, fetch each, parse.
        Never raises — failures on individual articles are logged and skipped
        so one bad page doesn't kill the whole run.
        """
        articles: List[CrawledArticle] = []
        client = await self._get_client()

        try:
            urls = await self.list_article_urls(client)
        except RobotsDisallowed:
            logger.warning("robots.txt disallows listing pages for %s", self.source_portal)
            return articles
        except Exception:
            logger.exception("Failed to list article URLs for %s", self.source_portal)
            return articles

        seen_this_run = set()
        for url in urls[: self.max_articles_per_run]:
            if url in seen_this_run:
                continue
            seen_this_run.add(url)

            try:
                html = await self._fetch(url)
            except RobotsDisallowed:
                continue
            if not html:
                continue

            try:
                article = self.parse_article(html, url)
            except Exception:
                logger.exception("Failed to parse article %s", url)
                continue

            if article and article["headline"] and article["body_text"]:
                articles.append(article)

        if self._client:
            await self._client.aclose()
            self._client = None

        return articles
