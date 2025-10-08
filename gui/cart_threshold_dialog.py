"""
Cart Threshold Configuration Dialog

Allows user to configure min/max cart values and item limits per shop.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict
import logging


class CartThresholdDialog(tk.Toplevel):
    """
    Dialog for configuring cart thresholds

    Allows per-shop configuration of:
    - Minimum cart value (don't checkout until reached)
    - Maximum cart value (spending limit warning)
    - Maximum items per cart
    """

    def __init__(self, parent, cart_storage):
        super().__init__(parent)
        self.cart_storage = cart_storage
        self.logger = logging.getLogger(__name__)

        self.title("Configure Cart Thresholds")
        self.geometry("700x500")

        # Threshold entries by shop
        self.threshold_entries = {}

        self._create_ui()
        self._load_thresholds()

        # Position at cursor
        from gui.ui_helpers import position_dialog_at_cursor
        position_dialog_at_cursor(self)

    def _create_ui(self):
        """Create threshold configuration UI"""

        # Instructions
        instructions = ttk.Label(
            self,
            text="Configure minimum/maximum cart values and item limits per shop.\n"
                 "Leave blank to use default values.",
            foreground="gray"
        )
        instructions.pack(padx=10, pady=10)

        # Global defaults frame
        defaults_frame = ttk.LabelFrame(self, text="Global Defaults", padding=10)
        defaults_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(defaults_frame, text="Min Cart Value:").grid(row=0, column=0, sticky=tk.W)
        self.default_min_var = tk.IntVar(value=5000)
        ttk.Spinbox(
            defaults_frame,
            from_=0,
            to=100000,
            increment=1000,
            textvariable=self.default_min_var,
            width=15
        ).grid(row=0, column=1, padx=5)
        ttk.Label(defaults_frame, text="¥").grid(row=0, column=2)

        ttk.Label(defaults_frame, text="Max Cart Value:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.default_max_var = tk.IntVar(value=50000)
        ttk.Spinbox(
            defaults_frame,
            from_=0,
            to=500000,
            increment=5000,
            textvariable=self.default_max_var,
            width=15
        ).grid(row=1, column=1, padx=5)
        ttk.Label(defaults_frame, text="¥").grid(row=1, column=2)

        ttk.Label(defaults_frame, text="Max Items:").grid(row=2, column=0, sticky=tk.W)
        self.default_items_var = tk.IntVar(value=20)
        ttk.Spinbox(
            defaults_frame,
            from_=1,
            to=100,
            textvariable=self.default_items_var,
            width=15
        ).grid(row=2, column=1, padx=5)

        ttk.Button(
            defaults_frame,
            text="Apply Defaults to All",
            command=self._apply_defaults_to_all
        ).grid(row=3, column=0, columnspan=3, pady=10)

        # Per-shop configuration
        shops_frame = ttk.LabelFrame(self, text="Per-Shop Configuration", padding=10)
        shops_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create canvas for scrolling
        canvas = tk.Canvas(shops_frame)
        scrollbar = ttk.Scrollbar(shops_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Headers
        ttk.Label(scrollable_frame, text="Shop", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W
        )
        ttk.Label(scrollable_frame, text="Min (¥)", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=1, padx=5, pady=5
        )
        ttk.Label(scrollable_frame, text="Max (¥)", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=2, padx=5, pady=5
        )
        ttk.Label(scrollable_frame, text="Max Items", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=3, padx=5, pady=5
        )
        ttk.Label(scrollable_frame, text="Enabled", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=4, padx=5, pady=5
        )

        # Get all Mandarake shops
        from mandarake_codes import MANDARAKE_STORES

        row = 1
        for shop_code, shop_name in sorted(MANDARAKE_STORES.items(), key=lambda x: x[1]):
            # Shop name
            ttk.Label(scrollable_frame, text=shop_name).grid(
                row=row, column=0, padx=5, pady=2, sticky=tk.W
            )

            # Min value
            min_var = tk.IntVar(value=5000)
            ttk.Spinbox(
                scrollable_frame,
                from_=0,
                to=100000,
                increment=1000,
                textvariable=min_var,
                width=12
            ).grid(row=row, column=1, padx=5, pady=2)

            # Max value
            max_var = tk.IntVar(value=50000)
            ttk.Spinbox(
                scrollable_frame,
                from_=0,
                to=500000,
                increment=5000,
                textvariable=max_var,
                width=12
            ).grid(row=row, column=2, padx=5, pady=2)

            # Max items
            items_var = tk.IntVar(value=20)
            ttk.Spinbox(
                scrollable_frame,
                from_=1,
                to=100,
                textvariable=items_var,
                width=10
            ).grid(row=row, column=3, padx=5, pady=2)

            # Enabled checkbox
            enabled_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                scrollable_frame,
                variable=enabled_var
            ).grid(row=row, column=4, padx=5, pady=2)

            self.threshold_entries[shop_code] = {
                'min': min_var,
                'max': max_var,
                'items': items_var,
                'enabled': enabled_var
            }

            row += 1

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="💾 Save",
            command=self._save_thresholds
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="🔄 Reset to Defaults",
            command=self._reset_to_defaults
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side=tk.LEFT, padx=5)

    def _load_thresholds(self):
        """Load existing thresholds from database"""
        for shop_code, vars_dict in self.threshold_entries.items():
            threshold = self.cart_storage.get_shop_threshold(shop_code)

            if threshold:
                vars_dict['min'].set(threshold.get('min_cart_value', 5000))
                vars_dict['max'].set(threshold.get('max_cart_value', 50000))
                vars_dict['items'].set(threshold.get('max_items', 20))
                vars_dict['enabled'].set(threshold.get('enabled', True))

    def _apply_defaults_to_all(self):
        """Apply global defaults to all shops"""
        min_val = self.default_min_var.get()
        max_val = self.default_max_var.get()
        items_val = self.default_items_var.get()

        for vars_dict in self.threshold_entries.values():
            vars_dict['min'].set(min_val)
            vars_dict['max'].set(max_val)
            vars_dict['items'].set(items_val)
            vars_dict['enabled'].set(True)

    def _reset_to_defaults(self):
        """Reset all thresholds to defaults"""
        if not messagebox.askyesno("Confirm Reset", "Reset all thresholds to defaults?"):
            return

        for vars_dict in self.threshold_entries.values():
            vars_dict['min'].set(5000)
            vars_dict['max'].set(50000)
            vars_dict['items'].set(20)
            vars_dict['enabled'].set(True)

    def _save_thresholds(self):
        """Save thresholds to database"""
        try:
            for shop_code, vars_dict in self.threshold_entries.items():
                self.cart_storage.set_shop_threshold(
                    shop_code=shop_code,
                    min_cart_value=vars_dict['min'].get(),
                    max_cart_value=vars_dict['max'].get(),
                    max_items=vars_dict['items'].get(),
                    enabled=vars_dict['enabled'].get()
                )

            messagebox.showinfo("Success", "Thresholds saved successfully!")
            self.destroy()

        except Exception as e:
            self.logger.error(f"Error saving thresholds: {e}")
            messagebox.showerror("Error", f"Failed to save thresholds: {e}")
