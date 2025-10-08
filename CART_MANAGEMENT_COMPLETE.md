# Cart Management System - Complete Implementation

**Status**: ✅ COMPLETE
**Date**: October 7, 2025
**Feature**: Bulk add Mandarake items to cart with alert workflow integration

---

## Overview

The Cart Management System allows users to:
1. **Bulk add "Yay" alerts to Mandarake cart** via single button click
2. **Track cart items** with local storage and session persistence
3. **Automatic state updates** (Yay → Purchased when added to cart)
4. **Progress tracking** with real-time dialog
5. **Results reporting** with success/failure breakdown

---

## Architecture

### Core Components

```
gui/cart_manager.py (301 lines)
├── CartManager - Main orchestrator
│   ├── add_yays_to_cart() - Convenience method for all Yays
│   ├── add_alerts_to_cart() - Core add-to-cart logic
│   ├── verify_cart_roi() - ROI verification
│   └── _fetch_alert_data() - Alert enrichment
│
gui/cart_ui.py (290 lines)
├── CartProgressDialog - Real-time progress bar
├── show_cart_results() - Success/failure summary
└── ThresholdWarningDialog - (unused, kept for reference)
│
gui/alert_tab.py
├── initialize_cart_ui() - Creates cart UI after cart_manager is set
├── _add_yays_to_cart() - Button click handler
└── _show_cart_results() - Results display
│
scrapers/mandarake_cart_api.py
├── MandarakeCartAPI.add_to_cart() - Low-level API call
├── MandarakeCartAPI.get_cart_items() - Fetch cart contents
└── MandarakeCartSession - Session persistence
```

### Data Flow

```
User clicks "Add Yays to Cart"
    ↓
alert_tab._add_yays_to_cart()
    ↓
cart_manager.add_yays_to_cart()
    ├── Fetch all Yay alerts
    ├── Extract product_id from store_link
    ├── Group by shop
    └── For each item:
        ├── cart_api.add_to_cart(product_id, shop_code)
        ├── Update local storage
        └── Update alert state (Yay → Purchased)
    ↓
Show results dialog
```

---

## GUI Integration

### Alert Tab UI

**Location**: `gui/alert_tab.py:697-737`

**Cart Management Frame**:
```python
Cart Management: [Not connected] [Add Yays to Cart]
```

**Lazy Initialization Pattern**:
```python
# In AlertTab.__init__
self.cart_manager = None  # Set later by gui_config.py
self.cart_frame = None    # Created in initialize_cart_ui()

# In gui_config.py after creating alert_tab
self.alert_tab.cart_manager = self.cart_manager
self.alert_tab.initialize_cart_ui()  # Creates UI
```

**Why lazy initialization?**
Cart UI requires cart_manager, but cart_manager requires alert_manager. This creates a circular dependency. Solution: Create cart UI *after* both managers exist.

---

## Implementation Details

### 1. Add-to-Cart Workflow

**Code**: `gui/cart_manager.py:121-227`

```python
def add_alerts_to_cart(self, alert_ids, force_below_threshold=False,
                       progress_callback=None):
    """
    Add alert items to Mandarake cart

    Workflow:
    1. Fetch alert data (enriched with product_id, shop_code, prices)
    2. Group by shop
    3. Add each item via cart API
    4. Update local storage
    5. Update alert state (Yay → Purchased)
    6. Calculate shop totals

    Returns:
        {
            'success': bool,
            'added': [...],      # Successfully added items
            'failed': [...],     # Failed items with error messages
            'shop_totals': {...} # Per-shop item counts and totals
        }
    """
```

**Key Features**:
- **Product ID extraction**: `r'itemCode=(\d+)'` regex from store_link
- **Shop code defaulting**: 'webshop' (not in URL)
- **Batch fetching**: `get_alerts_by_ids()` instead of looping
- **Progress callbacks**: `progress_callback(current, total, message)`
- **Atomic state updates**: Each item updates individually
- **Error isolation**: One failure doesn't stop the rest

### 2. Alert Data Enrichment

**Code**: `gui/cart_manager.py:272-312`

```python
def _fetch_alert_data(self, alert_ids):
    """
    Fetch and enrich alert data with product_id and shop_code

    Extracts:
    - product_id: from store_link (itemCode=XXXX)
    - shop_code: from store_link or defaults to 'webshop'
    - price_jpy: converted from price text

    Returns:
        List of enriched alert dicts
    """
```

**Regex Patterns**:
```python
# Product ID (required)
product_id_match = re.search(r'itemCode=(\d+)', store_link)

# Shop code (optional, defaults to 'webshop')
shop_match = re.search(r'shop=(\w+)', store_link)
```

**Price Parsing**:
```python
# Handles: "¥1,200", "1200 yen", "¥1200"
price_text = alert.get('store_price', '¥0')
price_jpy = int(''.join(c for c in price_text if c.isdigit()))
```

