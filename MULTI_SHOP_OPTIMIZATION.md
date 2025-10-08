# Multi-Shop Item Optimization

## Overview

Many Mandarake items are available from multiple shops. When adding items to cart, we can optimize by consolidating items into fewer shops to minimize shipping costs.

---

## 🎯 Use Case

### Scenario
```
User has 3 "Yay" items:
- Item A: Available at Nakano, Shibuya, SAHRA
- Item B: Available at Nakano only
- Item C: Available at Shibuya only

Current distribution:
├─ Nakano: Item B (¥3,000) ← Below ¥5,000 threshold
├─ Shibuya: Item C (¥1,500) ← Below ¥5,000 threshold
└─ SAHRA: 0 items

Optimized distribution:
└─ Nakano: Item A + Item B + Item C (¥8,500) ← Above threshold!
   (Move Item A and C to Nakano)
```

**Benefit**: One shop checkout instead of three, lower shipping cost per item.

---

## 📋 Detection Methods

### Method 1: Parse Product Page (Recommended)

When scraping/viewing product page:
```html
<!-- Product detail page shows available shops -->
<div class="shop-availability">
    <h3>Available at these stores:</h3>
    <ul>
        <li data-shop="nkn">Nakano - ¥3,000</li>
        <li data-shop="shr">Shibuya - ¥3,000</li>
        <li data-shop="sah">SAHRA - ¥3,500</li>
    </ul>
</div>
```

### Method 2: Search API

Some items appear in multiple search results:
```python
# Same item code appears in different shop searches
{
    'product_id': '1126279062',
    'title': 'Same Item',
    'shops': [
        {'code': 'nkn', 'price': 3000},
        {'code': 'shr', 'price': 3000},
        {'code': 'sah', 'price': 3500}
    ]
}
```

### Method 3: Item Code Pattern

Mandarake uses consistent item codes across shops:
```
Same base item: 1126279062
- Nakano listing: 1126279062
- Shibuya listing: 1126279062
- SAHRA listing: 1126279062 (same code!)
```

---

## 🔧 Implementation

### 1. Store Multi-Shop Availability During Scraping

Update `mandarake_scraper.py` to check product detail page:

```python
def fetch_product_details(product_url):
    """Fetch detailed product info including shop availability"""

    response = session.get(product_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find shop availability section
    available_shops = []
    shop_list = soup.find('div', class_='shop-availability')

    if shop_list:
        for shop_elem in shop_list.find_all('li'):
            shop_code = shop_elem.get('data-shop')
            price_text = shop_elem.get_text()

            # Extract price
            price_match = re.search(r'¥([\d,]+)', price_text)
            if price_match:
                price = int(price_match.group(1).replace(',', ''))
                available_shops.append({
                    'shop_code': shop_code,
                    'price': price
                })

    return {
        'product_id': extract_product_id(product_url),
        'available_shops': available_shops
    }
```

### 2. Add Available Shops to Alert Data

When creating alerts:

```python
# In alert creation
alert_data = {
    'title': item['title'],
    'price_jpy': item['price'],
    'shop_code': item['shop_code'],  # Original shop
    'available_shops': [
        {'code': 'nkn', 'price': 3000},
        {'code': 'shr', 'price': 3000},
        {'code': 'sah', 'price': 3500}
    ],  # All shops where item is available
    ...
}
```

### 3. Optimize Shop Distribution

Add optimization logic to `cart_manager.py`:

```python
def optimize_shop_distribution(self, items: List[Dict]) -> Dict:
    """
    Optimize item distribution across shops to minimize number of shipments

    Args:
        items: List of items to add to cart

    Returns:
        Optimized distribution with consolidation suggestions
    """

    # 1. Analyze multi-shop items
    multi_shop_items = [
        item for item in items
        if len(item.get('available_shops', [])) > 1
    ]

    # 2. Calculate all possible shop combinations
    from itertools import product

    # Generate all possible assignments
    if multi_shop_items:
        # For each multi-shop item, try assigning to each available shop
        possible_assignments = product(*[
            item['available_shops'] for item in multi_shop_items
        ])

        best_assignment = None
        min_shops = float('inf')

        for assignment in possible_assignments:
            # Count unique shops in this assignment
            shops_used = set(shop['code'] for shop in assignment)

            if len(shops_used) < min_shops:
                min_shops = len(shops_used)
                best_assignment = assignment

    # 3. Group by optimized shop
    optimized_distribution = {}

    for i, item in enumerate(multi_shop_items):
        assigned_shop = best_assignment[i]
        shop_code = assigned_shop['code']

        if shop_code not in optimized_distribution:
            optimized_distribution[shop_code] = []

        optimized_distribution[shop_code].append({
            **item,
            'assigned_shop': shop_code,
            'assigned_price': assigned_shop['price'],
            'original_shop': item['shop_code'],
            'was_reassigned': item['shop_code'] != shop_code
        })

    # 4. Add single-shop items
    single_shop_items = [
        item for item in items
        if len(item.get('available_shops', [])) <= 1
    ]

    for item in single_shop_items:
        shop = item['shop_code']
        if shop not in optimized_distribution:
            optimized_distribution[shop] = []
        optimized_distribution[shop].append(item)

    return optimized_distribution
```

