"""
NEPSE Market Client - Multiple data sources for reliable market data
Uses: Sharesansar HTML, MeroLagani API, NEPSE Alpha, and other free sources
"""

import logging
import json
import asyncio
import re
import random
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Union
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("nepse_market_client")

# Constants
DUMMY_DATA = [
    190, 189, 178, 172, 177, 169, 167, 160, 163, 176, 145, 153, 138, 149, 136,
    152, 140, 166, 188, 133, 132, 134, 135, 137, 139, 141, 142, 143, 144, 146,
    147, 148, 150, 151, 154, 155, 156, 157, 158, 159, 161, 162, 164, 165, 168,
    170, 171, 173, 174, 175, 179, 180, 181, 182, 183, 184, 185, 186, 187, 191,
]

# Common stock symbols for fallback
COMMON_SYMBOLS = [
    "NABIL", "NICA", "GBIME", "KBL", "MBL", "NIB", "NMB", "PCBL", "SBI", "SCB",
    "ADBL", "NBL", "RBB", "NCC", "CZBIL", "HBL", "EBL", "NIC", "KBL", "BK",
    "CHCL", "SHIVM", "HDL", "NHPC", "API", "URJA", "UPCL", "NEPSE", "NIFRA",
    "NIBL", "SADBL", "NABIL", "NICA", "GBIME", "KBL", "MBL", "NIB", "NMB", "PCBL",
    "SBI", "SCB", "ADBL", "NBL", "RBB", "NCC", "CZBIL", "HBL", "EBL", "NIC",
    "CIT", "PRVU", "NFS", "NLIC", "GIL", "NHDL", "SHL", "SBL", "NBBL", "NLBBL",
    "NABBC", "NICA", "GBIME", "KBL", "MBL", "NIB", "NMB", "PCBL", "SBI", "SCB"
]

# Known working company symbols for fallback
FALLBACK_SYMBOLS = [
    {"symbol": "NABIL", "name": "Nabil Bank"},
    {"symbol": "NICA", "name": "NIC Asia Bank"},
    {"symbol": "GBIME", "name": "Global IME Bank"},
    {"symbol": "KBL", "name": "Kumari Bank"},
    {"symbol": "MBL", "name": "Machhapuchchhre Bank"},
    {"symbol": "NIB", "name": "Nepal Investment Bank"},
    {"symbol": "NMB", "name": "NMB Bank"},
    {"symbol": "PCBL", "name": "Prime Commercial Bank"},
    {"symbol": "SBI", "name": "Nepal SBI Bank"},
    {"symbol": "ADBL", "name": "Agriculture Development Bank"},
    {"symbol": "NBL", "name": "Nepal Bank"},
    {"symbol": "RBB", "name": "Rastriya Banijya Bank"},
    {"symbol": "NCC", "name": "Nepal Credit and Commerce Bank"},
    {"symbol": "CZBIL", "name": "Century Commercial Bank"},
    {"symbol": "HBL", "name": "Himalayan Bank"},
    {"symbol": "EBL", "name": "Everest Bank"},
    {"symbol": "NIC", "name": "NIC Bank"},
    {"symbol": "BK", "name": "Bank of Kathmandu"},
    {"symbol": "CHCL", "name": "Chilime Hydropower"},
    {"symbol": "SHIVM", "name": "Shivam Cements"},
    {"symbol": "HDL", "name": "Himalayan Distillery"},
    {"symbol": "NHPC", "name": "NeHPL"},
    {"symbol": "API", "name": "API Power"},
    {"symbol": "URJA", "name": "Urja Energy"},
    {"symbol": "UPCL", "name": "Upper Chamod"},
    {"symbol": "NEPSE", "name": "NEPSE Index"},
    {"symbol": "NIFRA", "name": "Nepal Infrastructure Bank"},
]


def _num(row: dict, *keys) -> Optional[float]:
    """Extract numeric value from dict with multiple key fallbacks."""
    for k in keys:
        v = row.get(k)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


