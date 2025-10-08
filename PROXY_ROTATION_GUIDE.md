# Proxy Rotation Integration Guide

## Current Status

**Installed**: ✅ `scrapeops_scrapy_proxy_sdk` (v1.0)
**Configured**: ❌ Not yet enabled
**Purpose**: Avoid IP bans from Mandarake and eBay

---

## Why Proxy Rotation is Critical

### Current Problem
Your recent IP ban from Mandarake demonstrates the need for proxy rotation:
- ❌ Mandarake blocks automated access
- ❌ Even light scraping triggers Cloudflare
- ❌ Single IP = easy to detect and ban
- ❌ Cart/checkout endpoints = instant block

### Solution: Rotating Proxies
✅ **Different IP for each request** (appears like different users)
✅ **Bypasses IP-based rate limits**
✅ **Reduces ban risk significantly**
✅ **Enables more frequent monitoring**

---

## Integration Options

### Option 1: ScrapeOps Proxy SDK (Recommended for Scrapy)

**What you already have**: ScrapeOps SDK installed

**Setup for eBay Spider** (`scrapy_ebay/settings.py`):

```python
# Get API key from: https://scrapeops.io/app/register
SCRAPEOPS_API_KEY = 'YOUR_API_KEY_HERE'

# Enable proxy middleware
SCRAPEOPS_PROXY_ENABLED = True

# Add middleware
DOWNLOADER_MIDDLEWARES = {
    'scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk': 725,
    'scrapy_ebay.pipelines.EbayImagePipeline': 300,
}

# Proxy settings (optional customization)
SCRAPEOPS_PROXY_SETTINGS = {
    'country': 'us',  # Use US proxies for eBay
    'residential': True,  # More expensive but harder to detect
    'render_js': False,  # Set to True if pages need JavaScript
}

# Adjust concurrency based on your plan
# Free plan: 1 concurrent request
# Paid plans: Higher limits
CONCURRENT_REQUESTS = 1  # Adjust based on your ScrapeOps plan
DOWNLOAD_DELAY = 0  # Let ScrapeOps handle rate limiting
```

**ScrapeOps Plans**:
- **Free**: 1,000 requests/month, 1 concurrent request
- **Hobby ($29/mo)**: 100,000 requests, 10 concurrent
- **Startup ($99/mo)**: 500,000 requests, 25 concurrent

**Pros**:
- ✅ Easy integration (just API key)
- ✅ Managed proxy pool (no maintenance)
- ✅ Automatic rotation
- ✅ Works seamlessly with Scrapy

**Cons**:
- ❌ Costs money (after free tier)
- ❌ Only works with Scrapy (not `browser_mimic.py`)

---

### Option 2: Manual Proxy List Rotation

For non-Scrapy parts (BrowserMimic, requests, auto-purchase monitoring):

**Create custom middleware** (`scrapers/proxy_rotator.py`):

```python
"""
Proxy rotation for requests/BrowserMimic.

Rotates through a list of proxies for each request.
"""
import random
from typing import List, Optional
import requests


class ProxyRotator:
    """Manages proxy rotation for HTTP requests."""

    def __init__(self, proxy_file: str = "proxies.txt"):
        """
        Initialize proxy rotator.

        Args:
            proxy_file: File containing proxy list (one per line)
                Format: http://user:pass@host:port or http://host:port
        """
        self.proxies = self._load_proxies(proxy_file)
        self.current_index = 0
        self.failed_proxies = set()

    def _load_proxies(self, proxy_file: str) -> List[str]:
        """Load proxies from file."""
        try:
            with open(proxy_file, 'r') as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            print(f"Loaded {len(proxies)} proxies from {proxy_file}")
            return proxies
        except FileNotFoundError:
            print(f"Warning: Proxy file {proxy_file} not found. Using no proxies.")
            return []

    def get_next_proxy(self) -> Optional[dict]:
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

        # All proxies failed
        print("Warning: All proxies have failed. Resetting failed list.")
        self.failed_proxies.clear()
        return self.get_next_proxy()

    def get_random_proxy(self) -> Optional[dict]:
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


# Global instance
_proxy_rotator = None


def get_proxy_rotator() -> ProxyRotator:
    """Get global proxy rotator instance."""
    global _proxy_rotator
    if _proxy_rotator is None:
        _proxy_rotator = ProxyRotator()
    return _proxy_rotator
```

**Usage in BrowserMimic** (`browser_mimic.py`):

