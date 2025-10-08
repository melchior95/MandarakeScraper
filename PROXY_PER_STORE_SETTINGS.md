# Per-Store Proxy Settings - Implementation Summary

**Date**: October 8, 2025
**Status**: ✅ Complete

---

## What Was Added

Granular per-store control for proxy rotation. Users can now enable/disable proxies independently for each store:
- ☑ **eBay** (Scrapy spider)
- ☑ **Mandarake** (BrowserMimic)
- ☑ **Suruga-ya** (BrowserMimic)

---

## GUI Settings

**Location**: File → Preferences → Proxy Rotation tab

### Main Toggle
```
☑ Enable ScrapeOps proxy rotation
```

### Per-Store Toggles (new!)
```
Use proxy for:
  ☑ eBay scraping (Scrapy spider)
  ☑ Mandarake scraping (BrowserMimic)
  ☑ Suruga-ya scraping (BrowserMimic)
```

### How It Works
1. Check **"Enable ScrapeOps proxy rotation"** - Master switch
2. Select which stores to use proxy for
3. Enter API key
4. Click OK

**All fields auto-disable** when master switch is off.

---

## Settings Saved

**File**: `user_settings.json`

```json
{
  "proxy": {
    "enabled": true,
    "ebay_enabled": true,
    "mandarake_enabled": true,
    "surugaya_enabled": true,
    "api_key": "f3106dda-ac3c-4a67-badf-e95985d50a73",
    "country": "us",
    "render_js": false
  }
}
```

---

## Helper Functions (New!)

**File**: `gui/utils.py`

### `get_proxy_settings(store: str)`

Get proxy settings for a specific store.

**Parameters**:
- `store`: Store name ('ebay', 'mandarake', or 'surugaya')

**Returns**:
- `(use_proxy: bool, api_key: str or None)`

**Example**:
```python
from gui.utils import get_proxy_settings

use_proxy, api_key = get_proxy_settings('mandarake')
if use_proxy and api_key:
    browser = BrowserMimic(use_scrapeops=True, scrapeops_api_key=api_key)
else:
    browser = BrowserMimic()
```

### `get_browser_with_proxy(store: str)`

Get BrowserMimic with automatic proxy configuration.

**Parameters**:
- `store`: Store name ('mandarake' or 'surugaya')

**Returns**:
- `BrowserMimic` instance (with or without proxy)

**Example**:
```python
from gui.utils import get_browser_with_proxy

# Automatically uses proxy if enabled for mandarake
browser = get_browser_with_proxy('mandarake')
response = browser.get('https://order.mandarake.co.jp/...')
```

---

## Usage Examples

### Example 1: Only eBay with Proxy

**Settings**:
```
☑ Enable ScrapeOps proxy rotation
☑ eBay scraping
☐ Mandarake scraping
☐ Suruga-ya scraping
```

**Result**:
- ✅ eBay uses proxy (automatic via Scrapy middleware)
- ❌ Mandarake uses direct connection
- ❌ Suruga-ya uses direct connection

### Example 2: Only Mandarake with Proxy

**Settings**:
```
☑ Enable ScrapeOps proxy rotation
☐ eBay scraping
☑ Mandarake scraping
☐ Suruga-ya scraping
```

**Code**:
```python
from gui.utils import get_browser_with_proxy

# Mandarake - uses proxy
browser = get_browser_with_proxy('mandarake')

# Suruga-ya - no proxy
browser2 = get_browser_with_proxy('surugaya')
```

### Example 3: All Stores with Proxy

**Settings**:
```
☑ Enable ScrapeOps proxy rotation
☑ eBay scraping
☑ Mandarake scraping
☑ Suruga-ya scraping
```

**Result**: All stores use rotating proxies

---

## Use Cases

### Use Case 1: IP Banned from Mandarake Only

If you're only banned from Mandarake but eBay and Suruga-ya work fine:

```
☑ Enable ScrapeOps proxy rotation
☐ eBay scraping              (save requests)
☑ Mandarake scraping         (bypass ban)
☐ Suruga-ya scraping         (save requests)
```

**Benefit**: Only use proxy quota where needed!

### Use Case 2: High-Volume eBay Scraping

If you're doing lots of eBay searches but only occasional Mandarake:

```
☑ Enable ScrapeOps proxy rotation
☑ eBay scraping              (prevent ban)
☐ Mandarake scraping         (save requests)
☐ Suruga-ya scraping         (save requests)
```

### Use Case 3: Auto-Purchase Monitoring

