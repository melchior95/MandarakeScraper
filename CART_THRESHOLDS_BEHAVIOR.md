# Cart Threshold Behavior - Complete Guide

**Date**: October 7, 2025
**Status**: ✅ Fully Implemented

---

## Overview

This document explains **exactly what happens** when min/max cart thresholds are reached.

---

## Threshold Types

### 1. Minimum Cart Value (per shop)
**Default**: ¥5,000
**Purpose**: Ensure cart value is high enough to justify shipping costs
**Behavior**: **WARNING ONLY** (doesn't block adding items)

### 2. Maximum Cart Value (per shop)
**Default**: ¥50,000
**Purpose**: Prevent overspending, stay within budget
**Behavior**: **BLOCKS adding items** (requires confirmation to proceed)

### 3. Maximum Items (per shop)
**Default**: 20 items
**Purpose**: Prevent oversized orders
**Behavior**: **BLOCKS adding items** (requires confirmation to proceed)

---

## What Happens When Thresholds Are Reached

### Scenario 1: Adding Items - Maximum Value Exceeded

**Current cart**: Nakano shop has ¥45,000 worth of items
**Trying to add**: 3 items worth ¥8,000
**Maximum threshold**: ¥50,000

**What happens**:

1. User clicks "Add Yays to Cart"
2. System calculates: ¥45,000 + ¥8,000 = ¥53,000
3. Detects: ¥53,000 > ¥50,000 (over by ¥3,000)
4. **STOPS before adding anything**
5. Shows warning dialog:

```
⚠️ THRESHOLD VIOLATIONS DETECTED

Adding these items will exceed the following thresholds:

• Nakano:
  Current: ¥45,000
  Adding: ¥8,000 (3 items)
  New Total: ¥53,000
  Maximum: ¥50,000
  Over by: ¥3,000

Do you want to add them anyway?

[Yes] [No]
```

**User options**:
- **Click "Yes"** → Items are added anyway, threshold is violated
- **Click "No"** → Items are NOT added, operation canceled

### Scenario 2: Adding Items - Too Many Items

**Current cart**: Shibuya shop has 18 items
**Trying to add**: 5 items
**Maximum items**: 20

**What happens**:

1. User clicks "Add Yays to Cart"
2. System calculates: 18 + 5 = 23 items
3. Detects: 23 > 20 (over by 3 items)
4. **STOPS before adding anything**
5. Shows warning dialog:

```
⚠️ THRESHOLD VIOLATIONS DETECTED

Adding these items will exceed the following thresholds:

• Shibuya:
  Current: 18 items
  Adding: 5 items
  New Total: 23 items
  Maximum: 20 items
  Over by: 3 items

Do you want to add them anyway?

[Yes] [No]
```

**User options**:
- **Click "Yes"** → Items are added anyway, threshold is violated
- **Click "No"** → Items are NOT added, operation canceled

### Scenario 3: Cart Already Below Minimum (Visual Warning Only)

**Current cart**: Utsunomiya shop has ¥3,200
**Minimum threshold**: ¥5,000

**What happens**:

1. User opens "📊 Cart Overview"
2. Shop is displayed with **yellow background**
3. Warning message shown:

```
⚠️ Warnings:
• Utsunomiya cart below minimum (¥3,200 < ¥5,000, need ¥800 more)
```

4. **No blocking** - user can still:
   - Add more items to reach minimum
   - Proceed to checkout anyway
   - Remove items

**Note**: Below minimum does NOT prevent adding items - it only warns you that the cart isn't optimized for shipping.

### Scenario 4: Multiple Shops with Violations

**Trying to add items to**:
- Nakano: Would exceed max value (¥53,000 > ¥50,000)
- Shibuya: Would exceed max items (23 > 20)

**What happens**:

Shows combined warning:

```
⚠️ THRESHOLD VIOLATIONS DETECTED

Adding these items will exceed the following thresholds:

• Nakano:
  Current: ¥45,000
  Adding: ¥8,000 (3 items)
  New Total: ¥53,000
  Maximum: ¥50,000
  Over by: ¥3,000

• Shibuya:
  Current: 18 items
  Adding: 5 items
  New Total: 23 items
  Maximum: 20 items
  Over by: 3 items

Do you want to add them anyway?

[Yes] [No]
```

**Behavior**: All or nothing - clicking "Yes" adds ALL items to ALL shops (including violations)

---

## Threshold Enforcement Summary

| Threshold Type | When Checked | Enforcement | Can Override? |
|---------------|--------------|-------------|---------------|
| **Min Value** | When viewing cart | Warning only | N/A (doesn't block) |
| **Max Value** | Before adding items | **Blocks** with dialog | ✅ Yes ("Add anyway") |
| **Max Items** | Before adding items | **Blocks** with dialog | ✅ Yes ("Add anyway") |

---

## Technical Implementation

### Flow Diagram

```
User clicks "Add Yays to Cart"
    ↓
Confirm: "Add X Yay items?"
    ↓
cart_manager.add_yays_to_cart(force_below_threshold=False)
    ↓
_check_add_thresholds(items_to_add)
    ├── Fetches current cart from Mandarake
    ├── Calculates current totals per shop
    ├── Calculates new totals after adding
    └── Checks against thresholds
        ↓
        ├── No violations → Proceed to add items
        │
        └── Violations detected → Return threshold_warnings
                ↓
            Show violation dialog
                ↓
                ├── User clicks "No" → Cancel, don't add
                │
                └── User clicks "Yes" →
                    cart_manager.add_yays_to_cart(force_below_threshold=True)
                        ↓
                    Adds items (bypassing threshold checks)
```

### Code Location

**Threshold Check**: `gui/cart_manager.py:323-422`
```python
def _check_add_thresholds(self, items_to_add):
    """Check if adding items will violate thresholds"""
    warnings = {}

    # Get current cart state
    current_cart = self.cart_api.get_cart_items()

    # Calculate current + new totals
    for shop_code, items in items_to_add.items():
        new_total = current_total + value_to_add
        new_count = current_count + items_to_add_count

        # Check violations
        if new_total > max_val:
            warnings[shop_code] = {...}
        elif new_count > max_items:
            warnings[shop_code] = {...}

    return warnings
```

**Add Items Logic**: `gui/cart_manager.py:166-178`
```python
# Check thresholds (if not forcing)
if not force_below_threshold:
    threshold_warnings = self._check_add_thresholds(by_shop)
    if threshold_warnings:
        # Return warnings without adding items
        return {
            'success': False,
            'error': 'Threshold violations detected',
            'threshold_warnings': threshold_warnings
        }
```

**Warning Dialog**: `gui/alert_tab.py:1084-1138`
```python
def _show_threshold_violation_dialog(self, warnings):
    """Show threshold violation dialog with detailed breakdown"""
    # Build violation messages
    violation_messages = []
    for shop_code, violation in warnings.items():
        if violation_type == 'over_max':
            msg = f"Over by: ¥{violation['excess']:,}"
        elif violation_type == 'too_many_items':
            msg = f"Over by: {violation['excess']} items"

    # Show yes/no dialog
    response = messagebox.askyesno("Threshold Exceeded", warning_text)

    if response:
        # Force add anyway
        self._add_yays_forcing_thresholds()
```

---

## Configuration

### Viewing Current Thresholds

Click "📊 Cart Overview" → Look at bottom:
```
Thresholds: Min ¥5,000 | Max ¥50,000 | Max 20 items per shop
```

### Changing Thresholds

1. Click "⚙️ Configure Thresholds"
2. Set global defaults or per-shop values
3. Click "💾 Save"

**Example Custom Configuration**:
- Nakano: Min ¥3,000, Max ¥75,000, Max 30 items
- Shibuya: Min ¥5,000, Max ¥50,000, Max 20 items
- Grandchaos: Min ¥10,000, Max ¥100,000, Max 50 items

### Disabling Thresholds

In threshold configuration:
- **Uncheck "Enabled"** checkbox for a shop
- Thresholds for that shop will be ignored

**Note**: Global "disable all thresholds" feature not yet implemented. Workaround: Set max values to 999999.

---

## Use Cases

### Use Case 1: Budget Control

**Goal**: Never spend more than ¥50,000 per shop

**Setup**:
- Set Max Cart Value: ¥50,000
- Leave Min Cart Value: ¥5,000
- Max Items: 20

**Behavior**:
- System prevents adding items that would exceed ¥50,000
- User must explicitly confirm to exceed budget
- Helps avoid overspending

### Use Case 2: Shipping Optimization

**Goal**: Only checkout shops with ¥5,000+ to optimize shipping costs

**Setup**:
- Set Min Cart Value: ¥5,000
- Max Cart Value: ¥100,000 (high enough to not block)

**Behavior**:
- Yellow warning if cart < ¥5,000
- Can still add items (no blocking)
- Reminder to add more items before checkout

### Use Case 3: Avoiding Oversized Orders

**Goal**: Keep orders manageable (≤20 items per shop)

**Setup**:
- Max Items: 20
- Min/Max values: Default

**Behavior**:
- System prevents adding 21st item
- User must confirm to exceed
- Prevents overwhelming single shops

### Use Case 4: No Limits (Disable Thresholds)

**Goal**: Add items freely without any restrictions

**Setup**:
- Go to "⚙️ Configure Thresholds"
- For each shop, uncheck "Enabled"
- OR set very high values (Min: 0, Max: 999999, Items: 999)

**Behavior**:
- No blocking dialogs
- No warnings (except visual "below min")
- Complete freedom

---

## Edge Cases

### What if threshold is disabled for a shop?

**Behavior**: No checks performed, items added freely

### What if adding items to multiple shops, only one violates threshold?

**Behavior**:
- Entire operation blocked
- Violation dialog shows ALL shops with violations
- User must approve ALL violations to proceed
- Cannot selectively add to some shops

**Workaround**: Manually mark only non-violating items as "Yay"

### What if cart already exceeds threshold before adding?

**Example**: Cart already has ¥60,000, max is ¥50,000

**Behavior**:
- Adding MORE items will trigger warning
- System calculates NEW total vs. threshold
- Even adding ¥1 will show dialog (¥60,001 > ¥50,000)

### What if threshold is changed after items are in cart?

**Example**: Cart has 25 items, then max is changed from 30 → 20

**Behavior**:
- Cart display shows red background (over limit)
- Can still checkout (doesn't force removal)
- Cannot add MORE items without confirmation
- User must manually remove items to get below threshold

---

## Future Enhancements

### Potential Improvements

1. **Selective Shop Add**
   - When multiple shops violate, allow adding to non-violating shops only
   - "Add to ready shops, skip others"

2. **Smart Recommendations**
   - "Remove 1 item from Nakano to stay under ¥50,000"
   - "Add ¥800 more to Utsunomiya to reach minimum"

3. **Threshold Templates**
   - "Conservative" (Min: ¥10,000, Max: ¥30,000)
   - "Aggressive" (Min: ¥3,000, Max: ¥100,000)
   - "Unlimited" (No limits)

4. **Per-Item Threshold Override**
   - Mark specific items as "Must Buy" to bypass thresholds
   - Useful for rare/limited items

5. **Shipping Cost Integration**
   - Calculate actual shipping cost per shop
   - Show ROI including shipping
   - Smart threshold based on shipping breakpoints

---

## Related Documentation

- **[CART_DISPLAY_COMPLETE.md](CART_DISPLAY_COMPLETE.md)** - Visual cart display
- **[CART_MANAGEMENT_COMPLETE.md](CART_MANAGEMENT_COMPLETE.md)** - Cart operations
- **[CART_CONNECTION_UPDATE.md](CART_CONNECTION_UPDATE.md)** - Connection workflow

---

## Summary

**Minimum Threshold**:
- ⚠️ Visual warning only
- Doesn't block adding items
- Reminder to optimize cart for shipping

**Maximum Value/Items**:
- 🛑 Blocks adding items
- Shows detailed violation breakdown
- Requires user confirmation to proceed
- Can be overridden ("Add anyway")

**Philosophy**: Help users stay within limits while still allowing flexibility to exceed when needed.

---

**Last Updated**: October 7, 2025
**Status**: ✅ Fully documented and implemented
