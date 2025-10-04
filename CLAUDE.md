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

**GUI Application (`gui_config.py`)** - **MODULARIZED ARCHITECTURE**
- **1473 lines** (down from 4000+, 63% reduction)
- Main application orchestrator - delegates to modules
- Initializes managers and tabs
- Handles queue polling and thread management
- **IMPORTANT**: Minimal business logic (delegated to modules in `gui/`)

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

**⚠️ CRITICAL: The GUI is now fully modularized. DO NOT add functions to `gui_config.py` that belong in modules.**

#### Tab Modules (UI Components)
- **`gui/mandarake_tab.py`** - Mandarake store/category/config UI, results display
- **`gui/ebay_tab.py`** - eBay search interface, CSV comparison view
- **`gui/advanced_tab.py`** - Advanced settings, marketplace toggles
- **`gui/alert_tab.py`** - Review/Alerts workflow UI

#### Manager Classes (Business Logic)
- **`gui/configuration_manager.py`** - Config creation, loading, population
- **`gui/tree_manager.py`** - Treeview operations, drag-to-reorder
- **`gui/config_tree_manager.py`** - Config tree specific operations
- **`gui/window_manager.py`** - Window geometry, paned positions
- **`gui/menu_manager.py`** - Menu bar, recent files, dialogs
- **`gui/ebay_search_manager.py`** - eBay search, image comparison
- **`gui/csv_comparison_manager.py`** - CSV loading, filtering, comparison
- **`gui/alert_manager.py`** - Alert business logic, threshold filtering
- **`gui/surugaya_manager.py`** - Suruga-ya scraping operations
- **`gui/schedule_executor.py`** - Background scheduling thread

#### Support Modules
- **`gui/workers.py`** - Background thread workers for scraping, image analysis, CSV comparison
- **`gui/utils.py`** - Utility functions (slugify, image comparison, exchange rates, etc.)
- **`gui/constants.py`** - Shared constants (store/category mappings, keywords)
- **`gui/alert_storage.py`** - Alert persistence (JSON)
- **`gui/alert_states.py`** - State machine definitions
- **`gui/ui_helpers.py`** - Dialog helpers, help screens
- **`gui/schedule_frame.py`** - Schedule UI component

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
- Publishers stored in `publishers.txt`
- Used to extract secondary keywords by removing publisher names from titles

### Thread Safety
- All scraping/comparison operations run in background threads via `gui/workers.py`
- UI updates use `self.after()` to ensure thread-safe tkinter operations
- Progress bars and status updates communicate via queues

### Settings Persistence
- **Global settings**: `user_settings.json` (window size, recent files, etc.)
- **Alert data**: `alerts.json` (workflow state, timestamps)
- **Config order**: `configs/.config_order.json` (drag-to-reorder persistence)

## Code Style and Patterns

### 🚨 CRITICAL: Modularization Rules

#### 1. **NEVER add functions to `gui_config.py` that belong in modules**
```python
# ❌ BAD - Adding business logic to gui_config.py
def search_ebay(self, query):
    # Search logic here...
    pass

# ✅ GOOD - Create/use a manager module
# In gui/ebay_search_manager.py
class EbaySearchManager:
    def search_ebay(self, query):
        # Search logic here...
        pass

# In gui_config.py - just delegate
def search_ebay(self, query):
    if self.ebay_tab.ebay_search_manager:
        return self.ebay_tab.ebay_search_manager.search_ebay(query)
```

#### 2. **When to Create a New Module**
Create a new module in `gui/` when:
- Adding a new feature with multiple methods
- Logic spans 50+ lines
- Functionality is self-contained
- Multiple files would benefit from the functionality

#### 3. **Module Responsibilities**
- **`gui_config.py`**: Orchestration, initialization, queue polling, thread management
- **Tab modules (`*_tab.py`)**: UI layout, widget creation, event binding
- **Manager modules (`*_manager.py`)**: Business logic, data processing, API calls
- **`gui/workers.py`**: Background thread operations
- **`gui/utils.py`**: Pure utility functions (no UI, no state)

### When Adding GUI Features

**Step 1: Choose the right location**
```python
# Is it UI layout? → *_tab.py
# Is it business logic? → *_manager.py
# Is it a background operation? → workers.py
# Is it a pure utility function? → utils.py
# Is it a constant? → constants.py
```

