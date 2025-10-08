# ✅ "Add Yays to Cart" - Complete Workflow

## Status: ENDPOINT CAPTURED & IMPLEMENTED

**Endpoint:** `https://tools.mandarake.co.jp/basket/add/`
**Implementation:** `scrapers/mandarake_cart_api.py::add_to_cart()`
**Test Script:** `test_add_to_cart.py`

## Overview

One-click button to add all items marked as "Yay" in the Alert tab directly to your Mandarake cart, with automatic threshold checking and smart warnings.

---

## 🎯 User Workflow

### Step 1: Mark Items as "Yay"
User reviews items in Alert tab and marks profitable ones as "Yay":
```
Alert Tab - Review/Alerts Section
├─ Pending (15 items)
│  └─ [User reviews and marks 8 as "Yay", 7 as "Nay"]
├─ Yay (8 items) ← These will be added to cart
└─ Nay (7 items)
```

### Step 2: Click "Add Yays to Cart"
```
┌─ Cart Management Section ──────────────────────────────────┐
│                                                             │
│  [Add Yays to Cart] ← One click                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Step 3: System Groups by Shop & Checks Thresholds
```
System automatically:
1. Fetches all 8 "Yay" items from alerts
2. Groups by shop:
   - Nakano: 3 items, ¥8,500
   - Shibuya: 2 items, ¥2,100
   - SAHRA: 3 items, ¥6,200

3. Checks thresholds:
   ✅ Nakano: Above ¥5,000
   ⚠️ Shibuya: Below ¥5,000
   ✅ SAHRA: Above ¥5,000
```

### Step 4: Shows Threshold Warning (if needed)
```
┌─ Cart Threshold Warning ───────────────────────────────────┐
│                                                             │
│  ⚠️ Some shops are below minimum threshold:                │
│                                                             │
│  • Shibuya: ¥2,100 < ¥5,000 (¥2,900 short)                │
│                                                             │
│  Adding these items now may result in higher shipping      │
│  costs per item.                                            │
│                                                             │
│  ☐ Add only ready shops (Nakano, SAHRA) [6 items]         │
│  ☐ Add all items anyway [8 items]                          │
│  ☐ Cancel and wait for more items                          │
│                                                             │
│  [Proceed]  [Cancel]                                       │
└─────────────────────────────────────────────────────────────┘
```

### Step 5: Bulk Add to Cart
```
System adds items to Mandarake cart:
[Progress: 1/8] Adding "Item 1" to Nakano cart...
[Progress: 2/8] Adding "Item 2" to Nakano cart...
[Progress: 3/8] Adding "Item 3" to Nakano cart...
[Progress: 4/8] Adding "Item 4" to Shibuya cart...
...
[Progress: 8/8] Adding "Item 8" to SAHRA cart...

✅ Success: 8 items added to cart
❌ Failed: 0 items
```

### Step 6: Update Alert States
```
Items successfully added to cart are automatically marked:
Yay (8 items) → In Cart (8 items)

Alert tab now shows:
├─ Yay (0 items)
├─ In Cart (8 items) ← New state
└─ ...
```

---

## 💻 Technical Implementation

### 1. Fetch Yay Items from Alerts

```python
def add_yays_to_cart(self, force_below_threshold=False):
    """Add all Yay items to Mandarake cart"""

    # 1. Get all Yay alerts
    yay_alerts = self.alert_manager.get_alerts_by_state('yay')

    if not yay_alerts:
        return {
            'success': False,
            'message': 'No items marked as Yay',
            'added': [],
            'failed': []
        }

    # Convert alerts to cart format
    cart_items = []
    for alert in yay_alerts:
        cart_items.append({
            'alert_id': alert['id'],
            'product_id': alert['product_id'],
            'title': alert['title'],
            'price_jpy': alert['price_jpy'],
            'shop_code': alert['shop_code'],
            'shop_name': alert['shop_name'],
            'image_url': alert['image_url'],
            'product_url': alert['product_url']
        })