```python
from scrapers.proxy_rotator import get_proxy_rotator

class BrowserMimic:
    def __init__(self, use_proxy: bool = True):
        self.session = requests.Session()
        self.use_proxy = use_proxy
        self.proxy_rotator = get_proxy_rotator() if use_proxy else None

        # ... existing code ...

    def get(self, url, **kwargs):
        """HTTP GET with proxy rotation."""

        # Add proxy if enabled
        if self.use_proxy and self.proxy_rotator:
            proxy = self.proxy_rotator.get_next_proxy()
            if proxy:
                kwargs['proxies'] = proxy

        # Existing request logic
        response = self.session.get(url, **kwargs)

        # If request failed and we used a proxy, mark it as failed
        if self.use_proxy and response.status_code in [403, 407, 503]:
            if 'proxies' in kwargs:
                proxy_url = kwargs['proxies'].get('http')
                self.proxy_rotator.mark_failed(proxy_url)

        return response
```

**Proxy List Format** (`proxies.txt`):

```
# Free proxies (not recommended - often blocked)
http://free-proxy1.com:8080
http://free-proxy2.com:3128

# Paid residential proxies (recommended)
http://username:password@residential-proxy.com:12345

# SOCKS5 proxies (if supported)
socks5://user:pass@socks-proxy.com:1080
```

---

### Option 3: BrightData/Oxylabs/Smartproxy (Premium)

**For enterprise-grade scraping**:

1. **BrightData** (formerly Luminati)
   - Largest residential proxy network
   - Pay-as-you-go: ~$0.80/GB
   - Integration: Update `proxies.txt` with their proxy endpoint

2. **Oxylabs**
   - High-quality residential/datacenter proxies
   - Starting at $49/month
   - Good for e-commerce scraping

3. **Smartproxy**
   - Affordable residential proxies
   - $80/month for 8GB
   - Easy API integration

**Setup**:
```python
# proxies.txt for BrightData
http://username-country-us:password@brd.superproxy.io:22225

# For Oxylabs
http://customer-username:password@pr.oxylabs.io:7777
```

---

## Integration Strategy for Mandarake Scraper

### Phase 1: eBay Scrapy Integration (Immediate)

**Already using Scrapy** for eBay image comparison.

**Steps**:
1. Sign up for ScrapeOps: https://scrapeops.io/app/register
2. Get free API key (1,000 requests/month)
3. Update `scrapy_ebay/settings.py`:

```python
SCRAPEOPS_API_KEY = 'YOUR_KEY_HERE'
SCRAPEOPS_PROXY_ENABLED = True

DOWNLOADER_MIDDLEWARES = {
    'scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk': 725,
}

SCRAPEOPS_PROXY_SETTINGS = {
    'country': 'us',
}

CONCURRENT_REQUESTS = 1  # Free plan limit
DOWNLOAD_DELAY = 0
```

4. Test: `scrapy crawl ebay -a query="pokemon card" -a max_results=5`

**Result**: eBay scraping with rotating proxies ✅

---

### Phase 2: Mandarake Auto-Purchase Monitoring

**Current issue**: Auto-purchase polling triggers IP bans

**Solution**: Add proxy rotation to `ScheduleExecutor`

**Update** `gui/schedule_executor.py`:

```python
from scrapers.proxy_rotator import get_proxy_rotator

class ScheduleExecutor:
    def __init__(self, gui, manager):
        # ... existing code ...
        self.proxy_rotator = get_proxy_rotator()

    def _check_item_availability(self, schedule) -> dict:
        """Check availability with proxy rotation."""
        from browser_mimic import BrowserMimic

        # Use proxy for each check
        mimic = BrowserMimic(use_proxy=True)  # Enable proxy rotation

        # Fetch with rotating proxy
        response = mimic.get(check_url)

        # ... existing parsing code ...
```

**Result**: Auto-purchase monitoring with rotating IPs ✅

---

### Phase 3: RSS Monitoring with Proxies (Optional)

RSS feeds are less likely to be blocked, but for extra safety:

**Update** `scrapers/mandarake_rss_monitor.py`:

```python
from scrapers.proxy_rotator import get_proxy_rotator

class MandarakeRSSMonitor:
    def __init__(self, use_browser_mimic: bool = True, use_proxy: bool = False):
        # ... existing code ...
        self.use_proxy = use_proxy
        if use_proxy:
            self.proxy_rotator = get_proxy_rotator()

    def fetch_feed(self, shop_code: str = 'all') -> Optional[List[Dict]]:
        """Fetch RSS with optional proxy."""

        # Add proxy if enabled
        kwargs = {}
        if self.use_proxy:
            proxy = self.proxy_rotator.get_next_proxy()
            if proxy:
                kwargs['proxies'] = proxy

        response = self.session.get(url, **kwargs)
        # ... rest of code ...
```

---

## Free Proxy Sources (Not Recommended)

**Warning**: Free proxies are slow, unreliable, and often already blocked.

