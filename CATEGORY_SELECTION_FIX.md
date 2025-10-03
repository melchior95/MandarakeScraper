# Category Selection Enhancement

## Overview
Enhanced category selection when loading configs to properly select main category, populate detail categories, and scroll to make selected categories visible.

---

## Problem

When loading a config file with categories:
1. Main category dropdown wasn't always showing the correct selection
2. Detail categories weren't visible if they were far down in the list
3. User had to manually scroll to see which detail categories were selected

---

## Solution

Enhanced the `_select_categories()` method to:

### 1. Properly Select Main Category
```python
# Select main category
first_code = categories[0]
main_code = utils.match_main_code(first_code)
if main_code:
    label = f"{MANDARAKE_MAIN_CATEGORIES[main_code]['en']} ({main_code})"
    self.main_category_var.set(label)
```

**What this does:**
- Takes the first category code from config (e.g., "050101")
- Matches it to main category (e.g., "05" for Idol Goods)
- Sets the main category dropdown to show: "Idol Goods (05)"

### 2. Populate Detail Categories
```python
# Populate detail categories based on main category
self._populate_detail_categories(utils.extract_code(self.main_category_var.get()))
```

**What this does:**
- Extracts the code from the main category (e.g., "05" from "Idol Goods (05)")
- Populates the detail listbox with all categories starting with that code
- This ensures the detail categories are filtered correctly

### 3. Select and Scroll to Detail Categories
```python
# Select detail categories and scroll to first selected
first_selected_idx = None
for idx, code in enumerate(self.detail_code_map):
    if code in categories:
        self.detail_listbox.selection_set(idx)
        if first_selected_idx is None:
            first_selected_idx = idx

# Scroll to make the first selected category visible
if first_selected_idx is not None:
    self.detail_listbox.see(first_selected_idx)
```

**What this does:**
- Loops through all detail categories
- Selects the ones that match the config
- Tracks the first selected category
- Scrolls the listbox to make it visible using `.see()`

---

## Example Flow

### Config File Contains:
```json
{
  "category": ["050101"],
  "category_name": "Photobook"
}
```

### What Happens When Loading:

1. **Extract Main Category:**
   - Detail code: `"050101"`
   - Main code: `"05"` (Idol Goods)

2. **Set Main Category Dropdown:**
   - Shows: `"Idol Goods (05)"`

3. **Populate Detail Categories:**
   - Listbox shows all categories starting with "05":
     - `"05 - Idol Goods"`
     - `"0501 - Photobook / Photo"`
     - `"050101 - Photobook"`  ← Selected
     - `"050102 - Photo"`
     - ... etc

4. **Scroll to Selected:**
   - Listbox automatically scrolls to show "050101 - Photobook"
   - User can immediately see what's selected

---

## Code Location

**File:** `gui_config.py`

**Method:** `_select_categories()` at line ~2384

**Changes:**
- Added comments for clarity
- Added `first_selected_idx` tracking
- Added `.see()` call to scroll to selected item

---

## Testing

### Test Script
Run: `python test_category_selection.py`

**Expected Output:**
```
Testing category matching...
[OK] Detail '01' -> Main '01' (expected '01')
[OK] Detail '0101' -> Main '01' (expected '01')
[OK] Detail '05' -> Main '05' (expected '05')
[OK] Detail '050101' -> Main '05' (expected '05')
[OK] Detail '06' -> Main '06' (expected '06')
[OK] Detail '060101' -> Main '06' (expected '06')

Testing label format...
[OK] Label for code '01': 'Books (everything) (01)'

[SUCCESS] Category selection logic working correctly!
```

### Manual Testing

1. **Create or Load a Config with Categories:**
   ```bash
   python gui_config.py
   ```

2. **Load a Config:**
   - Click on a config in the tree that has categories
   - Example: Any config with category like "050101"

3. **Verify Main Category:**
   - Check that main category dropdown shows correct selection
   - Example: Should show "Idol Goods (05)"

4. **Verify Detail Categories:**
   - Check that detail categories are highlighted
   - Example: "050101 - Photobook" should be selected

5. **Verify Scroll:**
   - Detail listbox should automatically scroll
   - Selected category should be visible without manual scrolling

---

## Category Hierarchy Examples

### Example 1: Photobook
- **Detail Code:** `"050101"`
- **Main Code:** `"05"`
- **Main Category:** `"Idol Goods (05)"`
- **Detail Category:** `"050101 - Photobook"`

### Example 2: Pokemon Cards
- **Detail Code:** `"060101"`
- **Main Code:** `"06"`
- **Main Category:** `"Trading Cards (06)"`
- **Detail Category:** `"060101 - Pokemon Card"`

### Example 3: Manga
- **Detail Code:** `"0101"`
- **Main Code:** `"01"`
- **Main Category:** `"Books (everything) (01)"`
- **Detail Category:** `"0101 - Manga"`

---

## Benefits

### Before
❌ Main category not selected
❌ Detail categories hidden if far down in list
❌ User had to manually scroll to see selection
❌ Confusing UX

### After
✅ Main category automatically selected
✅ Detail categories automatically highlighted
✅ Listbox automatically scrolls to show selection
✅ Clear visual feedback

---

## Technical Details

### `.see()` Method
The tkinter Listbox `.see(index)` method scrolls the listbox to make the item at the given index visible. This is key to the enhancement.

```python
self.detail_listbox.see(first_selected_idx)
```

### Category Matching
Uses `utils.match_main_code()` to find the main category:

```python
def match_main_code(code: str) -> Optional[str]:
    """Match a detail category code to its main category."""
    if not code:
        return None
    # Try progressively shorter prefixes
    for length in range(len(code), 0, -1):
        prefix = code[:length]
        from .constants import MAIN_CATEGORY_OPTIONS
        for main_code, _ in MAIN_CATEGORY_OPTIONS:
            if main_code == prefix:
                return main_code
    return None
```

This handles cases like:
- `"050101"` → tries `"050101"`, `"05010"`, `"0501"`, `"050"`, `"05"` → matches `"05"`
- `"01"` → tries `"01"` → matches `"01"`

---

## Edge Cases Handled

1. **No Categories:**
   - Clears selections
   - Shows all detail categories

2. **Invalid Main Code:**
   - Sets main category to empty
   - Still populates detail categories

3. **Multiple Detail Categories:**
   - Selects all matching categories
   - Scrolls to show the first one

4. **Empty Config:**
   - Safely handles missing category data
   - Doesn't crash or error

---

## Related Files

- `gui_config.py` - Main implementation
- `gui/utils.py` - `match_main_code()`, `extract_code()`
- `gui/constants.py` - `MAIN_CATEGORY_OPTIONS`
- `test_category_selection.py` - Test script

---

## Status

✅ **Complete and tested**

All category selection logic now works correctly with proper visual feedback.
