# GUI Refactoring Plan

## Overview
Split the 5012-line `gui_config.py` monolith into maintainable modules.

## Completed Modules

### 1. `gui/constants.py` ✅
- Store options, category options, recent time filters
- Category keywords for eBay searches
- Global configuration constants
- **Lines extracted:** ~70 from original file

### 2. `gui/utils.py` ✅
- `slugify()` - Convert strings to filesystem-safe slugs
- `fetch_exchange_rate()` - Get USD/JPY rate
- `extract_price()` - Parse price from text
- `compare_images()` - SSIM + histogram similarity
- `create_debug_folder()` - Create debug directories
- `suggest_config_filename()` - Generate config filenames
- `generate_csv_filename()` - Generate CSV filenames
- `find_matching_csv()` - Find existing CSV files
- `clean_ebay_url()` - Clean eBay URLs
- `extract_code()` - Extract category codes
- `match_main_code()` - Match main category
- **Lines extracted:** ~300 from original file

### 3. `gui/workers.py` ✅
All background thread workers extracted:
- `run_scraper_worker` - Main scraper execution
- `schedule_worker` - Scheduled runs
- `run_image_analysis_worker` - eBay/Google Lens image search
- `run_ai_smart_search_worker` - AI-powered search
- `run_ebay_image_comparison_worker` - Computer vision matching
- `download_missing_images_worker` - Image downloads
- `run_scrapy_text_search_worker` - Scrapy text search
- `run_scrapy_search_with_compare_worker` - Scrapy with image comparison
- `run_cached_compare_worker` - Use cached results
- `load_csv_thumbnails_worker` - Load thumbnails
- `compare_csv_items_worker` - Batch CSV comparison
- `compare_csv_items_individually_worker` - Individual CSV comparison
- **Lines extracted:** ~1400 from original file

## Recommended Next Steps

### Phase 1: Immediate Wins (High Priority)
These modules are ready to use immediately:

1. **Update gui_config.py imports**
   ```python
   from gui.constants import *
   from gui.utils import *
   from gui import workers
   ```

2. **Replace method calls with util functions**
   - `self._slugify()` → `utils.slugify()`
   - `self._fetch_exchange_rate()` → `utils.fetch_exchange_rate()`
   - `self._extract_price()` → `utils.extract_price()`
   - `self._compare_images()` → `utils.compare_images()`
   - etc.

3. **Replace worker methods with function calls**
   - `self._run_scraper()` → `workers.run_scraper_worker()`
   - Pass necessary parameters explicitly
   - Use callbacks for UI updates

### Phase 2: Further Modularization (Medium Priority)

#### 4. `gui/config_manager.py`
Extract config operations:
- `load_config()`, `save_config()`, `_collect_config()`
- `_load_config_tree()`, `_update_tree_item()`
- `_delete_selected_config()`, `_move_config()`
- Config tree context menu operations
- **Lines to extract:** ~700

#### 5. `gui/ebay_search.py`
Extract eBay search functionality:
- `_search_ebay_sold()`, `_display_ebay_results()`
- `_ai_select_best_result()`, `_convert_ai_results_to_analysis()`
- `select_browserless_image()`, `run_scrapy_text_search()`
- **Lines to extract:** ~600

#### 6. `gui/csv_handler.py`
Extract CSV operations:
- `load_csv_file()`, `load_csv_for_comparison()`
- `filter_csv_items()`, `_display_csv_comparison_results()`
- `_delete_csv_items()`, `_save_updated_csv()`
- CSV tree context menu operations
- **Lines to extract:** ~500

### Phase 3: UI Separation (Lower Priority)

#### 7. `gui/tabs/search_tab.py`
- Build search tab UI
- Event handlers for search tab

#### 8. `gui/tabs/csv_tab.py`
- Build CSV comparison tab UI
- Event handlers for CSV tab

#### 9. `gui/tabs/advanced_tab.py`
- Build advanced settings tab UI
- Event handlers for advanced tab

## Current Status

### Extracted
- ✅ Constants and configuration data
- ✅ Utility functions
- ✅ Worker thread functions

### Remaining in gui_config.py
- Main ScraperGUI class (~3200 lines)
- UI construction and layout
- Event handlers
- Config management
- eBay search integration
- CSV comparison logic
- Settings management

## Migration Strategy

### Option A: Incremental Replacement (Recommended)
1. Keep `gui_config.py` as main file
2. Import and use new modules
3. Gradually remove duplicated code
4. Test after each change

### Option B: Complete Rewrite
1. Create new `gui_main.py` with minimal core
2. Mix in functionality from modules
3. Replace `gui_config.py` entirely
4. High risk but cleaner result

## Benefits Achieved So Far

1. **Reduced Complexity**: ~1770 lines extracted (35% reduction)
2. **Improved Testability**: Utility functions can be unit tested
3. **Better Reusability**: Workers can be used outside GUI
4. **Clearer Dependencies**: Imports show what's needed where
5. **Easier Maintenance**: Smaller files are easier to understand

## File Structure

```
gui/
├── __init__.py          # Package initialization
├── constants.py         # Global constants (70 lines) ✅
├── utils.py             # Utility functions (300 lines) ✅
├── workers.py           # Background workers (1400 lines) ✅
├── config_manager.py    # Config operations (700 lines) 🔄
├── ebay_search.py       # eBay integration (600 lines) 🔄
├── csv_handler.py       # CSV operations (500 lines) 🔄
└── tabs/
    ├── search_tab.py    # Search UI (300 lines) 📋
    ├── csv_tab.py       # CSV UI (300 lines) 📋
    └── advanced_tab.py  # Advanced UI (200 lines) 📋
```

Legend:
- ✅ Complete
- 🔄 Planned
- 📋 Future

## Testing Checklist

Before deploying refactored code:
- [ ] Import all modules successfully
- [ ] GUI launches without errors
- [ ] Search functionality works
- [ ] Config save/load works
- [ ] eBay search works
- [ ] CSV comparison works
- [ ] Image analysis works
- [ ] Workers complete successfully
- [ ] No performance regression
- [ ] No memory leaks from threading

## Notes

- Keep backward compatibility during migration
- Test thoroughly after each extraction
- Document breaking changes
- Consider creating `gui_config_legacy.py` backup
