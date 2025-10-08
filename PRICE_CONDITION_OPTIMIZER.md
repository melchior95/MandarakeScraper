# Price & Condition Optimizer

## Overview

Items available in multiple shops often have different prices and conditions. The system should help you choose the best shop based on:
- **Price** (lower is better)
- **Condition** (better condition preferred)
- **Shop consolidation** (fewer shipments)
- **Cart threshold optimization** (reach minimums)

---

## 🏷️ Item Condition Hierarchy

Mandarake uses these condition grades (best to worst):

```
1. "New" / "Unused"          ⭐⭐⭐⭐⭐
2. "Like New" / "Near Mint"  ⭐⭐⭐⭐
3. "Very Good"               ⭐⭐⭐⭐
4. "Good"                    ⭐⭐⭐
5. "Fair" / "Acceptable"     ⭐⭐
6. "Poor" / "Damaged"        ⭐
```

**Condition affects ROI:**
- Better condition = Higher eBay resale price
- Poor condition = May not sell or sells for less

---

## 📊 Multi-Shop Data Structure

### Extended Item Data

```python
{
    'product_id': '1126279062',
    'title': 'Nagasawa Marina Photograph Collection',
    'image_url': 'https://...',

    # Original shop (where user found it)
    'shop_code': 'nkn',
    'price_jpy': 3000,
    'condition': 'Good',

    # All available shops with prices and conditions
    'available_shops': [
        {
            'shop_code': 'nkn',
            'shop_name': 'Nakano',
            'price_jpy': 3000,
            'condition': 'Good',
            'condition_score': 3,
            'status': 'In Stock',
            'product_url': 'https://...'
        },
        {
            'shop_code': 'shr',
            'shop_name': 'Shibuya',
            'price_jpy': 2800,        # ← Cheaper!
            'condition': 'Very Good',  # ← Better condition!
            'condition_score': 4,
            'status': 'In Stock',
            'product_url': 'https://...'
        },
        {
            'shop_code': 'sah',
            'shop_name': 'SAHRA',
            'price_jpy': 2500,        # ← Cheapest!
            'condition': 'Fair',       # ← Worse condition
            'condition_score': 2,
            'status': 'In Stock',
            'product_url': 'https://...'
        }
    ],

    # Optimization recommendations
    'recommended_shop': 'shr',  # Best balance of price + condition
    'cheapest_shop': 'sah',
    'best_condition_shop': 'shr'
}
```

---

## 🧮 Scoring Algorithm

### Multi-Factor Optimization

```python
def calculate_shop_score(shop_data, preferences):
    """
    Calculate shop score based on multiple factors

    Args:
        shop_data: Dict with price, condition, etc.
        preferences: User preferences for weighting

    Returns:
        float: Score (higher is better)
    """

    score = 0

    # 1. Price score (lower price = higher score)
    # Normalize to 0-100 scale
    all_prices = [s['price_jpy'] for s in all_shops]
    min_price = min(all_prices)
    max_price = max(all_prices)

    if max_price > min_price:
        # Invert: cheapest gets 100, most expensive gets 0
        price_score = 100 * (1 - (shop_data['price_jpy'] - min_price) / (max_price - min_price))
    else:
        price_score = 100

    score += price_score * preferences['price_weight']  # Default: 0.5

    # 2. Condition score (better condition = higher score)
    condition_score = shop_data['condition_score'] * 20  # 1-5 → 20-100
    score += condition_score * preferences['condition_weight']  # Default: 0.3

    # 3. Consolidation bonus
    # If this shop is already in cart, bonus points
    if shop_data['shop_code'] in current_cart_shops:
        score += 50 * preferences['consolidation_weight']  # Default: 0.2

    return score
```

### Default Scoring Weights

```python
DEFAULT_PREFERENCES = {
    'price_weight': 0.5,          # 50% - Price matters most
    'condition_weight': 0.3,      # 30% - Condition important for resale
    'consolidation_weight': 0.2   # 20% - Prefer fewer shops
}
```