**If you must use free proxies**:
- https://www.proxy-list.download/
- https://free-proxy-list.net/
- https://www.sslproxies.org/

**Format into `proxies.txt`**:
```
http://123.45.67.89:8080
http://98.76.54.32:3128
```

**Better alternative**: Pay for a small proxy plan (~$10-30/month)

---

## Recommended Proxy Providers

### Budget Options ($10-30/month)
1. **Webshare.io** - $10/mo for 10 proxies
2. **Proxy-Cheap** - $15/mo for 1GB residential
3. **Rayobyte** - $22/mo for 5 proxies

### Mid-Tier ($30-100/month)
1. **Smartproxy** - $80/mo for 8GB residential
2. **GeoSurf** - $50/mo starter plan
3. **Storm Proxies** - $50/mo rotating residential

### Enterprise ($100+/month)
1. **BrightData** - Pay per GB, highly reliable
2. **Oxylabs** - Premium quality
3. **NetNut** - Fast residential proxies

---

## Testing Proxy Integration

### Test Script (`test_proxy_rotation.py`):

```python
"""Test proxy rotation."""
from scrapers.proxy_rotator import ProxyRotator
import requests

def test_proxy_rotation():
    """Test that proxies rotate and work."""
    rotator = ProxyRotator('proxies.txt')

    print(f"Loaded {len(rotator.proxies)} proxies")

    # Test first 5 proxies
    test_url = "https://httpbin.org/ip"

    for i in range(min(5, len(rotator.proxies))):
        proxy = rotator.get_next_proxy()
        print(f"\nTesting proxy {i+1}: {proxy['http']}")

        try:
            response = requests.get(test_url, proxies=proxy, timeout=10)
            if response.status_code == 200:
                ip_info = response.json()
                print(f"  ✓ Success! IP: {ip_info.get('origin')}")
            else:
                print(f"  ✗ Failed with status: {response.status_code}")
                rotator.mark_failed(proxy['http'])
        except Exception as e:
            print(f"  ✗ Error: {e}")
            rotator.mark_failed(proxy['http'])

if __name__ == '__main__':
    test_proxy_rotation()
```

---

## Summary & Recommendations

### Immediate Actions

1. **For eBay Scraping** (Scrapy-based):
   - ✅ Enable ScrapeOps proxy in `scrapy_ebay/settings.py`
   - ✅ Get free API key (1,000 requests/month)
   - ✅ Test with eBay searches

2. **For Mandarake Monitoring**:
   - ✅ Create `scrapers/proxy_rotator.py`
   - ✅ Get proxy list (paid service recommended)
   - ✅ Update `BrowserMimic` to use proxies
   - ✅ Enable in `ScheduleExecutor` for auto-purchase

3. **Test Everything**:
   - ✅ Run `test_proxy_rotation.py`
   - ✅ Monitor for 403 errors
   - ✅ Adjust rotation strategy based on results

### Cost Estimate

**Minimal Setup** (~$30/month):
- ScrapeOps Hobby: $29/mo (100k requests for eBay)
- Total: $29/mo

**Recommended Setup** (~$60/month):
- ScrapeOps Hobby: $29/mo (eBay scraping)
- Smartproxy: $28/mo for 2GB (Mandarake monitoring)
- Total: $57/mo

**Premium Setup** (~$150/month):
- ScrapeOps Startup: $99/mo (high-volume eBay)
- BrightData: ~$50/mo estimated (Mandarake)
- Total: $149/mo

### Expected Results

**Without Proxies** (current):
- ❌ IP bans after light usage
- ❌ Cannot run auto-purchase
- ❌ Limited eBay scraping

**With Proxies**:
- ✅ No IP bans
- ✅ Auto-purchase monitoring safe
- ✅ Unlimited eBay scraping (within proxy limits)
- ✅ Can check items every few minutes if needed

---

## Files to Create/Modify

### Create:
1. `scrapers/proxy_rotator.py` (~150 lines) - Manual proxy rotation
2. `proxies.txt` - Proxy list (if using manual rotation)
3. `test_proxy_rotation.py` (~50 lines) - Testing script

### Modify:
1. `scrapy_ebay/settings.py` - Add ScrapeOps config
2. `browser_mimic.py` - Add proxy support
3. `gui/schedule_executor.py` - Use proxies for monitoring
4. `scrapers/mandarake_rss_monitor.py` - Optional proxy support

---

**Status**: Ready to implement
**Priority**: HIGH (solves IP ban issue)
**Estimated Setup Time**: 1-2 hours
**Monthly Cost**: $0-150 depending on usage

The proxy rotation will solve your IP ban problem and make auto-purchase monitoring viable!
