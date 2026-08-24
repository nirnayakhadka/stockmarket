from app.crawlers.merolagani import MeroLaganiCrawler
from app.crawlers.sharesansar import ShareSansarCrawler
from app.crawlers.nepsealpha import NepseAlphaCrawler
from app.crawlers.bizmandu import BizmanduCrawler

# Registry used by the crawl service / admin API.
# Add new portals here — everything else (dedup, storage, run tracking)
# is handled generically by BaseCrawler + CrawlService.
CRAWLER_REGISTRY = {
    "merolagani": MeroLaganiCrawler,
    "sharesansar": ShareSansarCrawler,
    "nepsealpha": NepseAlphaCrawler,
    "bizmandu": BizmanduCrawler,
}
