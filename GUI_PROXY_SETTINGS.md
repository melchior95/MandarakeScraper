# GUI Proxy Settings - Implementation Summary

**Date**: October 8, 2025
**Status**: ✅ Complete

---

## What Was Added

A new **"Proxy Rotation"** tab in the GUI settings dialog that allows users to enable and configure ScrapeOps proxy rotation without touching code.

---

## How to Access

1. Open the GUI: `python gui_config.py`
2. Go to **File → Preferences**
3. Click the **"Proxy Rotation"** tab

---

## Settings Available

### Basic Settings
- ✅ **Enable/Disable** proxy rotation (checkbox)
- ✅ **API Key** (password field, hidden with *)
- ✅ Link to sign up for free API key

### Advanced Settings
- ✅ **Proxy Country** (dropdown: US, UK, CA, AU, DE, FR, JP)
- ✅ **JavaScript Rendering** (checkbox - slower, more expensive)

### Information Panels
- ✅ **Usage Information** - Free/Hobby/Startup plan details
- ✅ **When to Enable** - Guidelines for when to use proxies

---

## Settings Saved To

**File**: `user_settings.json`

**Settings keys**:
```json
{
  "proxy": {
    "enabled": false,
    "api_key": "f3106dda-ac3c-4a67-badf-e95985d50a73",
    "country": "us",
    "render_js": false
  }
}
```

---

## Files Modified

### `gui/settings_dialog.py`
**Changes**:
1. Added 4 new variables in `_init_variables()`:
   - `proxy_enabled_var`
   - `proxy_api_key_var`
   - `proxy_country_var`
   - `proxy_render_js_var`

2. Created `_create_proxy_tab()` method (~165 lines)
   - Full GUI layout with checkboxes, entry fields, dropdowns
   - Information panels and help links
   - Real-time field enabling/disabling

3. Added helper methods:
   - `_toggle_proxy_fields()` - Enable/disable fields based on checkbox
   - `_open_scrapeops_signup()` - Open browser to signup page

4. Updated `_load_settings()` - Load proxy settings from storage

5. Updated `_save_settings()` - Save proxy settings to storage

**Total Added**: ~175 lines

---

## How It Works

### 1. User Opens Preferences
```
File → Preferences → Proxy Rotation tab
```

### 2. User Enables Proxy
```
☑ Enable ScrapeOps proxy rotation
```

Fields become active:
- API Key entry (enabled)
- Country dropdown (enabled)
- JavaScript checkbox (enabled)

### 3. User Enters API Key
```
API Key: ******************** (hidden)
```

### 4. User Clicks OK
Settings saved to `user_settings.json`:
```python
self.settings.set_setting('proxy.enabled', True)
self.settings.set_setting('proxy.api_key', 'f3106dda-ac3c-4a67-badf-e95985d50a73')
self.settings.set_setting('proxy.country', 'us')
self.settings.set_setting('proxy.render_js', False)
```

### 5. Code Can Now Check Settings

**Example in `browser_mimic.py`**:
```python
from gui.settings_manager import SettingsManager

settings = SettingsManager()
use_proxy = settings.get_setting('proxy.enabled', False)
api_key = settings.get_setting('proxy.api_key', '')

if use_proxy and api_key:
    browser = BrowserMimic(
        use_scrapeops=True,
        scrapeops_api_key=api_key
    )
```

---

## User Experience

### Before (Code Required)
```python
# User had to edit code:
browser = BrowserMimic(
    use_scrapeops=True,
    scrapeops_api_key='YOUR_KEY_HERE'  # Manual entry
)
```

### After (GUI Settings)
```python
# User just checks a box in GUI
# Code automatically reads settings:
settings = SettingsManager()
if settings.get_setting('proxy.enabled'):
    api_key = settings.get_setting('proxy.api_key')
    browser = BrowserMimic(use_scrapeops=True, scrapeops_api_key=api_key)
```

---

## UI Elements

### Checkbox
```
☑ Enable ScrapeOps proxy rotation
```

### Info Label
```
Prevents IP bans by rotating through different proxy IPs for each request.
```

### API Key Field
```
API Key: ********************
```

### Help Link (clickable)
```
Get free API key at scrapeops.io/app/register
```

### Country Dropdown
```
Proxy country: [US ▼]
Options: US, UK, CA, AU, DE, FR, JP
```

### JavaScript Checkbox
```
☐ Enable JavaScript rendering (slower, more expensive)
```

### Usage Info Panel
```
Usage Information:
  Free Plan: 1,000 requests/month, 1 concurrent request
  Hobby Plan: $29/mo, 100,000 requests, 10 concurrent
  Startup Plan: $99/mo, 500,000 requests, 25 concurrent

  Monitor usage: scrapeops.io/app/dashboard
```

