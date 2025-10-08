# Mandarake Cart Management System - Design Document

## Overview

Smart cart management system that tracks items per shop, monitors cart thresholds, and verifies ROI before checkout.

**Key Insight**: Mandarake has separate carts per shop, and shipping is calculated per-shop. Optimizing cart value per shop minimizes shipping costs and maximizes ROI.

---

## Features

### 1. Shop-Level Cart Tracking
- Track cart totals per shop (Nakano, Shibuya, Sahra, etc.)
- Monitor item counts and total value per shop
- Visual breakdown in Alert tab showing each shop's cart

### 2. Threshold Management
- **Minimum cart value** - Don't checkout until shop cart reaches threshold (e.g., ¥5000)
- **Maximum cart value** - Warning when approaching spending limit (e.g., ¥50000)
- **Item count limits** - Max items per shop cart (avoid oversized orders)
- **Custom thresholds per shop** - Different minimums for different shops

### 3. ROI Verification (Pre-Checkout)
- **"Verify Cart ROI"** button - Runs eBay Compare All on current cart items
- Re-checks current eBay sold prices (prices may have changed since initial scrape)
- Calculates aggregate profit margin for entire cart
- Flags items with degraded ROI (price dropped on eBay)
- **Smart recommendations**: "Remove low-ROI items to improve margin"

### 4. Cart Operations
- **Add to Cart** - Add selected "Yay" items to Mandarake cart
- **Remove from Cart** - Remove items if ROI verification fails
- **Open Cart in Browser** - Launch browser for manual checkout
- **Cart Sync** - Fetch current cart state from Mandarake

---

## Architecture

### New Files

```
gui/
├── cart_manager.py              # Main cart management logic
├── cart_tab.py                  # UI for cart view (or section in alert_tab)
├── cart_storage.py              # SQLite cart state tracking
└── cart_roi_verifier.py         # ROI verification before checkout

scrapers/
└── mandarake_cart_api.py        # Mandarake cart API operations
```

### Database Schema (SQLite)

```sql
-- Cart items table
CREATE TABLE cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER,  -- Links to alerts.db
    product_id TEXT,
    title TEXT,
    price_jpy INTEGER,
    shop_code TEXT,
    shop_name TEXT,
    image_url TEXT,
    product_url TEXT,
    added_to_cart_at TIMESTAMP,
    verified_roi REAL,  -- Last verified profit %
    verified_at TIMESTAMP,
    in_mandarake_cart BOOLEAN DEFAULT 0,  -- Confirmed in actual cart
    FOREIGN KEY (alert_id) REFERENCES alerts(id)
);

-- Shop cart thresholds
CREATE TABLE shop_thresholds (
    shop_code TEXT PRIMARY KEY,
    min_cart_value INTEGER DEFAULT 5000,  -- ¥5000 minimum
    max_cart_value INTEGER DEFAULT 50000, -- ¥50000 maximum
    max_items INTEGER DEFAULT 20,
    enabled BOOLEAN DEFAULT 1
);

-- Cart verification history
CREATE TABLE cart_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verified_at TIMESTAMP,
    total_items INTEGER,
    total_value_jpy INTEGER,
    total_roi_percent REAL,
    items_flagged INTEGER,  -- Items with degraded ROI
    details TEXT  -- JSON with per-item results
);
```

---

## UI Design

### Location: Alert Tab → New "Cart" Section

```
┌─ Cart Management ──────────────────────────────────────────────┐
│                                                                 │
│  [Add Yays to Cart] [Verify Cart ROI] [Open Cart in Browser]  │
│                                                                 │
│  ┌─ Shop Breakdown ─────────────────────────────────────┐     │
│  │                                                        │     │
│  │  📍 Nakano        Items: 8   Total: ¥12,500  [Ready] │     │
│  │  📍 Shibuya       Items: 3   Total: ¥3,200   [Below] │     │
│  │  📍 Sahra         Items: 12  Total: ¥18,900  [Ready] │     │
│  │  📍 Grandchaos    Items: 5   Total: ¥6,500   [Ready] │     │
│  │                                                        │     │
│  │  Total Cart: 28 items, ¥41,100 (~$275 USD)           │     │
│  │  Estimated ROI: 32% profit (based on last verification)│   │
│  │                                                        │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
│  ⚙️ Thresholds:                                                │
│  Min per shop: ¥5000  Max per shop: ¥50000  Max items: 20     │
│  [Configure Thresholds...]                                     │
│                                                                 │
│  ⚠️ Warnings:                                                  │
│  • Shibuya cart below minimum (¥3,200 < ¥5,000)               │
│  • Cart not verified in 24 hours - recommend re-check ROI      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Status Indicators
- **[Ready]** ✅ - Above minimum, below maximum
- **[Below]** ⚠️ - Below minimum threshold (orange)
- **[Over]** 🔴 - Exceeds maximum threshold (red)
- **[Verify]** 🔍 - Needs ROI verification

---

## Workflow Examples

### Workflow 1: Building Carts to Threshold

```
1. User marks items as "Yay" (currently 15 items across 4 shops)
2. Clicks "Add Yays to Cart"
3. System groups by shop:
   - Nakano: 6 items, ¥8,500
   - Shibuya: 2 items, ¥2,100
   - Sahra: 5 items, ¥6,200
   - Grandchaos: 2 items, ¥1,800
