# Auto-Purchase Plan (Scheduler-Based)

## Overview
Automatically purchase out-of-stock Mandarake items when they become available by monitoring them through the **Scheduler** system, not the Alerts tab.

## Key Insight: Scheduler vs Alerts

**Why Scheduler, not Alerts?**
- ❌ **Alerts** = Mandarake items WITH eBay comparison data
- ✅ **Scheduler** = Mandarake items WITHOUT eBay data (just URLs to monitor)

**Auto-purchase items:**
- Have Mandarake URL (search or direct item link)
- Have last known price
- Have max price willing to pay
- **NO eBay data** (no similarity %, no profit %, no comparison)
- Just monitor → detect in stock → purchase

## Use Case

**Problem**: High-value items sell out quickly. Manual monitoring isn't fast enough.

**Solution**: Add out-of-stock item URLs to scheduler with auto-purchase enabled:
1. System monitors URL every X minutes
2. Detects when item comes back in stock **in ANY Mandarake store**
3. Validates price hasn't exceeded max
4. Adds to cart
5. Completes checkout
6. Notifies user of purchase

## Architecture

### 1. Enhanced Schedule Data Structure

**New fields in `Schedule` class** (`gui/schedule_states.py`):

```python
@dataclass
class Schedule:
    # ... existing fields ...

    # Auto-purchase fields
    auto_purchase_enabled: bool = False           # Enable auto-purchase for this schedule
    auto_purchase_url: Optional[str] = None       # Mandarake URL to monitor (search or item)
    auto_purchase_keyword: Optional[str] = None   # Search keyword (if using search URL)
    auto_purchase_last_price: Optional[int] = None  # Last known price in JPY
    auto_purchase_max_price: Optional[int] = None   # Max price willing to pay (default: last_price * 1.2)
    auto_purchase_check_interval: int = 30        # Check every X minutes
    auto_purchase_expiry: Optional[str] = None    # Stop checking after this date (YYYY-MM-DD)
    auto_purchase_last_check: Optional[str] = None  # Last time we checked
    auto_purchase_next_check: Optional[str] = None  # Next scheduled check
```

### 2. Scheduler Tab UI Enhancements

**New columns in schedule treeview:**

```
| Active | Name | Type | Frequency | Days | Start | Next Run | Configs | Auto-Purchase | Last Price | Max Price | Last Check |
```

**New Auto-Purchase columns:**
- **Auto-Purchase**: "Yes" / "No" / "Monitoring..." / "Purchased ✓"
- **Last Price**: Last known price (¥12,800)
- **Max Price**: Maximum willing to pay (¥15,360 default = +20%)
- **Last Check**: When we last checked availability

**New buttons in scheduler toolbar:**

```
[New Schedule] [Edit] [Delete] | [Activate] [Deactivate] | [Run Now] | [New Auto-Purchase] [Configure Auto-Purchase] | [Refresh]
```

### 2b. Right-Click Menu Integration

**CSV Treeview Right-Click Menu** (Mandarake tab):

```python
# gui/mandarake_tab.py or gui_config.py

def _create_csv_context_menu(self, event):
    """Create right-click menu for CSV treeview."""
    menu = tk.Menu(self.tree, tearoff=0)

    # Get selected item
    item = self.tree.identify_row(event.y)
    if not item:
        return

    # Get item data
    values = self.tree.item(item, 'values')
    # Assuming columns: [Title, Price, Shop, Stock, URL, ...]
    stock_status = values[3]  # Stock column

    # Standard menu items
    menu.add_command(label="Open Store Link", command=self._open_store_link)
    menu.add_command(label="Copy Title", command=self._copy_title)
    menu.add_separator()

    # Auto-Purchase option
    if stock_status == "Sold Out" or stock_status == "Out of Stock":
        # Show enabled option
        menu.add_command(
            label="📌 Add to Auto-Purchase Monitor",
            command=lambda: self._add_to_auto_purchase(item)
        )
    else:
        # Grey out if in stock
        menu.add_command(
            label="📌 Add to Auto-Purchase Monitor",
            command=lambda: None,
            state="disabled"
        )
        # Add tooltip explanation
        menu.entryconfigure(
            "📌 Add to Auto-Purchase Monitor",
            state="disabled"
        )

    menu.post(event.x_root, event.y_root)

def _add_to_auto_purchase(self, tree_item):
    """Open auto-purchase dialog from CSV item."""
    values = self.tree.item(tree_item, 'values')

    # Extract data
    title = values[0]
    price_str = values[1]  # "¥12,800"
    price_jpy = int(''.join(c for c in price_str if c.isdigit()))
    shop = values[2]
    url = values[4]  # Store link

    # Open auto-purchase dialog with pre-filled data
    from gui.auto_purchase_dialog import AutoPurchaseDialog

    dialog = AutoPurchaseDialog(
        self,
        item_name=title,
        url=url,
        last_price=price_jpy,
        shop=shop
    )
    self.wait_window(dialog)

    if dialog.result:
        # Add to scheduler
        self._create_auto_purchase_schedule(dialog.result)
```

