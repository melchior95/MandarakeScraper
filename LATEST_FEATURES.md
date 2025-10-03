# Latest Features Added

## Overview
Three new quality-of-life features added to improve the GUI user experience.

---

## 1. Deselect Treeview Items by Clicking Empty Space ✅

### Feature
Click on empty space in any treeview to deselect all items.

### Problem Solved
Previously, once you selected an item in a treeview (config tree, CSV tree, etc.), you couldn't easily deselect it. You had to click on another item or use keyboard shortcuts.

### Implementation
Added `_deselect_if_empty()` method that detects clicks on empty areas and deselects all items.

```python
def _deselect_if_empty(self, event, tree):
    """Deselect tree items if clicking on empty area"""
    # Check if click is on an item
    item = tree.identify_row(event.y)
    if not item:
        # Clicked on empty area, deselect all
        tree.selection_remove(tree.selection())
```

### Treeviews Updated
- **Config Tree** (main search tab) - Click empty space to deselect config
- **Browserless Tree** (eBay search results) - Click empty space to deselect result
- **CSV Items Tree** (CSV comparison tab) - Click empty space to deselect item

### Code Locations
- Method: `_deselect_if_empty()` at line ~3033
- Config tree binding: line ~502
- Browserless tree binding: line ~635
- CSV items tree binding: line ~756

### Usage
1. Click on any item in a treeview
2. Click on empty space below/between items
3. Selection is cleared

---

## 2. Auto-Load New CSV to Comparison Tree ✅

### Feature
When you run the scraper and a new CSV is created, it automatically loads into the CSV comparison tree at the bottom.

### Status
**Already implemented!** The code was already present in `_poll_queue()` method.

### How It Works
1. When scraper completes, it sends a "results" message with the config path
2. GUI finds the associated CSV file using `_find_matching_csv()`
3. CSV is automatically loaded into the comparison tree
4. Status shows: "Loaded X items into CSV tree"

### Code Location
- `_poll_queue()` method, lines ~2231-2264

### Behavior
- Loads CSV immediately after scraper completes
- Applies current filters
- Displays in CSV comparison tab
- Shows item count in console

---

## 3. Auto-Rename Config Files on Field Changes ✅

### Feature
When you change the keyword, category, or shop in a loaded config, the config file is automatically renamed to match the new values.

### Problem Solved
Previously, if you had a config named "naruto_01_0.json" and changed the keyword to "sasuke", the filename stayed as "naruto_01_0.json", causing confusion.

### Implementation
Enhanced `_auto_save_config()` to:
1. Calculate suggested filename based on current field values
2. Compare with current filename
3. Rename file if different (and safe to do so)
4. Update tree to reflect new name

### Filename Format
`{keyword}_{category}_{shop}.json`

Examples:
- `naruto_01_0.json` - Keyword: naruto, Category: 01, Shop: 0 (all)
- `sasuke_05_nkn.json` - Keyword: sasuke, Category: 05, Shop: nkn (Nakano)

### Safety Features
- Only renames if new filename doesn't exist
- Deletes old file after successful rename
- Updates `last_saved_path` to track new location
- Updates tree to show new filename
- Maintains selection on renamed item

### Code Location
- `_auto_save_config()` method, lines ~3103-3157
- Rename logic: lines ~3123-3142

### Behavior
**When you change:**
- Keyword: "naruto" → "sasuke"
- Category: "01" → "05"
- Shop: "0" → "nkn"

**File automatically renames:**
- From: `naruto_01_0.json`
- To: `sasuke_05_nkn.json`

**What you see:**
- Console message: `[AUTO-RENAME] Renamed config to sasuke_05_nkn.json`
- Tree updates with new filename
- Selection stays on the same (renamed) item

### Edge Cases Handled
1. **New filename exists:** Keeps old filename, doesn't rename
2. **Rename fails:** Logs error, continues with old name
3. **Loading config:** Renaming disabled during config load
4. **No config loaded:** Renaming only works on loaded configs

---

## Testing

### Test Deselect Feature:
1. Launch GUI: `python gui_config.py`
2. Click on a config in the tree
3. Click on empty space below the last item
4. Verify selection clears
5. Repeat for CSV comparison tree

### Test Auto-Load CSV:
1. Create/load a config
2. Click "Run Now" button
3. Wait for scraper to complete
4. Switch to "eBay Search & CSV" tab
5. Verify CSV is loaded in the comparison tree
6. Check console for: "Loaded X items into CSV tree"

### Test Auto-Rename Config:
1. Load an existing config (e.g., `naruto_01_0.json`)
2. Change keyword to "sasuke"
3. Watch console for: `[AUTO-RENAME] Renamed config to sasuke_01_0.json`
4. Verify tree shows new filename
5. Check `configs/` folder - old file deleted, new file created
6. Change category or shop - verify filename updates again

---

## Files Modified

### `gui_config.py`
**Added:**
- `_deselect_if_empty()` method (line ~3033)
- Button-1 bindings for 3 treeviews (lines ~502, ~635, ~756)
- Auto-rename logic in `_auto_save_config()` (lines ~3123-3142)

**Modified:**
- `_auto_save_config()` - Enhanced with rename functionality

---

## Benefits

### 1. Better User Experience
- No confusion about which item is selected
- Clear visual feedback
- Easier to "start fresh" without selection

### 2. Automatic Workflow
- CSV loads immediately after scraping
- No manual "Load CSV" step needed
- Faster analysis workflow

### 3. Better File Organization
- Config filenames always match their content
- Easy to identify configs at a glance
- No orphaned/misnamed files

---

## Known Limitations

### Auto-Rename
- Won't rename if target filename already exists
- Only works on loaded configs (not new configs)
- Requires auto-save to be enabled
- Japanese characters in keyword may result in hash-based names

### Auto-Load CSV
- Only loads CSV from most recent scraper run
- Doesn't load CSVs from manual file operations
- Requires CSV file to exist in expected location

---

## Console Messages

You'll see these new messages in the console:

```
[AUTO-RENAME] Renamed config to sasuke_01_0.json
[AUTO-SAVE] Saved changes to sasuke_01_0.json
[GUI DEBUG] Auto-loading CSV into comparison tree: results/sasuke_01_0.csv
[GUI DEBUG] Loaded 42 items into CSV tree
```

---

## Summary

| Feature | Status | Benefit |
|---------|--------|---------|
| Deselect on empty click | ✅ Complete | Better UX |
| Auto-load CSV | ✅ Already implemented | Faster workflow |
| Auto-rename config | ✅ Complete | Better organization |

All features are **backward compatible** and **non-breaking**.

---

## Next Steps

These features work automatically in the background. No additional user action required besides normal GUI usage!