4. System shows warnings:
   ⚠️ Shibuya below minimum (¥2,100 < ¥5,000)
   ⚠️ Grandchaos below minimum (¥1,800 < ¥5,000)
5. User options:
   a) "Add anyway" - Proceed with low-value carts (higher shipping %)
   b) "Wait for more items" - Don't add to cart yet
   c) "Add only ready shops" - Add Nakano + Sahra only
```

### Workflow 2: ROI Verification Before Checkout

```
1. User has built carts to threshold:
   - Nakano: 8 items, ¥12,500
   - Sahra: 12 items, ¥18,900
   - Total: ¥31,400 (~$210 USD)

2. Clicks "Verify Cart ROI"

3. System runs eBay Compare All on all 20 items:
   - Searches eBay sold listings for each item
   - Compares current eBay prices vs. original scrape
   - Calculates profit margin per item
   - Shows aggregate ROI

4. Results displayed:
   ┌─ ROI Verification Results ────────────────────────┐
   │                                                    │
   │  Total Cost:     ¥31,400 ($210 USD)              │
   │  Est. Revenue:   $312 USD (eBay average)         │
   │  Profit:         $102 USD                        │
   │  ROI:            48.6%                           │
   │                                                    │
   │  ⚠️ 2 items flagged for review:                  │
   │  • "Item XYZ" - ROI dropped from 45% → 15%       │
   │  • "Item ABC" - No recent eBay sales found       │
   │                                                    │
   │  [Remove Flagged Items] [Proceed Anyway] [Cancel]│
   └────────────────────────────────────────────────────┘

5. User can:
   - Remove low-ROI items from cart
   - Proceed with current cart
   - Cancel and review manually
```

### Workflow 3: Automatic Threshold Monitoring

```
Background monitoring (runs every hour or on-demand):

1. Check each shop's cart value
2. If shop reaches threshold → Notification
   🔔 "Nakano cart reached ¥12,500 - ready for checkout!"
3. If shop exceeds max → Warning
   ⚠️ "Sahra cart exceeds ¥50,000 - consider splitting order"
4. Suggest ROI verification if cart unchanged for 24 hours
   💡 "Cart hasn't been verified in 24h - prices may have changed"
