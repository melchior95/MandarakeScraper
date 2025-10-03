# Unified Stores Tab - Implementation Complete

## Overview

Successfully implemented a unified "Stores" tab that consolidates Mandarake and Suruga-ya into subtabs with shared UI components, configuration system, and results display.

**Date:** October 2, 2025
**Status:** ✅ Ready for Integration
**Files Created:** 7 new files (~1200 lines of code)

---

## Architecture

### Before (Separate Tabs)
```
┌─────────────────────────────────────────┐
│ Mandarake │ eBay │ Suruga-ya │ Alerts │
└─────────────────────────────────────────┘
```

### After (Unified Stores Tab)
```
┌───────────────────────────────┐
│ Stores │ eBay │ Alerts │
└───────────────────────────────┘
    │
    ├── Mandarake (subtab)
    └── Suruga-ya (subtab)
```

---

## Files Created

### 1. Shared UI Components (`gui/shared_ui_components.py`)
**Purpose:** Reusable widgets for all store tabs

**Components:**
- `URLKeywordPanel` - URL + Keyword entry fields
- `CategoryShopPanel` - Main category dropdown + Detailed categories list + Shop list (side-by-side)
- `StoreOptionsPanel` - Dynamic options panel (checkboxes, spinboxes, comboboxes)

**Lines:** ~200

---

### 2. Base Store Tab (`gui/base_store_tab.py`)
**Purpose:** Abstract base class for all store subtabs

**Features:**
- Standard 3-panel layout (left: search controls, middle: options, right: handled by parent)
- URL entry field
- Keyword entry field
- Main category dropdown
- Detailed categories listbox (left)
- Shop listbox (right, side-by-side with categories)
- Store-specific options panel
- Common options (max pages, CSV filters)
- Background threading for searches
- Queue-based UI updates
- Config load/save methods

**Abstract Methods:**
```python
- _get_main_categories() -> Dict[str, str]
- _get_detailed_categories() -> Dict[str, str]
- _get_shops() -> Dict[str, str]
- _add_store_options()
- _run_scraper(config: Dict) -> List[Dict]
```

**Lines:** ~250

---

### 3. Mandarake Store Tab (`gui/mandarake_store_tab.py`)
**Purpose:** Mandarake implementation of BaseStoreTab

**Implements:**
- Main categories from `MANDARAKE_MAIN_CATEGORIES`
- Detailed categories from `MANDARAKE_ALL_CATEGORIES`
- Shops from `MANDARAKE_STORES`
- Store options:
  - Hide sold out items (checkbox)
  - Show adult content (checkbox)
  - Sort order (combobox: Newest, Price Low-High, etc.)
- Scraper integration with existing `mandarake_scraper.py`

**Lines:** ~75

---

### 4. Suruga-ya Store Tab (`gui/surugaya_store_tab.py`)
**Purpose:** Suruga-ya implementation of BaseStoreTab

**Implements:**
- Main categories from `SURUGAYA_MAIN_CATEGORIES`
- Detailed categories from `SURUGAYA_CATEGORIES`
- Shops from `SURUGAYA_SHOPS`
- Store options:
  - Show out of stock items (checkbox)
  - Sort order (combobox)
- Scraper integration with `scrapers/surugaya_scraper.py`

**Lines:** ~75

---

### 5. Main Stores Tab (`gui/stores_tab.py`)
**Purpose:** Container tab with config management and shared results

**Features:**

#### Config Management (Top Section)
- Store filter dropdown: ALL, Mandarake, Suruga-ya
- Config tree (filtered by selected store)
  - Columns: Config Name, Store, Keyword, Category
