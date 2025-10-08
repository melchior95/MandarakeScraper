# ScrapeOps Quick Start Guide

**Goal**: Enable proxy rotation to avoid IP bans in 5 minutes.

---

## ✅ Already Done

1. ✅ ScrapeOps SDK installed
2. ✅ API key configured: `f3106dda-ac3c-4a67-badf-e95985d50a73`
3. ✅ Scrapy middleware configured (eBay spider)
4. ✅ BrowserMimic updated with ScrapeOps support

---

## How to Use

### Via GUI Settings (Easiest)

1. Open the GUI: `python gui_config.py`
2. Go to **File → Preferences**
3. Click the **"Proxy Rotation"** tab
4. Check **"Enable ScrapeOps proxy rotation"**
5. Enter your API key: `f3106dda-ac3c-4a67-badf-e95985d50a73`
6. Click **OK**

All scraping operations will now use rotating proxies automatically!

---

### For eBay Scraping (Automatic)

Just run the Scrapy spider as normal - proxies are automatic:

```bash
scrapy crawl ebay -a query="pokemon card" -a max_results=10
```

Every request automatically goes through a different proxy IP.

---

### For Mandarake Scraping (Manual Enable)

**Option 1: In Python Code**

```python
from browser_mimic import BrowserMimic

# Enable ScrapeOps
browser = BrowserMimic(
    use_scrapeops=True,
    scrapeops_api_key='f3106dda-ac3c-4a67-badf-e95985d50a73'
)

# All requests use rotating proxies
response = browser.get('https://order.mandarake.co.jp/...')
```

**Option 2: Auto-Purchase Monitoring**

Update `gui/schedule_executor.py` (line ~580):

```python
def _check_item_availability(self, schedule) -> dict:
    """Check availability with proxy rotation."""
    from browser_mimic import BrowserMimic

    # Enable proxy
    mimic = BrowserMimic(
        use_scrapeops=True,
        scrapeops_api_key='f3106dda-ac3c-4a67-badf-e95985d50a73'
    )

    response = mimic.get(check_url)
    # ... rest of code
```

---

## When to Enable

### Enable Proxies For:
- ✅ Auto-purchase monitoring (prevents bans)
- ✅ High-volume scraping (100+ pages)
- ✅ After getting IP banned

### Skip Proxies For:
- ❌ Single searches (wastes quota)
- ❌ Testing (save requests)
- ❌ When not banned (no need)

---

## Monitoring Usage

**Dashboard**: https://scrapeops.io/app/dashboard

**Free Plan Limits**:
- 1,000 requests/month
- 1 concurrent request

**Example Monthly Usage**:
- 50 eBay searches = 500 requests
- 100 Mandarake searches = 500 requests
- **Total: 1,000** (perfect!)

---

## Troubleshooting

### "Module not found: scrapeops_scrapy_proxy_sdk"

```bash
pip install scrapeops-scrapy-proxy-sdk
```

### Requests timing out

Increase timeout:

```python
browser.get(url, timeout=120)  # 2 minutes
```

### Still getting blocked

Try enabling JavaScript rendering:

```python
from scrapers.proxy_rotator import ScrapeOpsProxyRotator

rotator = ScrapeOpsProxyRotator(
    api_key='f3106dda-ac3c-4a67-badf-e95985d50a73',
    render_js=True  # Slower but bypasses more blocks
)
```

---

## Cost

- **Free**: $0/mo, 1,000 requests
- **Hobby**: $29/mo, 100,000 requests
- **Startup**: $99/mo, 500,000 requests

Current setup uses **Free plan** - perfect for testing and light usage.

---

## Summary

**What you have**:
- ✅ eBay: Automatic proxy rotation (Scrapy middleware)
- ✅ Mandarake: Optional proxy rotation (set `use_scrapeops=True`)
- ✅ Free plan: 1,000 requests/month

**Next step**: Just start using it! Proxies are ready to go.

**Documentation**: See `SCRAPEOPS_INTEGRATION.md` for full details.
