"""
Cart Connection Dialog

Simple dialog for connecting to Mandarake cart via URL.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging


class CartConnectionDialog(tk.Toplevel):
    """
    Dialog for connecting to Mandarake cart

    User pastes their cart URL (with jsessionid) to establish connection.
    """

    def __init__(self, parent, cart_manager):
        super().__init__(parent)
        self.cart_manager = cart_manager
        self.logger = logging.getLogger(__name__)
        self.connected = False

        self.title("Connect to Mandarake Cart")
        self.geometry("650x400")
        self.resizable(False, False)

        self._create_ui()

        # Center on parent
        self.transient(parent)
        self.grab_set()

    def _create_ui(self):
        """Create connection dialog UI"""

        # Instructions
        instructions = ttk.Label(
            self,
            text="To connect to your Mandarake cart:\n\n"
                 "METHOD 1 (Recommended): Export cookies using Cookie-Editor\n"
                 "  1. Install Cookie-Editor browser extension\n"
                 "  2. Open cart.mandarake.co.jp (logged in)\n"
                 "  3. Click extension → Export → Save as mandarake_cookies.json\n"
                 "  4. Place file in project folder, then restart GUI\n\n"
                 "METHOD 2: Paste cart URL with jsessionid\n"
                 "  Example: https://order.mandarake.co.jp/...;jsessionid=...\n"
                 "  (Note: te-uniquekey URLs often don't work)",
            justify=tk.LEFT,
            padding=10,
            font=('TkDefaultFont', 9)
        )
        instructions.pack(fill=tk.X, pady=10)

        # URL entry
        url_frame = ttk.Frame(self)
        url_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(url_frame, text="Cart URL:").pack(side=tk.LEFT, padx=(0, 5))

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=60)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        url_entry.focus()

        # Status label
        self.status_label = ttk.Label(
            self,
            text="",
            foreground="gray",
            padding=10
        )
        self.status_label.pack()

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)

        ttk.Button(
            button_frame,
            text="Connect",
            command=self._connect,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        # Bind Enter key to connect
        self.bind('<Return>', lambda e: self._connect())

    def _connect(self):
        """Attempt to connect to cart using provided URL"""
        cart_url = self.url_var.get().strip()

        if not cart_url:
            self.status_label.config(text="Please enter a cart URL", foreground="red")
            return

        # Check if URL contains session info
        if 'jsessionid' not in cart_url.lower() and 'te-uniquekey' not in cart_url.lower():
            self.status_label.config(
                text="⚠️ Warning: URL doesn't contain session info - connection may fail",
                foreground="orange"
            )

        self.status_label.config(text="Connecting...", foreground="blue")
        self.update_idletasks()

        try:
            success, message = self.cart_manager.connect_with_url(cart_url)

            if success:
                self.status_label.config(text=f"✓ {message}", foreground="green")
                self.connected = True
                # Close dialog after short delay
                self.after(1000, self.destroy)
            else:
                self.status_label.config(text=f"✗ {message}", foreground="red")

        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.status_label.config(text=f"✗ Connection failed: {e}", foreground="red")

    def _cancel(self):
        """Cancel and close dialog"""
        self.connected = False
        self.destroy()