**eBay Treeview Right-Click Menu** (eBay Search & CSV tab):

```python
# gui/ebay_tab.py or gui_config.py

def _create_ebay_context_menu(self, event):
    """Create right-click menu for eBay comparison treeview."""
    menu = tk.Menu(self.ebay_tree, tearoff=0)

    # Get selected item
    item = self.ebay_tree.identify_row(event.y)
    if not item:
        return

    # Get item data
    values = self.ebay_tree.item(item, 'values')
    # Check if this item has Mandarake data
    has_mandarake_data = self._item_has_mandarake_data(item)

    # Standard menu items
    menu.add_command(label="Open eBay Link", command=self._open_ebay_link)
    menu.add_command(label="Show Image Comparison", command=self._show_image_comparison)
    menu.add_separator()

    # Auto-Purchase option (conditional)
    if has_mandarake_data:
        # Check if Mandarake item is out of stock
        mandarake_stock = self._get_mandarake_stock_status(item)

        if mandarake_stock == "Out of Stock":
            menu.add_command(
                label="📌 Add to Auto-Purchase Monitor (Store Item)",
                command=lambda: self._add_mandarake_item_to_auto_purchase(item)
            )
        else:
            menu.add_command(
                label="📌 Add to Auto-Purchase Monitor (In Stock)",
                command=lambda: None,
                state="disabled"
            )
    else:
        # No Mandarake data - grey out
        menu.add_command(
            label="📌 Add to Auto-Purchase Monitor",
            command=lambda: None,
            state="disabled"
        )

    menu.post(event.x_root, event.y_root)

def _item_has_mandarake_data(self, tree_item) -> bool:
    """Check if eBay comparison item has linked Mandarake data."""
    # Check if the result has 'store_link' or 'store_title' fields
    item_id = self.ebay_tree.item(tree_item, 'tags')[0] if self.ebay_tree.item(tree_item, 'tags') else None

    if not item_id:
        return False

    # Lookup in comparison results
    for result in self.csv_comparison_results:
        if str(result.get('id')) == item_id:
            return bool(result.get('store_link') and result.get('store_price'))

    return False

def _get_mandarake_stock_status(self, tree_item) -> str:
    """Get stock status of linked Mandarake item."""
    item_id = self.ebay_tree.item(tree_item, 'tags')[0] if self.ebay_tree.item(tree_item, 'tags') else None

    if not item_id:
        return "Unknown"

    for result in self.csv_comparison_results:
        if str(result.get('id')) == item_id:
            return result.get('store_stock', 'Unknown')

    return "Unknown"

def _add_mandarake_item_to_auto_purchase(self, tree_item):
    """Open auto-purchase dialog from eBay comparison item (using Mandarake data)."""
    item_id = self.ebay_tree.item(tree_item, 'tags')[0]

    # Find the comparison result
    result = next((r for r in self.csv_comparison_results if str(r.get('id')) == item_id), None)

    if not result:
        messagebox.showerror("Error", "Could not find Mandarake data for this item")
        return

    # Extract Mandarake data
    title = result.get('store_title', 'Unknown')
    price_str = result.get('store_price', '¥0')
    price_jpy = int(''.join(c for c in price_str if c.isdigit()))
    url = result.get('store_link', '')
    shop = result.get('store_shop', 'Unknown')

    # Open auto-purchase dialog
    from gui.auto_purchase_dialog import AutoPurchaseDialog

    dialog = AutoPurchaseDialog(
        self,
        item_name=title,
        url=url,
        last_price=price_jpy,
        shop=shop
    )
    self.wait_window(dialog)

    if dialog.result:
        # Add to scheduler
        self._create_auto_purchase_schedule(dialog.result)
```

