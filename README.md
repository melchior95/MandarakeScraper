# Mandarake Scraper

Comprehensive reselling toolkit for Mandarake listings with eBay price comparison, computer vision image matching, and complete workflow management from discovery to sale tracking.

## ✨ Feature Highlights
- 🛒 **Multi-marketplace**: Mandarake, Suruga-ya, eBay (DejaJapan & Mercari coming soon)
- 🔍 **AI-powered image matching**: Multi-metric computer vision (Template, ORB, SSIM, histogram)
- 📊 **Complete workflow**: Track items from discovery → purchase → sale (8-state system)
- 💰 **Profit calculator**: Live USD/JPY rates with similarity-based filtering
- 🔔 **Desktop notifications**: Alerts for high-value items (Windows/macOS/Linux)
- 🧹 **Smart cleanup**: Automated orphaned file management
- 🗄️ **SQLite backend**: High-performance alert storage
- 📅 **Scheduling**: Daily/interval scraping with resume capability
- 🎨 **Modular architecture**: 46 modules, 63% code reduction vs. monolithic design

## Prerequisites
- Python 3.10+
- Mandarake credentials are not required; the scraper mimics browser access.
- Google service-account JSON (if uploading to Sheets/Drive)
- eBay developer keys (optional, for price comparisons)

## Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd mandarake_scraper
python -m venv venv
venv\Scripts\activate           # Windows (use `source venv/bin/activate` on macOS/Linux)
pip install -r requirements.txt

# 2. Launch GUI
python gui_config.py