---

## 🎨 UI: Shop Comparison View

### Inline Comparison (Alerts Tab)

When item has multiple shops, show comparison icon:

```
┌─ Alerts ──────────────────────────────────────────────────────┐
│                                                                │
│  ✓ Item 1                    ¥3,000   Nakano    [🔍 Compare] │
│     "Nagasawa Marina..."                                       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

Click [🔍 Compare] to open comparison dialog:

```
┌─ Shop Comparison: "Nagasawa Marina Photograph Collection" ────┐
│                                                                │
│  Available from 3 shops:                                       │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Shop      Price    Condition    Status    Score  ✓    │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  Shibuya   ¥2,800   Very Good    In Stock  ⭐92  [●]   │  │
│  │  Nakano    ¥3,000   Good         In Stock  ⭐76  [ ]   │  │
│  │  SAHRA     ¥2,500   Fair         In Stock  ⭐68  [ ]   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                │
│  💡 Recommendation: Shibuya                                   │
│     Best balance of price (¥2,800) and condition (Very Good) │
│                                                                │
│  💰 Savings: ¥200 vs Nakano (original)                        │
│  📦 Consolidation: Adding to existing Shibuya cart            │
│                                                                │
│  [Use Recommended]  [Choose Manually]  [Keep Original]        │
└────────────────────────────────────────────────────────────────┘
```

### Bulk Comparison (Before Adding to Cart)

When adding multiple items with multi-shop availability:

```
┌─ Optimize Item Selections ────────────────────────────────────┐
│                                                                │
│  5 items can be optimized for better prices/conditions:       │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Item                  Original      →  Optimized       │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  "Nagasawa Marina..."  Nakano ¥3K   →  Shibuya ¥2.8K  │  │
│  │                        (Good)        →  (Very Good) ✨  │  │
│  │                                                          │  │
│  │  "Okada Sayaka..."     SAHRA ¥4K    →  Nakano ¥3.5K    │  │
│  │                        (Fair)        →  (Good) ✨       │  │
│  │                                                          │  │
│  │  "Item C..."           Shibuya ¥2K  →  No change       │  │
│  │                        (New)                             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                │
│  💰 Total Savings: ¥1,200                                     │
│  📦 Shop Count: 3 → 2 (fewer shipments)                       │
│  ⭐ Better Conditions: 2 items upgraded                       │
│                                                                │
│  [Apply Optimizations]  [Review Individually]  [Skip]        │
└────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation

### 1. Condition Parser

```python
CONDITION_MAP = {
    # English
    'new': 5,
    'unused': 5,
    'like new': 4,
    'near mint': 4,
    'very good': 4,
    'good': 3,
    'fair': 2,
    'acceptable': 2,
    'poor': 1,
    'damaged': 1,

    # Japanese
    '新品': 5,
    '未使用': 5,
    '美品': 4,
    '良好': 3,
    '可': 2,
    '難あり': 1
}

def parse_condition(condition_text: str) -> Tuple[str, int]:
    """
    Parse condition text to standardized grade and score

    Args:
        condition_text: Condition from Mandarake page

    Returns:
        Tuple of (condition_name, condition_score)
    """
    text_lower = condition_text.lower().strip()

    for keyword, score in CONDITION_MAP.items():
        if keyword in text_lower:
            return (keyword.title(), score)

    # Default to "Good" if unknown
    return ("Good", 3)
```

### 2. Shop Comparison Engine