If you're monitoring rare Mandarake items with frequent checks:

```
☑ Enable ScrapeOps proxy rotation
☐ eBay scraping              (not needed)
☑ Mandarake scraping         (prevent ban from frequent checks)
☐ Suruga-ya scraping         (not needed)
```

---

## Integration in Code

### Auto-Purchase Monitoring

**File**: `gui/schedule_executor.py`

```python
def _check_item_availability(self, schedule) -> dict:
    """Check availability with optional proxy from settings."""
    from gui.utils import get_browser_with_proxy

    # Automatically uses proxy if enabled for mandarake
    mimic = get_browser_with_proxy('mandarake')

    # Rest of code...
    response = mimic.get(check_url)
```

### Mandarake Scraper

**File**: `mandarake_scraper.py`

```python
from gui.utils import get_browser_with_proxy

# Use proxy if configured
browser = get_browser_with_proxy('mandarake')
response = browser.get(mandarake_url)
```

### Suruga-ya Scraper

**File**: `gui/surugaya_manager.py`

```python
from gui.utils import get_browser_with_proxy

# Use proxy if configured
browser = get_browser_with_proxy('surugaya')
response = browser.get(surugaya_url)
```

---

## Request Quota Management

### Free Plan: 1,000 requests/month

**Scenario 1: All stores enabled**
- eBay searches: ~500 requests
- Mandarake searches: ~300 requests
- Suruga-ya searches: ~200 requests
- **Total: 1,000** ✅

**Scenario 2: Only Mandarake enabled**
- Mandarake searches: ~1,000 requests
- **Total: 1,000** ✅
- **Benefit**: 3x more Mandarake scraping!

**Scenario 3: Only eBay enabled**
- eBay searches: ~1,000 requests
- **Total: 1,000** ✅
- **Benefit**: 2x more eBay searches!

---

## Files Modified

### `gui/settings_dialog.py`

**Changes**:
1. Added 3 per-store variables:
   - `proxy_ebay_enabled_var`
   - `proxy_mandarake_enabled_var`
   - `proxy_surugaya_enabled_var`

2. Added UI checkboxes for each store

3. Updated `_toggle_proxy_fields()` to manage all 3 checkboxes

4. Updated load/save to handle per-store settings

**Lines Added**: ~15 lines

### `gui/utils.py`

**New Functions**:
1. `get_proxy_settings(store)` - Get settings for specific store
2. `get_browser_with_proxy(store)` - Get BrowserMimic with auto-config

**Lines Added**: ~65 lines

---

## Testing

### Test Per-Store Settings

1. Open GUI: `python gui_config.py`
2. File → Preferences → Proxy Rotation
3. Enable main toggle
4. Uncheck "Mandarake scraping"
5. Leave "eBay scraping" checked
6. Click OK

7. Test in code:
```python
from gui.utils import get_proxy_settings

# eBay should return (True, api_key)
use_ebay, key_ebay = get_proxy_settings('ebay')
print(f"eBay: {use_ebay}, {key_ebay}")

# Mandarake should return (False, None)
use_mand, key_mand = get_proxy_settings('mandarake')
print(f"Mandarake: {use_mand}, {key_mand}")
```

---

## Benefits

### For Users
✅ **Granular control** - Enable/disable per store
✅ **Save quota** - Only use proxies where needed
✅ **Flexibility** - Respond to bans quickly
✅ **Cost optimization** - Maximize free plan usage

### For Developers
✅ **Simple API** - `get_browser_with_proxy(store)`
✅ **Automatic** - Settings checked automatically
✅ **Consistent** - Same pattern for all stores
✅ **Maintainable** - Centralized in utils.py

---

## Summary

**Added**: Per-store proxy toggle controls

**Stores Supported**:
- eBay (Scrapy)
- Mandarake (BrowserMimic)
- Suruga-ya (BrowserMimic)

**Settings Structure**:
```
Main Toggle: Enable/Disable proxy globally
  ├─ eBay Toggle: Enable/Disable for eBay
  ├─ Mandarake Toggle: Enable/Disable for Mandarake
  └─ Suruga-ya Toggle: Enable/Disable for Suruga-ya
```

**Helper Functions**:
- `get_proxy_settings(store)` - Check settings
- `get_browser_with_proxy(store)` - Get configured browser

**Benefit**: Users can now save proxy quota by only enabling where needed!

---

**Implementation Date**: October 8, 2025
**Status**: ✅ Complete
**Ready to Use**: Yes
