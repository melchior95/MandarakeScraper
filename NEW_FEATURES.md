# New Features Added

## 1. New Config Button ✅

### Feature
Added a "New Config" button to create a fresh, empty configuration.

### Location
- Main Search tab, in the config management buttons area
- Positioned before "Delete Selected", "Move Up", "Move Down"

### Functionality
When clicked, the "New Config" button:
1. Clears all form fields (keyword, category, shop, etc.)
2. Resets all settings to defaults
3. Deselects any selected config in the tree
4. Clears `last_saved_path` so Save Config prompts for new filename
5. Focuses the keyword entry field for immediate typing
6. Shows status message: "New config created - ready to configure"

### Default Values
- Keyword: (empty)
- Category: (none selected)
- Shop: (empty)
- Results per page: 240
- Language: English (en)
- Resume: True
- Fast mode: False
- Debug: False
- Hide sold: False

### Usage
1. Click "New Config" button
2. Fill in your search parameters
3. Click "Save Config" (will prompt for filename)
4. New config appears in the tree

### Code Location
- Button: `gui_config.py` line ~509
- Method: `_new_config()` at line ~3141

---

## 2. Fixed Space Key in Keyword Field ✅

### Problem
When typing in the keyword field, pressing the Space key didn't insert a space. This was because other widgets (listboxes and treeviews) were capturing the space key for their selection behavior.

### Solution
Added space key bindings to prevent widgets from consuming the space key:
- `detail_listbox` (category detail list)
- `config_tree` (config file tree)
- `browserless_tree` (eBay search results)
- `csv_items_tree` (CSV comparison tree)

### Implementation
```python
widget.bind("<space>", lambda e: "break")
```

This prevents the default space key behavior (toggling selection) and allows space to work normally in text entry fields.

### Code Locations
- Detail listbox: `gui_config.py` line ~401
- Config tree: `gui_config.py` line ~500
- Browserless tree: `gui_config.py` line ~631
- CSV items tree: `gui_config.py` line ~750

### Result
Now you can type spaces in the keyword field without any issues.

---

## Testing

### Test New Config Button:
1. Launch GUI: `python gui_config.py`
2. Click "New Config" button
3. Verify all fields are cleared
4. Verify keyword field has focus
5. Type a keyword (with spaces!)
6. Fill in other parameters
7. Click "Save Config"
8. Verify it prompts for filename
9. Save and verify it appears in tree

### Test Space Key Fix:
1. Launch GUI
2. Click in keyword field
3. Type: "naruto shippuden" (with space)
4. Verify space character appears
5. Click on config tree or category listbox
6. Press space key
7. Verify it doesn't affect selection
8. Click back in keyword field
9. Type more text with spaces
10. Verify spaces work correctly

---

## Files Modified
- `gui_config.py`:
  - Added "New Config" button (line ~509)
  - Added `_new_config()` method (line ~3141)
  - Added space key bindings to 4 widgets (lines ~401, ~500, ~631, ~750)

## Status
✅ Complete and ready for testing