### 3. New Auto-Purchase Dialog

**"New Auto-Purchase" Button** opens simplified dialog:

```
┌─ Add Auto-Purchase Item ───────────────────────┐
│                                                  │
│ Item URL or Search Keyword:                     │
│   ○ Direct Item URL                             │
│      [https://order.mandarake.co.jp/order/...]  │
│                                                  │
│   ○ Search Keyword (monitors all stores)        │
│      [Yura Kano Photobook 2025        ]         │
│                                                  │
│ Current Status:                                  │
│   Price: ¥12,800 (Out of Stock)                 │
│   Store: Nakano                                  │
│                                                  │
│ Purchase Settings:                               │
│   Max Price:      [15,360] ¥ (+20% default)     │
│   Check Every:    [30] minutes                   │
│   Stop After:     [2025-11-01] (date picker)    │
│                                                  │
│ Auto-Purchase Actions:                           │
│   ☑ Add to cart when in stock                   │
│   ☑ Complete checkout automatically             │
│   ☐ Show confirmation before purchase           │
│                                                  │
│ Checkout Info:                                   │
│   ☑ Use saved payment method                    │
│   ☑ Use saved shipping address                  │
│   [Configure Checkout Settings...]              │
│                                                  │
│           [Add to Monitor]  [Cancel]             │
│                                                  │
│ 💡 This item will be checked every 30 minutes.  │
│    You'll be notified when purchased.           │
└──────────────────────────────────────────────────┘
```

### 4. Schedule Executor Enhancements

**Modified `ScheduleExecutor`** (`gui/schedule_executor.py`):

