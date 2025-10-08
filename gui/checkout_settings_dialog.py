"""
Checkout settings configuration dialog with safety warnings.

Allows users to configure automatic checkout settings with clear warnings.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from gui.checkout_settings_storage import CheckoutSettingsStorage


class CheckoutSettingsDialog(tk.Toplevel):
    """Dialog for configuring automatic checkout settings."""

    def __init__(self, parent):
        """
        Initialize checkout settings dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.result = None
        self.storage = CheckoutSettingsStorage()

        # Window configuration
        self.title("⚠️ Auto-Checkout Configuration")
        self.geometry("600x750")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_existing_settings()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        """Build the dialog UI."""
        # Warning banner
        warning_frame = ttk.Frame(self, style='Warning.TFrame')
        warning_frame.pack(fill=tk.X, padx=0, pady=0)

        warning_label = tk.Label(
            warning_frame,
            text="⚠️ WARNING: AUTOMATIC CHECKOUT ENABLED ⚠️",
            font=('TkDefaultFont', 12, 'bold'),
            bg='#ff6b6b',
            fg='white',
            pady=10
        )
        warning_label.pack(fill=tk.X)

        # Main content
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Warning text
        warning_text = tk.Text(
            main_frame,
            height=6,
            wrap=tk.WORD,
            bg='#fff3cd',
            relief=tk.FLAT,
            padx=10,
            pady=10,
            font=('TkDefaultFont', 9)
        )
        warning_text.pack(fill=tk.X, pady=(0, 15))
        warning_text.insert('1.0',
            "⚠️ IMPORTANT SAFETY NOTICE:\n\n"
            "• This will automatically complete REAL purchases without confirmation\n"
            "• Credit card charges will be processed immediately\n"
            "• You are responsible for all automated purchases\n"
            "• Use spending limits to prevent excessive purchases\n"
            "• Test with low-value items first"
        )
        warning_text.config(state='disabled')

        # Shipping information
        shipping_frame = ttk.LabelFrame(main_frame, text="Shipping Information", padding=10)
        shipping_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(shipping_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(shipping_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky=tk.EW, pady=2)

        ttk.Label(shipping_frame, text="Email:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.email_var = tk.StringVar()
        ttk.Entry(shipping_frame, textvariable=self.email_var, width=40).grid(row=1, column=1, sticky=tk.EW, pady=2)

        ttk.Label(shipping_frame, text="Postal Code:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.postal_var = tk.StringVar()
        ttk.Entry(shipping_frame, textvariable=self.postal_var, width=40).grid(row=2, column=1, sticky=tk.EW, pady=2)

        ttk.Label(shipping_frame, text="Address:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.address_var = tk.StringVar()
        ttk.Entry(shipping_frame, textvariable=self.address_var, width=40).grid(row=3, column=1, sticky=tk.EW, pady=2)

        ttk.Label(shipping_frame, text="Phone:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.phone_var = tk.StringVar()
        ttk.Entry(shipping_frame, textvariable=self.phone_var, width=40).grid(row=4, column=1, sticky=tk.EW, pady=2)

        shipping_frame.columnconfigure(1, weight=1)

        # Payment method
        payment_frame = ttk.LabelFrame(main_frame, text="Payment Method", padding=10)
        payment_frame.pack(fill=tk.X, pady=(0, 10))

        self.payment_var = tk.StringVar(value='stored')
        ttk.Radiobutton(payment_frame, text="Stored payment method (in Mandarake account)", variable=self.payment_var, value='stored').pack(anchor=tk.W)
        ttk.Radiobutton(payment_frame, text="Credit card", variable=self.payment_var, value='credit_card', state='disabled').pack(anchor=tk.W)
        ttk.Radiobutton(payment_frame, text="PayPal", variable=self.payment_var, value='paypal', state='disabled').pack(anchor=tk.W)

        # Spending limits
        limits_frame = ttk.LabelFrame(main_frame, text="Safety Limits", padding=10)
        limits_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(limits_frame, text="Max per purchase:").grid(row=0, column=0, sticky=tk.W, pady=2)
        limit_frame = ttk.Frame(limits_frame)
        limit_frame.grid(row=0, column=1, sticky=tk.W, pady=2)
        ttk.Label(limit_frame, text="¥").pack(side=tk.LEFT)
        self.max_purchase_var = tk.IntVar(value=50000)
        ttk.Entry(limit_frame, textvariable=self.max_purchase_var, width=15).pack(side=tk.LEFT)

        ttk.Label(limits_frame, text="Max daily total:").grid(row=1, column=0, sticky=tk.W, pady=2)
        daily_frame = ttk.Frame(limits_frame)
        daily_frame.grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Label(daily_frame, text="¥").pack(side=tk.LEFT)
        self.max_daily_var = tk.IntVar(value=100000)
        ttk.Entry(daily_frame, textvariable=self.max_daily_var, width=15).pack(side=tk.LEFT)

        ttk.Label(limits_frame, text="Max purchases/hour:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.max_hourly_var = tk.IntVar(value=3)
        ttk.Entry(limits_frame, textvariable=self.max_hourly_var, width=15).grid(row=2, column=1, sticky=tk.W, pady=2)

        limits_frame.columnconfigure(1, weight=1)

        # Enable checkbox
        enable_frame = ttk.Frame(main_frame)
        enable_frame.pack(fill=tk.X, pady=(10, 0))

        self.auto_checkout_var = tk.BooleanVar(value=False)
        enable_check = ttk.Checkbutton(
            enable_frame,
            text="✓ Enable Automatic Checkout (I understand the risks)",
            variable=self.auto_checkout_var,
            command=self._on_enable_toggle
        )
        enable_check.pack(anchor=tk.W)

        # Confirmation text
        self.confirm_frame = ttk.Frame(main_frame)
        self.confirm_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(self.confirm_frame, text="Type 'ENABLE' to confirm:", foreground='red').pack(anchor=tk.W)
        self.confirm_var = tk.StringVar()
        self.confirm_entry = ttk.Entry(self.confirm_frame, textvariable=self.confirm_var, width=20)
        self.confirm_entry.pack(anchor=tk.W, pady=5)
        self.confirm_frame.pack_forget()  # Hide initially

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(button_frame, text="Save Settings", command=self._on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT)

    def _on_enable_toggle(self):
        """Handle enable checkbox toggle."""
        if self.auto_checkout_var.get():
            self.confirm_frame.pack(fill=tk.X, pady=(10, 0))
        else:
            self.confirm_frame.pack_forget()

    def _load_existing_settings(self):
        """Load existing settings if available."""
        settings = self.storage.load_settings()
        if settings:
            shipping = settings.get('shipping_info', {})
            self.name_var.set(shipping.get('name', ''))
            self.email_var.set(shipping.get('email', ''))
            self.postal_var.set(shipping.get('postal_code', ''))
            self.address_var.set(shipping.get('address', ''))
            self.phone_var.set(shipping.get('phone', ''))

            self.payment_var.set(settings.get('payment_method', 'stored'))

            limits = settings.get('spending_limits', {})
            self.max_purchase_var.set(limits.get('max_per_purchase_jpy', 50000))
            self.max_daily_var.set(limits.get('max_daily_jpy', 100000))
            self.max_hourly_var.set(limits.get('max_purchases_per_hour', 3))

            self.auto_checkout_var.set(settings.get('auto_checkout_enabled', False))
            if self.auto_checkout_var.get():
                self.confirm_frame.pack(fill=tk.X, pady=(10, 0))

    def _on_save(self):
        """Handle save button click."""
        # Validate required fields
        if not self.name_var.get():
            messagebox.showerror("Missing Information", "Name is required")
            return

        if not self.email_var.get():
            messagebox.showerror("Missing Information", "Email is required")
            return

        if not self.postal_var.get():
            messagebox.showerror("Missing Information", "Postal code is required")
            return

        if not self.address_var.get():
            messagebox.showerror("Missing Information", "Address is required")
            return

        if not self.phone_var.get():
            messagebox.showerror("Missing Information", "Phone is required")
            return

        # Validate confirmation if auto-checkout is enabled
        if self.auto_checkout_var.get():
            if self.confirm_var.get() != 'ENABLE':
                messagebox.showerror(
                    "Confirmation Required",
                    "You must type 'ENABLE' to confirm automatic checkout"
                )
                return

            # Final warning
            if not messagebox.askyesno(
                "⚠️ FINAL CONFIRMATION",
                "Automatic checkout will complete REAL purchases without asking!\n\n"
                "Charges will be made to your payment method immediately.\n\n"
                "Are you absolutely sure you want to enable this?",
                icon='warning'
            ):
                return

        # Save settings
        shipping_info = {
            'name': self.name_var.get(),
            'email': self.email_var.get(),
            'postal_code': self.postal_var.get(),
            'address': self.address_var.get(),
            'phone': self.phone_var.get()
        }

        spending_limits = {
            'max_per_purchase_jpy': self.max_purchase_var.get(),
            'max_daily_jpy': self.max_daily_var.get(),
            'max_purchases_per_hour': self.max_hourly_var.get()
        }

        self.storage.save_settings(
            shipping_info=shipping_info,
            payment_method=self.payment_var.get(),
            auto_checkout_enabled=self.auto_checkout_var.get(),
            spending_limits=spending_limits
        )

        self.result = True
        self.destroy()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = False
        self.destroy()
