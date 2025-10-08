"""
Cart Display UI Components

Provides visual display of cart contents, shop breakdowns, threshold status,
and ROI verification results.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional
import logging


class CartDisplayFrame(ttk.LabelFrame):
    """
    Comprehensive cart management display

    Shows:
    - Shop breakdown (items, totals, threshold status)
    - Total cart value
    - ROI estimate (if available)
    - Threshold warnings
    - Action buttons (Verify ROI, Configure Thresholds)
    """

    def __init__(self, parent, cart_manager, **kwargs):
        super().__init__(parent, text="Cart Overview", padding=10, **kwargs)
        self.cart_manager = cart_manager
        self.logger = logging.getLogger(__name__)

        # Cache exchange rate to avoid fetching on every refresh
        self._exchange_rate_cache = None

        self._create_ui()

    def _create_ui(self):
        """Create cart display UI"""

        # Action buttons row
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            button_frame,
            text="🔄 Refresh Cart",
            command=self._manual_refresh
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text="🔍 Verify Cart ROI",
            command=self._verify_cart_roi
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text="⚙️ Configure Thresholds",
            command=self._configure_thresholds
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text="🌐 Open Cart in Browser",
            command=self._open_cart_in_browser
        ).pack(side=tk.LEFT, padx=2)

        # Shop breakdown frame
        breakdown_frame = ttk.LabelFrame(self, text="Shop Breakdown", padding=5)
        breakdown_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create treeview for shop display
        columns = ('shop', 'items', 'total_jpy', 'total_usd', 'roi', 'status')
        self.shop_tree = ttk.Treeview(
            breakdown_frame,
            columns=columns,
            show='headings',
            height=8
        )

        # Column headers
        self.shop_tree.heading('shop', text='Shop')
        self.shop_tree.heading('items', text='Items')
        self.shop_tree.heading('total_jpy', text='Total (¥)')
        self.shop_tree.heading('total_usd', text='Total ($)')
        self.shop_tree.heading('roi', text='ROI %')
        self.shop_tree.heading('status', text='Status')

        # Column widths
        self.shop_tree.column('shop', width=150)
        self.shop_tree.column('items', width=60, anchor='center')
        self.shop_tree.column('total_jpy', width=100, anchor='e')
        self.shop_tree.column('total_usd', width=100, anchor='e')
        self.shop_tree.column('roi', width=80, anchor='center')
        self.shop_tree.column('status', width=100, anchor='center')

        # Scrollbar
        scrollbar = ttk.Scrollbar(breakdown_frame, orient=tk.VERTICAL, command=self.shop_tree.yview)
        self.shop_tree.configure(yscrollcommand=scrollbar.set)

        self.shop_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Summary frame
        summary_frame = ttk.Frame(self)
        summary_frame.pack(fill=tk.X, pady=5)

        self.summary_label = ttk.Label(
            summary_frame,
            text="Total Cart: 0 items, ¥0 ($0)",
            font=('TkDefaultFont', 10, 'bold')
        )
        self.summary_label.pack(side=tk.LEFT)

        # ROI label (if available)
        self.roi_label = ttk.Label(
            summary_frame,
            text="",
            foreground="blue"
        )
        self.roi_label.pack(side=tk.LEFT, padx=(20, 0))

        # Warnings frame
        self.warnings_frame = ttk.LabelFrame(self, text="⚠️ Warnings", padding=5)
        self.warnings_text = tk.Text(
            self.warnings_frame,
            height=3,
            width=60,
            wrap=tk.WORD,
            state='disabled',
            background='#fff8dc',
            foreground='#8b4513'
        )
        self.warnings_text.pack(fill=tk.BOTH, expand=True)

        # Threshold config display
        threshold_frame = ttk.Frame(self)
        threshold_frame.pack(fill=tk.X, pady=5)

        self.threshold_label = ttk.Label(
            threshold_frame,
            text="Thresholds: Min ¥5,000 | Max ¥50,000 | Max 20 items per shop",
            font=('TkDefaultFont', 8),
            foreground='gray'
        )
        self.threshold_label.pack(side=tk.LEFT)

    def _manual_refresh(self):
        """Manual refresh - clears exchange rate cache"""
        self._exchange_rate_cache = None
        self.refresh_display()

    def refresh_display(self, async_refresh=True):
        """Refresh cart display with current data"""
        if not self.cart_manager or not self.cart_manager.is_connected():
            self._show_not_connected()
            return

        if async_refresh:
            # Show loading state immediately
            self._show_loading()
            # Refresh in background thread
            import threading
            thread = threading.Thread(target=self._refresh_in_background, daemon=True)
            thread.start()
        else:
            # Synchronous refresh
            self._do_refresh()

    def _show_loading(self):
        """Show loading state"""
        self.summary_label.config(text="Loading cart data...")
        self.roi_label.config(text="")
        self.warnings_text.config(state='normal')
        self.warnings_text.delete('1.0', 'end')
        self.warnings_text.config(state='disabled')

    def _refresh_in_background(self):
        """Refresh cart data in background thread"""
        try:
            self._do_refresh()
        except Exception as e:
            self.logger.error(f"Error refreshing cart display: {e}")
            # Schedule error message on main thread
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to refresh cart: {e}"))

    def _do_refresh(self):
        """Do the actual refresh (can be called from background thread)"""
        try:
            # Get cart items from Mandarake
            cart_items = self.cart_manager.cart_api.get_cart_items()

            if cart_items is None:
                self.after(0, lambda: messagebox.showerror("Error", "Failed to fetch cart items from Mandarake"))
                return

            # Group by shop and calculate totals
            shop_breakdown = self._calculate_shop_breakdown(cart_items)

            # Update display on main thread
            self.after(0, lambda: self._update_shop_tree(shop_breakdown))
            self.after(0, lambda: self._update_summary(shop_breakdown))
            self.after(0, lambda: self._update_warnings(shop_breakdown))

        except Exception as e:
            self.logger.error(f"Error refreshing cart display: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to refresh cart: {e}"))

    def _calculate_shop_breakdown(self, cart_items: List[Dict]) -> Dict:
        """
        Calculate shop-level breakdown

        Returns:
            {
                'nakano': {
                    'items': 5,
                    'total_jpy': 12500,
                    'total_usd': 83.50,
                    'status': 'ready',
                    'min_threshold': 5000,
                    'max_threshold': 50000
                },
                ...
                'totals': {
                    'items': 20,
                    'total_jpy': 45000,
                    'total_usd': 300.00
                }
            }
        """
        breakdown = {}
        total_items = 0
        total_jpy = 0

        # Get exchange rate (cached)
        if self._exchange_rate_cache is None:
            from gui.utils import fetch_exchange_rate
            self._exchange_rate_cache = fetch_exchange_rate()

        exchange_rate = self._exchange_rate_cache

        # Group by shop
        for item in cart_items:
            shop_code = item.get('shop_code', 'unknown')

            if shop_code not in breakdown:
                # Get thresholds for this shop
                thresholds = self.cart_manager.storage.get_shop_threshold(shop_code)

                breakdown[shop_code] = {
                    'items': 0,
                    'total_jpy': 0,
                    'total_usd': 0.0,
                    'roi_percent': None,
                    'status': 'unknown',
                    'min_threshold': thresholds.get('min_cart_value', 5000),
                    'max_threshold': thresholds.get('max_cart_value', 50000),
                    'max_items': thresholds.get('max_items', 20)
                }

            # Parse price
            price_str = item.get('price', '¥0')
            price_jpy = int(''.join(c for c in price_str if c.isdigit()))
            price_usd = price_jpy / exchange_rate

            breakdown[shop_code]['items'] += 1
            breakdown[shop_code]['total_jpy'] += price_jpy
            breakdown[shop_code]['total_usd'] += price_usd

            total_items += 1
            total_jpy += price_jpy

        # Get ROI data from last verification
        last_verification = self.cart_manager.storage.get_last_verification()
        if last_verification and last_verification.get('roi_percent'):
            # For now, use overall ROI for all shops (can be enhanced later to track per-shop)
            overall_roi = last_verification['roi_percent']
            for shop_code in breakdown.keys():
                breakdown[shop_code]['roi_percent'] = overall_roi

        # Calculate status for each shop
        for shop_code, data in breakdown.items():
            total = data['total_jpy']
            min_thresh = data['min_threshold']
            max_thresh = data['max_threshold']
            item_count = data['items']
            max_items = data['max_items']

            if total < min_thresh:
                data['status'] = 'below'
                data['status_text'] = f"⚠️ Below Min (¥{min_thresh - total:,} short)"
            elif total > max_thresh:
                data['status'] = 'over'
                data['status_text'] = f"🔴 Over Max"
            elif item_count > max_items:
                data['status'] = 'over_items'
                data['status_text'] = f"🔴 Too Many Items ({item_count}/{max_items})"
            else:
                data['status'] = 'ready'
                data['status_text'] = f"✅ Ready"

        # Add totals
        breakdown['totals'] = {
            'items': total_items,
            'total_jpy': total_jpy,
            'total_usd': total_jpy / exchange_rate
        }

        return breakdown

    def _update_shop_tree(self, breakdown: Dict):
        """Update shop treeview with breakdown data"""
        # Clear existing items
        for item in self.shop_tree.get_children():
            self.shop_tree.delete(item)

        # Add shops (sorted by total value descending)
        shops = [(k, v) for k, v in breakdown.items() if k != 'totals']
        shops.sort(key=lambda x: x[1]['total_jpy'], reverse=True)

        for shop_code, data in shops:
            # Format shop name
            from mandarake_codes import MANDARAKE_STORES
            shop_name = MANDARAKE_STORES.get(shop_code, shop_code.title())

            # Format ROI
            roi_text = f"{data['roi_percent']:.1f}%" if data['roi_percent'] is not None else "Not verified"

            values = (
                shop_name,
                str(data['items']),
                f"¥{data['total_jpy']:,}",
                f"${data['total_usd']:.2f}",
                roi_text,
                data['status_text']
            )

            # Color code by status
            item_id = self.shop_tree.insert('', 'end', values=values)

            if data['status'] == 'below':
                self.shop_tree.item(item_id, tags=('warning',))
            elif data['status'] in ['over', 'over_items']:
                self.shop_tree.item(item_id, tags=('error',))
            else:
                self.shop_tree.item(item_id, tags=('ready',))

        # Configure tags
        self.shop_tree.tag_configure('warning', background='#fff3cd')
        self.shop_tree.tag_configure('error', background='#f8d7da')
        self.shop_tree.tag_configure('ready', background='#d4edda')

    def _update_summary(self, breakdown: Dict):
        """Update summary label"""
        totals = breakdown.get('totals', {})
        total_items = totals.get('items', 0)
        total_jpy = totals.get('total_jpy', 0)
        total_usd = totals.get('total_usd', 0.0)

        self.summary_label.config(
            text=f"Total Cart: {total_items} items, ¥{total_jpy:,} (${total_usd:.2f})"
        )

    def _update_warnings(self, breakdown: Dict):
        """Update warnings section"""
        warnings = []

        # Check each shop for warnings
        for shop_code, data in breakdown.items():
            if shop_code == 'totals':
                continue

            from mandarake_codes import MANDARAKE_STORES
            shop_name = MANDARAKE_STORES.get(shop_code, shop_code.title())

            if data['status'] == 'below':
                shortage = data['min_threshold'] - data['total_jpy']
                warnings.append(
                    f"• {shop_name} cart below minimum (¥{data['total_jpy']:,} < ¥{data['min_threshold']:,}, need ¥{shortage:,} more)"
                )
            elif data['status'] == 'over':
                warnings.append(
                    f"• {shop_name} cart exceeds maximum (¥{data['total_jpy']:,} > ¥{data['max_threshold']:,})"
                )
            elif data['status'] == 'over_items':
                warnings.append(
                    f"• {shop_name} has too many items ({data['items']} > {data['max_items']})"
                )

        # Check if cart needs ROI verification
        # (Check if verification is older than 24 hours)
        last_verification = self.cart_manager.storage.get_last_verification()
        if last_verification:
            from datetime import datetime
            verified_at = datetime.fromisoformat(last_verification['verified_at'])
            hours_ago = (datetime.now() - verified_at).total_seconds() / 3600

            if hours_ago > 24:
                warnings.append(f"• Cart not verified in {int(hours_ago)} hours - recommend ROI re-check")
        elif breakdown.get('totals', {}).get('items', 0) > 0:
            warnings.append("• Cart has never been ROI verified")

        # Update warnings display
        self.warnings_text.config(state='normal')
        self.warnings_text.delete('1.0', 'end')

        if warnings:
            self.warnings_text.insert('1.0', '\n'.join(warnings))
            self.warnings_frame.pack(fill=tk.X, pady=5)
        else:
            self.warnings_text.insert('1.0', "No warnings - cart looks good!")
            self.warnings_frame.pack_forget()  # Hide if no warnings

        self.warnings_text.config(state='disabled')

    def _show_not_connected(self):
        """Show message when cart not connected"""
        # Clear shop tree
        for item in self.shop_tree.get_children():
            self.shop_tree.delete(item)

        self.summary_label.config(text="Not connected to Mandarake cart")
        self.roi_label.config(text="")

        self.warnings_text.config(state='normal')
        self.warnings_text.delete('1.0', 'end')
        self.warnings_text.insert('1.0', "Connect to Mandarake cart to view cart details")
        self.warnings_text.config(state='disabled')
        self.warnings_frame.pack(fill=tk.X, pady=5)

    def _verify_cart_roi(self):
        """Verify cart ROI using eBay comparison"""
        if not self._check_connection():
            return

        # Import ROI verification dialog
        from gui.cart_roi_dialog import CartROIDialog

        dialog = CartROIDialog(self, self.cart_manager)
        dialog.grab_set()
        dialog.wait_window()

        # Refresh display after verification
        self.refresh_display()

    def _configure_thresholds(self):
        """Open threshold configuration dialog"""
        # Thresholds can be configured without connection
        from gui.cart_threshold_dialog import CartThresholdDialog

        dialog = CartThresholdDialog(self, self.cart_manager.storage)
        dialog.grab_set()
        dialog.wait_window()

        # Refresh display after configuration (if connected)
        if self.cart_manager and self.cart_manager.is_connected():
            self.refresh_display()

    def _open_cart_in_browser(self):
        """Open Mandarake cart in web browser"""
        import webbrowser

        # Can open cart URL even without connection
        cart_url = "https://order.mandarake.co.jp/order/cartList/"
        webbrowser.open(cart_url)

    def _check_connection(self) -> bool:
        """
        Check if cart is connected, show error if not

        Returns:
            True if connected, False otherwise
        """
        if not self.cart_manager or not self.cart_manager.is_connected():
            messagebox.showerror(
                "Not Connected",
                "You are not connected to your Mandarake cart.\n\n"
                "Click '🔌 Connect to Cart' button to connect.",
                parent=self
            )
            return False
        return True