```python
class ScheduleExecutor:
    def __init__(self, gui_config_ref):
        self.gui = gui_config_ref
        self.manager = ScheduleManager()
        self.cart_manager = gui_config_ref.cart_manager  # NEW: Access to cart
        self.running = False
        self.thread = None
        self.check_interval = 60  # Check every 60 seconds

    def _run_loop(self):
        """Main loop that checks for due schedules AND auto-purchase items."""
        while self.running:
            try:
                # Existing: Check scheduled tasks
                self._check_and_execute()

                # NEW: Check auto-purchase items
                self._check_auto_purchase_items()

            except Exception as e:
                print(f"[SCHEDULE EXECUTOR] Error: {e}")

            # Sleep in small intervals
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _check_auto_purchase_items(self):
        """Check all active auto-purchase schedules."""
        schedules = self.manager.get_all_schedules()

        for schedule in schedules:
            # Skip non-auto-purchase schedules
            if not schedule.auto_purchase_enabled:
                continue

            # Skip if not time to check yet
            if not self._is_due_for_check(schedule):
                continue

            print(f"[AUTO-PURCHASE] Checking: {schedule.name}")

            # Check availability
            result = self._check_item_availability(schedule)

            if result['in_stock']:
                # Validate price
                if result['price'] <= schedule.auto_purchase_max_price:
                    # Execute purchase
                    self._execute_auto_purchase(schedule, result)
                else:
                    print(f"[AUTO-PURCHASE] Price too high: ¥{result['price']} > ¥{schedule.auto_purchase_max_price}")

            # Update last check time
            self.manager.update_auto_purchase_check_time(schedule.schedule_id)

    def _check_item_availability(self, schedule: Schedule) -> dict:
        """
        Check if item is in stock using keyword search.

        Strategy:
        1. If direct URL: scrape that page
        2. If keyword: search all stores using keyword URL
        3. Parse results for in-stock items
        4. Return first in-stock match

        Returns:
            {
                'in_stock': bool,
                'price': int,
                'url': str,
                'shop_code': str,
                'item_code': str
            }
        """
        from bs4 import BeautifulSoup
        from urllib.parse import quote
        from browser_mimic import BrowserMimic

        mimic = BrowserMimic()

        # Determine URL to check
        if schedule.auto_purchase_url and 'itemCode=' in schedule.auto_purchase_url:
            # Direct item URL
            check_url = schedule.auto_purchase_url
            is_search = False
        else:
            # Search keyword across all stores
            keyword = schedule.auto_purchase_keyword or schedule.name
            check_url = f"https://order.mandarake.co.jp/order/listPage/list?keyword={quote(keyword)}&lang=en"
            is_search = True

        # Fetch page
        response = mimic.get(check_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        if is_search:
            # Parse search results
            result_items = soup.find_all('div', class_='block', attrs={'data-itemidx': True})

            for result in result_items:
                # Skip sold out
                soldout = result.find('div', class_='soldout')
                if soldout:
                    continue

                # Extract details
                item_code = result.get('data-itemidx', '')

                shop_elem = result.find('p', class_='shop')
                shop_name = shop_elem.get_text(strip=True) if shop_elem else 'unknown'

                price_div = result.find('div', class_='price')
                price_text = price_div.get_text(strip=True) if price_div else '0'
                price_jpy = int(''.join(c for c in price_text if c.isdigit()))

                title_div = result.find('div', class_='title')
                title_link = title_div.find('a') if title_div else None
                item_url = f"https://order.mandarake.co.jp{title_link['href']}" if title_link else ''

                # Found in-stock item!
                return {
                    'in_stock': True,
                    'price': price_jpy,
                    'url': item_url,
                    'shop_code': self._shop_name_to_code(shop_name),
                    'item_code': item_code
                }

            return {'in_stock': False}

        else:
            # Direct item page check
            # Check for "Add to Cart" button or "Sold Out" indicator
            soldout = soup.find('div', class_='soldout') or soup.find(string=lambda t: t and 'Sold Out' in t)

            if soldout:
                return {'in_stock': False}

            # Extract price
            price_elem = soup.find('td', class_='price') or soup.find('div', class_='price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_jpy = int(''.join(c for c in price_text if c.isdigit()))

                return {
                    'in_stock': True,
                    'price': price_jpy,
                    'url': schedule.auto_purchase_url,
                    'shop_code': self._extract_shop_from_url(schedule.auto_purchase_url),
                    'item_code': self._extract_item_code_from_url(schedule.auto_purchase_url)
                }

            return {'in_stock': False}

    def _execute_auto_purchase(self, schedule: Schedule, item_data: dict):
        """
        Execute automatic purchase.

        Steps:
        1. Add item to cart
        2. Execute checkout
        3. Mark schedule as purchased
        4. Notify user

        Args:
            schedule: Schedule with auto-purchase config
            item_data: Item details from availability check
        """
        try:
            print(f"[AUTO-PURCHASE] Purchasing: {schedule.name} at ¥{item_data['price']}")

            # 1. Add to cart
            add_result = self.cart_manager.add_item_to_cart(
                url=item_data['url'],
                shop_code=item_data['shop_code']
            )

            if not add_result['success']:
                print(f"[AUTO-PURCHASE] Failed to add to cart: {add_result.get('error')}")
                return

            # 2. Execute checkout
            checkout_result = self.cart_manager.execute_checkout()

            if checkout_result['success']:
                # 3. Mark as purchased
                self.manager.mark_auto_purchase_completed(
                    schedule.schedule_id,
                    purchased_price=item_data['price'],
                    order_id=checkout_result.get('order_id')
                )

                # 4. Notify user
                self._notify_purchase_success(schedule, item_data, checkout_result)

                print(f"[AUTO-PURCHASE] ✓ Successfully purchased: {schedule.name}")
            else:
                print(f"[AUTO-PURCHASE] Checkout failed: {checkout_result.get('error')}")

        except Exception as e:
            print(f"[AUTO-PURCHASE] Error during purchase: {e}")

    def _notify_purchase_success(self, schedule: Schedule, item_data: dict, checkout_result: dict):
        """Send desktop notification and log purchase."""
        from gui.ui_helpers import show_notification

        message = (
            f"Auto-purchased: {schedule.name}\n"
            f"Price: ¥{item_data['price']:,}\n"
            f"Order: {checkout_result.get('order_id', 'N/A')}"
        )

        show_notification("Auto-Purchase Success", message)

        # Log to file
        self._log_purchase(schedule, item_data, checkout_result)
```

