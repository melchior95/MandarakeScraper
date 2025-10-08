# Cart URL Format Support

**Date**: October 7, 2025
**Issue**: User provided cart URL with `te-uniquekey` parameter instead of `jsessionid`
**Status**: ✅ Fixed - Now supports both formats

---

## Supported URL Formats

### Format 1: te-uniquekey (Query Parameter) - NEW
```
https://cart.mandarake.co.jp/cart/view/order/inputReceiverEn.html?te-uniquekey=199c1ff6120
```

**Characteristics**:
- Uses `te-uniquekey` as query parameter
- Typically appears on `cart.mandarake.co.jp` domain
- Newer format used by Mandarake

**How it works**:
1. System visits the URL
2. Mandarake server sets session cookies in response
3. Session cookies are extracted and saved
4. Cookies are used for subsequent cart API calls

### Format 2: jsessionid in Path (Semicolon) - CLASSIC
```
https://order.mandarake.co.jp/order/cartList/;jsessionid=ABC123DEF456789
```

**Characteristics**:
- Uses `;jsessionid=` in URL path
- Typically appears on `order.mandarake.co.jp` domain
- Older format, still supported

**How it works**:
1. Session ID extracted from URL
2. Set as cookie: `JSESSIONID=ABC123DEF456789`
3. Used directly for cart API calls

### Format 3: jsessionid as Query Parameter - ALTERNATE
```
https://order.mandarake.co.jp/order/cartList/?jsessionid=ABC123DEF456789
```

**Characteristics**:
- Uses `?jsessionid=` as query parameter
- Less common but still valid
- Treated same as Format 2

---

## How to Get Your Cart URL

### Method 1: From Browser Address Bar (Recommended)

1. **Open Mandarake cart** in your web browser
2. **Log in** to your account
3. **Go to cart page** or checkout page
4. **Copy the entire URL** from address bar
5. **Paste into connection dialog**

**Examples of valid cart pages**:
- `https://cart.mandarake.co.jp/cart/view/order/inputReceiverEn.html?te-uniquekey=...`
- `https://cart.mandarake.co.jp/cart/view/order/inputOrderEn.html?te-uniquekey=...`
- `https://order.mandarake.co.jp/order/cartList/;jsessionid=...`

### Method 2: From Email Link

If Mandarake sends cart recovery emails:
1. Open email
2. Click cart link
3. Wait for page to load
4. Copy URL from address bar

---

## Connection Process

### What Happens When You Connect

**With `te-uniquekey` URL**:
```
1. User pastes: https://cart.mandarake.co.jp/...?te-uniquekey=199c1ff6120
2. System extracts: unique_key = "199c1ff6120"
3. System visits URL with browser headers
4. Mandarake responds with cookies:
   - JSESSIONID
   - Other session cookies
5. System extracts all cookies from response
6. System verifies session by accessing cart page
7. If successful:
   - Cookies saved to mandarake_session.json
   - Status: "✓ Connected"
8. If failed:
   - Shows error message
   - Suggests re-copying URL
```

**With `jsessionid` URL**:
```
1. User pastes: https://order.mandarake.co.jp/...;jsessionid=ABC123
2. System extracts: session_id = "ABC123"
3. System creates cookie: JSESSIONID=ABC123
4. System verifies session by accessing cart page
5. If successful:
   - Cookie saved to mandarake_session.json
   - Status: "✓ Connected"
6. If failed:
   - Shows "Session expired" error
   - User needs to get fresh URL
```

---

## Troubleshooting

### Issue: "No session info found"

**Symptom**: Error message saying "Invalid cart URL - no session info found"

**Cause**: URL doesn't contain `jsessionid` or `te-uniquekey`

**Solution**:
1. Make sure you're copying from the **cart page**, not the homepage
2. Check that you're **logged in** before copying URL
3. Copy the **entire URL** including all parameters

**Bad examples**:
```
https://cart.mandarake.co.jp/                    ❌ (no session info)
https://order.mandarake.co.jp/                   ❌ (no session info)
https://order.mandarake.co.jp/order/listPage/... ❌ (not cart page)
```

**Good examples**:
```
https://cart.mandarake.co.jp/cart/view/order/inputReceiverEn.html?te-uniquekey=199c1ff6120 ✅
https://order.mandarake.co.jp/order/cartList/;jsessionid=ABC123DEF456                      ✅
```

### Issue: "Session expired" or "Connection failed"

**Symptom**: URL is valid format but connection fails

**Causes**:
1. **Session has expired** (URLs expire after ~30 minutes of inactivity)
2. **Logged out** in browser
3. **Network issues**

**Solutions**:
1. **Get a fresh URL**:
   - Go back to Mandarake cart in browser
   - Refresh the page
   - Copy the new URL
2. **Make sure you're logged in**:
   - Check browser shows your account
   - Re-login if needed
