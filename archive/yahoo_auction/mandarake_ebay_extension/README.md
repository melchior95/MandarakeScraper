# Mandarake Price Checker for eBay

Chrome extension that automatically checks Mandarake prices and stock status directly on eBay search results. Works like Keepa for Amazon - shows profit margins, stock availability, and direct links to Mandarake listings.

## Features

- 🔍 **Lazy Loading**: "Check Price" button on each eBay listing
- 💰 **Price Comparison**: Shows Mandarake price in JPY and USD with profit calculation
- ✅ **Stock Status**: Real-time stock availability at Mandarake stores
- 📊 **Profit Indicators**: Color-coded profit margins (green = high profit, red = low)
- 🔗 **Direct Links**: Click to view item on Mandarake
- 📦 **Caching**: Remembers checked prices to avoid repeated searches
- ⚡ **Rate Limited**: Built-in 2-second delay to avoid blocking

## Installation

### 1. Backend Setup

First, make sure the Flask backend is running:

```bash
cd "C:\Python Projects\mandarake_scraper\archive\yahoo_auction"
python rss_web_viewer.py
```

The backend should start at `http://localhost:5000`

### 2. Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right corner)
3. Click **Load unpacked**
4. Navigate to and select this folder: `C:\Python Projects\mandarake_scraper\archive\yahoo_auction\mandarake_ebay_extension`
5. The extension should now appear in your extensions list

### 3. Add Extension Icons (Optional)

The extension references icon files in manifest.json. You can:
- Add your own icon images (icon16.png, icon48.png, icon128.png)
- Or comment out the icon references in manifest.json

## Usage

### Basic Workflow

1. **Start the backend**: Run `rss_web_viewer.py`
2. **Search on eBay**: Go to eBay and search for items (e.g., "Pokemon card", "anime figure")
3. **Check prices**: Click "🔍 Check Mandarake Price" button on any listing
4. **View results**: See price comparison, profit margin, and stock status

### Example Output

When you click "Check Price", you'll see:

```
┌─────────────────────────────────────┐
│ 💰 Mandarake: ¥2,800 ($18.47)     │
│ 📊 Profit: +$23.03 (51%)           │ [Green background = High profit]
│ ✅ In Stock @ Nakano               │
│ 🔗 View on Mandarake               │
│                           📦 Cached│
└─────────────────────────────────────┘
```

### Profit Color Coding

- 🟢 **Green**: 50%+ profit margin (excellent deal)
- 🔵 **Blue**: 20-50% profit (good deal)
- 🟡 **Yellow**: 10-20% profit (marginal)
- 🔴 **Red**: <10% profit (not worth it)

### Stock Status

- ✅ **In Stock** - Item available for purchase
- ❌ **Out of Stock** - Item sold out (but still shows price for reference)

## Configuration

Click the extension icon in Chrome to access settings:

- **USD/JPY Exchange Rate**: Adjust currency conversion rate (default: 151.5)
- **Backend Status**: Shows if Flask server is running

## How It Works

### Frontend (Chrome Extension)

1. **content.js** - Injects "Check Price" buttons into eBay search results
2. When clicked, sends item title to backend API
3. Displays price overlay with color-coded profit margins
4. Caches results to avoid repeated API calls

### Backend (Flask API)

1. **Endpoint**: `POST /api/mandarake/search`
2. Receives eBay item title
3. Searches Mandarake using BrowserMimic (anti-bot detection)
4. Extracts:
   - Price (¥)
   - Stock status (In Stock / Out of Stock)
   - Store location
   - Item link
5. Returns JSON with all data

### Stock Detection

Checks for these indicators:
- ✅ English: "In stock", "In warehouse"
- ✅ Japanese: "在庫あります"
- ❌ "Sold out", "売切"

## Technical Details

### Files

```
mandarake_ebay_extension/
├── manifest.json      # Extension configuration
├── content.js         # Main logic (lazy loading, price display)
├── styles.css         # Price overlay styling
├── popup.html         # Settings UI
├── popup.js           # Settings logic
└── README.md          # This file
```

### API Endpoint

**Request:**
```json
POST http://localhost:5000/api/mandarake/search
{
  "title": "Pokemon Pikachu Card"
}
```

**Response (found):**
```json
{
  "found": true,
  "mandarake_price_jpy": 2800,
  "mandarake_price_usd": 18.48,
  "in_stock": true,
  "store": "Nakano",
  "link": "https://order.mandarake.co.jp/order/detailPage/item?itemCode=...",
  "title": "ポケモンカード ピカチュウ",
  "item_code": "1234567890"
}
```

**Response (not found):**
```json
{
  "found": false
}
```

### Rate Limiting

- Built-in 2-second delay between Mandarake requests
- Prevents IP blocking
- Caches results to minimize API calls

## Troubleshooting

### "Backend: Not Running" in popup

**Solution**: Start the Flask server:
```bash
cd "C:\Python Projects\mandarake_scraper\archive\yahoo_auction"
python rss_web_viewer.py
```

### "Check Price" buttons don't appear

**Solutions**:
1. Refresh the eBay page
2. Check Chrome console for errors (F12 → Console)
3. Verify extension is enabled in `chrome://extensions/`

### "❌ Not Found on Mandarake"

This means:
- Item doesn't exist on Mandarake
- Search term doesn't match any listings
- Mandarake blocked the request (wait 5 minutes, try again)

### Stock status always shows "Out of Stock"

Possible causes:
- Mandarake page structure changed (update `.stock` selector)
- Japanese vs English language mismatch (check `stock_text` in backend logs)

## Future Enhancements

- [ ] SQLite cache database for persistent storage
- [ ] Batch "Check All Prices" button
- [ ] Custom profit thresholds
- [ ] Firefox support
- [ ] Auto-translate Japanese titles
- [ ] Price history tracking
- [ ] Email alerts for high-profit items

## License

Part of the Mandarake Scraper project.

## Notes

- Requires active internet connection
- Mandarake may block excessive requests (use responsibly)
- Exchange rates are manual (update in settings as needed)
- Only works on eBay search results pages (`ebay.com/sch/*`)
