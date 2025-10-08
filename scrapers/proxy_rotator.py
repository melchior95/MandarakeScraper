"""
Proxy rotation for requests/BrowserMimic using ScrapeOps API.

Provides rotating proxy support for non-Scrapy parts of the project
(BrowserMimic, requests, auto-purchase monitoring).
"""
import requests
from typing import Optional, Dict
import random


class ScrapeOpsProxyRotator:
    """Manages proxy rotation using ScrapeOps API for requests-based scraping."""

    def __init__(self, api_key: str, country: str = 'us', render_js: bool = False):
        """
        Initialize ScrapeOps proxy rotator.

        Args:
            api_key: ScrapeOps API key
            country: Country code for proxies (us, uk, ca, au, etc.)
            render_js: Whether to render JavaScript (slower, more expensive)
        """
        self.api_key = api_key
        self.country = country
        self.render_js = render_js
        self.base_url = 'https://proxy.scrapeops.io/v1/'

    def get_proxy_url(self, target_url: str) -> str:
        """
        Get proxied URL via ScrapeOps.

        Instead of using traditional proxy settings, ScrapeOps works by
        wrapping your target URL. You make a request to ScrapeOps, and
        they fetch the content through their rotating proxies.

        Args:
            target_url: The URL you want to fetch

        Returns:
            ScrapeOps proxy URL that will fetch target_url

        Example:
            >>> rotator = ScrapeOpsProxyRotator('YOUR_API_KEY')
            >>> proxy_url = rotator.get_proxy_url('https://order.mandarake.co.jp/...')
            >>> response = requests.get(proxy_url)
        """
        params = {
            'api_key': self.api_key,
            'url': target_url,
            'country': self.country,
        }

        if self.render_js:
            params['render_js'] = 'true'

        # Build query string
        from urllib.parse import urlencode
        query_string = urlencode(params)

        return f"{self.base_url}?{query_string}"

    def get(self, url: str, session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
        """
        Make a GET request through ScrapeOps proxy.

        Args:
            url: Target URL to fetch
            session: Optional requests.Session to use
            **kwargs: Additional arguments for requests.get()

        Returns:
            Response from target URL (fetched via ScrapeOps proxy)
        """
        proxy_url = self.get_proxy_url(url)

        if session:
            return session.get(proxy_url, **kwargs)
        else:
            return requests.get(proxy_url, **kwargs)


class ManualProxyRotator:
    """Manages manual proxy rotation from a proxy list file."""

    def __init__(self, proxy_file: str = "proxies.txt"):
        """
        Initialize manual proxy rotator.

        Args:
            proxy_file: File containing proxy list (one per line)
                Format: http://user:pass@host:port or http://host:port
        """
        self.proxies = self._load_proxies(proxy_file)
        self.current_index = 0
        self.failed_proxies = set()

    def _load_proxies(self, proxy_file: str) -> list:
        """Load proxies from file."""
        try:
            with open(proxy_file, 'r') as f:
                proxies = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith('#')
                ]
            print(f"Loaded {len(proxies)} proxies from {proxy_file}")
            return proxies
        except FileNotFoundError:
            print(f"Warning: Proxy file {proxy_file} not found. Using no proxies.")
            return []

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get next proxy in rotation.

        Returns:
            {'http': 'proxy_url', 'https': 'proxy_url'} or None
        """
        if not self.proxies:
            return None

        # Skip failed proxies
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)

            if proxy not in self.failed_proxies:
                return {
                    'http': proxy,
                    'https': proxy
                }

            attempts += 1

        # All proxies failed - reset
        print("Warning: All proxies failed. Resetting failed list.")
        self.failed_proxies.clear()
        return self.get_next_proxy()

    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get random proxy (instead of sequential)."""
        if not self.proxies:
            return None

        available = [p for p in self.proxies if p not in self.failed_proxies]
        if not available:
            print("Warning: All proxies failed. Resetting.")
            self.failed_proxies.clear()
            available = self.proxies

        proxy = random.choice(available)
        return {
            'http': proxy,
            'https': proxy
        }

    def mark_failed(self, proxy_url: str):
        """Mark a proxy as failed."""
        self.failed_proxies.add(proxy_url)
        print(f"Marked proxy as failed: {proxy_url}")

    def test_proxy(self, proxy: dict, test_url: str = "https://httpbin.org/ip") -> bool:
        """
        Test if proxy is working.

        Args:
            proxy: Proxy dict
            test_url: URL to test against

        Returns:
            True if working
        """
        try:
            response = requests.get(test_url, proxies=proxy, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Proxy test failed: {e}")
            return False


# Global instances
_scrapeops_rotator = None
_manual_rotator = None


def get_scrapeops_rotator(api_key: str = None) -> ScrapeOpsProxyRotator:
    """
    Get global ScrapeOps rotator instance.

    Args:
        api_key: ScrapeOps API key (required on first call)
    """
    global _scrapeops_rotator

    if _scrapeops_rotator is None:
        if api_key is None:
            raise ValueError("API key required to initialize ScrapeOps rotator")
        _scrapeops_rotator = ScrapeOpsProxyRotator(api_key)

    return _scrapeops_rotator


def get_manual_rotator(proxy_file: str = "proxies.txt") -> ManualProxyRotator:
    """Get global manual proxy rotator instance."""
    global _manual_rotator

    if _manual_rotator is None:
        _manual_rotator = ManualProxyRotator(proxy_file)

    return _manual_rotator
