# Troubleshooting: No Buttons Appearing

## Quick Checks

### 1. Are you on the right page?

The extension ONLY works on **eBay search results pages**.

✅ **These URLs work:**
- `https://www.ebay.com/sch/i.html?_nkw=pokemon`
- `https://www.ebay.com/sch/i.html?_nkw=anime+figure`
- Any URL starting with `https://www.ebay.com/sch/`

❌ **These URLs DON'T work:**
- `https://www.ebay.com` (home page)
- `https://www.ebay.com/itm/...` (individual item pages)
- Other eBay pages (My eBay, Selling, etc.)

**Test:** Go to https://www.ebay.com/sch/i.html?_nkw=pokemon

---

### 2. Is the extension enabled?

1. Go to `chrome://extensions/`
2. Find "Mandarake Price Checker for eBay"
3. Make sure the toggle is **ON** (blue)
4. Check for any error messages

**If you see an error:**
- Click "Errors" to see details
- Most common: Missing icon files (you can ignore this)

---

### 3. Check the console

1. Go to eBay search page: https://www.ebay.com/sch/i.html?_nkw=pokemon
2. Press **F12** to open Developer Tools
3. Click **Console** tab
4. Refresh the page (F5)

**Look for these messages:**

✅ **Good (extension is working):**
```
Mandarake Price Checker: Initializing...
Mandarake Extension: Found 50 listings
Mandarake Price Checker: Ready!
```

❌ **Bad (extension has errors):**
```
Uncaught ReferenceError: ...
Failed to load resource: net::ERR_BLOCKED_BY_CLIENT
Content Security Policy violation...
```

---

## Debugging Steps

### Step 1: Verify extension files exist

Open this folder:
```
C:\Python Projects\mandarake_scraper\archive\yahoo_auction\mandarake_ebay_extension\
```

You should see:
- ✅ manifest.json
- ✅ content.js
- ✅ styles.css
- ✅ popup.html
- ✅ popup.js
- ✅ icon16.png, icon48.png, icon128.png

**Missing files?** Re-run the setup.

---

### Step 2: Reload the extension

1. Go to `chrome://extensions/`
2. Find "Mandarake Price Checker"
3. Click the **reload icon** (circular arrow)
4. Go back to eBay search page
5. Hard refresh: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)

---

### Step 3: Check manifest URL patterns

Open `manifest.json` and verify:

```json
{
  "content_scripts": [
    {
      "matches": ["https://www.ebay.com/sch/*"],
      ...
    }
  ]
}
```

**The matches pattern MUST be exactly:** `https://www.ebay.com/sch/*`

---

### Step 4: Test with console commands

1. Open eBay search: https://www.ebay.com/sch/i.html?_nkw=pokemon
2. Open Console (F12)
3. Paste this code:

```javascript
// Check if listings exist
const listings = document.querySelectorAll('.s-item');
console.log('Found', listings.length, 'listings');

// Check if extension already injected buttons
const buttons = document.querySelectorAll('.mandarake-check-btn');
console.log('Found', buttons.length, 'Mandarake buttons');

// Manually inject a test button
if (listings.length > 0 && buttons.length === 0) {
    const firstListing = listings[1]; // Skip ad in position 0
    const btn = document.createElement('button');
    btn.textContent = 'TEST BUTTON';
    btn.style.cssText = 'background: red; color: white; padding: 10px; margin: 10px;';

    const detail = firstListing.querySelector('.s-item__detail');
    if (detail) {
        detail.appendChild(btn);
        console.log('✅ Injected test button - if you see it, injection works!');
    } else {
        console.log('❌ Could not find .s-item__detail element');
    }
}
```

**Expected output:**
```
Found 50 listings
Found 0 Mandarake buttons
✅ Injected test button - if you see it, injection works!
```

If you see a red "TEST BUTTON" on the first listing, extension injection should work.

---

### Step 5: Check eBay page structure

eBay sometimes changes their HTML structure. As of October 2025, eBay uses:

**Current Structure (2025):**
- `.s-card` (main listing container) - **NEW**
- `span[role="heading"]` (item title) - **MOST COMMON**
- `[class*="price"]` or `[data-testid*="price"]` (item price)
- `.su-card-container` (where we inject button)

**Old Structure (pre-2025):**
- `.s-item` (main listing container) - **OLD**
- `.s-item__title` (item title)
- `.s-item__price` (item price)
- `.s-item__detail` or `.s-item__info` (where we inject button)

**The extension now tries 7+ selectors for title and 6+ selectors for price automatically!**

If you still see errors after the latest update, eBay may have changed their layout again. Check the debug output in the console for detailed information about what elements were found.

---

### Step 6: Check CORS / Backend connection

1. Open Console (F12)
2. Go to **Network** tab
3. Click on a "Check Price" button (if visible)
4. Look for a request to `localhost:5000`

**If you see:**
- ❌ `(failed) net::ERR_CONNECTION_REFUSED` → Backend not running
- ❌ `(blocked) CORS error` → Need to add CORS headers
- ✅ `200 OK` → Backend is working!

---

## Common Issues & Fixes

### Issue: "Extension file is missing"

**Cause:** Icons not found
**Fix:** Either add icons or remove icon references from manifest.json:

```json
{
  "action": {
    "default_popup": "popup.html"
    // Remove these lines:
    // "default_icon": { ... }
  },
  // Remove this section:
  // "icons": { ... }
}
```

---

### Issue: Buttons appear but say "Backend: Not Running"

**Cause:** Flask server not running
**Fix:**
```bash
cd "C:\Python Projects\mandarake_scraper\archive\yahoo_auction"
python rss_web_viewer.py
```

Keep terminal open while using extension.

---

### Issue: eBay page structure changed

**Symptom:** Console shows "Found 0 listings"
**Fix:** eBay updated their HTML. We need to update the selectors in content.js.

Open eBay, inspect an item, and tell me the new class names you see.

---

### Issue: Extension works on some items but not others

**Cause:** Sponsored ads vs regular listings
**Fix:** Already handled in code - we skip `.s-item--ad` items.

---

## Manual Test

Want to test if your extension files are valid? Create this test file:

**test.html** (place in extension folder):
```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <h1>Extension Test Page</h1>

    <div class="s-item">
        <div class="s-item__title">Test Pokemon Card</div>
        <div class="s-item__price">$42.00</div>
        <div class="s-item__detail">
            <!-- Button should appear here -->
        </div>
    </div>

    <script src="content.js"></script>
    <script>
        // Wait for script to run
        setTimeout(() => {
            const btn = document.querySelector('.mandarake-check-btn');
            if (btn) {
                console.log('✅ Button injected successfully!');
            } else {
                console.log('❌ Button not found');
            }
        }, 1000);
    </script>
</body>
</html>
```

Open `test.html` in Chrome. If you see the "Check Price" button, the extension code works.

---

## Still Not Working?

Share these details:

1. **Chrome version:** (chrome://version/)
2. **Extension status:** (enabled/disabled, any errors?)
3. **eBay URL you're testing:**
4. **Console messages:** (copy from Console tab)
5. **What you see:** (screenshot if possible)

I'll help debug further!
