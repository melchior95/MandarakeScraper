# Archive Directory

This directory contains deprecated, experimental, and orphaned files that are no longer used by the main application but are preserved for reference.

**Archived**: October 4, 2025

---

## Archived Files

### Old GUI Versions
- **`gui_config_refactored.py`** - Old refactored version of GUI
  - **Reason**: Superseded by current `gui_config.py` (1473 lines, fully modularized)
  - **Last Modified**: Before October 2025
  - **Status**: Deprecated

### Old Scraper Variants
- **`enhanced_mandarake_scraper.py`** - Enhanced scraper with browser mimicking
  - **Reason**: Functionality integrated into main `mandarake_scraper.py` and `browser_mimic.py`
  - **Status**: Deprecated

- **`enhanced_scraper.py`** - Another enhanced scraper variant
  - **Reason**: Superseded by main scraper
  - **Status**: Deprecated

### Experimental Tools
- **`auction_scraper.py`** - Generic auction scraper
  - **Reason**: Not integrated into main application, never imported
  - **Status**: Experimental

- **`google_lens_search.py`** - Google Lens integration
  - **Reason**: Not integrated, functionality may be replaced by eBay image search
  - **Status**: Experimental

- **`result_limiter.py`** - Result limiting utility
  - **Reason**: Not used by main application
  - **Status**: Orphaned

### Example Scripts
- **`example_strategic_search_usage.py`** - Example usage script
  - **Reason**: Example/demo file, not part of production code
  - **Status**: Example

---

## Yahoo Auction Files (`yahoo_auction/`)

All Yahoo Auction related files have been moved to `yahoo_auction/` subdirectory.

### Files:
1. **`yahoo_auction_browser.py`** - Yahoo Auction browser integration
2. **`yahoo_auction_json_viewer.py`** - JSON viewer for Yahoo data
3. **`yahoo_auction_render.py`** - Render Yahoo auction pages
4. **`yahoo_auction_viewer.py`** - View Yahoo auction listings
5. **`yahoo_category_scraper.py`** - Scrape Yahoo categories

### Status
- **Never imported** by main application
- **Not mentioned** in core documentation
- **Experimental** - Yahoo Auction integration was explored but not completed
- **Preserved** for potential future use

---

## Why Archived?

These files were archived because:
1. ✅ **Not imported** by any active code
2. ✅ **Superseded** by current implementations
3. ✅ **Experimental/incomplete** features
4. ✅ **Cluttering** root directory (38 files → reduced to ~26 active files)

## Can I Delete These?

**No, not recommended.**

These files are preserved for:
- Historical reference
- Code examples
- Potential future features
- Understanding project evolution

If you need to recover functionality from these files, they are safely preserved here.

---

## Related Cleanup

See also:
- **`ROOT_PY_FILES_AUDIT.md`** - Complete audit of root directory files
- **`DOCUMENTATION_CLEANUP_SUMMARY.md`** - Documentation consolidation
- **`GUI_MODULARIZATION_COMPLETE.md`** - GUI refactoring documentation

---

**Archived by**: Claude Code
**Date**: October 4, 2025
**Reason**: Root directory cleanup and organization