### 5. Schedule Manager Extensions

**New methods in `ScheduleManager`** (`gui/schedule_manager.py`):

```python
def create_auto_purchase_schedule(
    self,
    name: str,
    url_or_keyword: str,
    last_price: int,
    max_price: Optional[int] = None,
    check_interval: int = 30
) -> Schedule:
    """
    Create new auto-purchase schedule.

    Args:
        name: Item name
        url_or_keyword: Mandarake URL or search keyword
        last_price: Last known price in JPY
        max_price: Max price willing to pay (defaults to last_price * 1.2)
        check_interval: Check every X minutes

    Returns:
        Created schedule
    """
    if max_price is None:
        max_price = int(last_price * 1.2)

    # Determine if URL or keyword
    is_url = url_or_keyword.startswith('http')

    schedule = Schedule(
        schedule_id=0,  # Auto-assigned
        name=name,
        active=True,
        schedule_type=ScheduleType.DAILY,
        frequency_hours=24,  # Run daily checks (actual checks are per-minute)
        config_files=[],  # No config files for auto-purchase
        auto_purchase_enabled=True,
        auto_purchase_url=url_or_keyword if is_url else None,
        auto_purchase_keyword=url_or_keyword if not is_url else None,
        auto_purchase_last_price=last_price,
        auto_purchase_max_price=max_price,
        auto_purchase_check_interval=check_interval
    )

    return self.storage.add_schedule(schedule)

def update_auto_purchase_check_time(self, schedule_id: int):
    """Update last check time for auto-purchase schedule."""
    from datetime import datetime, timedelta

    schedule = self.storage.get_by_id(schedule_id)
    if schedule:
        now = datetime.now()
        schedule.auto_purchase_last_check = now.isoformat()
        schedule.auto_purchase_next_check = (
            now + timedelta(minutes=schedule.auto_purchase_check_interval)
        ).isoformat()
        self.storage.update_schedule(schedule)

def mark_auto_purchase_completed(
    self,
    schedule_id: int,
    purchased_price: int,
    order_id: Optional[str] = None
):
    """Mark auto-purchase as completed and disable monitoring."""
    schedule = self.storage.get_by_id(schedule_id)
    if schedule:
        schedule.auto_purchase_enabled = False
        schedule.active = False  # Stop monitoring
        schedule.name = f"{schedule.name} ✓ PURCHASED"
        self.storage.update_schedule(schedule)

        # Log to purchase history
        self._log_auto_purchase(schedule_id, purchased_price, order_id)
```

### 6. Cart Manager Extensions

**New methods in `CartManager`** (`gui/cart_manager.py`):

```python
def add_item_to_cart(self, url: str, shop_code: str) -> dict:
    """
    Add single item to cart by URL.

    Args:
        url: Item URL
        shop_code: Shop code (e.g. 'nakano')

    Returns:
        {'success': bool, 'error': str}
    """
    try:
        from browser_mimic import BrowserMimic

        # Extract item code from URL
        item_code = self._extract_item_code(url)

        # Add to cart endpoint
        cart_url = f"https://order.mandarake.co.jp/order/cart/add?itemCode={item_code}"

        mimic = BrowserMimic()
        response = mimic.post(cart_url)

        if response.status_code == 200:
            return {'success': True}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}

def execute_checkout(self) -> dict:
    """
    Execute full checkout process.

    Uses stored payment/shipping info to complete order.

    Returns:
        {
            'success': bool,
            'order_id': str,
            'total_jpy': int,
            'error': str
        }
    """
    try:
        # 1. Navigate to cart
        # 2. Verify cart contents
        # 3. Proceed to checkout
        # 4. Fill payment/shipping from stored info
        # 5. Submit order
        # 6. Capture order confirmation

        # Implementation depends on Mandarake's checkout flow
        # This is a placeholder for the full implementation

        return {
            'success': True,
            'order_id': 'ORD-12345',
            'total_jpy': 15000
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}
```