```

---

## Implementation Details

### 1. Cart Manager Core (`gui/cart_manager.py`)

```python
class CartManager:
    """Manages Mandarake cart operations and tracking"""

    def __init__(self, alert_manager, ebay_search_manager):
        self.alert_manager = alert_manager
        self.ebay_search_manager = ebay_search_manager
        self.cart_api = MandarakeCartAPI()
        self.storage = CartStorage()

    def add_alerts_to_cart(self, alert_ids: List[int],
                          force_below_threshold: bool = False):
        """
        Add alert items to Mandarake cart with threshold checking

        Args:
            alert_ids: Alert IDs to add (usually all "Yay" items)
            force_below_threshold: Add even if below minimum threshold

        Returns:
            dict: {
                'added': [...],
                'failed': [...],
                'warnings': [...]
            }
        """
        # 1. Group alerts by shop
        by_shop = self._group_by_shop(alert_ids)

        # 2. Check thresholds per shop
        warnings = []
        for shop_code, items in by_shop.items():
            total = sum(item['price_jpy'] for item in items)
            threshold = self.storage.get_shop_threshold(shop_code)

            if total < threshold['min_cart_value']:
                warnings.append({
                    'shop': shop_code,
                    'total': total,
                    'threshold': threshold['min_cart_value'],
                    'message': f"{shop_code} below minimum"
                })

        # 3. If warnings and not forced, return for user decision
        if warnings and not force_below_threshold:
            return {'warnings': warnings, 'proceed': False}

        # 4. Add items to cart via API
        results = {'added': [], 'failed': []}
        for shop_code, items in by_shop.items():
            for item in items:
                try:
                    success = self.cart_api.add_to_cart(
                        product_id=item['product_id'],
                        shop_code=shop_code
                    )
                    if success:
                        results['added'].append(item)
                        self.storage.mark_in_cart(item['alert_id'])
                    else:
                        results['failed'].append(item)
                except Exception as e:
                    results['failed'].append({**item, 'error': str(e)})

        return results

    def verify_cart_roi(self) -> dict:
        """
        Re-run eBay comparison on all cart items to verify ROI

        Returns:
            dict: {
                'total_cost_jpy': int,
                'total_cost_usd': float,
                'est_revenue_usd': float,
                'profit_usd': float,
                'roi_percent': float,
                'items': [...],
                'flagged_items': [...]  # Items with degraded ROI
            }
        """
        # 1. Get all items currently in cart
        cart_items = self.storage.get_cart_items()

        # 2. Run eBay search for each item
        flagged = []
        total_cost_jpy = 0
        total_revenue_usd = 0

        for item in cart_items:
            # Use existing eBay search functionality
            ebay_results = self.ebay_search_manager.search_and_compare(
                keyword=item['title'],
                category=item.get('category'),
                mandarake_image_url=item['image_url']
            )

            # Find best match
            if ebay_results:
                best_match = max(ebay_results, key=lambda x: x['similarity'])
                current_roi = self._calculate_roi(
                    item['price_jpy'],
                    best_match['ebay_price_usd']
                )

                # Compare to original ROI
                original_roi = item.get('verified_roi', 0)
                if current_roi < original_roi * 0.7:  # 30% degradation
                    flagged.append({
                        **item,
                        'original_roi': original_roi,
                        'current_roi': current_roi,
                        'degradation': original_roi - current_roi
                    })

                total_cost_jpy += item['price_jpy']
                total_revenue_usd += best_match['ebay_price_usd']

        # 3. Calculate aggregate metrics
        exchange_rate = self._get_exchange_rate()
        total_cost_usd = total_cost_jpy / exchange_rate
        profit_usd = total_revenue_usd - total_cost_usd
        roi_percent = (profit_usd / total_cost_usd) * 100

        # 4. Save verification record
        verification = {
            'verified_at': datetime.now(),
            'total_cost_jpy': total_cost_jpy,
            'total_cost_usd': total_cost_usd,
            'est_revenue_usd': total_revenue_usd,
            'profit_usd': profit_usd,
            'roi_percent': roi_percent,
            'items_flagged': len(flagged),
            'flagged_items': flagged
        }
        self.storage.save_verification(verification)

        return verification

    def get_shop_breakdown(self) -> dict:
        """
        Get current cart breakdown by shop

        Returns:
            dict: {
                'shop_code': {
                    'items': int,
                    'total_jpy': int,
                    'status': 'ready|below|over',
                    'threshold': {...}
                }
            }
        """
        cart_items = self.storage.get_cart_items()
        thresholds = self.storage.get_all_thresholds()

        breakdown = {}
        for shop_code in set(item['shop_code'] for item in cart_items):
            shop_items = [i for i in cart_items if i['shop_code'] == shop_code]
            total = sum(i['price_jpy'] for i in shop_items)
            threshold = thresholds.get(shop_code, {})

            # Determine status
            if total < threshold.get('min_cart_value', 0):
                status = 'below'
            elif total > threshold.get('max_cart_value', float('inf')):
                status = 'over'
            else:
                status = 'ready'

            breakdown[shop_code] = {
                'items': len(shop_items),
                'total_jpy': total,
                'status': status,
                'threshold': threshold
            }

        return breakdown
```

### 2. Mandarake Cart API (`scrapers/mandarake_cart_api.py`)

```python
class MandarakeCartAPI:
    """API wrapper for Mandarake cart operations"""

    def __init__(self, session_cookies: dict = None):
        self.session = requests.Session()
        self.base_url = "https://order.mandarake.co.jp"

        if session_cookies:
            self.session.cookies.update(session_cookies)

    def login(self, username: str, password: str) -> bool:
        """Login to Mandarake account"""
        # Implementation depends on Mandarake's login flow
        pass

    def add_to_cart(self, product_id: str, shop_code: str,
                   quantity: int = 1) -> bool:
        """
        Add item to cart

        Args:
            product_id: Mandarake product ID
            shop_code: Shop code (e.g., 'nkn' for Nakano)
            quantity: Quantity to add (default: 1)

        Returns:
            bool: True if added successfully
        """
        # POST to cart endpoint
        # Typical endpoint: /order/cart/add
        url = f"{self.base_url}/order/cart/add"
        data = {
            'productId': product_id,
            'shop': shop_code,
            'quantity': quantity
        }

        response = self.session.post(url, data=data)
        return response.status_code == 200

    def get_cart(self) -> dict:
        """
        Fetch current cart state from Mandarake

        Returns:
            dict: Cart data by shop
        """
        # GET cart page and parse
        url = f"{self.base_url}/order/cart"
        response = self.session.get(url)

        # Parse HTML to extract cart items
        # Return structured cart data
        pass

    def remove_from_cart(self, cart_item_id: str) -> bool:
        """Remove item from cart"""
        pass