# 3. Or run CLI scraper
python mandarake_scraper.py --config configs/example.json
```

**First time users**: See the GUI walkthrough in the [Mandarake Tab](#1-mandarake-tab) section below.

## Configuration
Create JSON configs in `configs/`. Example:
```json
{
  "keyword": "Naruto",
  "category": "30",
  "shop": "nakano",
  "hide_sold_out": false,
  "recent_hours": 24,
  "max_pages": 5,
  "client_id": "YOUR_EBAY_CLIENT_ID",
  "client_secret": "YOUR_EBAY_CLIENT_SECRET",
  "mimic": false,
  "google_sheets": {
    "sheet_name": "Mandarake Results",
    "worksheet_name": "Sheet1"
  },
  "upload_sheets": true,
  "csv": "results/naruto_nakano.csv",
  "download_images": "images/naruto/",
  "upload_drive": true,
  "drive_folder": "YOUR_DRIVE_FOLDER_ID",
  "thumbnails": 400,
  "fast": false,
  "resume": true,
  "debug": false
}
```

### Key Options
- `keyword`: Mandarake search term (required).
- `category`: Code or list of codes; omit for all categories.
- `shop`: Store code/slug/list; see `MANDARAKE_CODES.md`.
- `hide_sold_out`: Adds `soldOut=1` to hide unavailable items.
- `recent_hours`: Only items uploaded in the last N hours (maps to `upToMinutes`).
- `max_pages`: Maximum pages to scrape per category/shop.
- `upload_sheets`: Toggle Google Sheets export.
- `upload_drive`: Upload downloaded images to Drive.
- `fast`: Skip eBay enrichment.
- `resume`: Persist checkpoints.
- `debug`: Verbose logging.

## Running from CLI
```bash
python mandarake_scraper.py --config configs/naruto.json
```
Schedule or interval runs:
```bash
python mandarake_scraper.py --config configs/naruto.json --schedule 14:00
python mandarake_scraper.py --config configs/naruto.json --interval 30
```
Direct Mandarake URL:
```bash
python mandarake_scraper.py --url "https://order.mandarake.co.jp/order/ListPage/list?keyword=pokemon&shop=1"
```

## GUI Application (`gui_config.py`) - Primary Interface

Run `python gui_config.py` for the complete reselling workflow interface.

### Architecture
**Fully modularized** (46 modules, 1473 lines down from 4000+, 63% reduction):
- **Tab modules** (11 files): UI layout and widgets (`gui/*_tab.py`)
- **Manager classes** (15+ files): Business logic and data processing (`gui/*_manager.py`)
- **Workers** (`gui/workers.py`): Background thread operations
- **Scrapers** (`scrapers/*.py`): Marketplace integrations with `BaseScraper` pattern
- **Utils** (`gui/utils.py`): Pure utility functions
- **Storage** (`gui/alert_storage_db.py`): SQLite-based persistence

### Four Main Tabs

#### 1. Mandarake Tab
- Visual config builder with store/category dropdowns
- Live URL preview
- Auto-named configs (`keyword_category_shop.json`)
- Results treeview with thumbnails
- Schedule daily runs or interval scraping
- Press Enter in keyword field to auto-save config

#### 2. eBay Search & CSV Tab
- Load Mandarake CSV results
- Search eBay sold listings (Scrapy-based)
- **Computer vision image comparison**:
  - Multi-metric matching: Template (60%), ORB features (25%), SSIM (10%), histogram (5%)
  - Optional RANSAC geometric verification
  - Debug output saved to `debug_comparison/`
- Profit margin calculation (USD/JPY auto-updated)
- Filter by similarity % and profit %
- Send high-value items to Review/Alerts tab

#### 3. Review/Alerts Tab - Complete Reselling Workflow
Track items through 8 states:
1. **Pending** - Auto-added items meeting thresholds (default: 70% similarity, 20% profit)
2. **Yay** - Items marked for purchase
3. **Nay** - Items rejected
4. **Purchased** - Bulk purchase from Yays
5. **Shipped** - In transit
6. **Received** - Arrived
7. **Posted** - Listed for resale
8. **Sold** - Transaction complete

Features:
- Drag-and-drop reordering
- Bulk state transitions
- Threshold filtering (auto-populate from CSV comparison)
- Persistence via `alerts.json`

#### 4. Advanced Tab
- **Google Sheets/Drive integration** - OAuth service account configuration
- **Image download settings** - Thumbnail size, download location
- **Marketplace toggles** - Enable/disable eBay, Mercari, etc.
- **Notification settings** - Desktop alerts for high-value items
- **Cleanup utility** - Smart orphaned file management
  - CSV/image cleanup for deleted configs
  - Debug folder pruning (7+ days old)
  - Log rotation (30+ days old)
  - Python cache cleanup
  - Protects active configs and scheduled searches
- **Schedule viewer** - View/edit all scheduled scrapes
- **Debug options** - Verbose logging, RANSAC verification

## Key Features

### 🛒 Multi-Marketplace Support
**Implemented:**
- **Mandarake** - Primary Japanese marketplace (order.mandarake.co.jp)
- **Suruga-ya** - Books, games, collectibles (www.suruga-ya.jp)
- **eBay** - Price comparison and sold listings analysis

**Extensible Architecture:**
- `BaseScraper` abstract class for new marketplace integrations
- `BaseMarketplaceTab` for consistent GUI experience
- Normalized data format across all marketplaces
- 46+ GUI modules supporting modular marketplace additions

**Coming Soon:**
- DejaJapan integration (tab UI ready)
- Yahoo Auctions (archived implementation available)
- Mercari support

### 🔍 Advanced Image Comparison
- **Multi-metric computer vision** algorithm with weighted scoring:
  - Template matching (60%) - Exact visual match detection
  - ORB features (25%) - Keypoint-based matching
  - SSIM (10%) - Structural similarity
  - Histogram (5%) - Color distribution
- **Optional RANSAC** geometric verification for perspective changes
- **Debug output system** - Visual comparison images saved to `debug_comparison/`
- **Thumbnail caching** - Optimized performance with PIL image cache
- **Secondary keyword extraction** - Publisher list-based refinement

### 📊 Complete Reselling Workflow
- **Automated threshold-based discovery** (customizable similarity % and profit %)
- **8-state workflow tracking**:
  1. Pending → 2. Yay → 3. Nay → 4. Purchased → 5. Shipped → 6. Received → 7. Posted → 8. Sold
- **Profit margin calculation** with live USD/JPY exchange rates
- **Bulk operations** - Multi-select state transitions
- **Drag-to-reorder** items within each state
- **SQLite backend** for performance (migrated from JSON)
- **Desktop notifications** for high-value alerts (Windows/macOS/Linux via plyer)
- **Export functionality** - CSV export with filtering by state

### 🛡️ Anti-Detection & Reliability
- **Browser mimicking** with custom headers, cookies, and timing patterns
- **Configurable rate limiting** per marketplace (default: 2s between requests)
- **Resume/checkpoint functionality** - Never lose progress on interrupted scrapes
- **Session persistence** - Maintains cookies and state
- **Scrapy-based eBay scraping** - More reliable than Playwright for sold listings
- **Anti-bot measures** - Random delays, realistic User-Agent rotation

### 📁 Data Management & Automation
- **Auto-named configs** - `keyword_category_shop.json` pattern
- **CSV auto-export** - Matching naming scheme in `results/`
- **Image organization** - Downloaded to `images/keyword_category_shop/`
- **Google Sheets/Drive integration** - OAuth service account support
- **Publisher list management** - Right-click keyword extraction
- **Persistent settings** - User preferences in `user_settings.json`
- **Alert persistence** - SQLite database (`alerts.db`)
- **Schedule management** - Daily/interval scraping with `schedules.json`

### 🧹 Maintenance & Cleanup
- **Orphaned file detection** - Finds CSV/images with no matching config
- **Smart cleanup utility** - Protects active configs and scheduled searches
- **Debug folder pruning** - Removes comparison images older than 7 days
- **Cache cleanup** - Python `__pycache__` removal
- **Log rotation** - Removes logs older than 30 days
- **Dry-run preview** - See what will be deleted before confirming

## Outputs & Data Files

### Generated Files
- **CSV results**: `results/keyword_category_shop.csv` (auto-named)
- **Product images**: `images/keyword_category_shop/` (organized by config)
- **Debug images**: `debug_comparison/query_timestamp/` (image comparison visual output)
- **Logs**: `mandarake_scraper_YYYYMMDD.log` (daily rotation)

### Configuration & State
- **User settings**: `user_settings.json` (window geometry, preferences, recent files)
- **Alert database**: `alerts.db` (SQLite, replaces legacy `alerts.json`)
- **Schedules**: `schedules.json` (daily/interval scraping configs)
- **Publisher list**: `publishers.txt` (for keyword extraction)
- **Config order**: `configs/.config_order.json` (drag-to-reorder persistence)

### Cloud Integration (Optional)
- **Google Sheets**: Live spreadsheet updates
- **Google Drive**: Automatic image uploads to specified folder

## Testing
```bash
# Test alert workflow
python test_alert_tab.py

# Test image comparison algorithms
python test_image_comparison.py

# Test eBay Scrapy integration
python test_scrapy_ebay.py

# Test CSV comparison with configs
python test_comparison_configs.py
```

## Troubleshooting

### Mandarake Issues
- **403 / Captcha**: Enable browser mimic mode (`use_mimic=True`), reduce request rate, or try off-peak hours
- **Empty results**: Verify keyword/category/shop codes; use GUI URL preview

### eBay Issues
- **Access blocked**: Wait 2-5 minutes between searches; Scrapy-based search is more reliable
- **403 errors**: Ensure Browse API scope is enabled; check credentials

### General
- **Google quota errors**: Verify credentials, folder permissions, and quotas
- **Japanese text encoding**: Config filenames use MD5 hash for non-ASCII characters
- **Image comparison accuracy**: RANSAC helps with perspective changes; watermarks may reduce accuracy

## Project Status

### Current Release: v1.0 (Modularized)
**Architecture**: ✅ Fully Modularized (46 modules, 63% code reduction)
**Documentation**: ✅ Consolidated and Current
**Test Coverage**: ✅ Manual testing complete
**Last Updated**: October 2025

### Module Count
- **GUI Modules**: 46 files in `gui/`
- **Scrapers**: 3 implementations (Mandarake, Suruga-ya, eBay)
- **Tab Modules**: 11 (Mandarake, eBay, Advanced, Alert, Suruga-ya, etc.)
- **Manager Classes**: 15+ (Configuration, Tree, Alert, CSV, eBay Search, etc.)
- **Total Lines**: ~1473 (main GUI) + ~3000 (modules)

### Recent Features (Oct 2025)
- ✅ SQLite migration for alert storage (performance boost)
- ✅ Desktop notification system (plyer/win10toast)
- ✅ Cleanup utility for orphaned files
- ✅ Suruga-ya marketplace integration
- ✅ Image comparison scheduler ("Compare All")
- ✅ Unified settings/preferences dialog
- ✅ Thumbnail caching optimization
- ✅ Export alerts to CSV

### Planned Features
- 🔄 DejaJapan marketplace integration (UI ready)
- 🔄 Mercari support
- 🔄 Unit tests for manager classes
- 🔄 Type hints across codebase
- 🔄 Event-driven architecture migration
- 🔄 Advanced filtering (date ranges, price ranges)
- 🔄 Batch image comparison improvements

## Documentation

### Essential Reading
- **[PROJECT_DOCUMENTATION_INDEX.md](PROJECT_DOCUMENTATION_INDEX.md)** - Complete documentation index
- **[MANDARAKE_CODES.md](MANDARAKE_CODES.md)** - Store and category code mappings
- **[GUI_MODULARIZATION_COMPLETE.md](GUI_MODULARIZATION_COMPLETE.md)** - Architecture details
- **[ALERT_TAB_COMPLETE.md](ALERT_TAB_COMPLETE.md)** - Alert system documentation
- **[EBAY_IMAGE_COMPARISON_GUIDE.md](EBAY_IMAGE_COMPARISON_GUIDE.md)** - Image matching algorithms
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for working with this codebase