3. **Try immediately**:
   - Copy URL
   - Paste into dialog right away
   - Don't wait more than a few minutes

### Issue: "No session cookies received"

**Symptom**: Specific to `te-uniquekey` URLs

**Cause**: Mandarake didn't send cookies in response

**Solutions**:
1. **Try a different cart page**:
   - Instead of receiver address page, try cart list page
   - Different pages may have different cookie behavior
2. **Check browser cookies**:
   - Open browser dev tools (F12)
   - Go to Application → Cookies
   - Look for mandarake.co.jp cookies
   - If none exist, re-login
3. **Use jsessionid format** (if available):
   - Some users get jsessionid URLs
   - Those are more reliable

---

## Technical Details

### URL Parsing Code

**Location**: `scrapers/mandarake_cart_api.py:54-91`

```python
def extract_session_from_url(self, cart_url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract session info from cart URL"""
    session_id = None
    unique_key = None

    # Try jsessionid in path: ;jsessionid=ABC123
    match = re.search(r';jsessionid=([A-Fa-f0-9]+)', cart_url)
    if match:
        session_id = match.group(1)

    # Try jsessionid as query param: ?jsessionid=ABC123
    if not session_id:
        match = re.search(r'[?&]jsessionid=([A-Fa-f0-9]+)', cart_url)
        if match:
            session_id = match.group(1)

    # Try te-uniquekey: ?te-uniquekey=199c1ff6120
    match = re.search(r'[?&]te-uniquekey=([A-Fa-f0-9]+)', cart_url)
    if match:
        unique_key = match.group(1)

    return session_id, unique_key
```

### Connection Logic

**Location**: `scrapers/mandarake_cart_api.py:414-454`

```python
def login_with_url(self, cart_url: str) -> MandarakeCartAPI:
    """Create cart API from URL"""
    session_id, unique_key = api.extract_session_from_url(cart_url)

    # If jsessionid found, use it directly
    if session_id:
        cart_api = MandarakeCartAPI(session_id=session_id)
        if cart_api.verify_session():
            return cart_api

    # If te-uniquekey found, visit URL to get cookies
    if unique_key:
        temp_api = MandarakeCartAPI()
        response = temp_api.session.get(cart_url)

        if response.cookies:
            cookies = dict(response.cookies)
            cart_api = MandarakeCartAPI(session_cookies=cookies)
            if cart_api.verify_session():
                return cart_api

    raise ValueError("Invalid cart URL or session expired")
```

---

## Session Persistence

### How Sessions are Saved

**File**: `mandarake_session.json`

**Contents** (example):
```json
{
  "JSESSIONID": "ABC123DEF456789",
  "other-cookie": "value",
  "timestamp": "2025-10-07T12:34:56"
}
```

**Behavior**:
- Session saved after successful connection
- Automatically loaded on next GUI launch
- Remains valid for ~24-48 hours (Mandarake server decides)
- When expired, user must reconnect

### Session Verification

**How it works**:
```python
def verify_session(self) -> bool:
    """Verify session is still valid"""
    response = session.get("https://cart.mandarake.co.jp/cart/view/order/inputOrderEn.html")

    # If redirected to login page, session is expired
    if 'login' in response.url.lower():
        return False

    return response.status_code == 200
```

**Verification triggers**:
- On connection
- Before add-to-cart operations
- When refreshing cart display
- On GUI startup (if session file exists)

---

## Security Notes

### What is Stored?

- **Session cookies** (temporary, expire after ~24-48h)
- **No passwords** or personal info
- **No payment details**

### Where is it Stored?

- Local file: `mandarake_session.json`
- In project directory
- **Not uploaded to GitHub** (in `.gitignore`)

### Can Someone Steal My Session?

**If someone gets your session cookies**:
- They can access your cart
- They can see items you've added
- They **CANNOT** complete purchase (needs password confirmation)
- They **CANNOT** change password
- They **CANNOT** see payment methods

**Protection**:
- Sessions expire automatically
- Don't share `mandarake_session.json` file
- Don't post cart URLs publicly (they include session tokens)

---

## Related Documentation

- **[CART_CONNECTION_UPDATE.md](CART_CONNECTION_UPDATE.md)** - Connection workflow
- **[CART_SYSTEM_COMPLETE.md](CART_SYSTEM_COMPLETE.md)** - Cart API documentation

---

## Changelog

### October 7, 2025
- ✅ Added support for `te-uniquekey` URL format
- ✅ Updated URL extraction to handle 3 formats
- ✅ Added cookie extraction from URL visit
- ✅ Updated connection dialog instructions
- ✅ Improved error messages

---

**Status**: ✅ Both URL formats now supported
**Tested With**: User's URL `https://cart.mandarake.co.jp/cart/view/order/inputReceiverEn.html?te-uniquekey=199c1ff6120`