### When to Enable Panel
```
When to Enable:
  ✅ Auto-purchase monitoring (prevents bans from repeated checks)
  ✅ High-volume scraping (100+ pages in a session)
  ✅ After getting IP banned (immediate workaround)

  ❌ Single searches (wastes quota)
  ❌ Low-volume usage (<10 searches/day)
  ❌ Testing (save requests for production)
```

---

## Next Steps

### To Use Settings in Code

**Method 1: Check settings directly**
```python
from gui.settings_manager import SettingsManager

settings = SettingsManager()
proxy_enabled = settings.get_setting('proxy.enabled', False)
proxy_api_key = settings.get_setting('proxy.api_key', '')

if proxy_enabled and proxy_api_key:
    # Use proxy
    from browser_mimic import BrowserMimic
    browser = BrowserMimic(
        use_scrapeops=True,
        scrapeops_api_key=proxy_api_key
    )
```

**Method 2: Helper function**
```python
# Create in gui/utils.py
def get_browser_with_proxy_if_enabled():
    """Get BrowserMimic with proxy if enabled in settings."""
    from gui.settings_manager import SettingsManager
    from browser_mimic import BrowserMimic

    settings = SettingsManager()
    use_proxy = settings.get_setting('proxy.enabled', False)

    if use_proxy:
        api_key = settings.get_setting('proxy.api_key', '')
        if api_key:
            return BrowserMimic(use_scrapeops=True, scrapeops_api_key=api_key)

    return BrowserMimic()  # No proxy

# Usage
browser = get_browser_with_proxy_if_enabled()
response = browser.get('https://order.mandarake.co.jp/...')
```

### To Apply to Auto-Purchase Monitoring

Update `gui/schedule_executor.py`:
```python
def _check_item_availability(self, schedule) -> dict:
    """Check availability with optional proxy from settings."""
    from gui.settings_manager import SettingsManager
    from browser_mimic import BrowserMimic

    # Check if proxy is enabled in settings
    settings = SettingsManager()
    use_proxy = settings.get_setting('proxy.enabled', False)

    if use_proxy:
        api_key = settings.get_setting('proxy.api_key', '')
        if api_key:
            mimic = BrowserMimic(use_scrapeops=True, scrapeops_api_key=api_key)
            print(f"[AUTO-PURCHASE] Using ScrapeOps proxy for monitoring")
        else:
            mimic = BrowserMimic()
    else:
        mimic = BrowserMimic()

    # ... rest of code
```

---

## Testing

### Test the Settings Dialog

1. Run GUI: `python gui_config.py`
2. Open Preferences
3. Go to Proxy Rotation tab
4. Check "Enable ScrapeOps proxy rotation"
5. Verify fields become active
6. Uncheck the checkbox
7. Verify fields become disabled
8. Re-enable and enter API key
9. Click OK
10. Reopen Preferences
11. Verify settings were saved

### Test Settings Persistence

```python
from gui.settings_manager import SettingsManager

settings = SettingsManager()

# Check saved values
print(f"Enabled: {settings.get_setting('proxy.enabled')}")
print(f"API Key: {settings.get_setting('proxy.api_key')}")
print(f"Country: {settings.get_setting('proxy.country')}")
print(f"Render JS: {settings.get_setting('proxy.render_js')}")
```

---

## Benefits

### For Users
✅ No code editing required
✅ Easy enable/disable toggle
✅ Settings persist across sessions
✅ Clear usage guidelines
✅ One-click access to signup

### For Developers
✅ Centralized settings storage
✅ Easy to check if proxy is enabled
✅ Consistent across all code
✅ Can add more proxy providers later

---

## Documentation Updated

1. ✅ `SCRAPEOPS_QUICKSTART.md` - Added GUI method as first option
2. ✅ `SCRAPEOPS_INTEGRATION.md` - Added GUI settings section
3. ✅ `GUI_PROXY_SETTINGS.md` (this file) - Complete implementation docs

---

## Summary

**Added**: Complete GUI settings panel for ScrapeOps proxy configuration

**Location**: File → Preferences → Proxy Rotation tab

**Features**:
- Enable/disable checkbox
- API key entry (password field)
- Country selection dropdown
- JavaScript rendering toggle
- Usage information
- When to use guidelines
- Clickable help links

**Settings Saved To**: `user_settings.json`

**Benefits**: Users can now enable proxy rotation without editing code!

---

**Implementation Date**: October 8, 2025
**Status**: ✅ Complete and tested
**Ready to Use**: Yes
