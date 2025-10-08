# Cart Display & Management UI - COMPLETE ✅

**Status**: ✅ COMPLETE
**Date**: October 7, 2025
**Feature**: Visual cart management with shop breakdown, ROI verification, and threshold configuration

---

## Overview

Complete visual cart management system that provides:

1. **Shop Breakdown Display** - See items and totals per Mandarake shop
2. **Threshold Status** - Visual indicators for shops below/above thresholds
3. **ROI Verification** - Verify cart profitability before checkout
4. **Threshold Configuration** - Customize min/max values per shop
5. **Cart Actions** - Refresh, verify, configure, open in browser

---

## Architecture

### New Files Created

```
gui/
├── cart_display.py (442 lines)
│   └── CartDisplayFrame - Main cart overview UI
│
├── cart_roi_dialog.py (365 lines)
│   └── CartROIDialog - ROI verification interface
│
└── cart_threshold_dialog.py (311 lines)
    └── CartThresholdDialog - Threshold configuration

Total: 1,118 lines of new UI code
```

### Integration

```
gui/alert_tab.py
└── initialize_cart_ui()
    ├── Quick Actions Frame (top right)
    │   ├── Connection status
    │   ├── "Add Yays to Cart" button
    │   └── "📊 Cart Overview" button (toggle)
    └── CartDisplayFrame (expandable section)
        ├── Action buttons row
        ├── Shop breakdown treeview
        ├── Summary labels
        ├── Warnings section
        └── Threshold display
```

---

## User Interface

### Quick Actions (Always Visible)

```
┌─ Cart Quick Actions: ─────────────────────────────────┐
│  [✓ Connected]  [Add Yays to Cart]  [📊 Cart Overview]│
└────────────────────────────────────────────────────────┘
```

### Cart Overview (Toggleable)

Click "📊 Cart Overview" to expand:

```
┌─ Cart Overview ───────────────────────────────────────────────┐
│                                                                 │
│  [🔄 Refresh] [🔍 Verify ROI] [⚙️ Configure] [🌐 Open Browser]│
│                                                                 │
│  ┌─ Shop Breakdown ────────────────────────────────────────┐  │
│  │ Shop       Items  Total(¥)  Total($)   Status          │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ SAHRA      17     ¥25,800   $172.50    ✅ Ready        │  │
│  │ Kyoto      11     ¥21,600   $144.00    ✅ Ready        │  │
│  │ Sapporo    8      ¥19,000   $126.67    ✅ Ready        │  │
│  │ Nakano     5      ¥11,000   $73.33     ✅ Ready        │  │
│  │ Shibuya    5      ¥9,300    $62.00     ✅ Ready        │  │
│  │ Utsunomiya 3      ¥4,200    $28.00     ⚠️ Below Min    │  │
│  │ Kokura     4      ¥2,100    $14.00     ⚠️ Below Min    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Total Cart: 53 items, ¥93,000 ($620.00)                      │
│                                                                 │
│  ┌─ ⚠️ Warnings ─────────────────────────────────────────┐  │
│  │ • Utsunomiya cart below minimum (¥4,200 < ¥5,000,    │  │
│  │   need ¥800 more)                                      │  │
│  │ • Kokura cart below minimum (¥2,100 < ¥5,000,        │  │
│  │   need ¥2,900 more)                                    │  │
│  │ • Cart not verified in 48 hours - recommend ROI check │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Thresholds: Min ¥5,000 | Max ¥50,000 | Max 20 items per shop │
└─────────────────────────────────────────────────────────────────┘
```

### Color Coding

- **Green background** (✅ Ready) - Shop above minimum, below maximum
- **Yellow background** (⚠️ Below Min) - Shop below minimum threshold
- **Red background** (🔴 Over Max/Too Many Items) - Shop exceeds limits

---

## Features

### 1. Shop Breakdown Display

**File**: `gui/cart_display.py:CartDisplayFrame`

**Data Shown**:
- Shop name (from MANDARAKE_STORES mapping)
- Item count
- Total value in ¥ and $ (auto-converted using exchange rate)
- Status indicator with threshold check

**Sorting**: Shops sorted by total value (descending)

**Auto-refresh**: Refreshes when toggled or manually via "🔄 Refresh" button

### 2. Threshold Status Indicators

**Status Types**:

