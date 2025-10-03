# Suruga-ya Advanced Search Integration Plan

**Date:** October 3, 2025
**Status:** Research Complete - Ready for Implementation
**Source:** https://www.suruga-ya.jp/detailed_search?search_word=

---

## Research Summary

### Current Implementation
- Basic search with keyword and single-level category (200-series codes)
- Shop filter (tenpo_code)
- Basic in-stock filtering

### Advanced Search Form Fields Discovered

**Search Parameters:**
- `search_word` - Main keyword
- `exclude_word` - Keywords to exclude (NEW)
- `category1` - First-level category (NEW - using simple codes: 2, 3, 4, 5, etc.)
- `category2` - Second-level category (dynamic based on category1)
- `category3` - Third-level category (dynamic based on category2)
- `tenpo_code` - Shop/store filter
- `sale_classified` - Condition filter (NEW/USED)
- `inStock` - Stock availability filter
- `year1`, `month1`, `day1` - Release date FROM (NEW)
- `year2`, `month2`, `day2` - Release date TO (NEW)
- `jan10` / `gtin` - Product barcode (JAN code) (NEW)
- `id_s` - Product ID search (NEW)

---

## Category Structure (3 Levels)

### First-Level Categories (Extracted from HTML)

**KEEP - Import/Hobby Categories:**
- `2` - **ゲーム (Games)**
- `3` - **映像ソフト (Video Software)** - Anime, Movies, Dramas
- `4` - **音楽ソフト (Music Software)** - CDs, Anime Music
- `5` - **おもちゃホビー (Toys & Hobby)** - Figures, Models, Trading Cards
- `7` - **本 (Books)** - Books, Comics, Magazines, Photobooks
- `10` - **雑貨・小物 (Goods & Accessories)** - Keychains, Posters, Stationery
- `11` - **同人 (Doujinshi)** - Doujin works

**REMOVE - Non-Hobby/Practical Categories:**
- `6` - パソコン・スマホ (Computers & Smartphones) - Electronics
- `8` - 家電・カメラ・AV機器 (Home Appliances/Cameras) - Practical electronics
- `9` - 食品・食玩 (Food & Food Toys) - Perishable items
- `12` - 福袋 (Lucky Bags) - Random grab bags
- `13` - ギフト (Gifts) - Generic gift category
- `14` - 生き物・生体 (Living Creatures) - Animals/pets

---

## Proposed 2-Level Category System

Since Suruga-ya has 3 levels but we want 2, we'll **flatten Level 2 and Level 3** into a single "Detailed Category" dropdown.

### Strategy:
1. **Main Category** - User selects from 7 hobby categories (codes: 2, 3, 4, 5, 7, 10, 11)
2. **Detailed Category** - Combined Level 2 + Level 3 options
   - When user selects Main Category, populate detailed dropdown
   - Store as `category2:category3` or just use the most specific code

---

## Recommended Category Mappings (2-Level Structure)

### Level 1: Main Categories (Simplified)

```python
SURUGAYA_MAIN_CATEGORIES = {
    '2': 'Games',
    '3': 'Video Software (Anime/Movies)',
    '4': 'Music (CDs/Soundtracks)',
    '5': 'Toys & Hobby',
    '7': 'Books & Photobooks',
    '10': 'Goods & Accessories',
    '11': 'Doujinshi',
}
```

### Level 2: Detailed Categories (Combined L2+L3)

**Need to research subcategories** - These are dynamically loaded via JavaScript when Level 1 is selected.

**Next Step:** Scrape each category page to extract Level 2 and Level 3 options with their codes.

---

## Additional Search Options to Integrate

### 1. Exclude Keywords ✅ HIGH PRIORITY
**Field:** `exclude_word`
**Use Case:** Filter out unwanted items (e.g., search "Pokemon" exclude "plush")
**UI:** Add text entry field below keyword field

### 2. Condition Filter ✅ HIGH PRIORITY
**Field:** `sale_classified`
**Options:**
- All
- New only
- Used only
**UI:** Radio buttons or dropdown in options panel

### 3. Release Date Range ⚠️ MEDIUM PRIORITY
**Fields:** `year1`, `month1`, `day1`, `year2`, `month2`, `day2`
**Use Case:** Find items released in specific time period
**UI:** Date picker or year/month dropdowns

