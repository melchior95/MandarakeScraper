"""
Base Scraper Class

Abstract base class for all marketplace scrapers (Mandarake, Suruga-ya, DejaJapan, etc.)
Provides common functionality for HTTP requests, rate limiting, error handling, and data normalization.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class BaseScraper(ABC):
    """
    Abstract base class for marketplace scrapers

    Subclasses must implement:
    - search()
    - parse_item()
    """

    def __init__(self, marketplace_name: str, base_url: str, rate_limit: float = 2.0):
        """
        Initialize base scraper

        Args:
            marketplace_name: Name of marketplace (e.g., 'surugaya', 'mandarake')
            base_url: Base URL for the marketplace
            rate_limit: Minimum seconds between requests (default: 2.0)
        """
        self.marketplace_name = marketplace_name
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.last_request_time = 0

        # Initialize session with anti-detection headers
        self.session = requests.Session()
        self.session.headers.update(self._get_default_headers())

        # Setup logging
        self.logger = logging.getLogger(f'{self.__class__.__name__}')

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers to mimic browser"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def _rate_limit_check(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def fetch_page(self, url: str, params: Optional[Dict] = None) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a page with rate limiting

        Args:
            url: URL to fetch
            params: Optional query parameters

        Returns:
            BeautifulSoup object or None if failed
        """
        self._rate_limit_check()

        try:
            self.logger.info(f"Fetching: {url}")
            print(f"  → Fetching URL...", flush=True)
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            print(f"  → Got response ({len(response.content)} bytes)", flush=True)

            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            print(f"  → Parsed HTML", flush=True)
            return soup

        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            print(f"  → ERROR: {e}", flush=True)
            return None

    def normalize_result(self, raw_data: Dict) -> Dict:
        """
        Normalize marketplace-specific data to standard format

        Standard format:
        {
            'marketplace': str,      # Marketplace name
            'title': str,            # Product title
            'price': float,          # Price in JPY
            'currency': str,         # Currency code (JPY, USD, etc.)
            'condition': str,        # Condition (New, Used, etc.)
            'url': str,              # Product URL
            'image_url': str,        # Main image URL
            'thumbnail_url': str,    # Thumbnail URL
            'seller': str,           # Seller name/ID
            'location': str,         # Shop location/region
            'stock_status': str,     # Stock status
            'product_id': str,       # Product ID
            'scraped_at': datetime,  # Scrape timestamp
            'extra': dict            # Marketplace-specific fields
        }

        Args:
            raw_data: Marketplace-specific raw data

        Returns:
            Normalized data dictionary
        """
        return {
            'marketplace': self.marketplace_name,
            'title': raw_data.get('title', ''),
            'price': self._parse_price(raw_data.get('price', '')),
            'currency': raw_data.get('currency', 'JPY'),
            'condition': raw_data.get('condition', ''),
            'url': raw_data.get('url', ''),
            'image_url': raw_data.get('image_url', ''),
            'thumbnail_url': raw_data.get('thumbnail_url', raw_data.get('image_url', '')),
            'seller': raw_data.get('seller', ''),
            'location': raw_data.get('location', ''),
            'stock_status': raw_data.get('stock_status', ''),
            'product_id': raw_data.get('product_id', ''),
            'scraped_at': datetime.now(),
            'extra': raw_data.get('extra', {})
        }

    def _parse_price(self, price_text: str) -> float:
        """
        Parse price from text to float

        Handles formats like:
        - "¥1,234"
        - "1234円"
        - "$12.34"
        - "中古：￥1,234 税込"

        Args:
            price_text: Price text to parse

        Returns:
            Price as float, or 0.0 if parsing fails
        """
        if not price_text:
            return 0.0

        # Remove common Japanese price prefixes
        price_text = price_text.replace('中古：', '').replace('新品：', '').replace('税込', '').strip()

        # Extract numeric part
        import re
        match = re.search(r'[\d,]+\.?\d*', price_text.replace('¥', '').replace('￥', '').replace('円', '').replace(',', ''))

        if match:
            try:
                return float(match.group(0))
            except ValueError:
                pass

        return 0.0

    def _build_absolute_url(self, relative_url: str) -> str:
        """Convert relative URL to absolute URL"""
        if not relative_url:
            return ''
        if relative_url.startswith('http'):
            return relative_url
        return urljoin(self.base_url, relative_url)

    @abstractmethod
    def search(self, keyword: str, **kwargs) -> List[Dict]:
        """
        Search marketplace for items

        Args:
            keyword: Search keyword
            **kwargs: Marketplace-specific search parameters

        Returns:
            List of normalized result dictionaries
        """
        raise NotImplementedError("Subclass must implement search()")

    @abstractmethod
    def parse_item(self, item_element) -> Optional[Dict]:
        """
        Parse a single item from HTML element

        Args:
            item_element: BeautifulSoup element containing item data

        Returns:
            Raw data dictionary or None if parsing fails
        """
        raise NotImplementedError("Subclass must implement parse_item()")

    def close(self):
        """Close session and cleanup resources"""
        if hasattr(self, 'session'):
            self.session.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