```

### 2. Group by Shop

```python
    # 2. Group by shop
    by_shop = {}
    for item in cart_items:
        shop = item['shop_code']
        if shop not in by_shop:
            by_shop[shop] = []
        by_shop[shop].append(item)

    # Result:
    # {
    #   'nkn': [item1, item2, item3],
    #   'shr': [item4, item5],
    #   'sah': [item6, item7, item8]
    # }
```

### 3. Check Thresholds

```python
    # 3. Check thresholds per shop
    warnings = []
    for shop, items in by_shop.items():
        total = sum(item['price_jpy'] for item in items)
        threshold = self.storage.get_shop_threshold(shop)

        if total < threshold['min_cart_value']:
            warnings.append({
                'shop_code': shop,
                'shop_name': items[0]['shop_name'],
                'total': total,
                'threshold': threshold['min_cart_value'],
                'shortage': threshold['min_cart_value'] - total,
                'items': items
            })
```

### 4. Show Warning Dialog (if needed)

```python
    # 4. If warnings and not forced, return for user decision
    if warnings and not force_below_threshold:
        # GUI shows warning dialog with 3 options:
        # - Add only ready shops
        # - Add all anyway
        # - Cancel

        return {
            'success': False,
            'need_confirmation': True,
            'warnings': warnings,
            'ready_shops': [s for s in by_shop.keys()
                           if s not in [w['shop_code'] for w in warnings]],
            'total_items': len(cart_items)
        }
```

### 5. Bulk Add to Cart

```python
    # 5. Add items to cart
    added = []
    failed = []

    for shop, items in by_shop.items():
        for item in items:
            try:
                # POST to Mandarake add-to-cart endpoint
                success = self.cart_api.add_to_cart(
                    product_id=item['product_id'],
                    shop_code=shop,
                    quantity=1
                )

                if success:
                    added.append(item)

                    # Save to local cart storage
                    self.storage.add_cart_item(
                        alert_id=item['alert_id'],
                        product_data=item
                    )
                    self.storage.mark_in_cart(item['alert_id'], True)

                    # Update alert state: Yay → In Cart
                    self.alert_manager.update_alert_state(
                        item['alert_id'],
                        'in_cart'
                    )
                else:
                    failed.append({**item, 'error': 'API returned false'})

            except Exception as e:
                failed.append({**item, 'error': str(e)})

    return {
        'success': True,
        'added': added,
        'failed': failed,
        'message': f"Added {len(added)} items to cart"
    }
```

---

## 🖥️ GUI Implementation

### Cart Management Section in Alert Tab

```python
class AlertTab(ttk.Frame):
    """Alert/Review tab with cart management"""

    def _create_cart_section(self):
        """Create cart management section"""

        cart_frame = ttk.LabelFrame(self, text="Cart Management")
        cart_frame.pack(fill=tk.X, padx=5, pady=5)

        # Connection status
        self.cart_status_label = ttk.Label(
            cart_frame,
            text="Not connected to Mandarake cart"
        )
        self.cart_status_label.pack(pady=5)

        # Buttons frame
        btn_frame = ttk.Frame(cart_frame)
        btn_frame.pack(pady=5)

        # Add Yays to Cart button
        self.add_yays_btn = ttk.Button(
            btn_frame,
            text="Add Yays to Cart",
            command=self._on_add_yays_to_cart,
            state='disabled'  # Enabled when connected
        )
        self.add_yays_btn.pack(side=tk.LEFT, padx=5)

        # Verify ROI button (dropdown)
        self.verify_roi_btn = ttk.Menubutton(
            btn_frame,
            text="Verify ROI ▼",
            state='disabled'
        )
        roi_menu = tk.Menu(self.verify_roi_btn, tearoff=0)
        roi_menu.add_command(
            label="Text Search",
            command=lambda: self._verify_cart_roi('text')
        )
        roi_menu.add_command(
            label="Image Compare",
            command=lambda: self._verify_cart_roi('image')
        )
        roi_menu.add_command(
            label="Hybrid (Both)",
            command=lambda: self._verify_cart_roi('hybrid')
        )
        self.verify_roi_btn['menu'] = roi_menu
        self.verify_roi_btn.pack(side=tk.LEFT, padx=5)

        # Open in Browser
        ttk.Button(
            btn_frame,
            text="Open in Browser",
            command=self._open_cart_in_browser,
            state='disabled'
        ).pack(side=tk.LEFT, padx=5)

        # Shop breakdown tree
        self._create_shop_breakdown_tree(cart_frame)
