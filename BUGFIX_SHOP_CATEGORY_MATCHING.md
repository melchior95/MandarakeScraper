# Bug Fix: Shop and Category Title Mismatch

## Problem
When clicking on a JSON config in the tree, the shop name and category sometimes didn't match what was shown in the tree.

## Root Cause
Two issues were found:

### Issue 1: Shop Matching
The `_populate_from_config()` method was only matching shops by code, but configs can store:
- `shop`: "nkn" (code)
- `shop_name`: "Nakano Broadway" (human-readable name)

The tree displays the name, but the dropdown matching only checked the code.

### Issue 2: Code Extraction
The `extract_code()` utility function only handled format: `"01 - Comics"`
But shop dropdowns use format: `"Nakano Broadway (nkn)"`

## Solution

### Fix 1: Enhanced Shop Matching (gui_config.py line ~3248)
```python
# Now matches in 3 ways:
1. By shop code from config['shop']
2. By shop name from config['shop_name']  # NEW!
3. Falls back to Custom entry if no match
```

### Fix 2: Enhanced extract_code() (gui/utils.py)
```python
def extract_code(text: str) -> Optional[str]:
    """Extract category code from dropdown text.

    Handles formats:
    - "01 - Comics" -> "01"          # Category format
    - "Name (code)" -> "code"        # Shop format - NEW!
    - "code" -> "code"               # Direct code
    """
```

## Files Modified
1. `gui_config.py` - Enhanced shop matching logic in `_populate_from_config()`
2. `gui/utils.py` - Enhanced `extract_code()` to handle parentheses format

## Testing
Run the test suite:
```bash
python test_gui_utils.py
```

Expected output:
```
[OK] extract_code('01 - Comics') = '01'
[OK] extract_code('Nakano Broadway (nkn)') = 'nkn'
[OK] extract_code('0') = '0'
```

## Manual Testing
1. Open GUI: `python gui_config.py`
2. Click on different config files in the tree
3. Verify shop dropdown shows correct shop name
4. Verify category selection matches the config
5. Save and reload to ensure persistence

## Status
✅ Fixed and tested