### 7. Storage Schema

**schedules.json enhancement:**

```json
[
  {
    "schedule_id": 1,
    "name": "Yura Kano Photobook 2025",
    "active": true,
    "type": "daily",
    "config_files": [],

    "auto_purchase_enabled": true,
    "auto_purchase_url": null,
    "auto_purchase_keyword": "Yura Kano Photobook 2025",
    "auto_purchase_last_price": 12800,
    "auto_purchase_max_price": 15360,
    "auto_purchase_check_interval": 30,
    "auto_purchase_expiry": "2025-11-01",
    "auto_purchase_last_check": "2025-10-07T10:30:00",
    "auto_purchase_next_check": "2025-10-07T11:00:00"
  }
]
```

**New file: auto_purchase_log.json** (purchase history):

```json
[
  {
    "schedule_id": 1,
    "item_name": "Yura Kano Photobook 2025",
    "purchased_at": "2025-10-07T11:45:00",
    "purchased_price": 12800,
    "order_id": "ORD-12345",
    "url": "https://order.mandarake.co.jp/order/detailPage/item?itemCode=1312244361"
  }
]
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Add auto-purchase fields to `Schedule` dataclass
- [ ] Update `schedule_storage.py` to handle new fields
- [ ] Add auto-purchase columns to scheduler treeview
- [ ] Create "New Auto-Purchase" dialog UI (`gui/auto_purchase_dialog.py`)
- [ ] Add right-click menu to CSV treeview (Mandarake tab)
- [ ] Add right-click menu to eBay comparison treeview (eBay tab)
- [ ] Implement `_item_has_mandarake_data()` check for eBay menu

### Phase 2: Monitoring Logic (Week 2)
- [ ] Implement `_check_auto_purchase_items()` in `ScheduleExecutor`
- [ ] Implement `_check_item_availability()` (keyword search + direct URL)
- [ ] Add `_is_due_for_check()` timing logic
- [ ] Add `update_auto_purchase_check_time()` to manager

### Phase 3: Cart Integration (Week 3)
- [ ] Implement `add_item_to_cart()` in `CartManager`
- [ ] Implement `execute_checkout()` in `CartManager`
- [ ] Add checkout info storage (encrypted)
- [ ] Test full purchase flow (with test mode)

### Phase 4: Purchase Execution (Week 4)
- [ ] Implement `_execute_auto_purchase()` in executor
- [ ] Add purchase validation (price check, confirmations)
- [ ] Implement `mark_auto_purchase_completed()` in manager
- [ ] Add purchase logging to `auto_purchase_log.json`

### Phase 5: UI Polish & Safety (Week 5)
- [ ] Add desktop notifications
- [ ] Add purchase confirmation dialogs (optional)
- [ ] Implement spending limits
- [ ] Add "Configure Checkout Settings" dialog
- [ ] Create user documentation

## Quick Start Workflow

### Method 1: From Mandarake CSV Results (Recommended)

1. **Run Mandarake search** → Results appear in CSV treeview
2. **Right-click out-of-stock item** in CSV treeview
3. **Select "Add to Auto-Purchase Monitor"**
4. **Configure settings:**
   - Max price: ¥15,360 (default +20% of current price)
   - Check every: 30 minutes
   - Expiry: 2025-11-01
5. **Click "Add to Monitor"**
6. Item appears in **Scheduler tab** with "Auto-Purchase: Monitoring..."
7. System checks every 30 minutes
8. When in stock → purchases automatically → shows "Auto-Purchase: Purchased ✓"

### Method 2: From eBay Comparison Results

1. **Run eBay comparison** → Results appear in eBay treeview
2. **Right-click item** in eBay treeview
3. **If item has Mandarake data:**
   - Menu shows: "Add to Auto-Purchase Monitor (Store Item)"
   - Opens auto-purchase dialog with Mandarake URL/price pre-filled
4. **If item has NO Mandarake data:**
   - Menu option is **greyed out**
   - Tooltip: "No Mandarake item linked - use CSV treeview instead"

### Method 3: Manual Entry (Advanced)

1. **Scheduler tab** → Click "New Auto-Purchase"
2. **Enter URL or keyword** manually
3. **Configure settings** and save

## Safety Features

### 1. Price Validation
- Always check current price ≤ max price before purchase
- Don't auto-buy if price increased significantly

### 2. Spending Limits (Global Settings)
- Max daily auto-purchase total: ¥100,000
- Max purchases per hour: 3
- Confirmation required for purchases > ¥50,000

### 3. Expiry Dates
- Auto-purchase monitoring expires after set date
- Prevents indefinite monitoring

### 4. Manual Confirmation (Optional)
- Show confirmation dialog before final purchase
- User can approve/reject in real-time

### 5. Purchase Logging
- Complete audit trail in `auto_purchase_log.json`
- Desktop notifications for all purchases
- Email alerts (optional)

## Advantages of Scheduler-Based Approach

### ✅ Cleaner Architecture
- No mixing of eBay comparison data with auto-purchase monitoring
- Scheduler already handles background tasks
- Reuses existing schedule storage/UI

### ✅ Simpler Data Model
- No need for alert states (YAY, NAY, etc.)
- Just: Active/Monitoring/Purchased
- Fewer database tables

### ✅ Better UX
- All scheduled tasks in one place
- Easy to see what's being monitored
- Clear separation: Alerts = comparison, Scheduler = automation

### ✅ Flexible Monitoring
- Can monitor direct URLs or keywords
- Keywords automatically search all stores
- Same infrastructure for scheduled scrapes and auto-purchase

## Example Scenarios

### Scenario 1: Direct URL Monitoring
```
Item: Nanase Nishino Photobook
URL: https://order.mandarake.co.jp/order/detailPage/item?itemCode=1234567890
Last Price: ¥9,800
Max Price: ¥11,760 (+20%)
Status: Sold Out