### 4. Show Optimization Dialog

Before adding to cart, show optimization suggestions:

```python
def _show_optimization_dialog(self, original_distribution, optimized_distribution):
    """Show shop consolidation suggestions"""

    dialog = tk.Toplevel(self)
    dialog.title("Shop Consolidation Suggestions")
    dialog.geometry("600x500")

    # Header
    ttk.Label(
        dialog,
        text="💡 Items can be consolidated to fewer shops:",
        font=('', 11, 'bold')
    ).pack(pady=10)

    # Original vs Optimized comparison
    comp_frame = ttk.Frame(dialog)
    comp_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    # Original distribution
    orig_frame = ttk.LabelFrame(comp_frame, text="Current Distribution")
    orig_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

    orig_text = tk.Text(orig_frame, height=15, width=25)
    orig_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    for shop, items in original_distribution.items():
        total = sum(i['price_jpy'] for i in items)
        orig_text.insert('end', f"📍 {shop}\n")
        orig_text.insert('end', f"   {len(items)} items, ¥{total:,}\n\n")

    total_shops_orig = len(original_distribution)
    orig_text.insert('end', f"\nTotal: {total_shops_orig} shops\n")
    orig_text['state'] = 'disabled'

    # Arrow
    ttk.Label(comp_frame, text="→", font=('', 20)).pack(side=tk.LEFT, padx=10)

    # Optimized distribution
    opt_frame = ttk.LabelFrame(comp_frame, text="Optimized Distribution")
    opt_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

    opt_text = tk.Text(opt_frame, height=15, width=25)
    opt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    for shop, items in optimized_distribution.items():
        total = sum(i.get('assigned_price', i['price_jpy']) for i in items)
        reassigned = sum(1 for i in items if i.get('was_reassigned'))

        opt_text.insert('end', f"📍 {shop}\n")
        opt_text.insert('end', f"   {len(items)} items, ¥{total:,}\n")
        if reassigned > 0:
            opt_text.insert('end', f"   (+{reassigned} moved here)\n")
        opt_text.insert('end', '\n')

    total_shops_opt = len(optimized_distribution)
    opt_text.insert('end', f"\nTotal: {total_shops_opt} shops\n")
    opt_text.insert('end', f"✅ Saves {total_shops_orig - total_shops_opt} shipment(s)!")
    opt_text['state'] = 'disabled'

    # Savings summary
    savings_frame = ttk.Frame(dialog)
    savings_frame.pack(fill=tk.X, padx=20, pady=10)

    ttk.Label(
        savings_frame,
        text=f"💰 Consolidating to {total_shops_opt} shops instead of {total_shops_orig}",
        font=('', 10, 'bold'),
        foreground='green'
    ).pack()

    # Buttons
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=20)

    def use_optimized():
        dialog.result = 'optimized'
        dialog.destroy()

    def use_original():
        dialog.result = 'original'
        dialog.destroy()

    ttk.Button(
        btn_frame,
        text="Use Optimized (Recommended)",
        command=use_optimized,
        style='Accent.TButton'
    ).pack(side=tk.LEFT, padx=5)

    ttk.Button(
        btn_frame,
        text="Keep Original",
        command=use_original
    ).pack(side=tk.LEFT, padx=5)

    ttk.Button(
        btn_frame,
        text="Cancel",
        command=dialog.destroy
    ).pack(side=tk.LEFT, padx=5)

    dialog.wait_window()
    return getattr(dialog, 'result', None)
```

---

## 🔄 Complete Workflow with Optimization

### Step 1: User clicks "Add Yays to Cart"

System fetches 8 Yay items:
```python
items = [
    {
        'title': 'Item A',
        'shop_code': 'nkn',
        'price_jpy': 3000,
        'available_shops': [
            {'code': 'nkn', 'price': 3000},
            {'code': 'shr', 'price': 3000},
            {'code': 'sah', 'price': 3500}
        ]
    },
    {
        'title': 'Item B',
        'shop_code': 'nkn',
        'price_jpy': 2000,
        'available_shops': [
            {'code': 'nkn', 'price': 2000}
        ]
    },
    {
        'title': 'Item C',
        'shop_code': 'shr',
        'price_jpy': 1500,
        'available_shops': [
            {'code': 'nkn', 'price': 1600},
            {'code': 'shr', 'price': 1500}
        ]
    },
    ...
]
```

### Step 2: System Optimizes Distribution

```python
# Original distribution (by scraped shop)
{
    'nkn': [Item A, Item B],     # ¥5,000
    'shr': [Item C, Item D],     # ¥3,500 ← Below threshold
    'sah': [Item E],             # ¥2,000 ← Below threshold
}

# Optimized distribution (consolidated)
{
    'nkn': [Item A, Item B, Item C, Item D, Item E],  # ¥12,100 ✅
}
```

### Step 3: Show Optimization Dialog

