# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A comprehensive Mandarake scraper with GUI that extracts product listings from order.mandarake.co.jp, performs eBay price comparison with computer vision image matching, and manages reselling workflow through an alert system. Supports CSV export, Google Sheets integration, and automated scheduling.

## Running the Application

### GUI (Primary Interface)
```bash
python gui_config.py
```

The GUI has 4 tabs:
1. **Mandarake** - Configure and run Mandarake scrapes
2. **eBay Search & CSV** - Search eBay sold listings, compare with Mandarake CSV results
3. **Review/Alerts** - Manage reselling workflow (Pending → Yay → Purchased → Shipped → Received → Posted → Sold)
4. **Advanced** - Additional configuration options

### CLI Scraper
```bash
# Run with config file
python mandarake_scraper.py --config configs/yura_kano.json

# Schedule daily run
python mandarake_scraper.py --config configs/yura_kano.json --schedule 14:00

# Direct URL scrape
python mandarake_scraper.py --url "https://order.mandarake.co.jp/order/ListPage/list?keyword=pokemon"
```

### Testing
```bash
# Test alert tab functionality
python test_alert_tab.py

# Test image comparison
python test_image_comparison.py

# Test eBay Scrapy integration
python test_scrapy_ebay.py
```

## Architecture

### Core Components

**Main Scraper (`mandarake_scraper.py`)**
- Scrapes Mandarake listings with anti-detection measures
- Handles pagination, resume functionality, checkpointing
- Integrates with eBay API for price enrichment
- Exports to CSV and Google Sheets

**GUI Application (`gui_config.py`)**
- 4000+ line monolithic GUI (refactoring into `gui/` directory in progress)
- Manages configs, runs scraper, displays results
- Integrates eBay search, CSV comparison, and alert workflow

**Browser Mimic (`browser_mimic.py`)**
- Mimics real browser behavior to avoid bot detection
- Uses requests with custom headers, cookies, timing

**eBay Integration**
- `ebay_scrapy_search.py` - Scrapy-based eBay sold listings scraper
- `sold_listing_matcher.py` - Playwright-based image matching (visible browser)
- `sold_listing_matcher_requests.py` - Requests-based image matching (headless, faster)

**Image Comparison System**
- Multi-metric computer vision: Template matching (60%), ORB features (25%), SSIM (10%), histogram (5%)
- Optional RANSAC geometric verification for higher accuracy
- Debug output saves comparison images to `debug_comparison/`

### Modular GUI Components (`gui/` directory)

**Alert System** (Review/Alerts tab):
- `gui/alert_states.py` - State machine (Pending → Yay → Purchased → ... → Sold)
- `gui/alert_storage.py` - JSON persistence (`alerts.json`)
- `gui/alert_manager.py` - Business logic, threshold filtering
- `gui/alert_tab.py` - UI component with treeview, bulk actions

**Shared Utilities**:
- `gui/utils.py` - Config filename generation, CSV matching, exchange rates
- `gui/constants.py` - Store/category mappings, keywords
- `gui/workers.py` - Background thread workers for scraping, image analysis, CSV comparison

### Configuration System

**Config Files (`configs/*.json`)**
```json
{
  "keyword": "Yura Kano",
  "category": "701101",  // AV Actress Photograph Collection
  "shop": "all",
  "hide_sold_out": false,
  "max_pages": 5,
  "csv_show_in_stock_only": true,
  "csv_add_secondary_keyword": false,
  "client_id": "YOUR_EBAY_CLIENT_ID",
  "client_secret": "YOUR_EBAY_CLIENT_SECRET"
}
```

**Auto-naming**: Configs saved as `keyword_category_shop.json`
**CSV Output**: Results saved to `results/keyword_category_shop.csv`
**Images**: Downloaded to `images/keyword_category_shop/`

### Key Workflows

**Mandarake Scraping Workflow**:
1. User creates/loads config in Mandarake tab
2. Press Enter in keyword field → auto-saves config with new filename
3. Click "Search Mandarake" → runs scraper in background thread
4. Results saved to CSV, displayed in Results treeview
5. Optional: Schedule daily runs or upload to Google Sheets

