# Root Directory Python Files Audit

## Overview
Audit of all .py files in root directory to identify duplicates, orphaned files, and cleanup opportunities.

**Date**: October 4, 2025
**Total Files**: 38 Python files in root

---

## File Status

### ✅ ACTIVE - Core Application Files (9 files)

#### Essential
1. **`gui_config.py`** (66KB, 1473 lines) - Main GUI application
2. **`mandarake_scraper.py`** (93KB) - Core scraper
3. **`browser_mimic.py`** (25KB) - Anti-bot browser mimicking
4. **`settings_manager.py`** (18KB) - User settings persistence
5. **`mandarake_codes.py`** (28KB) - Store/category codes (imported by main files)

#### Integration/Support
6. **`ebay_scrapy_search.py`** (3.5KB) - eBay scrapy search (imported by gui/workers.py)
7. **`surugaya_codes.py`** (4KB) - Suruga-ya codes (imported by gui modules)
8. **`scrapy_runner.py`** (5KB) - Scrapy execution helper
9. **`ebay_listing_creator.py`** (11KB) - eBay listing creation

---

## ⚠️ POTENTIALLY ORPHANED - Need Review (29 files)

### Duplicate/Old Versions (3 files)
1. **`gui_config_refactored.py`** (11KB) - **LIKELY ORPHANED**
   - Old refactored version of GUI
   - NOT imported anywhere
   - Superseded by current `gui_config.py`
   - **Recommendation**: Archive or delete

2. **`enhanced_mandarake_scraper.py`** (14KB) - **LIKELY ORPHANED**
   - Enhanced scraper variant
   - Only mentioned in README.md
   - Superseded by main `mandarake_scraper.py`
   - **Recommendation**: Archive or delete

3. **`enhanced_scraper.py`** (13KB) - **LIKELY ORPHANED**
   - Another enhanced scraper variant
   - NOT imported by main application
   - **Recommendation**: Archive or delete

### eBay-Related Tools (7 files)
4. **`ebay_api_search.py`** (9KB) - eBay API search
5. **`ebay_deletion_endpoint.py`** (7KB) - eBay deletion endpoint
6. **`ebay_endpoint_config.py`** (7KB) - eBay endpoint configuration
7. **`ebay_image_search.py`** (21KB) - eBay image search
8. **`browserless_ebay_search.py`** (13KB) - Browserless eBay search
9. **`sold_listing_matcher.py`** (65KB) - Playwright-based sold listing matcher
10. **`sold_listing_matcher_requests.py`** (36KB) - Requests-based sold listing matcher

**Status**: Used by documentation but NOT imported by GUI
**Recommendation**:
- Check if functionality is integrated into gui/ebay_search_manager.py
- If duplicated, archive these standalone versions
- If unique, create a tools/ directory

### Category/Search Optimization Tools (6 files)
11. **`category_keyword_manager.py`** (13KB) - Category keyword management
12. **`category_optimizer.py`** (24KB) - Category optimization research
13. **`search_optimizer.py`** (27KB) - Search optimization
14. **`image_analysis_engine.py`** (19KB) - Image analysis
15. **`image_processor.py`** (18KB) - Image processing
16. **`price_validation_service.py`** (14KB) - Price validation

**Status**: Standalone CLI tools
- `category_optimizer.py` and `category_keyword_manager.py` imported by `search_optimizer.py`
- `search_optimizer.py` used by gui/advanced_tools.py
**Recommendation**:
- Move to `tools/` directory if not integrated into GUI
- OR integrate into gui/utils.py if functionality is needed

### Yahoo Auction Files (5 files) - **LIKELY ORPHANED**
17. **`yahoo_auction_browser.py`** (18KB)
18. **`yahoo_auction_json_viewer.py`** (5KB)
19. **`yahoo_auction_render.py`** (9KB)
20. **`yahoo_auction_viewer.py`** (3KB)
21. **`yahoo_category_scraper.py`** (11KB)

**Status**: NOT imported anywhere, NOT mentioned in main docs
**Recommendation**: Move to `archive/` or `experimental/`

### Other Standalone Tools (8 files)
22. **`auction_scraper.py`** (8KB) - Generic auction scraper
23. **`google_lens_search.py`** (19KB) - Google Lens integration
24. **`lookup_codes.py`** (5KB) - Code lookup utility
25. **`result_limiter.py`** (12KB) - Result limiting
26. **`scrape_surugaya_categories.py`** (1KB) - Suruga-ya category scraper
27. **`fix_configs.py`** (5KB) - Config fixing utility
28. **`example_strategic_search_usage.py`** (3KB) - Example script
29. **`analyze_all_comparisons.py`** (4KB) - Comparison analysis tool

**Status**: Utility scripts, not integrated
**Recommendation**: Move to `tools/` or `scripts/` directory

---

## 🔍 Code Duplication Issues

### Issue 1: Duplicate Code Files in Two Locations
**Problem**: Both root and `store_codes/` have the same files

| File | Root Location | store_codes/ Location | Used By |
|------|--------------|---------------------|---------|
| `mandarake_codes.py` | ✅ 28KB | ✅ 28KB | Main files use root, gui uses store_codes |
| `surugaya_codes.py` | ✅ 4KB | ✅ 7KB | gui uses store_codes version |

**Impact**: Confusing imports, potential version mismatch
**Recommendation**:
- Consolidate to `store_codes/` directory
- Update imports in main files to use `from store_codes.mandarake_codes import ...`
- Delete root versions