### 3. Alert State Updates

**Code**: `gui/cart_manager.py:197-203`

```python
# Update alert state: Yay → Purchased
if self.alert_manager:
    try:
        from gui.alert_states import AlertState
        self.alert_manager.update_alert_state(
            item['alert_id'],
            AlertState.PURCHASED
        )
    except Exception as e:
        self.logger.warning(f"Could not update alert state: {e}")
```

**CRITICAL**: Must use `AlertState.PURCHASED` enum, not string `'purchased'`

### 4. Progress Tracking

**Code**: `gui/cart_ui.py:8-79`

```python
class CartProgressDialog:
    """
    Real-time progress dialog for cart operations

    Features:
    - Item counter (X of Y)
    - Progress bar (0-100%)
    - Current item message
    - Auto-closes on completion
    """

    def update(self, current, total, message):
        """Called by cart_manager during add-to-cart loop"""
        self.progress_label.config(text=f"{current} of {total}")
        self.message_label.config(text=message)
        self.progress_bar['value'] = (current / total) * 100
        self.update_idletasks()

    def finish(self):
        """Close dialog after operation completes"""
        self.destroy()
```

**Usage**:
```python
# In alert_tab._add_yays_to_cart()
progress_dialog = CartProgressDialog(self, yay_count)

def progress_callback(current, total, msg):
    progress_dialog.update(current, total, msg)

result = cart_manager.add_yays_to_cart(
    progress_callback=progress_callback
)

progress_dialog.finish()
```

### 5. Results Display

**Code**: `gui/cart_ui.py:82-222`

```python
def show_cart_results(parent, result):
    """
    Display add-to-cart results in dialog

    Shows:
    - Overall success/failure
    - Shop-by-shop breakdown
    - Added items (green)
    - Failed items (red)
    - Shop totals
    """
```

**Display Format**:
```
Cart Update Complete

✅ Successfully added 8 items to cart
❌ Failed to add 2 items

══════════════════════════════════════════════
Added Items (8):
══════════════════════════════════════════════
nakano
  • Item Title                       ¥1,200
  • Another Item                     ¥2,500

sahra
  • Third Item                       ¥800

══════════════════════════════════════════════
Failed Items (2):
══════════════════════════════════════════════
  • Failed Item Title
    Error: Item sold out

Shop Totals:
  nakano: 5 items, ¥15,000
  sahra: 3 items, ¥8,500
```

---

## Testing

### Manual Testing Steps

1. **Connect to Cart**:
   ```bash
   python gui_config.py
   ```
   - Go to Review/Alerts tab
   - Click "Connect to Cart"
   - Paste cart URL with jsessionid

2. **Add Items to Alerts**:
   - Go to eBay Search & CSV tab
   - Load CSV file
   - Right-click items → "Send to Alerts (without eBay data)"

3. **Mark as Yay**:
   - Go to Review/Alerts tab
   - Select items → "Mark Yay"

4. **Add to Cart**:
   - Click "Add Yays to Cart"
   - Confirm dialog
   - Watch progress dialog
   - Review results

### Automated Testing

**Test Script**: `test_cart_add.py`

```bash
python test_cart_add.py
```

**What it tests**:
1. ✅ Session loading and validation
2. ✅ Add single item to cart via API
3. ✅ Fetch cart contents
4. ✅ Verify item was added

**Prerequisites**:
- Must have active cart session (connect via GUI first)
- Must provide valid product ID from Mandarake URL

**Example Output**:
```
Cart session connected successfully!

Enter a Mandarake product ID: 1309040459

============================================================
Testing add_to_cart with product ID: 1309040459
============================================================

Test 1: Adding item to cart...
SUCCESS: Item added to cart!

Test 2: Fetching cart contents...
SUCCESS: Cart contains 3 items

Current cart items:
ID              Title                                              Price           Shop
------------------------------------------------------------------------------------------
1309040459      Yura Kano Tamayura Yura Kano Photograph Collect... ¥2,400          webshop
1308675432      Another Item Title...                              ¥1,200          nakano
1307891234      Third Item...                                      ¥800            sahra

Test 3: Checking if product 1309040459 is in cart...
SUCCESS: Found item in cart:
   Title: Yura Kano Tamayura Yura Kano Photograph Collection
   Price: ¥2,400
   Shop: webshop

============================================================
Test complete!
============================================================
```

---

## Error Handling

### Common Errors and Fixes

#### 1. AttributeError: 'AlertTab' object has no attribute 'cart_status_label'

**Cause**: Cart UI not initialized
**Fix**: Call `initialize_cart_ui()` after setting `cart_manager`

```python
# In gui_config.py
self.alert_tab.cart_manager = self.cart_manager
self.alert_tab.initialize_cart_ui()  # ← Critical!
```