```

### Add Yays Handler

```python
    def _on_add_yays_to_cart(self):
        """Handle Add Yays to Cart button click"""

        # Get yay count
        yay_count = self.alert_manager.get_alert_count_by_state('yay')

        if yay_count == 0:
            messagebox.showinfo(
                "No Yays",
                "No items marked as 'Yay' to add to cart."
            )
            return

        # Confirm action
        if not messagebox.askyesno(
            "Confirm",
            f"Add {yay_count} Yay items to Mandarake cart?"
        ):
            return

        # Disable button during operation
        self.add_yays_btn['state'] = 'disabled'
        self.cart_status_label['text'] = f"Adding {yay_count} items..."

        # Run in background thread
        def worker():
            try:
                result = self.cart_manager.add_yays_to_cart()

                # Update UI in main thread
                self.after(0, self._handle_add_result, result)

            except Exception as e:
                self.after(0, self._handle_add_error, str(e))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
```

### Handle Results

```python
    def _handle_add_result(self, result):
        """Handle add to cart result"""

        # Re-enable button
        self.add_yays_btn['state'] = 'normal'

        if result.get('need_confirmation'):
            # Show threshold warning dialog
            self._show_threshold_warning(result)
            return

        if result['success']:
            added = len(result['added'])
            failed = len(result['failed'])

            # Update status
            self.cart_status_label['text'] = \
                f"✅ Added {added} items to cart"

            # Show detailed result
            msg = f"Successfully added {added} items to cart"
            if failed > 0:
                msg += f"\n❌ {failed} items failed to add"

            messagebox.showinfo("Cart Updated", msg)

            # Refresh alert list and cart breakdown
            self.refresh_alerts()
            self.refresh_cart_breakdown()
        else:
            messagebox.showerror("Error", result.get('message', 'Unknown error'))
```

### Threshold Warning Dialog

```python
    def _show_threshold_warning(self, result):
        """Show threshold warning dialog"""

        dialog = tk.Toplevel(self)
        dialog.title("Cart Threshold Warning")
        dialog.geometry("500x400")

        # Warning message
        msg_frame = ttk.Frame(dialog)
        msg_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            msg_frame,
            text="⚠️ Some shops are below minimum threshold:",
            font=('', 10, 'bold')
        ).pack(anchor=tk.W)

        # List warnings
        for warning in result['warnings']:
            warn_text = (
                f"• {warning['shop_name']}: "
                f"¥{warning['total']:,} < ¥{warning['threshold']:,} "
                f"(¥{warning['shortage']:,} short)"
            )
            ttk.Label(msg_frame, text=warn_text).pack(anchor=tk.W, padx=20)

        ttk.Label(
            msg_frame,
            text="\nAdding items now may result in higher shipping costs per item.",
            wraplength=450
        ).pack(anchor=tk.W, pady=(10, 0))

        # Options
        opt_frame = ttk.Frame(dialog)
        opt_frame.pack(fill=tk.X, padx=20, pady=10)

        option_var = tk.StringVar(value='ready')

        ready_count = len([i for shop in result['ready_shops']
                          for i in result.get('by_shop', {}).get(shop, [])])

        ttk.Radiobutton(
            opt_frame,
            text=f"Add only ready shops ({ready_count} items)",
            variable=option_var,
            value='ready'
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            opt_frame,
            text=f"Add all items anyway ({result['total_items']} items)",
            variable=option_var,
            value='all'
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            opt_frame,
            text="Cancel and wait for more items",
            variable=option_var,
            value='cancel'
        ).pack(anchor=tk.W)

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)

        def on_proceed():
            choice = option_var.get()
            dialog.destroy()

            if choice == 'ready':
                # Add only ready shops
                self._add_ready_shops_only(result['ready_shops'])
            elif choice == 'all':
                # Force add all (bypass threshold check)
                self.cart_manager.add_yays_to_cart(force_below_threshold=True)
            # else: cancel (do nothing)

        ttk.Button(btn_frame, text="Proceed", command=on_proceed).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