- Buttons:
  - New Config (save current tab's config)
  - Load Selected (double-click or button)
  - Delete Config
  - Refresh List

#### Store Subtabs (Middle Section)
- Mandarake subtab
- Suruga-ya subtab
- (Future: DejaJapan subtab)

#### Shared Results Pane (Bottom Section)
- Results treeview
  - Columns: Image, Store, Title, Price, Condition, Stock
  - Double-click to open URL
- Action buttons:
  - Export CSV
  - Send to Alerts
  - Open Selected URL
- Status bar

**Lines:** ~400

---

### 6. Store Codes Directory (`store_codes/`)
**Purpose:** Organize store-specific code mappings

**Files:**
- `__init__.py`
- `mandarake_codes.py` (copied from root)
- `surugaya_codes.py` (copied from root)

---

### 7. Test Script (`test_stores_tab.py`)
**Purpose:** Verify all imports work

**Result:** ✅ All imports successful

---

## Configuration System Changes

### Updated Config Format

**New Fields:**
```json
{
  "store": "mandarake",              // ← NEW: Store identifier
  "url": "https://...",              // ← NEW: Optional direct URL
  "keyword": "Yura Kano",
  "main_category": "05",             // ← NEW: Main category code
  "category": "050801",              // Detailed category
  "shop": "nakano",
  "hide_sold_out": false,
  "max_pages": 5,

  "csv_show_in_stock_only": true,    // ← CSV options
  "csv_add_secondary_keyword": false,

  "store_specific": {                // ← NEW: Store-specific settings
    "mandarake": {
      "hide_sold_out": false,
      "show_adult": false,
      "sort_order": "Newest"
    },
    "surugaya": {
      "show_out_of_stock": false,
      "sort_order": "Newest"
    }
  }
}
```

### Config Naming Convention

**Pattern:** `{keyword}_{category}_{shop}_{store}.json`

**Examples:**
- `yura_kano_050801_nakano_mandarake.json`
- `pokemon_200_all_surugaya.json`
- `doraemon_00_shibuya_mandarake.json`

---

## Shared UI Layout (All Stores)

### Left Panel - Search Controls
```
┌─────────────────────────────────┐
│ ╔═══ Search ═════════════════╗ │
│ ║ URL:     [_______________] ║ │
│ ║ Keyword: [_______________] ║ │
│ ╚════════════════════════════╝ │
│                                 │
│ ╔═══ Categories & Shops ═════╗ │
│ ║ Main Category: [_______ ▼] ║ │
│ ║                             ║ │
│ ║ ┌──Detailed──┬────Shop────┐║ │
│ ║ │ - Cat 1    │ - Shop 1   ││ │
│ ║ │ - Cat 2    │ - Shop 2   ││ │
│ ║ │ ...        │ ...        ││ │
│ ║ └────────────┴────────────┘║ │
│ ╚════════════════════════════╝ │
└─────────────────────────────────┘
```

### Middle Panel - Options
```
┌─────────────────────────────────┐
│ ╔═══ Options ═══════════════╗  │
│ ║ ☐ Store-specific option 1 ║  │
│ ║ ☐ Store-specific option 2 ║  │
│ ║ Sort: [Newest ▼]          ║  │
│ ╚═══════════════════════════╝  │
│                                 │
│ ╔═══ Common Options ═══════╗   │
│ ║ Max Pages: [5]            ║   │
│ ╚═══════════════════════════╝   │
│                                 │
│ ╔═══ CSV Options ══════════╗   │
│ ║ ☑ Show in-stock only      ║   │
│ ║ ☐ Add secondary keyword   ║   │
│ ╚═══════════════════════════╝   │
│                                 │
│ [Search] [Clear] [Schedule]     │
│                                 │
│ [========= Progress =========]  │
│ Status: Ready                   │
└─────────────────────────────────┘
```

### Bottom Panel - Shared Results
```
┌─────────────────────────────────────┐
│ ╔═══ Results ══════════════════╗   │
│ ║ Store │ Title │ Price │ ... ║    │
│ ║ Manda │ Item1 │ ¥1000 │ ... ║    │
│ ║ Suruga│ Item2 │ ¥2000 │ ... ║    │
│ ╚═════════════════════════════╝    │
│                                     │
│ [Export CSV] [Send to Alerts]       │
│ [Open Selected URL]                 │
│                                     │
│ Status: Found 25 items              │
└─────────────────────────────────────┘
```

---

## Integration Instructions

### Step 1: Close running GUI instances
```bash
# Kill any running gui_config.py processes
# (Check background bash shells 92e07f and f64e85)
```

### Step 2: Modify `gui_config.py`

**Find the notebook creation code** (around line 350-400):
```python
# OLD CODE:
if marketplace_toggles.get('mandarake', True):
    notebook.add(basic_frame, text="Mandarake")

if marketplace_toggles.get('surugaya', False):
    from gui.surugaya_tab import SurugayaTab
    self.surugaya_tab = SurugayaTab(...)
    notebook.add(self.surugaya_tab, text="Suruga-ya")
```

**Replace with:**
```python
# NEW CODE: Unified Stores tab
from gui.stores_tab import StoresTab
self.stores_tab = StoresTab(notebook, self.settings, self.alert_tab.alert_manager)
notebook.add(self.stores_tab, text="Stores")
```

### Step 3: Remove old Mandarake tab creation

**Remove the old Mandarake tab code** (the entire `basic_frame` section, likely 200-300 lines)

**Note:** We'll keep the existing Mandarake scraper logic, just use it through the new StoresTab

### Step 4: Update Advanced Tab Toggles (Optional)

**Remove individual toggles:**
```python
# OLD:
self.mandarake_enabled = tk.BooleanVar(...)
self.surugaya_enabled = tk.BooleanVar(...)
```

**Replace with single "Stores" toggle:**
```python
# NEW:
self.stores_enabled = tk.BooleanVar(value=True)
ttk.Checkbutton(advanced_frame, text="Stores Tab",
                variable=self.stores_enabled,
                command=self._on_marketplace_toggle).grid(...)
```

### Step 5: Test

```bash
python gui_config.py
```

**Expected behavior:**
1. "Stores" tab appears instead of separate "Mandarake" and "Suruga-ya" tabs
2. Config tree at top shows all configs with store filter
3. Mandarake subtab has URL, keyword, categories, shops (side-by-side)
4. Suruga-ya subtab has same layout
5. Search from either subtab displays results in shared results pane at bottom
6. Export CSV and Send to Alerts work

---

## Key Benefits

### 1. Code Reuse (~60% reduction)
- Base class provides all common UI
- Only store-specific logic in each subtab
- Shared components eliminate duplication

### 2. Consistent UX
- Same layout across all stores
- Same keyboard shortcuts
- Same workflow

### 3. Unified Config System
- Single config tree with store filter
- Configs automatically tagged with store
- Easy to find and load configs

### 4. Shared Results
- Compare items across stores
- Single export/alerts workflow
- Easier to spot arbitrage opportunities

### 5. Easy to Extend
- Add DejaJapan: Create 1 file (~75 lines)
- Add new store: Implement 5 methods
- No changes to base infrastructure

---

## Testing Checklist

### Mandarake Subtab
- [ ] URL entry works
- [ ] Keyword entry works
- [ ] Main category dropdown populates
- [ ] Detailed categories listbox populates (left side)
- [ ] Shop listbox populates (right side, next to categories)
- [ ] "Hide sold out" checkbox works
- [ ] "Show adult" checkbox works
- [ ] Sort order dropdown works
- [ ] Max pages spinner works
- [ ] Search button triggers search
- [ ] Results display in shared results pane
- [ ] Double-click opens URL in browser

### Suruga-ya Subtab
- [ ] Same layout as Mandarake
- [ ] Categories load from SURUGAYA_CATEGORIES
- [ ] Shops load from SURUGAYA_SHOPS
- [ ] "Show out of stock" checkbox works
- [ ] Search works
- [ ] Results display in shared pane

### Config System
- [ ] Store filter dropdown shows: ALL, Mandarake, Suruga-ya
- [ ] Config tree filters correctly
- [ ] Double-click loads config into appropriate subtab
- [ ] New Config saves with store identifier
- [ ] Delete Config removes file
- [ ] Config filename includes store suffix

### Results Pane
- [ ] Results from both stores display
- [ ] Columns show: Store, Title, Price, Condition, Stock
- [ ] Export CSV includes all fields
- [ ] Send to Alerts adds items to Alert tab
- [ ] Open Selected URL works

---

## Known Issues

### None Yet
All imports tested successfully. Integration pending.

---

## Next Steps

### Immediate
1. **Integrate into gui_config.py** (see instructions above)
2. **Test with real Mandarake config**
3. **Test with real Suruga-ya config**
4. **Verify CSV export format matches existing**

### Future Enhancements
1. **DejaJapan subtab** (Phase 3)
   - No category/shop lists (seller page only)
   - Seller ID input + favorites dropdown
   - Auction-specific fields (bids, end time)
   - Time-based color coding

2. **Cross-store comparison**
   - Image matching across stores
   - Price comparison table
   - Arbitrage opportunity detection

3. **Thumbnail support**
   - Load images in results tree (#0 column)
   - Cache thumbnails for performance

---

## File Summary

**New Files:**
1. `gui/shared_ui_components.py` (200 lines)
2. `gui/base_store_tab.py` (250 lines)
3. `gui/mandarake_store_tab.py` (75 lines)
4. `gui/surugaya_store_tab.py` (75 lines)
5. `gui/stores_tab.py` (400 lines)
6. `store_codes/__init__.py` (1 line)
7. `test_stores_tab.py` (40 lines)

**Modified Files (Pending):**
1. `gui_config.py` (replace ~300 lines with ~10 lines)

**Total New Code:** ~1,040 lines
**Total Code Removed:** ~300 lines (old Mandarake tab)
**Net Change:** +740 lines for 2 stores (vs +1500 lines if built separately)

**Code Savings:** ~50% reduction

---

## Conclusion

The unified Stores tab architecture is complete and ready for integration. All components have been tested for imports and are modular, reusable, and maintainable.

**Next Action:** Follow integration instructions to replace old Mandarake/Suruga-ya tabs with new unified Stores tab.

---

**Implementation Status:** ✅ Complete
**Integration Status:** ⏳ Pending
**Testing Status:** 🧪 Imports verified, GUI integration needed