#### 2. AttributeError: 'str' object has no attribute 'value'

**Cause**: Passing string instead of AlertState enum
**Fix**: Use `AlertState.YAY`, `AlertState.PURCHASED`

```python
# ❌ Wrong
yay_alerts = alert_manager.get_alerts_by_state('yay')

# ✅ Correct
from gui.alert_states import AlertState
yay_alerts = alert_manager.get_alerts_by_state(AlertState.YAY)
```

#### 3. AttributeError: 'AlertManager' object has no attribute 'get_alert'

**Cause**: Wrong method name
**Fix**: Use `get_alerts_by_ids()` (plural, batch operation)

```python
# ❌ Wrong
for alert_id in alert_ids:
    alert = alert_manager.get_alert(alert_id)

# ✅ Correct
alerts = alert_manager.get_alerts_by_ids(alert_ids)
for alert in alerts:
    # Process alert
```

#### 4. WARNING: 'AlertManager' object has no attribute 'update_state'

**Cause**: Wrong method name
**Fix**: Use `update_alert_state()` (singular)

```python
# ❌ Wrong
alert_manager.update_state(alert_id, 'purchased')

# ✅ Correct
alert_manager.update_alert_state(alert_id, AlertState.PURCHASED)
```

#### 5. "No CSV data loaded" when sending to alerts

**Cause**: Looking in wrong location
**Fix**: Use `csv_comparison_manager.csv_compare_data`

```python
# ❌ Wrong
csv_data = main_window.csv_data

# ✅ Correct
csv_data = self.csv_comparison_manager.csv_compare_data
```

---

## Design Decisions

### 1. No Threshold Checking Before Add

**Decision**: Remove pre-add threshold warnings
**Rationale**: User feedback indicated this was unnecessary friction
**Implementation**: Add all items, report shop totals afterward

**Original Flow** (removed):
```
Click "Add Yays to Cart"
  → Check thresholds
  → Show warning dialog if below minimum
  → User confirms
  → Add items
  → Show results
```

**Current Flow**:
```
Click "Add Yays to Cart"
  → Confirm dialog
  → Add items
  → Show results (includes shop totals)
```

### 2. Dummy eBay Data for CSV Items

**Decision**: Allow sending CSV items to alerts without eBay comparison
**Rationale**: Users may want to track items without eBay data
**Implementation**: Create dummy eBay fields (similarity=0, profit=0)

```python
comparison_result = {
    'store_title': csv_row.get('title'),
    'store_price': csv_row.get('price'),
    # ... other store fields

    # Dummy eBay data
    'ebay_title': 'No eBay data',
    'ebay_link': '',
    'ebay_price': '$0',
    'similarity': 0,
    'profit_margin': 0,
}
```

### 3. Lazy UI Initialization

**Decision**: Create cart UI after cart_manager is set
**Rationale**: Avoid circular dependency (alert_tab needs cart_manager, cart_manager needs alert_manager)
**Implementation**: `initialize_cart_ui()` method called from gui_config.py

### 4. Shop Code Defaulting

**Decision**: Default shop_code to 'webshop' if not in URL
**Rationale**: Most Mandarake product URLs don't include shop parameter
**Implementation**: Regex extraction with fallback

```python
shop_match = re.search(r'shop=(\w+)', store_link)
shop_code = shop_match.group(1) if shop_match else 'webshop'
```

---

## File Changes Summary

### New Files

1. **`gui/cart_manager.py`** (301 lines)
   - Core business logic for cart operations
   - Alert data enrichment
   - Progress tracking
   - State updates

2. **`gui/cart_ui.py`** (290 lines)
   - CartProgressDialog
   - show_cart_results()
   - ThresholdWarningDialog (unused)

3. **`test_cart_add.py`** (116 lines)
   - Automated testing script
   - Session validation
   - Add-to-cart verification

### Modified Files

1. **`gui/alert_tab.py`**
   - Added `cart_manager` parameter
   - Added `initialize_cart_ui()` method
   - Added `_add_yays_to_cart()` handler
   - Added `_show_cart_results()` display

2. **`gui/ebay_tab.py`**
   - Added `_send_csv_to_alerts()` method
   - Added "Send to Alerts (without eBay data)" to context menu
   - Removed "Search by Image on eBay (Web)" option

3. **`gui_config.py`**
   - Imported CartManager
   - Initialized cart_manager after alert_tab
   - Called `alert_tab.initialize_cart_ui()`

---

## Usage Examples

### Example 1: Basic Workflow

```python
# 1. Load CSV and send items to alerts
csv_data = load_csv('results/yura_kano.csv')
send_to_alerts(csv_data)

# 2. Mark items as Yay
for item in pending_items:
    if item['profit_margin'] > 30:
        mark_yay(item)

# 3. Add Yays to cart
cart_manager.add_yays_to_cart(
    progress_callback=progress_callback
)

# Result:
# - Items added to Mandarake cart
# - Alert states updated to Purchased
# - Shop totals calculated
```