```

### 3. Cart Storage (`gui/cart_storage.py`)

```python
class CartStorage:
    """SQLite storage for cart tracking"""

    def __init__(self, db_path: str = 'cart.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist"""
        # SQL schema from above
        pass

    def add_cart_item(self, alert_id: int, product_data: dict):
        """Add item to local cart tracking"""
        pass

    def mark_in_cart(self, alert_id: int, in_cart: bool = True):
        """Mark item as added to Mandarake cart"""
        pass

    def get_cart_items(self, shop_code: str = None) -> List[dict]:
        """Get all cart items, optionally filtered by shop"""
        pass

    def get_shop_threshold(self, shop_code: str) -> dict:
        """Get threshold settings for a shop"""
        pass

    def save_verification(self, verification_data: dict):
        """Save ROI verification results"""
        pass
```

---

## Configuration

### Threshold Settings UI

```
┌─ Configure Shop Thresholds ─────────────────────────────────┐
│                                                              │
│  Shop          Min Cart    Max Cart    Max Items   Enabled │
│  ──────────────────────────────────────────────────────────│
│  Nakano        ¥5,000      ¥50,000     20          ☑       │
│  Shibuya       ¥5,000      ¥50,000     20          ☑       │
│  Sahra         ¥10,000     ¥100,000    30          ☑       │
│  Grandchaos    ¥3,000      ¥30,000     15          ☑       │
│  ...                                                        │
│                                                              │
│  [Restore Defaults]  [Save]  [Cancel]                      │
└──────────────────────────────────────────────────────────────┘
```

---

## Smart Recommendations

### Cart Optimization Suggestions

```python
def suggest_cart_optimizations(self) -> List[str]:
    """
    Analyze cart and suggest optimizations

    Returns:
        List of recommendation strings
    """
    suggestions = []
    breakdown = self.get_shop_breakdown()

    # Find shops below threshold
    below_threshold = [
        shop for shop, data in breakdown.items()
        if data['status'] == 'below'
    ]

    if below_threshold:
        suggestions.append(
            f"💡 {len(below_threshold)} shop(s) below minimum - "
            f"consider waiting for more items or combining orders"
        )

    # Check if items could be redistributed
    # (Some Mandarake items available from multiple shops)
    suggestions.extend(self._suggest_shop_consolidation())

    # Check for old verifications
    last_verified = self.storage.get_last_verification_time()
    if last_verified and (datetime.now() - last_verified).days > 1:
        suggestions.append(
            "⏰ Cart not verified in 24h - eBay prices may have changed"
        )

    return suggestions
```

---

## Benefits

### 💰 Cost Optimization
- **Minimize shipping costs** - Reach minimum cart values before checkout
- **Avoid oversized orders** - Stay below maximums (may trigger extra fees)
- **Batch purchasing** - Group items efficiently by shop

### 📊 ROI Protection
- **Pre-checkout verification** - Catch price drops on eBay before purchasing
- **Remove low-performers** - Filter out items with degraded margins
- **Confidence in purchases** - Know your expected profit before buying

### ⚡ Efficiency
- **Semi-automated** - Add items to cart automatically, checkout manually
- **Visual tracking** - See cart status at a glance
- **Smart notifications** - Alerts when carts reach thresholds

### 🛡️ Safety
- **No auto-checkout** - Final purchase always requires manual confirmation
- **Threshold warnings** - Prevent accidental overspending
- **ROI safeguards** - Don't buy items with poor margins

---

## Next Steps

1. **Implement CartManager** - Core logic and API integration
2. **Create Cart UI** - Visual breakdown in Alert tab
3. **Add ROI Verification** - Integrate with existing eBay search
4. **Test with real cart** - Use test account to verify API calls
5. **Add threshold configuration** - UI for customizing limits
6. **Implement notifications** - Desktop alerts for cart milestones

---

**Status**: Design Complete - Ready for Implementation
**Priority**: High - Directly improves reselling workflow efficiency
**Risk**: Medium - Requires Mandarake API reverse engineering
