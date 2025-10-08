# Image Comparison Architecture

## Overview

The Mandarake Scraper uses **2 distinct image comparison systems** for different purposes. This document clarifies which code is active and when each system is used.

---

## Active Image Comparison Implementations

### 1. **CSV Batch Comparison** (`gui/workers.py`)

**Location**: `gui/workers.py::compare_images()` (lines 51-200+)

**Algorithm**:
- **ORB Feature Matching** - 50% weight (most robust to crops/additions)
- **SSIM (Structural Similarity)** - 25% weight
- **Color Histogram** - 15% weight
- **Template Matching** - 10% weight
- **Optional RANSAC** - Geometric verification for higher accuracy (slower)

**When Used**:
- When comparing Mandarake CSV items with eBay sold listings
- Triggered by: "Compare Selected" or "Compare All" buttons in eBay tab
- Processes multiple items in batch

**Key Features**:
- Multi-threaded batch processing
- Configurable RANSAC toggle
- Debug image output to `debug_comparison/`
- Profit margin calculation with USD/JPY exchange rate

**Code Path**:
```
eBay Tab → Compare Button
  ↓
csv_comparison_manager.py::_compare_csv_items_worker()
  ↓
gui/workers.py::compare_csv_items_worker()
  ↓
gui/workers.py::compare_images()  ← ACTUAL COMPARISON
```

---

### 2. **eBay Image Search** (`sold_listing_matcher*.py`)

**Two Implementations** (same algorithm, different transport):

#### A. **Requests-Based (Headless)** - `sold_listing_matcher_requests.py`

**Location**: `sold_listing_matcher_requests.py::_compare_images_with_listings()` (lines 627-740)

**Algorithm**:
- **ORB Feature Matching** - 40% weight
- **Color Histogram** - 30% weight
- **Structure (Template)** - 20% weight
- **Edge Detection** - 10% weight

**When Used**:
- Right-click CSV item → "Search by Image on eBay (API)"
- Faster, headless operation using requests library
- **Default method** for image-based eBay searches

#### B. **Playwright-Based (Visible Browser)** - `sold_listing_matcher.py`

**Location**: `sold_listing_matcher.py::_compare_images_with_listings()` (lines 806-900+)

**Algorithm**: *Identical to requests-based version*

**When Used**:
- Right-click CSV item → "Search by Image on eBay (Web)"
- Opens visible browser window
- Useful for debugging/visual confirmation
- Slower but more transparent

**Code Path**:
```
CSV Context Menu → "Search by Image"
  ↓
gui/workers.py::run_ebay_image_search_worker()
  ↓
IF show_browser:
    sold_listing_matcher.py (Playwright) ← COMPARISON HERE
ELSE:
    sold_listing_matcher_requests.py (Requests) ← COMPARISON HERE
```

---

## Algorithm Comparison

| Feature | CSV Batch Comparison | eBay Image Search |
|---------|---------------------|-------------------|
| **ORB Weight** | 50% | 40% |
| **SSIM** | ✅ 25% | ❌ Not used |
| **Color Histogram** | 15% | 30% |
| **Template Matching** | 10% | 20% (called "Structure") |
| **Edge Detection** | ❌ Not used | ✅ 10% |
| **RANSAC** | ✅ Optional | ❌ Not available |
| **Image Size** | 400x400px | 300x300px |
| **Debug Output** | ✅ Full comparison images | ✅ Downloaded listing images |

---

## Configuration

### CSV Batch Comparison Settings

**Location**: eBay Tab → CSV Comparison section

1. **RANSAC Toggle** - Enable geometric verification (slower, more accurate)
2. **2nd Keyword Toggle** - Add secondary keyword from publisher extraction
3. **Alert Threshold** - Auto-send items meeting similarity/profit thresholds
   - Min Similarity % (default: 70%)
   - Min Profit % (default: 20%)
   - Active checkbox to enable/disable auto-alerting

**Settings Persistence**: `user_settings.json`

### eBay Image Search Settings

**Location**: Right-click context menu on CSV items

- Method selection happens at runtime (API vs Web)
- No user-configurable thresholds
- Uses fixed similarity threshold from matcher initialization

---

## Debug Output

### CSV Batch Comparison
**Directory**: `debug_comparison/query_timestamp/`

**Files Generated**:
- `query_image.jpg` - Original Mandarake image
- `match_N_sim_XX.jpg` - Each eBay match with similarity score
- Side-by-side comparison with feature matching visualization (if RANSAC enabled)

### eBay Image Search
**Directory**: `debug_comparison/search_term/`

**Files Generated**:
- `query_image.jpg` - Original search image
- `listing_N.jpg` - Each scraped eBay listing image
- Console output with similarity scores for each listing

---

## Removed Dead Code (2025-01-04)

The following functions were **removed** as they were never called:

1. ❌ `gui/utils.py::compare_images()` - Simple SSIM (70%) + Histogram (30%)
2. ❌ `gui_config.py::_compare_images()` - Wrapper for above
3. ❌ Unused imports: `cv2`, `ssim` from `gui/utils.py`

These were replaced by the more robust multi-metric implementations in `gui/workers.py`.

---

## Auto-Alert System Integration

When **Alert Threshold → Active** is checked in the eBay tab:

1. **CSV Comparison** completes
2. Results filtered by thresholds:
   - `similarity >= alert_min_similarity` (default: 70%)
   - `profit_margin >= alert_min_profit` (default: 20%)
3. Filtered items **automatically sent** to Alert tab as "Pending"
4. User sees messagebox with count of created alerts

**Implementation**: `gui_config.py::_send_to_alerts_with_thresholds()` (lines 1378-1406)

**Trigger Points**:
- `csv_comparison_manager.py` lines 515-520 (batch comparison)
- `csv_comparison_manager.py` lines 574-579 (individual comparison)

---

## Performance Notes

### CSV Batch Comparison
- **Speed**: ~2-5 seconds per item comparison
- **Parallelization**: Processes items sequentially (thread-safe UI updates)
- **RANSAC Impact**: Adds ~40% processing time when enabled
- **Memory**: Moderate (loads all CSV images into memory)

### eBay Image Search
- **Requests (Headless)**: ~30-60 seconds for 20 listings
- **Playwright (Browser)**: ~45-90 seconds for 20 listings
- **Bottleneck**: eBay scraping, not image comparison
- **eBay Rate Limiting**: Wait 2-5 minutes between searches to avoid blocks

---

## Testing

### Test CSV Batch Comparison
```bash
python test_comparison_configs.py
```

### Test eBay Image Search
```bash
# Requests-based (headless)
python sold_listing_matcher_requests.py images/test.jpg "yura kano photobook"

# Playwright-based (visible browser)
python sold_listing_matcher.py images/test.jpg "yura kano photobook"
```

---

## Future Improvements

### Possible Consolidation
- **Option 1**: Use same algorithm for both systems (standardize on ORB weights)
- **Option 2**: Make algorithm configurable (user-selectable weights)
- **Option 3**: Add RANSAC support to eBay Image Search

### Enhancement Opportunities
- Persist RANSAC preference in settings
- Add similarity threshold slider for eBay Image Search
- Parallel image comparison for batch processing
- GPU acceleration for large batches (OpenCV CUDA)

---

**Last Updated**: 2025-01-04
**Related Documentation**:
- `EBAY_IMAGE_COMPARISON_GUIDE.md` - User-facing comparison guide
- `SOLD_LISTING_MATCHER.md` - eBay image search implementation details
- `GUI_MODULARIZATION_COMPLETE.md` - GUI architecture overview