**eBay Comparison Workflow**:
1. Load Mandarake CSV in eBay Search & CSV tab
2. Select items, click "Compare Selected" or "Compare All"
3. System searches eBay sold listings matching keyword + category
4. Downloads images, compares with OpenCV (similarity %)
5. Calculates profit margin based on USD/JPY rate
6. Results displayed with filters (min similarity %, min profit %)
7. Click "→ Send to Alerts" to send high-value items to Review/Alerts tab

**Alert/Review Workflow**:
1. Set thresholds (default: 70% similarity, 20% profit)
2. Items meeting thresholds auto-added as "Pending"
3. Review items → Mark "Yay" or "Nay"
4. Select Yays → Bulk "Purchase"
5. Track through workflow: Shipped → Received → Posted → Sold
6. All state changes persisted to `alerts.json`

## Important Implementation Details

### GUI State Management
- **Config tree auto-reloads** when saving via Enter key in keyword field
- **CSV filtering** preserves original data in `self.csv_compare_data`, displays filtered view
- **Thumbnail loading** happens in background threads to avoid UI blocking
- **RANSAC toggle** in CSV comparison area controls geometric verification (slower, more accurate)

### Image Comparison Settings
Located in CSV comparison button row:
- **2nd keyword toggle** - Adds secondary keyword extracted from title
- **RANSAC toggle** - Enables geometric verification (adds ~40% processing time)
- Images saved to `debug_comparison/query_timestamp/` for inspection

### Publisher List Management
Right-click keyword field → "Add Selected Text to Publisher List"
- Publishers stored in `user_settings.json` under `publisher_list`
- Used to extract secondary keywords by removing publisher names from titles

### Thread Safety
- All scraping/comparison operations run in background threads via `gui/workers.py`
- UI updates use `self.after()` to ensure thread-safe tkinter operations
- Progress bars and status updates communicate via queues

### Settings Persistence
- **Global settings**: `user_settings.json` (window size, recent files, publisher list)
- **Alert data**: `alerts.json` (workflow state, timestamps)
- **Config order**: `configs/.config_order.json` (drag-to-reorder persistence)

## Code Style and Patterns

### When Adding GUI Features
1. **Create separate module in `gui/`** - Don't add to monolithic `gui_config.py`
2. **Use worker functions** - Add to `gui/workers.py` for background operations
3. **Import and integrate** - Add minimal integration code to `gui_config.py`
4. Example: Alert tab is 4 separate files in `gui/`, only 10 lines of integration in main GUI

### State Management Pattern
```python
# DON'T store filtered data - always filter from source
self.all_comparison_results = results  # Original data
self.apply_results_filter()  # Filter and display

# DO use threading for long operations
worker = threading.Thread(target=workers.run_scraper_worker, args=(...))
worker.daemon = True
worker.start()
```

### Config Auto-save Pattern
All field changes trigger `self._auto_save_config()` via trace callbacks:
```python
self.keyword_var.trace_add("write", self._auto_save_config)
```

## Known Issues and Workarounds

**Mandarake 403 Errors**: Anti-bot protection may block requests. Use browser mimic mode (`use_mimic=True`) or reduce request rate.

**eBay Access Blocked**: eBay blocks automated browsing. Wait 2-5 minutes between searches. Scrapy-based search is more reliable than Playwright.

**Japanese Text Encoding**: Config filenames use MD5 hash for non-ASCII characters. Original keyword stored in JSON.

**Malformed Configs**: `_load_config_tree()` skips configs that aren't dictionaries (line 2316).

**Image Comparison Accuracy**: Template matching works best for exact matches. RANSAC helps with perspective changes. Watermarks can reduce accuracy.

## Testing

Run individual test files to verify components:
- `test_alert_tab.py` - Alert workflow state machine
- `test_image_comparison.py` - OpenCV comparison algorithms
- `test_scrapy_ebay.py` - eBay Scrapy spider
- `test_comparison_configs.py` - Config-based CSV comparison

## References

- `MANDARAKE_CODES.md` - Complete store and category code mappings
- `ALERT_TAB_COMPLETE.md` - Alert system documentation
- `EBAY_IMAGE_COMPARISON_GUIDE.md` - Image matching algorithms
- `README.md` - User-facing setup and usage guide