```python
class ShopComparer:
    """Compare item availability across shops"""

    def __init__(self):
        self.preferences = DEFAULT_PREFERENCES

    def compare_shops(self, item_data: Dict) -> Dict:
        """
        Compare all shops for an item

        Args:
            item_data: Item with available_shops list

        Returns:
            Comparison results with recommendations
        """
        shops = item_data.get('available_shops', [])

        if len(shops) <= 1:
            return {
                'has_options': False,
                'recommended_shop': item_data.get('shop_code')
            }

        # Score each shop
        scored_shops = []
        for shop in shops:
            score = self._calculate_shop_score(shop, shops)
            scored_shops.append({
                **shop,
                'score': score
            })

        # Sort by score (highest first)
        scored_shops.sort(key=lambda x: x['score'], reverse=True)

        # Find cheapest and best condition
        cheapest = min(shops, key=lambda x: x['price_jpy'])
        best_condition = max(shops, key=lambda x: x['condition_score'])

        return {
            'has_options': True,
            'shops': scored_shops,
            'recommended': scored_shops[0],  # Highest score
            'cheapest': cheapest,
            'best_condition': best_condition,
            'price_range': {
                'min': cheapest['price_jpy'],
                'max': max(s['price_jpy'] for s in shops),
                'savings': max(s['price_jpy'] for s in shops) - cheapest['price_jpy']
            }
        }

    def _calculate_shop_score(self, shop: Dict, all_shops: List[Dict]) -> float:
        """Calculate score for a shop option"""

        # Get current cart shops for consolidation bonus
        current_cart_shops = set(self._get_current_cart_shops())

        prices = [s['price_jpy'] for s in all_shops]
        min_price = min(prices)
        max_price = max(prices)

        # Price score (0-100, higher is better)
        if max_price > min_price:
            price_score = 100 * (1 - (shop['price_jpy'] - min_price) / (max_price - min_price))
        else:
            price_score = 100

        # Condition score (20-100, based on 1-5 scale)
        condition_score = shop['condition_score'] * 20

        # Consolidation bonus
        consolidation_bonus = 50 if shop['shop_code'] in current_cart_shops else 0

        # Weighted total
        score = (
            price_score * self.preferences['price_weight'] +
            condition_score * self.preferences['condition_weight'] +
            consolidation_bonus * self.preferences['consolidation_weight']
        )

        return round(score, 1)
```

### 3. Bulk Optimizer

```python
def optimize_bulk_selection(self, items: List[Dict]) -> Dict:
    """
    Optimize shop selection for multiple items

    Args:
        items: List of items with multi-shop availability

    Returns:
        Optimized selection with savings and improvements
    """
    optimizations = []
    total_savings = 0
    condition_improvements = 0
    shop_changes = {}

    for item in items:
        comparison = self.compare_shops(item)

        if not comparison['has_options']:
            continue

        original_shop = item['shop_code']
        original_price = item['price_jpy']
        original_condition = item.get('condition_score', 3)

        recommended = comparison['recommended']

        # Check if recommendation differs from original
        if recommended['shop_code'] != original_shop:
            savings = original_price - recommended['price_jpy']
            condition_change = recommended['condition_score'] - original_condition

            optimizations.append({
                'item': item,
                'original_shop': original_shop,
                'recommended_shop': recommended['shop_code'],
                'original_price': original_price,
                'recommended_price': recommended['price_jpy'],
                'savings': savings,
                'condition_improvement': condition_change > 0,
                'condition_degradation': condition_change < 0
            })

            total_savings += savings
            if condition_change > 0:
                condition_improvements += 1

            # Track shop changes
            shop_changes[original_shop] = shop_changes.get(original_shop, 0) - 1
            shop_changes[recommended['shop_code']] = shop_changes.get(recommended['shop_code'], 0) + 1

    # Calculate shop count change
    original_shops = len(set(item['shop_code'] for item in items))
    optimized_shops = len([s for s in shop_changes.values() if s > 0])

    return {
        'has_optimizations': len(optimizations) > 0,
        'optimizations': optimizations,
        'total_savings': total_savings,
        'condition_improvements': condition_improvements,
        'shop_count_before': original_shops,
        'shop_count_after': optimized_shops,
        'shop_consolidation': original_shops - optimized_shops
    }
```

---

## ⚙️ Configuration Options

### User Preferences

Allow users to configure optimization priorities:

```python
# In settings/preferences
OPTIMIZATION_PREFERENCES = {
    'auto_optimize': True,          # Automatically optimize on "Add to Cart"
    'price_weight': 0.5,            # How much to prioritize price (0-1)
    'condition_weight': 0.3,        # How much to prioritize condition (0-1)
    'consolidation_weight': 0.2,    # How much to prioritize fewer shops (0-1)
    'min_savings_threshold': 200,   # Min ¥ savings to suggest optimization
    'allow_condition_downgrade': False  # Never downgrade condition for price
}
```

### Condition Override Rules

```python
CONDITION_RULES = {
    # Never downgrade from these conditions
    'protected_conditions': ['New', 'Unused', 'Near Mint'],

    # Maximum price increase acceptable for condition upgrade
    'max_price_increase_for_upgrade': 500,  # ¥500

    # Minimum price decrease required for condition downgrade
    'min_savings_for_downgrade': 1000  # ¥1000
}
```

---

## 🎯 Smart Recommendations

### Scenario 1: Better Condition, Slightly Higher Price

```
Original: Nakano ¥3,000 (Good)
Option: Shibuya ¥3,200 (Very Good) +¥200

Recommendation: ✅ Shibuya
Reason: "Upgrade to Very Good condition for only ¥200 extra.
         Better condition = higher eBay resale value."
```

### Scenario 2: Worse Condition, Lower Price

```
Original: Shibuya ¥4,000 (Very Good)
Option: SAHRA ¥2,500 (Fair) -¥1,500

Recommendation: ⚠️ Shibuya (keep original)
Reason: "SAHRA is ¥1,500 cheaper but condition is significantly worse.
         Fair condition may not resell well on eBay."

Alternative: Let user decide with warning
```

### Scenario 3: Same Condition, Lower Price

```
Original: Nakano ¥5,000 (Good)
Option: Kyoto ¥4,200 (Good) -¥800

Recommendation: ✅ Kyoto
Reason: "Save ¥800 with same condition. Clear win!"
```

### Scenario 4: Shop Consolidation Priority

```
Original Distribution:
- Nakano: 1 item ¥3,000
- Shibuya: 5 items ¥12,000
- SAHRA: 1 item ¥2,500

Item A available at: Nakano ¥3,000, Shibuya ¥3,100

Recommendation: ✅ Shibuya
Reason: "Add to existing Shibuya cart (already 5 items).
         Only ¥100 more but saves 1 shipment."
```

---

## 📋 Integration with Add-to-Cart Flow

### Updated Workflow

```python
def add_yays_to_cart(self):
    """Add Yays to cart with optimization"""

    # 1. Get Yay items
    items = self.alert_manager.get_alerts_by_state('yay')

    # 2. Run optimization
    if self.preferences['auto_optimize']:
        optimization_results = self.optimize_bulk_selection(items)

        if optimization_results['has_optimizations']:
            # Show optimization dialog
            choice = self._show_optimization_dialog(optimization_results)

            if choice == 'apply':
                # Apply recommended shops
                for opt in optimization_results['optimizations']:
                    opt['item']['shop_code'] = opt['recommended_shop']
                    opt['item']['price_jpy'] = opt['recommended_price']

    # 3. Check thresholds
    distribution = self._group_by_shop(items)
    warnings = self._check_thresholds(distribution)

    # 4. Add to cart
    return self._bulk_add_to_cart(distribution)
```

---

## ✅ Benefits

### Financial
- **Lower costs** - Choose cheapest option when condition is same
- **Better resale value** - Choose better condition when price difference is small
- **Shop consolidation** - Fewer shipments = lower shipping costs

### Quality
- **Condition awareness** - Never blindly choose cheapest
- **Resale optimization** - Better condition = easier to sell on eBay
- **Informed decisions** - Show all options with clear comparisons

### UX
- **Transparent** - User always sees all options
- **Configurable** - Adjust priorities based on preference
- **Safe defaults** - Protect condition quality by default

---

**Status**: Design complete - ready for implementation
**Key Feature**: Multi-factor optimization (price + condition + consolidation)
**User Control**: Full transparency with ability to override

