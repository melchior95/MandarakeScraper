# Chrome Extension Update Log

## October 10, 2025 - Enhanced Selector Robustness

### Problem
eBay changed their HTML structure from `.s-item` to `.s-card` in 2025, breaking the extension's ability to find listing titles and prices.

### Solution
Implemented **multi-strategy selector fallback system** that tries 7+ different selectors for titles and 6+ for prices.

### Changes Made

#### 1. Enhanced Title Detection (`content.js:127-135`)
Now tries selectors in this order:
1. `.s-item__title` - Old eBay layout (pre-2025)
2. `span[role="heading"]` - **NEW layout, most common**
3. `h3` - Generic heading fallback
4. `[class*="title"]` - Wildcard class match
5. `.s-card__title` - Card title variant
6. `a[role="heading"]` - Link with heading role
7. `[data-testid*="title"]` - Test ID attribute

#### 2. Enhanced Price Detection (`content.js:137-144`)
Now tries selectors in this order:
1. `.s-item__price` - Old eBay layout
2. `[class*="s-item__price"]` - Price variants
3. `[class*="price"][class*="display"]` - Display price combos
4. `span[aria-label*="rice"]` - Accessibility label (P might be trimmed)
5. `[class*="POSITIVE"]` - eBay color classes for prices
6. `[data-testid*="price"]` - Test ID attribute

#### 3. Improved Debug Logging (`content.js:146-199`)
Added comprehensive debugging that shows:
- Whether title/price were found and their content
- All links with their roles and test IDs
- All spans with roles, aria-labels, and test IDs
- All elements with `role="heading"`
- Price-like text patterns found in listing

### How to Update

1. **Reload Extension:**
   ```
   chrome://extensions/ → Find "Mandarake Price Checker" → Click reload icon
   ```

2. **Hard Refresh eBay:**
   ```
   Go to eBay search page → Press Ctrl+Shift+R (or Cmd+Shift+R on Mac)
   ```

3. **Check Console:**
   ```
   Press F12 → Console tab → Look for "Mandarake Extension: Found X listings"
   ```

### Expected Behavior

**Before Update:**
```
Mandarake Extension: Found 73 listings
Could not find title or price in listing (×73)
```

**After Update:**
```
Mandarake Extension: Found 73 listings
[If selectors work: Buttons appear on listings]
[If selectors fail: Debug output shows detailed element structure]
```

### Debug Output Example

If selectors still fail, you'll see detailed debug for first 3 listings:

```
=== DEBUG LISTING #1 ===
Listing classes: s-card s-card--vertical
Title found: true "Pokemon Pikachu Card PSA 10"
Price found: true "$42.00"

Links found: 3
  Link 1 [s-card__link]: Pokemon Pikachu Card PSA 10
    → role="heading" data-testid="null"

Spans found: 15
  Span 1 [s-card__title]: "Pokemon Pikachu Card PSA 10"
    → role="heading"
  Span 2 [s-card__price]: "$42.00"
    → data-testid="price-display"

Elements with role="heading": 1
  Heading 1 [SPAN.s-card__title]: Pokemon Pikachu Card PSA 10
=== END DEBUG ===
```

### Testing

1. Go to: https://www.ebay.com/sch/i.html?_nkw=pokemon+card
2. Open Console (F12)
3. Check for messages:
   - ✅ "Mandarake Extension: Found X listings" (X > 0)
   - ✅ "Mutation observer attached to:"
   - ✅ Buttons appear on listings OR debug output shows element structure

### If Still Not Working

If buttons still don't appear after this update:

1. Copy the debug output from Console
2. Share the output - it will show us the exact element structure eBay is using
3. We'll create a targeted selector based on the actual HTML

### Related Files
- `content.js` - Main extension logic
- `TROUBLESHOOTING.md` - Complete troubleshooting guide
- `README.md` - Installation and usage guide

---

**Previous Updates:**
- Initial release - October 10, 2025
- Added lazy loading approach
- Added stock status checking
- Added profit calculation with color coding
