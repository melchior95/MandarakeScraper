# Alternative Cart Connection Methods

**Issue**: `te-uniquekey` URLs expire quickly and redirect to login when accessed programmatically.

---

## Recommended Solution: Export Browser Cookies

Since the `te-uniquekey` URL doesn't work, the best approach is to **export your browser cookies** directly.

### Method 1: Cookie Export (Recommended)

#### Step 1: Install Browser Extension

Install one of these extensions:
- **Chrome/Edge**: [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
- **Firefox**: [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

#### Step 2: Export Mandarake Cookies

1. **Open Mandarake cart** in your browser (stay logged in)
2. **Click the Cookie-Editor extension** icon
3. **Click "Export"** button (exports all cookies for current site)
4. **Save as JSON** to: `mandarake_cookies.json` in your project folder

#### Step 3: Test Connection

Run this to test your cookies:

```bash
python test_cart_with_cookies.py
```

Or in GUI:
1. Place `mandarake_cookies.json` in project root
2. Open GUI: `python gui_config.py`
3. Go to Review/Alerts tab
4. Click "🔌 Connect to Cart"
5. The connection should work automatically if cookies are valid

---

## Method 2: Browser DevTools (Manual Cookie Copy)

If you don't want to install an extension:

### Step 1: Get Cookies from DevTools

1. **Open Mandarake cart** in browser
2. Press **F12** to open DevTools
3. Go to **Application** tab (Chrome) or **Storage** tab (Firefox)
4. Click **Cookies** → **https://cart.mandarake.co.jp**
5. Look for these important cookies:
   - `JSESSIONID`
   - `PHPSESSID`
   - Any other cookies you see

### Step 2: Create mandarake_cookies.json

Create a file `mandarake_cookies.json` with this format:

```json
{
  "JSESSIONID": "YOUR_JSESSIONID_VALUE_HERE",
  "PHPSESSID": "YOUR_PHPSESSID_VALUE_HERE"
}
```

Replace `YOUR_JSESSIONID_VALUE_HERE` with the actual cookie value from DevTools.

### Step 3: Test

```bash
python gui_config.py
```

Connection should work automatically.

---

## Method 3: Get jsessionid URL Instead

Some Mandarake pages use the older `jsessionid` format which works better programmatically.

### How to Find jsessionid URL

1. **Open Mandarake cart** in browser
2. **Click through cart steps** (cart → checkout → delivery address)
3. **Watch the URL** - if it changes to include `;jsessionid=`, copy that URL
4. Example: `https://order.mandarake.co.jp/order/cartList/;jsessionid=ABC123DEF456`

**This URL format works more reliably** because:
- The session ID is in the URL path, not a query parameter
- It doesn't redirect to login when accessed programmatically
- It's more stable

---

## Why te-uniquekey Doesn't Work

**The problem with te-uniquekey URLs**:

1. **Short expiration**: Only valid for a few minutes
2. **One-time use**: May be consumed when you first visit the page
3. **Requires active session**: Expects you to already be logged in
4. **Redirects to login**: When accessed without valid session cookies

**Technical explanation**:
```
Your browser:
1. Already logged in with session cookies
2. te-uniquekey is just a temporary cart recovery token
3. Works because you have valid session

Our script:
1. No session cookies (not logged in)
2. Visits URL with te-uniquekey
3. Mandarake: "You're not logged in, go to login page"
4. Redirect to login → no cart access
```

---

## Recommended Workflow

### Best Approach:

**Use Cookie Export Method**:

1. ✅ **Most reliable**
2. ✅ **Works with any Mandarake page**
3. ✅ **Session stays valid for 24-48 hours**
4. ✅ **Easy to update when session expires**

### Steps:

```bash
# 1. Install Cookie-Editor extension in your browser

# 2. Open Mandarake cart in browser (logged in)

# 3. Click Cookie-Editor icon → Export → Save as mandarake_cookies.json

# 4. Place file in project root:
#    C:\Python Projects\mandarake_scraper\mandarake_cookies.json

# 5. Run GUI:
python gui_config.py

# 6. Click "Connect to Cart" - should connect automatically
```

### When Session Expires:

**Symptoms**:
- "Session expired" error
- "Redirected to login" warning

**Solution**:
1. Delete old `mandarake_cookies.json`
2. Export fresh cookies from browser
3. Save new file
4. Reconnect in GUI

---

## Quick Cookie Export Guide

### Chrome/Edge:

1. Install [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
2. Open https://cart.mandarake.co.jp in browser (logged in)
3. Click Cookie-Editor extension icon (🍪)
4. Click **"Export"** button (bottom right)
5. **Copy the JSON** or save to file
6. Save as `mandarake_cookies.json` in project folder

### Firefox:

1. Install [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)
2. Open https://cart.mandarake.co.jp (logged in)
3. Click Cookie-Editor extension icon
4. Click **"Export"**
5. Save as `mandarake_cookies.json`

---

## Testing Your Connection

### Test Script:

```bash
python -c "
from scrapers.mandarake_cart_api import MandarakeCartSession
import json

# Load cookies
with open('mandarake_cookies.json', 'r') as f:
    cookies = json.load(f)

# Try to connect
session_mgr = MandarakeCartSession()
try:
    cart_api = session_mgr.login_with_cookies(cookies)
    print('✓ Connected successfully!')

    # Try to get cart
    cart_items = cart_api.get_cart_items()
    if cart_items:
        print(f'✓ Cart has {len(cart_items)} items')
    else:
        print('✓ Cart is empty')
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

---

## Summary

| Method | Reliability | Ease | Recommendation |
|--------|-------------|------|----------------|
| **Cookie Export** | ⭐⭐⭐⭐⭐ | Easy | ✅ **BEST** |
| **Manual DevTools** | ⭐⭐⭐⭐ | Medium | ✅ Good |
| **jsessionid URL** | ⭐⭐⭐ | Easy (if available) | ✅ OK |
| **te-uniquekey URL** | ⭐ | Easy | ❌ **Doesn't work** |

**Bottom line**: Use Cookie Export method for best results!

---

## Related Documentation

- **[CART_CONNECTION_UPDATE.md](CART_CONNECTION_UPDATE.md)** - Connection workflow
- **[CART_URL_FORMATS.md](CART_URL_FORMATS.md)** - URL format guide

---

**Last Updated**: October 7, 2025
**Status**: Cookie export recommended as primary method