```
┌─ Shop Consolidation Suggestions ──────────────────────────────┐
│                                                                │
│  💡 Items can be consolidated to fewer shops:                 │
│                                                                │
│  ┌─ Current Distribution ─┐    →    ┌─ Optimized ────────┐  │
│  │                          │         │                     │  │
│  │  📍 Nakano              │         │  📍 Nakano         │  │
│  │     2 items, ¥5,000     │         │     5 items,        │  │
│  │                          │         │     ¥12,100         │  │
│  │  📍 Shibuya             │         │     (+3 moved here) │  │
│  │     2 items, ¥3,500     │         │                     │  │
│  │                          │         │  Total: 1 shop      │  │
│  │  📍 SAHRA               │         │  ✅ Saves 2         │  │
│  │     1 items, ¥2,000     │         │     shipments!      │  │
│  │                          │         │                     │  │
│  │  Total: 3 shops          │         │                     │  │
│  └──────────────────────────┘         └─────────────────────┘  │
│                                                                │
│  💰 Consolidating to 1 shop instead of 3                      │
│                                                                │
│  [Use Optimized (Recommended)]  [Keep Original]  [Cancel]    │
└────────────────────────────────────────────────────────────────┘
```

### Step 4: Add Items with Optimal Shop Assignment

```python
if user_choice == 'optimized':
    for shop, items in optimized_distribution.items():
        for item in items:
            # Use assigned shop (may differ from original)
            cart_api.add_to_cart(
                product_id=item['product_id'],
                shop_code=item.get('assigned_shop', item['shop_code']),
                quantity=1
            )
```

---

## 📊 Benefits

### Cost Savings
- **Fewer shipments** - Consolidate 3 shops → 1 shop
- **Reach thresholds** - Combine small carts into one large cart
- **Lower shipping per item** - Economies of scale

### Smart Features
- **Automatic detection** - Finds multi-shop items
- **Price comparison** - Chooses cheapest shop when available
- **User choice** - Can override optimization if desired

### Example Savings

```
Scenario: 5 items across 3 shops

Original (3 shipments):
- Nakano: ¥5,000 + ¥1,500 shipping = ¥6,500
- Shibuya: ¥3,000 + ¥1,500 shipping = ¥4,500
- SAHRA: ¥2,000 + ¥1,500 shipping = ¥3,500
Total: ¥10,000 items + ¥4,500 shipping = ¥14,500

Optimized (1 shipment):
- Nakano: ¥10,000 + ¥2,000 shipping = ¥12,000
Total: ¥10,000 items + ¥2,000 shipping = ¥12,000

Savings: ¥2,500 (17% reduction!)
```

---

## 🔍 Data Collection

### Option 1: Scrape Product Detail Pages

When scraping Mandarake, for each item:
```python
# 1. Scrape search results
items = scrape_search_results(keyword)

# 2. For each item, fetch detail page
for item in items:
    details = fetch_product_details(item['url'])
    item['available_shops'] = details['available_shops']
```

### Option 2: Search Multiple Shops

```python
# Search same keyword in all shops
results_by_shop = {}

for shop in ['all', 'nkn', 'shr', 'sah', ...]:
    results = scrape_mandarake(keyword, shop=shop)
    results_by_shop[shop] = results

# Find duplicates by product_id
multi_shop_items = find_duplicates_by_product_id(results_by_shop)
```

### Option 3: Manual Entry (Fallback)

If automatic detection fails, allow manual shop selection:
```
┌─ Item Available in Multiple Shops ────────────────────────────┐
│                                                                │
│  "Nagasawa Marina Photograph Collection"                      │
│                                                                │
│  This item is available from:                                 │
│  ○ Nakano - ¥3,000                                            │
│  ○ Shibuya - ¥3,000                                           │
│  ○ SAHRA - ¥3,500                                             │
│                                                                │
│  Add to cart from which shop?                                 │
│  [Auto-Optimize]  [Choose Manually]                           │
└────────────────────────────────────────────────────────────────┘
```

---

## ✅ Updated Add-to-Cart Flow

```python
def add_yays_to_cart(self, use_optimization=True):
    """Add Yays to cart with optional shop optimization"""

    # 1. Get Yay items
    items = self.alert_manager.get_alerts_by_state('yay')

    if use_optimization:
        # 2. Check for multi-shop items
        has_multi_shop = any(
            len(item.get('available_shops', [])) > 1
            for item in items
        )

        if has_multi_shop:
            # 3. Optimize distribution
            original = self._group_by_shop(items)
            optimized = self.optimize_shop_distribution(items)

            # 4. Show optimization dialog
            choice = self._show_optimization_dialog(original, optimized)

            if choice == 'optimized':
                distribution = optimized
            elif choice == 'original':
                distribution = original
            else:
                return {'cancelled': True}
        else:
            distribution = self._group_by_shop(items)
    else:
        distribution = self._group_by_shop(items)

    # 5. Check thresholds
    warnings = self._check_thresholds(distribution)

    # 6. Add to cart
    return self._bulk_add_to_cart(distribution)
```

---

**Status**: Design complete - ready for implementation
**Benefit**: Significant shipping cost savings through shop consolidation
**Requirement**: Detect multi-shop availability during scraping or from product pages

