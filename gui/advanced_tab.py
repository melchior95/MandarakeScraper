"""
Advanced Settings Tab

This tab provides:
1. Scraper options (fast mode, resume, debug, browser mimic)
2. eBay search method selection
3. Marketplace toggles (Mandarake, eBay, Suruga-ya, DejaJapan, Alerts)
4. Scheduling settings
5. Output settings (CSV path, image folder, thumbnails)
"""

import tkinter as tk
from tkinter import ttk


class AdvancedTab(ttk.Frame):
    """Advanced settings tab for scraper configuration."""

    def __init__(self, parent, settings_manager, main_window):
        """
        Initialize Advanced tab.

        Args:
            parent: Parent widget (notebook)
            settings_manager: Settings manager instance
            main_window: Reference to main window for shared resources
        """
        super().__init__(parent)
        self.settings = settings_manager
        self.main_window = main_window

        # Initialize variables
        self.fast_var = tk.BooleanVar(value=False)
        self.resume_var = tk.BooleanVar(value=True)
        self.debug_var = tk.BooleanVar(value=False)
        self.mimic_var = tk.BooleanVar(value=True)  # Enable by default for Unicode support
        self.max_csv_items_var = tk.StringVar(
            value=str(settings_manager.get_setting('scraper.max_csv_items', 0))
        )
        self.ebay_search_method = tk.StringVar(value="scrapy")
        self.schedule_var = tk.StringVar()
        self.csv_show_thumbnails = tk.BooleanVar(value=True)

        # Marketplace toggles
        marketplace_toggles = settings_manager.get_marketplace_toggles()
        self.mandarake_enabled = tk.BooleanVar(value=marketplace_toggles.get('mandarake', True))
        self.ebay_enabled = tk.BooleanVar(value=marketplace_toggles.get('ebay', True))
        self.surugaya_enabled = tk.BooleanVar(value=marketplace_toggles.get('surugaya', False))
        self.dejapan_enabled = tk.BooleanVar(value=marketplace_toggles.get('dejapan', False))
        self.alerts_enabled = tk.BooleanVar(value=marketplace_toggles.get('alerts', True))

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the Advanced tab UI."""
        pad = {'padx': 5, 'pady': 5}
        current_row = 0

        # Scraper Options Section
        ttk.Label(
            self,
            text="Scraper Options",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        ttk.Checkbutton(
            self,
            text="Fast mode (skip eBay)",
            variable=self.fast_var
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            self,
            text="Resume interrupted runs",
            variable=self.resume_var
        ).grid(row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(
            self,
            text="Debug logging",
            variable=self.debug_var
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            self,
            text="Use browser mimic (recommended for Japanese text)",
            variable=self.mimic_var
        ).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        self.mimic_var.trace_add('write', self._on_mimic_changed)
        current_row += 1

        # Max CSV items control
        ttk.Label(
            self,
            text="Max CSV items (0 = unlimited):"
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        max_csv_entry = ttk.Entry(
            self,
            textvariable=self.max_csv_items_var,
            width=10
        )
        max_csv_entry.grid(row=current_row, column=1, sticky=tk.W, **pad)
        self.max_csv_items_var.trace_add('write', self._on_max_csv_items_changed)
        current_row += 1

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10
        )
        current_row += 1

        # eBay Search Method Section
        ttk.Label(
            self,
            text="eBay Search Method",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        ttk.Radiobutton(
            self,
            text="Scrapy (Sold Listings - slower, more complete)",
            variable=self.ebay_search_method,
            value="scrapy"
        ).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        ttk.Radiobutton(
            self,
            text="eBay API (Active Listings - faster, official API)",
            variable=self.ebay_search_method,
            value="api"
        ).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10
        )
        current_row += 1

        # Marketplace Toggles Section
        ttk.Label(
            self,
            text="Enabled Marketplaces",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        # Create checkboxes
        ttk.Checkbutton(
            self,
            text="Mandarake",
            variable=self.mandarake_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            self,
            text="eBay",
            variable=self.ebay_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(
            self,
            text="Suruga-ya",
            variable=self.surugaya_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            self,
            text="DejaJapan",
            variable=self.dejapan_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(
            self,
            text="Review/Alerts Tab",
            variable=self.alerts_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)
        current_row += 1

        # Restart warning
        ttk.Label(
            self,
            text="(Restart required for changes to take effect)",
            foreground='gray',
            font=('TkDefaultFont', 8)
        ).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, padx=5)
        current_row += 1

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10
        )
        current_row += 1

        # Scheduling Section
        ttk.Label(
            self,
            text="Scheduling",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        ttk.Label(self, text="Schedule (HH:MM):").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(self, textvariable=self.schedule_var, width=10).grid(
            row=current_row, column=1, sticky=tk.W, **pad
        )
        ttk.Label(self, text="(Daily run time)", foreground='gray').grid(
            row=current_row, column=2, sticky=tk.W, padx=(5, 0)
        )
        current_row += 1

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10
        )
        current_row += 1

        # Output Settings Section
        ttk.Label(
            self,
            text="Output Settings",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        ttk.Label(self, text="CSV Output:").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(
            self,
            textvariable=self.main_window.csv_path_var,
            width=32,
            state='readonly'
        ).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Label(self, text="(Auto-generated)", foreground='gray').grid(
            row=current_row, column=3, sticky=tk.W, padx=(5, 0)
        )
        current_row += 1

        ttk.Label(self, text="Image Download Folder:").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(
            self,
            textvariable=self.main_window.download_dir_var,
            width=32,
            state='readonly'
        ).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Label(self, text="(Auto-generated)", foreground='gray').grid(
            row=current_row, column=3, sticky=tk.W, padx=(5, 0)
        )
        current_row += 1

        ttk.Label(self, text="Thumbnail width (px):").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(
            self,
            textvariable=self.main_window.thumbnails_var,
            width=10
        ).grid(row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        # CSV Thumbnails toggle
        ttk.Checkbutton(
            self,
            text="Show CSV thumbnails",
            variable=self.csv_show_thumbnails,
            command=self._toggle_csv_thumbnails
        ).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

    # ==================== Event Handlers ====================

    def _on_mimic_changed(self, *args):
        """Handle browser mimic setting change."""
        return self.main_window._on_mimic_changed(*args)

    def _on_max_csv_items_changed(self, *args):
        """Handle max CSV items change."""
        return self.main_window._on_max_csv_items_changed(*args)

    def _on_marketplace_toggle(self):
        """Handle marketplace toggle change."""
        return self.main_window._on_marketplace_toggle()

    def _toggle_csv_thumbnails(self):
        """Toggle CSV thumbnails display."""
        return self.main_window.toggle_csv_thumbnails()
