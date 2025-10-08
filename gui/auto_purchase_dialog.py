"""
Auto-purchase dialog for configuring automatic item monitoring and purchasing.

Allows user to set max price, check interval, and expiry date for auto-purchase items.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from datetime import datetime, timedelta

# Optional: tkcalendar for date picker
try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False


class AutoPurchaseDialog(tk.Toplevel):
    """Dialog for configuring auto-purchase settings."""

    def __init__(self, parent, item_name: str = "", url: str = "",
                 last_price: int = 0, shop: str = ""):
        """
        Initialize auto-purchase dialog.

        Args:
            parent: Parent widget
            item_name: Item title
            url: Mandarake URL (item or search)
            last_price: Last known price in JPY
            shop: Shop name (e.g. "Nakano")
        """
        super().__init__(parent)
        self.result = None
        self.item_name = item_name
        self.url = url
        self.last_price = last_price
        self.shop = shop

        # Window configuration
        self.title("Add Auto-Purchase Item")
        self.geometry("500x550")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        self._build_ui()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        """Build the dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Item info section
        info_frame = ttk.LabelFrame(main_frame, text="Item Information", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="Item:").grid(row=0, column=0, sticky=tk.W, pady=2)
        item_label = ttk.Label(info_frame, text=self.item_name, font=('TkDefaultFont', 9, 'bold'))
        item_label.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(info_frame, text="Shop:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=self.shop).grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(info_frame, text="Current Price:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=f"¥{self.last_price:,}").grid(row=2, column=1, sticky=tk.W, pady=2)

        ttk.Label(info_frame, text="Status:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text="Out of Stock", foreground="red").grid(row=3, column=1, sticky=tk.W, pady=2)

        # URL/Keyword section
        url_frame = ttk.LabelFrame(main_frame, text="Monitor Target", padding=10)
        url_frame.pack(fill=tk.X, pady=(0, 10))

        self.url_type = tk.StringVar(value="url" if self.url else "keyword")

        # URL option
        url_radio = ttk.Radiobutton(
            url_frame,
            text="Direct Item URL",
            variable=self.url_type,
            value="url",
            command=self._on_url_type_change
        )
        url_radio.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.grid(row=1, column=0, sticky=tk.EW, pady=2)
        self.url_entry.insert(0, self.url if self.url else "")

        # Keyword option
        keyword_radio = ttk.Radiobutton(
            url_frame,
            text="Search Keyword (monitors all stores)",
            variable=self.url_type,
            value="keyword",
            command=self._on_url_type_change
        )
        keyword_radio.grid(row=2, column=0, sticky=tk.W, pady=(10, 2))

        self.keyword_entry = ttk.Entry(url_frame, width=50)
        self.keyword_entry.grid(row=3, column=0, sticky=tk.EW, pady=2)
        self.keyword_entry.insert(0, self.item_name if not self.url else "")

        url_frame.columnconfigure(0, weight=1)

        # Purchase settings
        settings_frame = ttk.LabelFrame(main_frame, text="Purchase Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Max price
        ttk.Label(settings_frame, text="Max Price:").grid(row=0, column=0, sticky=tk.W, pady=5)
        price_frame = ttk.Frame(settings_frame)
        price_frame.grid(row=0, column=1, sticky=tk.W, pady=5)

        self.max_price_var = tk.IntVar(value=int(self.last_price * 1.2) if self.last_price else 0)
        ttk.Entry(price_frame, textvariable=self.max_price_var, width=10).pack(side=tk.LEFT)
        ttk.Label(price_frame, text=f"¥  (+20% default = ¥{int(self.last_price * 1.2):,})").pack(side=tk.LEFT, padx=(5, 0))

        # Monitoring method
        ttk.Label(settings_frame, text="Monitoring:").grid(row=1, column=0, sticky=tk.W, pady=5)
        method_frame = ttk.Frame(settings_frame)
        method_frame.grid(row=1, column=1, sticky=tk.W, pady=5, columnspan=2)

        self.monitoring_method = tk.StringVar(value='polling')  # Default to polling (safer)
        ttk.Radiobutton(
            method_frame,
            text="RSS (~60s, experimental)",
            variable=self.monitoring_method,
            value='rss'
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            method_frame,
            text="Polling (30min, staggered)",
            variable=self.monitoring_method,
            value='polling'
        ).pack(side=tk.LEFT)

        # Check interval
        ttk.Label(settings_frame, text="Check Every:").grid(row=2, column=0, sticky=tk.W, pady=5)
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.grid(row=2, column=1, sticky=tk.W, pady=5)

        self.check_interval_var = tk.IntVar(value=30)
        ttk.Entry(interval_frame, textvariable=self.check_interval_var, width=10).pack(side=tk.LEFT)
        ttk.Label(interval_frame, text="minutes").pack(side=tk.LEFT, padx=(5, 0))

        # Expiry date
        ttk.Label(settings_frame, text="Stop After:").grid(row=3, column=0, sticky=tk.W, pady=5)

        # Default: 1 month from now
        default_expiry = datetime.now() + timedelta(days=30)

        if HAS_TKCALENDAR:
            self.expiry_date = DateEntry(
                settings_frame,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                year=default_expiry.year,
                month=default_expiry.month,
                day=default_expiry.day
            )
            self.expiry_date.grid(row=3, column=1, sticky=tk.W, pady=5)
        else:
            # Fallback: simple Entry field
            self.expiry_var = tk.StringVar(value=default_expiry.strftime('%Y-%m-%d'))
            self.expiry_entry = ttk.Entry(settings_frame, textvariable=self.expiry_var, width=15)
            self.expiry_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
            ttk.Label(settings_frame, text="(YYYY-MM-DD)", font=('TkDefaultFont', 8)).grid(row=3, column=2, sticky=tk.W, padx=5)

        # Actions section
        actions_frame = ttk.LabelFrame(main_frame, text="Auto-Purchase Actions", padding=10)
        actions_frame.pack(fill=tk.X, pady=(0, 10))

        self.add_to_cart_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            actions_frame,
            text="Add to cart when in stock",
            variable=self.add_to_cart_var,
            state="disabled"
        ).pack(anchor=tk.W)

        self.auto_checkout_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            actions_frame,
            text="Complete checkout automatically",
            variable=self.auto_checkout_var,
            state="disabled"
        ).pack(anchor=tk.W)

        self.confirm_before_purchase_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            actions_frame,
            text="Show confirmation before purchase",
            variable=self.confirm_before_purchase_var
        ).pack(anchor=tk.W)

        # Info note
        note_frame = ttk.Frame(main_frame)
        note_frame.pack(fill=tk.X, pady=(0, 10))

        note_label = ttk.Label(
            note_frame,
            text=f"💡 This item will be checked every 30 minutes.\n    You'll be notified when purchased.",
            foreground="blue"
        )
        note_label.pack(anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Add to Monitor", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT)

        # Update UI state
        self._on_url_type_change()

    def _on_url_type_change(self):
        """Handle URL type radio button change."""
        if self.url_type.get() == "url":
            self.url_entry.config(state="normal")
            self.keyword_entry.config(state="disabled")
        else:
            self.url_entry.config(state="disabled")
            self.keyword_entry.config(state="normal")

    def _on_ok(self):
        """Handle OK button click."""
        # Validate inputs
        max_price = self.max_price_var.get()
        if max_price <= 0:
            messagebox.showerror("Invalid Input", "Max price must be greater than 0")
            return

        check_interval = self.check_interval_var.get()
        if check_interval < 1:
            messagebox.showerror("Invalid Input", "Check interval must be at least 1 minute")
            return

        # Get expiry date (different methods for DateEntry vs Entry)
        if HAS_TKCALENDAR:
            expiry = self.expiry_date.get_date().strftime('%Y-%m-%d')
        else:
            expiry = self.expiry_var.get().strip()
            # Validate format
            try:
                datetime.strptime(expiry, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Invalid Input", "Expiry date must be in YYYY-MM-DD format")
                return

        # Get URL or keyword
        if self.url_type.get() == "url":
            url = self.url_entry.get().strip()
            keyword = None
            if not url:
                messagebox.showerror("Invalid Input", "Please enter a URL")
                return
        else:
            url = None
            keyword = self.keyword_entry.get().strip()
            if not keyword:
                messagebox.showerror("Invalid Input", "Please enter a search keyword")
                return

        # Build result
        self.result = {
            'name': self.item_name,
            'url': url,
            'keyword': keyword,
            'last_price': self.last_price,
            'max_price': max_price,
            'check_interval': check_interval,
            'expiry': expiry,
            'monitoring_method': self.monitoring_method.get(),
            'confirm_before_purchase': self.confirm_before_purchase_var.get()
        }

        self.destroy()

    def _on_cancel(self):
        """Handle Cancel button click."""
        self.result = None
        self.destroy()

    def get_result(self):
        """Get dialog result."""
        return self.result