---

## 📊 File Usage Analysis

### Import Chain Analysis
```
gui_config.py
├── imports mandarake_codes.py (ROOT)
├── imports mandarake_scraper.py
├── imports settings_manager.py
├── imports browser_mimic.py
└── imports gui/* (which import from store_codes/*)

gui/workers.py
├── imports ebay_scrapy_search.py
└── imports from store_codes/*

gui/surugaya_manager.py
└── imports from store_codes.surugaya_codes
```

### Files Never Imported
- gui_config_refactored.py
- enhanced_mandarake_scraper.py
- enhanced_scraper.py
- All Yahoo Auction files (5)
- auction_scraper.py
- google_lens_search.py
- Many eBay tools (may be CLI tools)
- Category optimizer tools (may be CLI tools)

---

## 🗂️ Recommended Directory Structure

```
mandarake_scraper/
├── gui_config.py                # Main GUI
├── mandarake_scraper.py         # Core scraper
├── browser_mimic.py             # Core support
├── settings_manager.py          # Core support
├── ebay_scrapy_search.py        # Core integration
├── scrapy_runner.py             # Core integration
│
├── store_codes/                 # Store/category codes (keep)
│   ├── mandarake_codes.py
│   └── surugaya_codes.py
│
├── gui/                         # GUI modules (keep)
│   └── ... (20+ modules)
│
├── tools/                       # CLI utilities (NEW)
│   ├── category_optimizer.py
│   ├── category_keyword_manager.py
│   ├── search_optimizer.py
│   ├── image_analysis_engine.py
│   ├── image_processor.py
│   ├── price_validation_service.py
│   ├── lookup_codes.py
│   ├── fix_configs.py
│   ├── analyze_all_comparisons.py
│   └── scrape_surugaya_categories.py
│
├── ebay_tools/                  # eBay standalone tools (NEW)
│   ├── ebay_api_search.py
│   ├── ebay_image_search.py
│   ├── sold_listing_matcher.py
│   ├── sold_listing_matcher_requests.py
│   ├── ebay_deletion_endpoint.py
│   ├── ebay_endpoint_config.py
│   └── browserless_ebay_search.py
│
└── archive/                     # Deprecated/experimental (NEW)
    ├── gui_config_refactored.py
    ├── enhanced_mandarake_scraper.py
    ├── enhanced_scraper.py
    ├── auction_scraper.py
    ├── google_lens_search.py
    ├── result_limiter.py
    ├── example_strategic_search_usage.py
    └── yahoo_auction/
        ├── yahoo_auction_browser.py
        ├── yahoo_auction_json_viewer.py
        ├── yahoo_auction_render.py
        ├── yahoo_auction_viewer.py
        └── yahoo_category_scraper.py
```

---

## ✅ Recommended Actions

### Phase 1: Consolidate Code Files (PRIORITY)
1. **Update imports** in `gui_config.py`, `mandarake_scraper.py` to use `store_codes/`
2. **Delete** root `mandarake_codes.py` and `surugaya_codes.py`
3. **Test** that everything still works

### Phase 2: Archive Orphaned Files
1. Create `archive/` directory
2. Move orphaned files:
   - `gui_config_refactored.py`
   - `enhanced_mandarake_scraper.py`
   - `enhanced_scraper.py`
   - `auction_scraper.py`
   - `google_lens_search.py`
   - `result_limiter.py`
   - `example_strategic_search_usage.py`

### Phase 3: Organize Standalone Tools
1. Create `tools/` directory for CLI utilities
2. Move category/search optimization tools
3. Create `ebay_tools/` for eBay standalone scripts
4. Create `archive/yahoo_auction/` for Yahoo files

### Phase 4: Update Documentation
1. Update `CLAUDE.md` with new directory structure
2. Update `PROJECT_DOCUMENTATION_INDEX.md`
3. Create `tools/README.md` explaining CLI tools

---

## 🎯 Quick Wins (Can Do Immediately)

### Safe to Archive (No Dependencies)
```bash
mkdir -p archive/yahoo_auction
mv gui_config_refactored.py archive/
mv enhanced_mandarake_scraper.py archive/
mv enhanced_scraper.py archive/
mv yahoo_auction_*.py archive/yahoo_auction/
mv yahoo_category_scraper.py archive/yahoo_auction/
mv example_strategic_search_usage.py archive/
```

### Safe to Organize (Standalone CLI tools)
```bash
mkdir -p tools
mv category_optimizer.py tools/
mv category_keyword_manager.py tools/
mv search_optimizer.py tools/
mv image_analysis_engine.py tools/
mv image_processor.py tools/
mv price_validation_service.py tools/
mv lookup_codes.py tools/
mv fix_configs.py tools/
mv analyze_all_comparisons.py tools/
mv scrape_surugaya_categories.py tools/
```

---

## 📝 Summary

- **Total Files**: 38 Python files
- **Active Core**: 9 files
- **Orphaned/Unused**: 29 files (~76%)
- **Duplicates**: 2 files (mandarake_codes.py, surugaya_codes.py)
- **Recommended to Archive**: 8 files
- **Recommended to Organize**: 21 files (tools/)

**Impact**: Cleanup will reduce root directory clutter by 76%, improve code organization, and prevent confusion from duplicate imports.

---

**Last Updated**: October 4, 2025
**Status**: Audit Complete - Awaiting Action