### 4. Product ID Search ⚠️ LOW PRIORITY
**Fields:** `id_s` (Suruga-ya product ID), `jan10`/`gtin` (JAN barcode)
**Use Case:** Direct product lookup
**UI:** Additional text field (advanced users only)

### 5. In-Stock Filter ✅ ALREADY IMPLEMENTED
**Field:** `inStock`
**Status:** Already in config as `show_out_of_stock`

---

## Implementation Plan

### Phase 1: Category System Overhaul ✅ CRITICAL

**1.1 Research Subcategories**
- Scrape each Level 1 category page to extract Level 2 + Level 3 mappings
- Example URLs:
  - Games: `https://www.suruga-ya.jp/search?category=2&search_word=`
  - Video: `https://www.suruga-ya.jp/search?category=3&search_word=`
  - Books: `https://www.suruga-ya.jp/search?category=7&search_word=`

**1.2 Create Category Code Mappings**
```python
# store_codes/surugaya_codes.py

# Level 1 (Main)
SURUGAYA_MAIN_CATEGORIES = {
    '2': 'Games',
    '3': 'Video Software',
    '4': 'Music',
    '5': 'Toys & Hobby',
    '7': 'Books & Photobooks',
    '10': 'Goods & Accessories',
    '11': 'Doujinshi',
}

# Level 2 (Detailed) - Organized by parent
SURUGAYA_DETAILED_CATEGORIES = {
    # Games (2)
    '2': {
        '200': 'All Games',
        '201': 'Nintendo Switch',
        '202': 'PlayStation 5',
        '203': 'PlayStation 4',
        # ... more subcategories
    },
    # Video (3)
    '3': {
        '300': 'All Video',
        '301': 'Anime DVD',
        '302': 'Anime Blu-ray',
        # ... more subcategories
    },
    # ... other categories
}
```

**1.3 Update GUI Category Loading**
- Modify `_on_main_category_selected` to filter detailed categories by parent
- Update `_populate_surugaya_categories()` to show only relevant subcategories

### Phase 2: Additional Search Options ✅ HIGH PRIORITY

**2.1 Exclude Keywords**
```python
# Add to GUI (after keyword field)
ttk.Label(options_pane, text="Exclude words:").grid(row=X, column=0, sticky=tk.W)
self.exclude_word_var = tk.StringVar()
ttk.Entry(options_pane, textvariable=self.exclude_word_var, width=42).grid(row=X, column=1)
```

**2.2 Condition Filter**
```python
# Add to store-specific options
self.condition_var = tk.StringVar(value='all')
ttk.Label(options_pane, text="Condition:").grid(...)
condition_combo = ttk.Combobox(
    options_pane,
    textvariable=self.condition_var,
    values=['All', 'New Only', 'Used Only'],
    state='readonly'
)
```

**2.3 Update Config Schema**
```json
{
  "store": "suruga-ya",
  "keyword": "Yura Kano",
  "exclude_word": "DVD",  // NEW
  "category1": "7",       // NEW: Main category
  "category2": "703",     // Detailed category
  "shop": "all",
  "condition": "all",     // NEW: all/new/used
  "release_date_from": "",  // NEW (optional)
  "release_date_to": "",    // NEW (optional)
  "max_pages": 5,
  "show_out_of_stock": false
}
```

### Phase 3: Scraper Updates ✅ MEDIUM PRIORITY

**3.1 Update `_build_search_url` in surugaya_scraper.py**
```python
def _build_search_url(self, keyword, category1, category2, shop_code, page, **kwargs):
    params = [
        f"search_word={quote(keyword)}",
        f"category1={category1}",   # NEW: Main category
        f"category2={category2}",   # Detailed category
        "searchbox=1"
    ]

    # Exclude words
    if kwargs.get('exclude_word'):
        params.append(f"exclude_word={quote(kwargs['exclude_word'])}")

    # Condition filter
    if kwargs.get('condition') and kwargs['condition'] != 'all':
        params.append(f"sale_classified={kwargs['condition']}")

    # Shop filter
    if shop_code and shop_code != 'all':
        params.append(f"tenpo_code={shop_code}")

    # Stock filter
    if not kwargs.get('show_out_of_stock'):
        params.append("inStock=1")

    # Pagination
    if page > 1:
        params.append(f"page={page}")

    return f"{self.base_url}/search?{'&'.join(params)}"
```

