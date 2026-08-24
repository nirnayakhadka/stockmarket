
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger("nepse_market_client")

NEPSE_BASE = "https://nepalstock.com.np"

# Static obfuscation tables — copied verbatim from nepseDataService.js
DATA_ARR = [
    9, 8, 4, 1, 2, 3, 2, 5, 8, 7, 9, 8, 0, 3, 1, 2, 2, 4, 3, 0, 1, 9, 5, 4, 6, 3,
    7, 2, 1, 6, 9, 8, 4, 1, 2, 2, 3, 3, 4, 4,
]
DUMMY_DATA = [
    190, 189, 178, 172, 177, 169, 167, 160, 163, 176, 145, 153, 138, 149, 136,
    152, 140, 166, 188, 133, 132, 134, 135, 137, 139, 141, 142, 143, 144, 146,
    147, 148, 150, 151, 154, 155, 156, 157, 158, 159, 161, 162, 164, 165, 168,
    170, 171, 173, 174, 175, 179, 180, 181, 182, 183, 184, 185, 186, 187, 191,
]


def _decode1(salt_num: int, data: list[int]) -> int:
    idx = (
        (salt_num // 10) % 10
        + (salt_num - (salt_num // 10) * 10)
        + (salt_num // 100) % 10
    )
    return data[idx] + 22


def _decode2(salt_num: int, data: list[int]) -> int:
    idx = (
        (salt_num // 10) % 10
        + (salt_num // 100) % 10
        + (salt_num - (salt_num // 10) * 10)
    )
    return data[idx] + (salt_num // 10) % 10 + (salt_num // 100) % 10 + 22


# Process-global token cache — same tradeoff as the JS module-level cache.
_token_cache: Optional[dict] = None
_token_expiry_ms: float = 0


def _now_ms() -> float:
    return datetime.utcnow().timestamp() * 1000


class NepseMarketClient:
    """
    Async client for nepalstock.com.np's obfuscated token-auth API.
    One instance can be reused across a scheduled job run; call `.aclose()`
    when done.
    """

    def __init__(self):
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nepalstock.com.np/",
                "Origin": "https://www.nepalstock.com.np",
                "Content-Type": "application/json",
            },
            timeout=settings.request_timeout_seconds,
            verify=getattr(settings, "verify_ssl", True),
        )

    async def aclose(self):
        await self._client.aclose()

    async def _get_token(self) -> dict:
        global _token_cache, _token_expiry_ms
        if _token_cache and _now_ms() < _token_expiry_ms:
            return _token_cache

        resp = await self._client.get(f"{NEPSE_BASE}/api/authenticate/prove")
        resp.raise_for_status()
        logger.info("Prove response cookies: %s", dict(resp.cookies))
        data = resp.json()

        access_token = data["accessToken"]
        refresh_token = data["refreshToken"]
        salt1 = data["salt1"]
        salt2 = data["salt2"]

        num1 = _decode1(salt2, DATA_ARR)
        num2 = _decode2(salt2, DATA_ARR)
        num3 = _decode1(salt1, DATA_ARR)
        num4 = _decode2(salt1, DATA_ARR)

        valid_access_token = (
            access_token[:num1] + access_token[num1 + 1 : num2] + access_token[num2 + 1 :]
        )
        valid_refresh_token = (
            refresh_token[:num3] + refresh_token[num3 + 1 : num4] + refresh_token[num4 + 1 :]
        )

        _token_cache = {"accessToken": valid_access_token, "refreshToken": valid_refresh_token}
        _token_expiry_ms = _now_ms() + 55_000
        logger.info("Decoded token (len=%d): %s...", len(valid_access_token), valid_access_token[:12])
        return _token_cache

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        token = await self._get_token()
        resp = await self._client.get(
            f"{NEPSE_BASE}/api/nots/{path}",
            headers={"Authorization": f"Salter {token['accessToken']}"},
            params=params or {},
        )
        resp.raise_for_status()
        if not resp.text.strip():
            logger.error(
                "Empty body from GET %s (status=%s, headers=%s)",
                path, resp.status_code, dict(resp.headers),
            )
            raise ValueError(f"Empty response from NEPSE API for {path}")
        return resp.json()

    async def _post(self, path: str, body: Optional[dict] = None) -> Any:
        token = await self._get_token()
        resp = await self._client.post(
            f"{NEPSE_BASE}/api/nots/{path}",
            headers={"Authorization": f"Salter {token['accessToken']}"},
            json=body or {},
        )
        resp.raise_for_status()
        if not resp.text.strip():
            logger.error(
                "Empty body from POST %s (status=%s, headers=%s)",
                path, resp.status_code, dict(resp.headers),
            )
            raise ValueError(f"Empty response from NEPSE API for {path}")
        return resp.json()

    async def fetch_market_open(self) -> dict:
        data = await self._get("nepse-data/market-open")
        return {
            "is_open": data.get("isOpen") != "CLOSE",
            "is_open_raw": data.get("isOpen"),
            "as_of": data.get("asOf"),
            "dummy_id": data.get("id"),
        }

    async def fetch_today_price(self, dummy_id: Optional[int] = None) -> list[dict]:
        """
        Returns today's snapshot for ALL scrips: symbol, ltp (== close for
        the day), open/high/low, volume, turnover, transactions. This is
        the source for daily OHLCV — call once per trading day (e.g. after
        market close) to build up real historical rows over time.
        """
        body_id = DUMMY_DATA[dummy_id % len(DUMMY_DATA)] if dummy_id else DUMMY_DATA[0]
        data = await self._post("nepse-data/today-price", {"id": body_id})
        if not isinstance(data, list):
            return []
        return [
            {
                "symbol": s.get("symbol"),
                "ltp": s.get("lastTradedPrice"),
                "open_price": s.get("openPrice"),
                "high_price": s.get("highPrice"),
                "low_price": s.get("lowPrice"),
                "prev_close": s.get("previousClose"),
                "volume": s.get("totalTradedQuantity"),
                "turnover": s.get("totalTradedValue"),
                "transactions": s.get("totalTrades"),
            }
            for s in data
        ]

    async def fetch_floorsheet(self, page: int = 0, size: int = 500) -> dict:
        """
        Raw floorsheet page from the official API: contractId, stockSymbol,
        buyerMemberId, sellerMemberId, contractQuantity, contractRate,
        contractAmount. Only covers the current trading day (this endpoint
        does not accept a historical businessDate on the free tier — passing
        one is a no-op in the JS version too, kept here for parity).
        """
        data = await self._get("nepse-data/floorsheet", {"page": page, "size": size, "businessDate": ""})
        return data


async def collect_watchlist_prices(watchlist_symbols: set[str]) -> list[dict]:
    """
    Convenience wrapper: authenticate, fetch market-open + today-price,
    filter to only the symbols we track. Returns a list of dicts ready to
    map onto DailyPrice rows (caller attaches company_id + date).
    """
    client = NepseMarketClient()
    try:
        market_open = await client.fetch_market_open()
        prices = await client.fetch_today_price(market_open.get("dummy_id"))
        return [p for p in prices if p.get("symbol") in watchlist_symbols]
    finally:
        await client.aclose()


async def collect_watchlist_floorsheet(watchlist_symbols: set[str], max_pages: int = 5) -> list[dict]:
    """
    Fetches up to `max_pages` of the floorsheet (500 rows/page) and filters
    to watchlist symbols. The official floorsheet can run into the
    thousands of rows across the whole market; max_pages caps how deep we
    page before giving up, since only watchlist rows matter here.
    """
    client = NepseMarketClient()
    matched: list[dict] = []
    try:
        for page in range(max_pages):
            raw = await client.fetch_floorsheet(page=page)
            content = (raw.get("floorsheets") or {}).get("content") or raw.get("content") or []
            if not content:
                break
            for f in content:
                symbol = f.get("stockSymbol") or f.get("symbol")
                if symbol in watchlist_symbols:
                    matched.append(
                        {
                            "symbol": symbol,
                            "buyer_broker": str(f.get("buyerMemberId") or f.get("buyerBroker") or ""),
                            "seller_broker": str(f.get("sellerMemberId") or f.get("sellerBroker") or ""),
                            "quantity": int(f.get("contractQuantity") or f.get("quantity") or 0),
                            "rate": float(f.get("contractRate") or f.get("rate") or 0),
                            "amount": float(f.get("contractAmount") or f.get("amount") or 0),
                        }
                    )
            if len(content) < 500:
                break  # last page
        return matched
    finally:
        await client.aclose()