```

---

## 📊 Shop Breakdown Display

After adding items, show live cart breakdown:

```python
    def _create_shop_breakdown_tree(self, parent):
        """Create shop breakdown treeview"""

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview
        columns = ('items', 'total', 'status')
        self.shop_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='tree headings',
            height=8
        )

        self.shop_tree.heading('#0', text='Shop')
        self.shop_tree.heading('items', text='Items')
        self.shop_tree.heading('total', text='Total (¥)')
        self.shop_tree.heading('status', text='Status')

        self.shop_tree.column('#0', width=150)
        self.shop_tree.column('items', width=60, anchor='center')
        self.shop_tree.column('total', width=100, anchor='e')
        self.shop_tree.column('status', width=120)

        self.shop_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.shop_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.shop_tree['yscrollcommand'] = scrollbar.set

    def refresh_cart_breakdown(self):
        """Refresh shop breakdown display"""

        # Clear existing
        for item in self.shop_tree.get_children():
            self.shop_tree.delete(item)

        # Get breakdown
        breakdown = self.cart_manager.get_shop_breakdown()

        total_items = 0
        total_value = 0

        for shop, data in sorted(breakdown.items()):
            # Status icon
            status_icon = {
                'ready': '✅',
                'below': '⚠️',
                'over': '🔴'
            }.get(data['status'], '')

            status_text = f"{status_icon} {data['status'].title()}"

            # Insert row
            self.shop_tree.insert(
                '',
                'end',
                text=shop,
                values=(
                    data['items'],
                    f"¥{data['total_jpy']:,}",
                    status_text
                )
            )

            total_items += data['items']
            total_value += data['total_jpy']

        # Add total row
        self.shop_tree.insert(
            '',
            'end',
            text='TOTAL',
            values=(
                total_items,
                f"¥{total_value:,}",
                ''
            ),
            tags=('total',)
        )

        self.shop_tree.tag_configure('total', font=('', 9, 'bold'))
```

---

## 🔍 What We Need to Capture

To make "Add Yays to Cart" work, we need to capture the add-to-cart POST request:

### Using Browser DevTools

1. **Open Mandarake** in browser
2. **Open DevTools** (F12) → Network tab
3. **Add any item to cart** manually
4. **Find the POST request** in Network tab
5. **Capture**:
   - URL endpoint (e.g., `/cart/add` or similar)
   - POST parameters (productId, shopCode, quantity, etc.)
   - Required headers (CSRF token, etc.)

### Example Captured Request

```http
POST https://cart.mandarake.co.jp/cart/add HTTP/1.1
Content-Type: application/x-www-form-urlencoded

itemCode=1126279062
&shopCode=nkn
&quantity=1
&_csrf=abc123token
&referrer=/order/detailPage/item
```

Then update `mandarake_cart_api.py`:

```python
def add_to_cart(self, product_id: str, shop_code: str = None, quantity: int = 1) -> bool:
    """Add item to cart (with real endpoint)"""

    url = f"{self.cart_url}/cart/add"  # ← Real endpoint

    data = {
        'itemCode': product_id,
        'shopCode': shop_code,
        'quantity': quantity,
        # Add any other required parameters
    }

    response = self.session.post(url, data=data)
    return response.status_code == 200
```

---

## ✅ Benefits of "Add Yays to Cart"

1. **One Click** - Add 8, 10, 20+ items instantly
2. **Smart Grouping** - Automatically organized by shop
3. **Threshold Safety** - Warns before adding low-value carts
4. **Bulk Efficiency** - Much faster than manual adding
5. **State Tracking** - Alerts automatically update to "In Cart"
6. **Progress Feedback** - See each item being added
7. **Error Handling** - Shows which items failed and why

---

**Status**: Implementation ready, just need add-to-cart endpoint!
**Next**: Capture POST request and update `add_to_cart()` method