### Phase 4: GUI Integration ✅ MEDIUM PRIORITY

**4.1 Update `_on_store_changed` Method**
- Load new category structure when Suruga-ya selected
- Populate main category dropdown with 7 hobby categories
- Clear/reset exclude word and condition fields

**4.2 Update `_collect_config` Method**
- Add exclude_word field
- Add condition field
- Store category1 and category2 separately

**4.3 Update `_run_surugaya_scraper` Method**
- Pass new parameters to scraper
- Handle category1/category2 structure

---

## Category Research Tasks

### Required Research (Use Web Scraping)

For each main category, extract subcategories:

1. **Games (2)**
   - Visit: https://www.suruga-ya.jp/search?category=2
   - Extract Level 2 categories (Nintendo Switch, PlayStation, etc.)
   - Extract Level 3 categories (if any)

2. **Video Software (3)**
   - Visit: https://www.suruga-ya.jp/search?category=3
   - Extract Anime, Movies, Drama subcategories

3. **Music (4)**
   - Visit: https://www.suruga-ya.jp/search?category=4
   - Extract J-Pop, Anime Music, etc.

4. **Toys & Hobby (5)**
   - Visit: https://www.suruga-ya.jp/search?category=5
   - Extract Figures, Models, Trading Cards, etc.

5. **Books (7)**
   - Visit: https://www.suruga-ya.jp/search?category=7
   - Extract Books, Comics, Magazines, Photobooks

6. **Goods (10)**
   - Visit: https://www.suruga-ya.jp/search?category=10
   - Extract Keychains, Posters, Stickers, etc.

7. **Doujinshi (11)**
   - Visit: https://www.suruga-ya.jp/search?category=11
   - Extract Doujin Comics, Doujin Games, etc.

### Extraction Method

Use WebFetch or curl to get HTML, then parse:
- Look for category links in sidebar/navigation
- Extract codes from URLs (e.g., `/search?category=201` = Nintendo Switch)
- Map codes to Japanese and English names

---

## File Changes Required

### 1. `store_codes/surugaya_codes.py`
- ✅ Add SURUGAYA_MAIN_CATEGORIES (7 categories)
- ⏳ Add SURUGAYA_DETAILED_CATEGORIES (nested by parent)
- ⏳ Add condition filter constants
- ⏳ Update `build_surugaya_search_url()` with new parameters

### 2. `scrapers/surugaya_scraper.py`
- ⏳ Update `_build_search_url()` to accept category1, category2, exclude_word, condition
- ⏳ Update `search()` method signature

### 3. `gui_config.py`
- ⏳ Add exclude_word text field
- ⏳ Add condition dropdown
- ⏳ Update `_populate_surugaya_categories()` to use hierarchical structure
- ⏳ Update `_collect_config()` to include new fields
- ⏳ Update `_run_surugaya_scraper()` to pass new parameters

---

## Testing Checklist

- [ ] Load Suruga-ya categories in GUI dropdown
- [ ] Select main category → Detailed categories populate correctly
- [ ] Enter keyword + exclude word → Both used in search URL
- [ ] Select condition filter → Applied in search results
- [ ] Search with category1 + category2 → Correct results
- [ ] Save config → All new fields saved
- [ ] Load config → All fields restored
- [ ] CSV export → Results formatted correctly

---

## Priority Summary

**Immediate (Phase 1):**
1. Research and document all subcategories for 7 main categories
2. Update `surugaya_codes.py` with hierarchical category structure
3. Update GUI to show correct categories when Suruga-ya selected

**High Priority (Phase 2):**
1. Add exclude_word field to GUI and scraper
2. Add condition filter (New/Used/All)
3. Update config schema

**Medium Priority (Phase 3):**
1. Release date range filter
2. Product ID/JAN code search
3. Better pagination handling

**Low Priority:**
1. Advanced search UI (collapsible panel)
2. Saved search presets
3. Search history

---

## Notes

- **Category codes are NOT the same as the 200/300/400 series** - Advanced search uses simpler codes (2, 3, 4, etc.) for Level 1
- **Current implementation uses old 200-series codes** - Need to migrate to new 2-level system
- **JavaScript-loaded categories** - May need to inspect network requests to get full category tree
- **Testing required** - Ensure URLs built with new params actually work on live site

---

**Next Step:** Research subcategories for all 7 main categories using web scraping.