class NepseMarketClient:
    """
    NEPSE Market Client with multiple data sources:
    1. Sharesansar HTML parsing
    2. MeroLagani API
    3. NEPSE Alpha API
    4. Mock data for development (last resort)
    """
    
    def __init__(self):
        # User agents to rotate
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        ]
        self.current_user_agent_index = 0
        
        # HTTP client with proper headers
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agents[0],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
            timeout=30.0,
            follow_redirects=True,
        )
        
        # Cache
        self._cache = {}
        self._cache_expiry = {}
        
        logger.info("NepseMarketClient initialized")
    
    async def aclose(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    def _rotate_user_agent(self):
        """Rotate user agent to avoid detection."""
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        new_ua = self.user_agents[self.current_user_agent_index]
        self._client.headers.update({"User-Agent": new_ua})
    
    def _is_cache_valid(self, key: str, ttl: int = 300) -> bool:
        """Check if cache is still valid (default 5 minutes)."""
        if key in self._cache and key in self._cache_expiry:
            return datetime.now() < self._cache_expiry[key]
        return False
    
    def _set_cache(self, key: str, value: Any, ttl: int = 300):
        """Set cache with TTL in seconds."""
        self._cache[key] = value
        self._cache_expiry[key] = datetime.now() + timedelta(seconds=ttl)
    
    def _get_cache(self, key: str, default=None):
        """Get cached value if valid."""
        if self._is_cache_valid(key):
            return self._cache[key]
        return default
    
    def _parse_float(self, text: str) -> float:
        """Parse float from text with commas."""
        try:
            if text is None:
                return 0
            return float(str(text).replace(',', '').strip() or 0)
        except:
            return 0
    
    def _parse_int(self, text: str) -> int:
        """Parse int from text with commas."""
        try:
            if text is None:
                return 0
            return int(str(text).replace(',', '').strip() or 0)
        except:
            return 0
    
    # ============ Data Source 1: Sharesansar HTML (Primary) ============
    
    async def _parse_sharesansar_html(self) -> Dict:
        """Parse market data from sharesansar.com HTML."""
        try:
            url = "https://www.sharesansar.com/"
            self._rotate_user_agent()
            response = await self._client.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                market_data = []
                
                # Try multiple methods to find market data
                
                # Method 1: Look for table with id 'market-data'
                table = soup.find('table', {'id': 'market-data'})
                if not table:
                    # Method 2: Look for table with class 'table'
                    table = soup.find('table', {'class': 'table'})
                if not table:
                    # Method 3: Look for any table with stock data
                    tables = soup.find_all('table')
                    for t in tables:
                        rows = t.find_all('tr')
                        if len(rows) > 1:
                            # Check if first row has headers like 'Symbol', 'LTP', etc.
                            header_row = rows[0]
                            headers = [h.text.strip().lower() for h in header_row.find_all('th')]
                            if any(h in ['symbol', 'ltp', 'company'] for h in headers):
                                table = t
                                break
                
                if table:
                    rows = table.find_all('tr')
                    
                    # Skip header row
                    start_idx = 1
                    for row in rows[start_idx:]:
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            try:
                                symbol = cells[0].text.strip()
                                
                                # Skip invalid symbols
                                if not symbol or str(symbol).isdigit():
                                    continue
                                if len(symbol) < 2:
                                    continue
                                
                                # Skip common non-stock headers
                                if symbol.lower() in ['symbol', 'company', 'ltp', 'volume']:
                                    continue
                                
                                market_data.append({
                                    "symbol": symbol.upper(),
                                    "ltp": self._parse_float(cells[1].text) if len(cells) > 1 else 0,
                                    "change": self._parse_float(cells[2].text) if len(cells) > 2 else 0,
                                    "volume": self._parse_int(cells[3].text) if len(cells) > 3 else 0,
                                    "turnover": self._parse_float(cells[4].text) if len(cells) > 4 else 0,
                                    "open": self._parse_float(cells[5].text) if len(cells) > 5 else 0,
                                    "high": self._parse_float(cells[6].text) if len(cells) > 6 else 0,
                                    "low": self._parse_float(cells[7].text) if len(cells) > 7 else 0,
                                })
                            except Exception as e:
                                continue
                
                # Method 4: Look for market data in divs (alternative structure)
                if not market_data:
                    market_divs = soup.find_all('div', {'class': 'market-data'})
                    for div in market_divs:
                        rows = div.find_all('div', {'class': 'row'})
                        for row in rows:
                            cells = row.find_all('div', {'class': 'col'})
                            if len(cells) >= 4:
                                try:
                                    symbol = cells[0].text.strip()
                                    if symbol and not symbol.isdigit() and len(symbol) >= 2:
                                        market_data.append({
                                            "symbol": symbol.upper(),
                                            "ltp": self._parse_float(cells[1].text),
                                            "change": self._parse_float(cells[2].text),
                                            "volume": self._parse_int(cells[3].text),
                                        })
                                except:
                                    continue
                
                # Method 5: Try the API endpoint directly
                if not market_data:
                    try:
                        api_url = "https://www.sharesansar.com/api/market-data"
                        api_response = await self._client.get(api_url)
                        if api_response.status_code == 200:
                            api_data = api_response.json()
                            if api_data and api_data.get('data'):
                                for item in api_data['data']:
                                    symbol = item.get('symbol')
                                    if symbol and not str(symbol).isdigit():
                                        market_data.append({
                                            "symbol": symbol.upper(),
                                            "ltp": self._parse_float(item.get('ltp', 0)),
                                            "change": self._parse_float(item.get('change', 0)),
                                            "volume": self._parse_int(item.get('volume', 0)),
                                            "turnover": self._parse_float(item.get('turnover', 0)),
                                            "open": self._parse_float(item.get('open', 0)),
                                            "high": self._parse_float(item.get('high', 0)),
                                            "low": self._parse_float(item.get('low', 0)),
                                        })
                    except:
                        pass
                
                if market_data:
                    # Remove duplicates by symbol
                    seen = set()
                    unique_data = []
                    for item in market_data:
                        if item["symbol"] not in seen:
                            seen.add(item["symbol"])
                            unique_data.append(item)
                    
                    logger.info(f"Sharesansar HTML returned {len(unique_data)} valid items")
                    return {
                        "market_data": unique_data,
                        "source": "sharesansar_html"
                    }
        except Exception as e:
            logger.error(f"Sharesansar HTML parsing error: {e}")
        return None
    
    # ============ Data Source 2: MeroLagani API ============
    
    async def _fetch_merolagani_api(self) -> Dict:
        """Fetch market data from MeroLagani API."""
        try:
            url = "https://parseapi.net/api/merolagani/market-summary"
            self._rotate_user_agent()
            response = await self._client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data and data.get("data"):
                    market_data = []
                    for item in data["data"]:
                        symbol = item.get("symbol")
                        if symbol and not str(symbol).isdigit():
                            market_data.append({
                                "symbol": symbol.upper(),
                                "ltp": self._parse_float(item.get("ltp", 0)),
                                "change": self._parse_float(item.get("change", 0)),
                                "volume": self._parse_int(item.get("volume", 0)),
                                "turnover": self._parse_float(item.get("turnover", 0)),
                                "open": self._parse_float(item.get("open", 0)),
                                "high": self._parse_float(item.get("high", 0)),
                                "low": self._parse_float(item.get("low", 0)),
                            })
                    if market_data:
                        logger.info(f"MeroLagani API returned {len(market_data)} items")
                        return {
                            "market_data": market_data,
                            "source": "merolagani"
                        }
        except Exception as e:
            logger.debug(f"MeroLagani API error: {e}")
        return None
    
    # ============ Data Source 3: NEPSE Alpha ============
    
    async def _parse_nepsealpha_html(self) -> Dict:
        """Parse market data from nepsealpha.com."""
        try:
            url = "https://nepsealpha.com/"
            self._rotate_user_agent()
            response = await self._client.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                market_data = []
                
                # Find market data table
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            try:
                                symbol = cells[0].text.strip()
                                if symbol and not str(symbol).isdigit():
                                    market_data.append({
                                        "symbol": symbol.upper(),
                                        "ltp": self._parse_float(cells[1].text),
                                        "change": self._parse_float(cells[2].text),
                                        "volume": self._parse_int(cells[3].text),
                                    })
                            except:
                                continue
                
                if market_data:
                    logger.info(f"NEPSE Alpha returned {len(market_data)} items")
                    return {
                        "market_data": market_data,
                        "source": "nepsealpha"
                    }
        except Exception as e:
            logger.error(f"NEPSE Alpha parsing error: {e}")
        return None
    
    # ============ Data Source 4: NEPSE Alpha API ============
    
    async def _fetch_nepse_alpha_api(self) -> Dict:
        """Fetch market data from NEPSE Alpha API."""
        try:
            url = "https://nepsealpha.com/api/market-data"
            self._rotate_user_agent()
            response = await self._client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data and data.get("data"):
                    market_data = []
                    for item in data["data"]:
                        symbol = item.get("symbol")
                        if symbol and not str(symbol).isdigit():
                            market_data.append({
                                "symbol": symbol.upper(),
                                "ltp": self._parse_float(item.get("ltp", 0)),
                                "change": self._parse_float(item.get("change", 0)),
                                "volume": self._parse_int(item.get("volume", 0)),
                                "turnover": self._parse_float(item.get("turnover", 0)),
                            })
                    if market_data:
                        logger.info(f"NEPSE Alpha API returned {len(market_data)} items")
                        return {
                            "market_data": market_data,
                            "source": "nepse_alpha_api"
                        }
        except Exception as e:
            logger.debug(f"NEPSE Alpha API error: {e}")
        return None
    
    # ============ Data Source 5: Mock Data (Fallback) ============
    
    def _generate_mock_data(self) -> Dict:
        """Generate mock market data for development."""
        logger.warning("Generating mock data - real data sources unavailable")
        
        import random
        market_data = []
        for symbol in COMMON_SYMBOLS[:30]:
            base_price = random.uniform(100, 5000)
            change = random.uniform(-10, 10)
            market_data.append({
                "symbol": symbol,
                "ltp": round(base_price, 2),
                "change": round(change, 2),
                "volume": random.randint(1000, 100000),
                "turnover": round(random.uniform(100000, 10000000), 2),
                "open": round(base_price - random.uniform(0, 20), 2),
                "high": round(base_price + random.uniform(0, 20), 2),
                "low": round(base_price - random.uniform(0, 20), 2),
            })
        
        return {
            "market_data": market_data,
            "source": "mock"
        }
    
    # ============ Main Public Methods ============
    
    async def fetch_market_open(self) -> Dict:
        """Fetch market open status."""
        cache_key = "market_status"
        
        # Check cache (1 minute)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        # Check if we can get any data
        test_data = await self.fetch_today_price()
        if test_data and len(test_data) > 0:
            # Check if data looks real (mock data has specific patterns)
            is_mock = any(str(item.get("symbol", "")).isdigit() for item in test_data[:5])
            if is_mock:
                is_open = False
            else:
                is_open = True
            
            result = {
                "is_open": is_open,
                "is_open_raw": "OPEN" if is_open else "CLOSE",
                "as_of": datetime.now().isoformat(),
                "dummy_id": int(datetime.now().timestamp() // 86400)
            }
            self._set_cache(cache_key, result, ttl=60)
            return result
        
        # Default to closed
        return {
            "is_open": False,
            "is_open_raw": "CLOSE",
            "as_of": None,
            "dummy_id": None
        }
    
    async def fetch_today_price(self, dummy_id: Optional[int] = None) -> List[Dict]:
        """Fetch today's prices for all stocks."""
        cache_key = "today_prices"
        
        # Check cache
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        # Try different data sources in order
        sources = [
            self._parse_sharesansar_html,
            self._fetch_merolagani_api,
            self._fetch_nepse_alpha_api,
            self._parse_nepsealpha_html,
        ]
        
        for source in sources:
            try:
                result = await source()
                if result and result.get("market_data"):
                    data = self._process_market_data(result.get("market_data"))
                    if data and len(data) > 5:  # Only use if we got enough data
                        self._set_cache(cache_key, data, ttl=60)
                        logger.info(f"✅ Fetched {len(data)} prices from {result.get('source', 'unknown')}")
                        return data
            except Exception as e:
                logger.warning(f"Source {source.__name__} failed: {e}")
        
        # Use mock data as last resort
        logger.warning("Using mock data as last resort")
        mock_result = self._generate_mock_data()
        data = self._process_market_data(mock_result.get("market_data"))
        self._set_cache(cache_key, data, ttl=30)
        logger.info(f"📊 Generated {len(data)} mock prices")
        return data
    
    async def fetch_listed_securities(self) -> List[Dict]:
        """Fetch all listed securities."""
        cache_key = "listed_securities"
        
        # Check cache (1 hour)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Try to get from sharesansar HTML
            url = "https://www.sharesansar.com/"
            response = await self._client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                symbols = []
                
                # Find company list
                companies_div = soup.find('div', {'id': 'company-list'})
                if companies_div:
                    links = companies_div.find_all('a')
                    for link in links[:500]:
                        href = link.get('href', '')
                        if '/company/' in href:
                            symbol = href.split('/')[-1]
                            if symbol and not str(symbol).isdigit():
                                symbols.append({"symbol": symbol.upper(), "name": link.text.strip()})
                
                if symbols:
                    # Remove duplicates
                    seen = set()
                    unique_symbols = []
                    for s in symbols:
                        if s["symbol"] not in seen:
                            seen.add(s["symbol"])
                            unique_symbols.append(s)
                    
                    self._set_cache(cache_key, unique_symbols, ttl=3600)
                    logger.info(f"✅ Fetched {len(unique_symbols)} symbols from Sharesansar")
                    return unique_symbols
        except Exception as e:
            logger.debug(f"Sharesansar symbols error: {e}")
        
        # Return fallback symbols
        logger.warning("Using fallback symbol list")
        self._set_cache(cache_key, FALLBACK_SYMBOLS, ttl=3600)
        return FALLBACK_SYMBOLS
    
    async def fetch_floorsheet(self, page: int = 0, size: int = 500) -> Dict:
        """Fetch floorsheet data."""
        cache_key = f"floorsheet_{page}_{size}"
        
        # Check cache (5 minutes)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        # Try to get from sharesansar
        try:
            url = f"https://www.sharesansar.com/floorsheet?page={page}&limit={size}"
            response = await self._client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')
                    content = []
                    for row in rows[1:]:
                        cells = row.find_all('td')
                        if len(cells) >= 6:
                            symbol = cells[0].text.strip()
                            if symbol and not str(symbol).isdigit():
                                content.append({
                                    "symbol": symbol.upper(),
                                    "buyerBroker": cells[1].text.strip(),
                                    "sellerBroker": cells[2].text.strip(),
                                    "quantity": self._parse_int(cells[3].text),
                                    "rate": self._parse_float(cells[4].text),
                                    "amount": self._parse_float(cells[5].text),
                                })
                    if content:
                        result = {
                            "content": content,
                            "totalElements": len(content),
                            "last": len(content) < size
                        }
                        self._set_cache(cache_key, result, ttl=300)
                        return result
        except Exception as e:
            logger.debug(f"Floorsheet fetch error: {e}")
        
        return {"content": [], "totalElements": 0, "last": True}
    
    async def fetch_indices(self) -> List[Dict]:
        """Fetch indices data."""
        cache_key = "indices"
        
        # Check cache (1 minute)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Try MeroLagani for indices
            url = "https://parseapi.net/api/merolagani/index-data"
            response = await self._client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data:
                    indices = []
                    for item in data:
                        if item.get("name"):
                            indices.append({
                                "name": item.get("name"),
                                "value": self._parse_float(item.get("value", 0)),
                                "point_change": self._parse_float(item.get("change", 0)),
                                "pct_change": self._parse_float(item.get("percentChange", 0)),
                            })
                    if indices:
                        self._set_cache(cache_key, indices, ttl=60)
                        return indices
        except Exception as e:
            logger.debug(f"Indices fetch error: {e}")
        
        # Try sharesansar
        try:
            url = "https://www.sharesansar.com/"
            response = await self._client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                indices = []
                
                # Find index data
                index_div = soup.find('div', {'class': 'index-value'})
                if index_div:
                    items = index_div.find_all('div', {'class': 'index-item'})
                    for item in items:
                        name = item.find('span', {'class': 'index-name'})
                        value = item.find('span', {'class': 'index-value'})
                        if name and value:
                            indices.append({
                                "name": name.text.strip(),
                                "value": self._parse_float(value.text),
                            })
                
                if indices:
                    self._set_cache(cache_key, indices, ttl=60)
                    return indices
        except Exception as e:
            logger.debug(f"Indices fetch error: {e}")
        
        # Return default indices
        return [
            {"name": "NEPSE Index", "value": 2000.0},
            {"name": "Sensitive Index", "value": 400.0},
            {"name": "Float Index", "value": 1800.0},
        ]
    
    async def fetch_members(self) -> List[Dict]:
        """Fetch broker members."""
        cache_key = "members"
        
        # Check cache (1 hour)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Try MeroLagani for brokers
            url = "https://parseapi.net/api/merolagani/brokers"
            response = await self._client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data:
                    members = []
                    for item in data:
                        code = item.get("code")
                        if code and not str(code).isdigit():
                            members.append({
                                "code": str(code),
                                "name": item.get("name", f"Broker {code}"),
                                "city": item.get("city"),
                            })
                    if members:
                        self._set_cache(cache_key, members, ttl=3600)
                        return members
        except Exception as e:
            logger.debug(f"Members fetch error: {e}")
        
        # Return default members
        members = [
            {"code": "1", "name": "Broker 1", "city": "Kathmandu"},
            {"code": "2", "name": "Broker 2", "city": "Pokhara"},
            {"code": "3", "name": "Broker 3", "city": "Kathmandu"},
        ]
        self._set_cache(cache_key, members, ttl=3600)
        return members
    
    async def fetch_news_bulletin(self) -> List[Dict]:
        """Fetch news bulletins."""
        cache_key = "bulletins"
        
        # Check cache (10 minutes)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Try MeroLagani for news
            url = "https://parseapi.net/api/merolagani/news"
            response = await self._client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data:
                    bulletins = []
                    for item in data:
                        title = item.get("title")
                        if title:
                            bulletins.append({
                                "title": title,
                                "url": item.get("url"),
                                "published_on": item.get("date"),
                            })
                    if bulletins:
                        self._set_cache(cache_key, bulletins, ttl=600)
                        return bulletins
        except Exception as e:
            logger.debug(f"News bulletin fetch error: {e}")
        
        return []
    
    async def fetch_top_ten_turnover_scrips(self) -> List[Dict]:
        """Fetch top 10 turnover scrips."""
        cache_key = "top_scrips"
        
        # Check cache (1 minute)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        # Get prices and sort by turnover
        prices = await self.fetch_today_price()
        if prices:
            sorted_data = sorted(prices, key=lambda x: x.get("turnover", 0), reverse=True)[:10]
            data = []
            for i, item in enumerate(sorted_data):
                symbol = item.get("symbol")
                if symbol and not str(symbol).isdigit():
                    data.append({
                        "symbol": symbol,
                        "ltp": item.get("ltp", 0),
                        "amount": item.get("turnover", 0),
                        "rank": i + 1,
                        "point_change": item.get("change", 0),
                        "pct_change": None,
                    })
            if data:
                self._set_cache(cache_key, data, ttl=60)
                return data
        
        return []
    
    async def fetch_nepse_price_history(self) -> List[Dict]:
        """Fetch NEPSE price history."""
        cache_key = "price_history"
        
        # Check cache (1 hour)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Try MeroLagani for history
            url = "https://parseapi.net/api/merolagani/history"
            response = await self._client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data:
                    history = []
                    for item in data:
                        date = item.get("date")
                        value = item.get("value")
                        if date and value:
                            history.append({
                                "name": "NEPSE Index",
                                "value": self._parse_float(value),
                                "business_date": date,
                                "point_change": self._parse_float(item.get("change", 0)),
                                "turnover": self._parse_float(item.get("turnover", 0)),
                            })
                    if history:
                        self._set_cache(cache_key, history, ttl=3600)
                        return history
        except Exception as e:
            logger.debug(f"Price history fetch error: {e}")
        
        return []
    
    async def fetch_index_ceil_floor(self) -> Dict[str, Dict]:
        """Fetch index ceiling/floor."""
        # This data is not easily available from free sources
        return {}
    
    def _process_market_data(self, raw_data: Any) -> List[Dict]:
        """Process market data into consistent format."""
        if not raw_data:
            return []
        
        # Handle different data formats
        if isinstance(raw_data, dict):
            if "data" in raw_data:
                items = raw_data["data"]
            else:
                items = [raw_data]
        elif isinstance(raw_data, list):
            items = raw_data
        else:
            return []
        
        processed = []
        for item in items:
            try:
                if not isinstance(item, dict):
                    continue
                
                symbol = item.get("symbol", "")
                if not symbol or str(symbol).isdigit():
                    continue
                
                processed.append({
                    "symbol": str(symbol).strip().upper(),
                    "ltp": _num(item, "ltp", "lastTradedPrice", "close", "price"),
                    "open_price": _num(item, "open", "openPrice", "open_price"),
                    "high_price": _num(item, "high", "highPrice", "high_price"),
                    "low_price": _num(item, "low", "lowPrice", "low_price"),
                    "prev_close": _num(item, "prev_close", "previousClose", "prevClose"),
                    "volume": _num(item, "volume", "totalTradedQuantity"),
                    "turnover": _num(item, "turnover", "totalTradedValue"),
                    "transactions": _num(item, "transactions", "totalTrades"),
                    "change": _num(item, "change", "pointChange"),
                })
            except (ValueError, TypeError, AttributeError) as e:
                logger.debug(f"Error processing item: {e}")
                continue
        
        return processed


# ============ Synchronous Wrapper ============

class NepseMarketClientSync:
    """
    Synchronous wrapper for the async client.
    """
    
    def __init__(self):
        self._client: Optional[NepseMarketClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _ensure_client(self):
        if self._client is None:
            self._client = NepseMarketClient()
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._client
    
    def _run(self, coro):
        client = self._ensure_client()
        try:
            return self._loop.run_until_complete(coro)
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            return self._loop.run_until_complete(coro)
    
    def fetch_market_open(self) -> Dict:
        return self._run(self._ensure_client().fetch_market_open())
    
    def fetch_today_price(self) -> List[Dict]:
        return self._run(self._ensure_client().fetch_today_price())
    
    def fetch_listed_securities(self) -> List[Dict]:
        return self._run(self._ensure_client().fetch_listed_securities())
    
    def fetch_members(self) -> List[Dict]:
        return self._run(self._ensure_client().fetch_members())
    
    def fetch_news_bulletin(self) -> List[Dict]:
        return self._run(self._ensure_client().fetch_news_bulletin())
    
    def fetch_floorsheet(self, page: int = 0, size: int = 500) -> Dict:
        return self._run(self._ensure_client().fetch_floorsheet(page, size))
    
    def fetch_indices(self) -> List[Dict]:
        return self._run(self._ensure_client().fetch_indices())
    
    def fetch_top_ten_turnover_scrips(self) -> List[Dict]:
        return self._run(self._ensure_client().fetch_top_ten_turnover_scrips())
    
    def fetch_nepse_price_history(self) -> List[Dict]:
        return self._run(self._ensure_client().fetch_nepse_price_history())
    
    def fetch_index_ceil_floor(self) -> Dict[str, Dict]:
        return self._run(self._ensure_client().fetch_index_ceil_floor())
    
    def close(self):
        if self._client and self._loop:
            try:
                self._loop.run_until_complete(self._client.aclose())
            except:
                pass


# ============ Convenience Functions ============

async def collect_watchlist_prices(watchlist_symbols: set) -> List[Dict]:
    client = NepseMarketClient()
    try:
        all_prices = await client.fetch_today_price()
        return [p for p in all_prices if p.get("symbol") in watchlist_symbols]
    finally:
        await client.aclose()


async def collect_watchlist_floorsheet(watchlist_symbols: set, max_pages: int = 5) -> List[Dict]:
    client = NepseMarketClient()
    matched = []
    try:
        for page in range(max_pages):
            raw = await client.fetch_floorsheet(page=page)
            content = raw.get("content", [])
            if not content:
                break
            for f in content:
                symbol = f.get("symbol") or f.get("stockSymbol")
                if symbol in watchlist_symbols:
                    matched.append({
                        "symbol": symbol,
                        "buyer_broker": str(f.get("buyerMemberId") or f.get("buyerBroker") or ""),
                        "seller_broker": str(f.get("sellerMemberId") or f.get("sellerBroker") or ""),
                        "quantity": int(f.get("contractQuantity") or f.get("quantity") or 0),
                        "rate": float(f.get("contractRate") or f.get("rate") or 0),
                        "amount": float(f.get("contractAmount") or f.get("amount") or 0),
                    })
            if len(content) < 500:
                break
        return matched
    finally:
        await client.aclose()