**Step 2: Create/update the appropriate module**
```python
# Example: Adding eBay search feature
# 1. Create logic in gui/ebay_search_manager.py
# 2. Create UI in gui/ebay_tab.py
# 3. Add worker if needed in gui/workers.py
# 4. Import and integrate in gui_config.py (minimal code)
```

**Step 3: Integration in `gui_config.py`**
```python
# Initialize manager in __init__
self.ebay_manager = EbaySearchManager(...)

# Delegate in methods (if needed)
def some_action(self):
    return self.ebay_manager.perform_action()
```

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

### Best Practices from Refactoring

1. **Thread Safety**: Always use `self.after()` for UI updates from threads
2. **Queue Communication**: Workers use `run_queue.put()` for status updates
3. **Manager Delegation**: `gui_config.py` delegates to managers, never implements inline
4. **State Flags**: Use `_loading_config`, `_settings_loaded` to prevent recursive updates
5. **Separation of Concerns**: UI in tabs, logic in managers, background ops in workers

### File Size Guidelines
- **Target**: ≤500 lines per file (sweet spot for AI + human readability)
- **Utility modules**: ≤200 lines
- **Tab/Manager modules**: ≤800 lines (split if larger)
- **`gui_config.py`**: Keep minimal, delegate everything

## Documentation Standards

### 📝 CRITICAL: Update Documentation When Creating New Files

**When you create a new `.md` documentation file**, you MUST update `PROJECT_DOCUMENTATION_INDEX.md`:

1. **Add the file to the appropriate section**:
   - Essential Documentation
   - Architecture & Implementation
   - Feature Documentation
   - API & Integration
   - etc.

2. **Include a brief description** of what the document contains

3. **Update the file count** at the bottom of the index

4. **Link to related documentation** if applicable

**Example**:
```markdown
### Feature Documentation
- **[NEW_FEATURE.md](NEW_FEATURE.md)** - Description of new feature
  - Implementation details
  - Usage examples
  - Related modules
```

### Documentation File Naming
- `FEATURE_COMPLETE.md` - Feature documentation
- `COMPONENT_COMPLETE.md` - Component documentation
- `*_GUIDE.md` - User guides and tutorials
- `*_PLAN.md` - Planning documents (archive when complete)

### Documentation Standards
Each markdown file should include:
- Clear title and overview
- Implementation details (for technical docs)
- Usage examples (for guides)
- Testing results (if applicable)
- Related documentation links

## Known Issues and Workarounds

**Mandarake 403 Errors**: Anti-bot protection may block requests. Use browser mimic mode (`use_mimic=True`) or reduce request rate.

**eBay Access Blocked**: eBay blocks automated browsing. Wait 2-5 minutes between searches. Scrapy-based search is more reliable than Playwright.

**Japanese Text Encoding**: Config filenames use MD5 hash for non-ASCII characters. Original keyword stored in JSON.

**Image Comparison Accuracy**: Template matching works best for exact matches. RANSAC helps with perspective changes. Watermarks can reduce accuracy.

## Testing

Run individual test files to verify components:
- `test_alert_tab.py` - Alert workflow state machine
- `test_image_comparison.py` - OpenCV comparison algorithms
- `test_scrapy_ebay.py` - eBay Scrapy spider
- `test_comparison_configs.py` - Config-based CSV comparison

## References

### Core Documentation
- `GUI_MODULARIZATION_COMPLETE.md` - **Complete modularization documentation**
- `PROJECT_DOCUMENTATION_INDEX.md` - **Comprehensive documentation index**
- `MANDARAKE_CODES.md` - Complete store and category code mappings
- `ALERT_TAB_COMPLETE.md` - Alert system documentation
- `EBAY_IMAGE_COMPARISON_GUIDE.md` - Image matching algorithms
- `README.md` - User-facing setup and usage guide

### Quick Reference
See `PROJECT_DOCUMENTATION_INDEX.md` for a complete list of all documentation files organized by category.

---

**Last Updated**: October 4, 2025
**Architecture Status**: ✅ Fully Modularized (20+ modules, 63% code reduction)
**Documentation Status**: ✅ Consolidated and Current
