# Quick Start Guide

## 1. Start the Backend (5 seconds)

Open a terminal and run:

```bash
cd "C:\Python Projects\mandarake_scraper\archive\yahoo_auction"
python rss_web_viewer.py
```

You should see:
```
============================================================
Mandarake RSS Web Viewer
============================================================

Starting server at http://localhost:5000
Press Ctrl+C to stop
```

**Keep this terminal open while using the extension!**

---

## 2. Install Chrome Extension (30 seconds)

1. Open Chrome
2. Go to `chrome://extensions/`
3. Turn ON **Developer mode** (top-right toggle)
4. Click **Load unpacked**
5. Select folder: `C:\Python Projects\mandarake_scraper\archive\yahoo_auction\mandarake_ebay_extension`
6. Done! You should see "Mandarake Price Checker for eBay" in your extensions

---

## 3. Test It Out (1 minute)

1. Go to eBay: https://www.ebay.com
2. Search for something Japanese (e.g., "Pokemon card", "anime figure", "manga")
3. Look for "🔍 Check Mandarake Price" buttons below each listing
4. Click a button and wait 2-3 seconds
5. See the price comparison!

**Example result:**
```
💰 Mandarake: ¥2,800 ($18.47)
📊 Profit: +$23.03 (51%)
✅ In Stock @ Nakano
🔗 View on Mandarake
```

---

## Troubleshooting

### No buttons appear on eBay

**Fix**: Refresh the eBay page (F5)

### "Backend: Not Running" in extension popup

**Fix**: Start the Flask server (see step 1)

### "❌ Not Found on Mandarake"

This is normal - the item doesn't exist on Mandarake. Try another listing.

### Buttons say "⚠️ Error - Click to Retry"

**Fix**: Make sure Flask server is running at localhost:5000

---

## Tips

- ✅ Only click "Check Price" on items you're interested in (lazy loading saves time)
- ✅ Results are cached - clicking twice won't make extra API calls
- ✅ Green backgrounds = high profit items (50%+)
- ✅ Stock status shows if you can actually buy it at Mandarake
- ⚠️ Wait 2-3 seconds per request (built-in rate limiting)

---

## What Next?

- Click the extension icon to adjust USD/JPY rate
- Check backend terminal to see search logs
- Read README.md for full documentation