### Example 2: Custom Alert Selection

```python
# Add specific alerts (not just Yays)
alert_ids = [1, 5, 8, 12]

result = cart_manager.add_alerts_to_cart(
    alert_ids=alert_ids,
    progress_callback=lambda c, t, m: print(f"{c}/{t}: {m}")
)

print(f"Added: {len(result['added'])}")
print(f"Failed: {len(result['failed'])}")
print(f"Shop totals: {result['shop_totals']}")
```

### Example 3: Error Recovery

```python
result = cart_manager.add_yays_to_cart()

# Check failures
if result['failed']:
    print("Failed items:")
    for item in result['failed']:
        print(f"  {item['title']}: {item['error']}")

    # Retry failed items
    failed_ids = [item['alert_id'] for item in result['failed']]
    retry_result = cart_manager.add_alerts_to_cart(failed_ids)
```

---

## API Reference

### CartManager

#### `add_yays_to_cart(force_below_threshold=False, progress_callback=None)`

Add all "Yay" alerts to cart.

**Parameters**:
- `force_below_threshold` (bool): Unused (kept for compatibility)
- `progress_callback` (callable): Optional callback(current, total, message)

**Returns**:
```python
{
    'success': bool,
    'added': [
        {
            'alert_id': int,
            'product_id': str,
            'title': str,
            'price_jpy': int,
            'shop_code': str,
            'store_link': str
        },
        ...
    ],
    'failed': [
        {
            'alert_id': int,
            'title': str,
            'error': str
        },
        ...
    ],
    'shop_totals': {
        'nakano': {'items': 5, 'total_jpy': 15000},
        'sahra': {'items': 3, 'total_jpy': 8500},
        ...
    }
}
```

#### `add_alerts_to_cart(alert_ids, force_below_threshold=False, progress_callback=None)`

Add specific alerts to cart.

**Parameters**:
- `alert_ids` (List[int]): Alert IDs to add
- `force_below_threshold` (bool): Unused (kept for compatibility)
- `progress_callback` (callable): Optional callback(current, total, message)

**Returns**: Same as `add_yays_to_cart()`

#### `is_connected()`

Check if cart API is connected and session is valid.

**Returns**: bool

#### `connect_with_url(cart_url)`

Connect to Mandarake cart using cart URL.

**Parameters**:
- `cart_url` (str): Full cart URL with jsessionid

**Returns**: `(success: bool, message: str)`

---

## Future Enhancements

### Potential Improvements

1. **Batch Add Optimization**
   - Currently adds items one-by-one
   - Could batch by shop for faster processing
   - Would require Mandarake API support

2. **Smart Retry Logic**
   - Auto-retry failed items with exponential backoff
   - Distinguish between transient errors (network) and permanent (sold out)

3. **Cart Threshold Warnings**
   - Optional post-add threshold reporting
   - Alert if shop total > maximum or < minimum
   - Configurable thresholds per shop

4. **ROI Verification Before Add**
   - Optional: Verify eBay prices before adding to cart
   - Warn if profit margin dropped since last check
   - Auto-remove items with negative ROI

5. **Undo Functionality**
   - Track items added in last operation
   - "Undo Add to Cart" button
   - Would require Mandarake remove-from-cart API

6. **Export Cart to CSV**
   - Save cart snapshot for record-keeping
   - Include purchase date, prices, profit margins
   - Track historical purchases

---

## Related Documentation

- **[MANDARAKE_CART_API_COMPLETE.md](MANDARAKE_CART_API_COMPLETE.md)** - Cart API implementation
- **[CART_ROI_VERIFICATION_COMPLETE.md](CART_ROI_VERIFICATION_COMPLETE.md)** - ROI verification system
- **[ALERT_TAB_COMPLETE.md](ALERT_TAB_COMPLETE.md)** - Alert workflow integration
- **[GUI_MODULARIZATION_COMPLETE.md](GUI_MODULARIZATION_COMPLETE.md)** - GUI architecture

---

## Changelog

### October 7, 2025
- ✅ Implemented `add_yays_to_cart()` convenience method
- ✅ Created CartProgressDialog for real-time progress
- ✅ Added automatic alert state updates (Yay → Purchased)
- ✅ Integrated cart UI into alert tab
- ✅ Removed threshold checking before add (user feedback)
- ✅ Fixed AlertState enum usage throughout codebase
- ✅ Added CSV-to-alerts without eBay data
- ✅ Created test_cart_add.py for automated testing
- ✅ Documented complete system

---

**Implementation Status**: ✅ COMPLETE
**Testing Status**: ✅ Manual testing steps documented, automated test script created
**Documentation Status**: ✅ Complete with examples and API reference