| Status | Display | Condition | Background |
|--------|---------|-----------|----------|
| Ready | ✅ Ready | Min ≤ Total ≤ Max, Items ≤ Max | Green (#d4edda) |
| Below Min | ⚠️ Below Min (¥X short) | Total < Min | Yellow (#fff3cd) |
| Over Max | 🔴 Over Max | Total > Max | Red (#f8d7da) |
| Too Many Items | 🔴 Too Many Items (X/Max) | Items > Max | Red (#f8d7da) |

**Default Thresholds**:
- Min cart value: ¥5,000 per shop
- Max cart value: ¥50,000 per shop
- Max items: 20 per shop

### 3. ROI Verification

**File**: `gui/cart_roi_dialog.py:CartROIDialog`

**Purpose**: Re-verify cart profitability before checkout (prices may have changed since initial scrape)

**Verification Methods**:

1. **Hybrid** (Recommended) - Text + Image comparison
   - Searches eBay by keyword
   - Filters results by image similarity
   - Most accurate, moderate speed

2. **Text Only** (Fast) - Keyword matching only
   - Quick searches
   - May match wrong items
   - Use for rough estimates

3. **Image Only** (Slow, Accurate) - Visual comparison only
   - Downloads and compares images
   - Highest accuracy
   - Takes longer (2-3 sec per item)

**Options**:
- Min Similarity %: 50-95% (default 70%)
- RANSAC toggle: Enable geometric verification (slower, more accurate)

**Results Display**:

```
┌─ ROI Verification Results ─────────────────────────────┐
│                                                          │
│  Total Cost:     ¥93,000 ($620.00 USD)                 │
│  Est. Revenue:   $920.00 USD (eBay average)            │
│  Profit:         $300.00 USD                           │
│  ROI:            48.4%                                  │
│                                                          │
│  Items Verified: 51                                     │
│  No Match Found: 2                                      │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Item                Cost    eBay   Profit  ROI  │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ Yura Kano Photo... ¥2,400  $29.99  $13.87  85% │   │
│  │ Minamo DVD Set     ¥1,800  $24.95  $12.95 103% │   │
│  │ Norio Photobook    ¥3,500  $38.00  $14.67  61% │   │
│  │ ...                                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  [📋 Copy Summary] [🗑️ Remove Low ROI] [✓ Close]      │
└──────────────────────────────────────────────────────────┘
```

**Color Coding**:
- **Green** (ROI ≥ 30%) - Excellent profit
- **Yellow** (15% ≤ ROI < 30%) - Acceptable profit
- **Red** (ROI < 15%) - Poor profit margin
- **Gray** (No match) - Could not verify

**Actions**:
- **Copy Summary** - Copy results to clipboard
- **Remove Low ROI Items** - Remove items below threshold (coming soon)
- **Close** - Save verification and close dialog

### 4. Threshold Configuration

**File**: `gui/cart_threshold_dialog.py:CartThresholdDialog`

**Purpose**: Customize cart thresholds per shop or globally

**Global Defaults Section**:
```
┌─ Global Defaults ────────────────────────┐
│  Min Cart Value:  [5000] ¥               │
│  Max Cart Value:  [50000] ¥              │
│  Max Items:       [20]                   │
│  [Apply Defaults to All]                 │
└──────────────────────────────────────────┘
```

**Per-Shop Configuration**:
```
┌─ Per-Shop Configuration ─────────────────────────────┐
│  Shop          Min(¥)    Max(¥)    Max Items  Enabled│
│  ────────────────────────────────────────────────────│
│  Nakano        [5000]    [50000]   [20]       [✓]   │
│  Shibuya       [5000]    [50000]   [20]       [✓]   │
│  SAHRA         [5000]    [50000]   [20]       [✓]   │
│  Grandchaos    [10000]   [75000]   [30]       [✓]   │
│  ...                                                  │
└───────────────────────────────────────────────────────┘
```

**Features**:
- **Scrollable list** - All Mandarake shops shown
- **Individual control** - Set different thresholds per shop
- **Enable/disable** - Turn off threshold checking for specific shops
- **Bulk apply** - Apply global defaults to all shops
- **Reset** - Reset all to factory defaults

**Persistence**: Saved to `cart_storage.db` (SQLite)

### 5. Cart Actions

**🔄 Refresh Cart**
- Fetches current cart from Mandarake
- Updates shop breakdown
- Recalculates thresholds
- Updates warnings

**🔍 Verify Cart ROI**
- Opens ROI verification dialog
- Runs eBay comparison on all cart items
- Shows profit analysis
- Saves verification to database

**⚙️ Configure Thresholds**
- Opens threshold configuration dialog
- Modify min/max values per shop
- Enable/disable threshold checking

**🌐 Open Cart in Browser**
- Opens Mandarake cart page in default browser
- URL: `https://order.mandarake.co.jp/order/cartList/`
- Useful for manual checkout

---

## Workflows

### Workflow 1: Building Carts to Threshold

**Goal**: Build cart per shop until minimum threshold reached

1. **Mark items as "Yay"** in Alert tab
2. **Click "📊 Cart Overview"** to expand cart display
3. **Click "Add Yays to Cart"**
   - System adds items to Mandarake cart
   - Updates alert states (Yay → Purchased)
4. **Review shop breakdown**
   - ✅ Green shops are ready for checkout
   - ⚠️ Yellow shops need more items
5. **Continue adding items** until all shops are green
6. **Click "🌐 Open Cart in Browser"** to checkout

### Workflow 2: ROI Verification Before Checkout

**Goal**: Ensure profitability hasn't degraded before purchasing

1. **Cart is built** (53 items, ¥93,000)
2. **Click "🔍 Verify Cart ROI"**
3. **Select verification method** (Hybrid recommended)
4. **Click "🔍 Start Verification"**
   - Progress bar shows verification status
   - "Verifying item 15 of 53..."
5. **Review results**
   - Overall ROI: 48.4% ✅
   - Items flagged: 2 items dropped below 15% ROI
6. **Options**:
   - **Proceed anyway** - Close dialog
   - **Remove low ROI items** - Remove flagged items from cart
   - **Cancel** - Cancel checkout, review manually

### Workflow 3: Custom Threshold Configuration

**Goal**: Set higher minimums for specific shops

1. **Click "⚙️ Configure Thresholds"**
2. **Set global defaults** (if desired)
   - Min: ¥10,000
   - Max: ¥100,000
   - Items: 30
3. **Click "Apply Defaults to All"** (or configure individually)
4. **Override for specific shops**:
   - Grandchaos: Min ¥15,000 (higher due to shipping)
   - Nakano: Min ¥3,000 (lower due to cheap items)
5. **Click "💾 Save"**
6. **Cart display updates** with new thresholds

---

## Implementation Details

### Data Flow

```
User clicks "📊 Cart Overview"
    ↓
alert_tab._toggle_cart_display()
    ↓
cart_display.refresh_display()
    ├── cart_api.get_cart_items() - Fetch from Mandarake
    ├── _calculate_shop_breakdown() - Group by shop, calculate totals
    ├── _update_shop_tree() - Display in treeview
    ├── _update_summary() - Update total labels
    └── _update_warnings() - Show threshold warnings
```

### Shop Breakdown Calculation

**Code**: `gui/cart_display.py:_calculate_shop_breakdown()`

```python
def _calculate_shop_breakdown(self, cart_items):
    breakdown = {}

    for item in cart_items:
        shop_code = item['shop_code']
        price_jpy = parse_price(item['price'])
        price_usd = price_jpy / exchange_rate

        breakdown[shop_code]['items'] += 1
        breakdown[shop_code]['total_jpy'] += price_jpy
        breakdown[shop_code]['total_usd'] += price_usd

        # Calculate status
        if total < min_threshold:
            status = 'below'
        elif total > max_threshold:
            status = 'over'
        else:
            status = 'ready'

    return breakdown
```

### Warning Generation

**Code**: `gui/cart_display.py:_update_warnings()`

**Warning Types**:
1. **Shop below minimum** - "Shop X cart below minimum (¥X < ¥Y, need ¥Z more)"
2. **Shop exceeds maximum** - "Shop X cart exceeds maximum (¥X > ¥Y)"
3. **Too many items** - "Shop X has too many items (X > Y)"
4. **Verification stale** - "Cart not verified in X hours - recommend ROI re-check"
5. **Never verified** - "Cart has never been ROI verified"

**Display Logic**:
- If warnings exist: Show warnings frame with yellow background
- If no warnings: Show "No warnings - cart looks good!" and collapse frame

### Threshold Storage

**Database**: `cart_storage.db` (SQLite)

**Table**: `shop_thresholds`

```sql
CREATE TABLE shop_thresholds (
    shop_code TEXT PRIMARY KEY,
    min_cart_value INTEGER DEFAULT 5000,
    max_cart_value INTEGER DEFAULT 50000,
    max_items INTEGER DEFAULT 20,
    enabled BOOLEAN DEFAULT 1
);
```

**Methods**:
- `cart_storage.get_shop_threshold(shop_code)` - Get threshold for shop
- `cart_storage.set_shop_threshold(...)` - Update threshold
- `cart_storage.get_all_shop_thresholds()` - Get all thresholds

### ROI Verification Storage

**Table**: `cart_verifications`

```sql
CREATE TABLE cart_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verified_at TIMESTAMP,
    total_items INTEGER,
    total_value_jpy INTEGER,
    total_roi_percent REAL,
    items_flagged INTEGER,
    details TEXT  -- JSON with full results
);
```

**Purpose**: Track verification history, show staleness warnings

---

## API Reference

### CartDisplayFrame

**Constructor**:
```python
CartDisplayFrame(parent, cart_manager, **kwargs)
```

**Methods**:

#### `refresh_display()`
Refresh cart display with current Mandarake cart data.

**Returns**: None
**Side effects**: Updates shop tree, summary, warnings

#### `_calculate_shop_breakdown(cart_items)`
Calculate shop-level totals and threshold status.

**Parameters**:
- `cart_items` (List[Dict]): Cart items from Mandarake API

**Returns**:
```python
{
    'nakano': {
        'items': 5,
        'total_jpy': 12500,
        'total_usd': 83.33,
        'status': 'ready',
        'status_text': '✅ Ready',
        'min_threshold': 5000,
        'max_threshold': 50000
    },
    ...
    'totals': {
        'items': 53,
        'total_jpy': 93000,
        'total_usd': 620.00
    }
}
```

### CartROIDialog

**Constructor**:
```python
CartROIDialog(parent, cart_manager)
```

**Methods**:

#### `_start_verification()`
Start ROI verification process.

**Uses**:
- `cart_manager.verify_cart_roi(method, exchange_rate, min_similarity, use_ransac, progress_callback)`

**Returns**: None
**Side effects**: Updates UI with results, saves to database

### CartThresholdDialog

**Constructor**:
```python
CartThresholdDialog(parent, cart_storage)
```

**Methods**:

#### `_save_thresholds()`
Save threshold configuration to database.

**Returns**: None
**Side effects**: Updates `shop_thresholds` table

#### `_apply_defaults_to_all()`
Apply global defaults to all shops.

**Returns**: None
**Side effects**: Updates all UI fields

---

## Testing

### Manual Testing Steps

1. **Connect to cart**:
   ```bash
   python gui_config.py
   ```
   - Go to Review/Alerts tab
   - Connect to Mandarake cart (paste cart URL)

2. **View cart overview**:
   - Click "📊 Cart Overview"
   - Verify shop breakdown shows correctly
   - Check color coding matches thresholds

3. **Test ROI verification**:
   - Click "🔍 Verify Cart ROI"
   - Select "Hybrid" method
   - Click "🔍 Start Verification"
   - Verify progress bar works
   - Review results display

4. **Test threshold configuration**:
   - Click "⚙️ Configure Thresholds"
   - Change some values
   - Click "💾 Save"
   - Refresh cart display
   - Verify new thresholds applied

5. **Test refresh**:
   - Add items to cart via "Add Yays to Cart"
   - Click "🔄 Refresh Cart"
   - Verify cart display updates

### Edge Cases

**Empty cart**:
- Should show "Total Cart: 0 items, ¥0 ($0)"
- No warnings

**Not connected**:
- Should show "Not connected to Mandarake cart"
- Warning: "Connect to Mandarake cart to view cart details"

**All shops below minimum**:
- All rows should be yellow
- Multiple warnings listed

**Verification never run**:
- Warning: "Cart has never been ROI verified"

---

## Future Enhancements

### Potential Improvements

1. **Remove from Cart**
   - Implement "Remove Low ROI Items" button
   - Requires Mandarake remove-from-cart API endpoint

2. **Cart History**
   - Track cart changes over time
   - Show graph of cart value growth

3. **Smart Recommendations**
   - "Add 2 more items to reach Shibuya minimum"
   - "Consider removing Item X - ROI only 8%"

4. **Export Cart**
   - Export cart to CSV/Excel
   - Include ROI data, thresholds

5. **Shipping Estimates**
   - Calculate shipping costs per shop
   - Show total cost including shipping
   - Factor into ROI calculations

6. **Auto-refresh**
   - Refresh cart automatically every 5 minutes
   - Show last refresh time

---

## Related Documentation

- **[CART_SYSTEM_COMPLETE.md](CART_SYSTEM_COMPLETE.md)** - Cart API and backend
- **[CART_MANAGEMENT_COMPLETE.md](CART_MANAGEMENT_COMPLETE.md)** - Add-to-cart workflow
- **[ALERT_TAB_COMPLETE.md](ALERT_TAB_COMPLETE.md)** - Alert system integration
- **[GUI_MODULARIZATION_COMPLETE.md](GUI_MODULARIZATION_COMPLETE.md)** - GUI architecture

---

## Changelog

### October 7, 2025
- ✅ Created CartDisplayFrame with shop breakdown
- ✅ Implemented threshold status indicators
- ✅ Created ROI verification dialog
- ✅ Created threshold configuration dialog
- ✅ Integrated into Alert tab as toggleable section
- ✅ Added cart action buttons (refresh, verify, configure, open)
- ✅ Documented complete system

---

**Implementation Status**: ✅ COMPLETE
**Lines of Code**: 1,118 lines (3 new files)
**Documentation Status**: ✅ Complete with workflows and API reference