→ System checks URL every 30 minutes
→ Detects "Add to Cart" button appears
→ Price still ¥9,800
→ Adds to cart → Checkout → Purchased!
→ Notification: "Auto-purchased Nanase Nishino Photobook for ¥9,800"
```

### Scenario 2: Keyword Monitoring (Multi-Store)
```
Item: Yura Kano First Photobook
Keyword: "Yura Kano first"
Last Price: ¥12,800 (Nakano - Sold Out)
Max Price: ¥15,360

→ System searches keyword every 30 minutes across ALL stores
→ Finds item in Shibuya at ¥13,200 (in stock!)
→ Price ≤ max (✓)
→ Adds to cart → Checkout → Purchased!
→ Notification: "Auto-purchased from Shibuya (was originally Nakano)"
```

### Scenario 3: Price Increase Protection
```
Item: Rare Photobook
Last Price: ¥8,000
Max Price: ¥9,600

→ System finds item back in stock
→ Current price: ¥12,000
→ Price > max (✗)
→ Skips purchase
→ Notification: "Item in stock but price too high: ¥12,000 (max: ¥9,600)"
```

## Summary

This scheduler-based approach provides:

1. ✅ **Clean architecture** - No eBay data mixing with auto-purchase
2. ✅ **Simple workflow** - Monitor → Detect → Purchase
3. ✅ **Multi-store search** - Keyword search finds items across all stores
4. ✅ **Price protection** - Never pay more than max price
5. ✅ **Expiry dates** - Monitoring stops after set date
6. ✅ **Reuses infrastructure** - Scheduler already handles background tasks
7. ✅ **Better UX** - All automation in one tab (Scheduler)
8. ✅ **Safety features** - Spending limits, confirmations, logging

**The system monitors out-of-stock items and automatically purchases them when they become available, all integrated seamlessly into the existing Scheduler tab.**
