"""
eBay Search & CSV Comparison Tab

This tab provides:
1. eBay sold listings search using Scrapy
2. CSV batch comparison with image matching
3. Alert threshold configuration
4. Integration with Alert tab for workflow management
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from typing import Optional, List, Dict, Any


class EbayTab(ttk.Frame):
    """eBay Search & CSV Comparison tab for finding comparable sold listings."""

    def __init__(self, parent, settings_manager, alert_tab, main_window):
        """
        Initialize eBay tab.

        Args:
            parent: Parent widget (notebook)
            settings_manager: Settings manager instance
            alert_tab: Alert tab instance for sending filtered results
            main_window: Reference to main window for shared resources
        """
        super().__init__(parent)
        self.settings = settings_manager
        self.alert_tab = alert_tab
        self.main_window = main_window

        # Initialize variables
        self.browserless_query_var = tk.StringVar(value="")
        self.browserless_max_results = tk.StringVar(value="10")
        self.browserless_status = tk.StringVar(value="Ready for eBay text search")

        # Alert threshold variables
        self.alert_threshold_active = tk.BooleanVar(value=True)
        alert_settings = settings_manager.get_alert_settings()
        self.alert_min_similarity = tk.DoubleVar(
            value=alert_settings.get('ebay_send_min_similarity', 70.0)
        )
        self.alert_min_profit = tk.DoubleVar(
            value=alert_settings.get('ebay_send_min_profit', 20.0)
        )

        # CSV comparison variables
        self.csv_newly_listed_only = tk.BooleanVar(value=False)
        self.csv_in_stock_only = tk.BooleanVar(value=False)
        self.csv_add_secondary_keyword = tk.BooleanVar(value=False)
        self.ransac_var = tk.BooleanVar(value=False)

        # Data storage
        self.browserless_image_path = None
        self.browserless_results_data = []
        self.all_comparison_results = []  # Unfiltered results for filtering
        self.csv_compare_data = []
        self.csv_compare_path = None
        self.browserless_images = {}  # Thumbnail cache
        self.csv_images = {}  # CSV thumbnail cache

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the eBay tab UI."""
        pad = {'padx': 5, 'pady': 5}

        # Main heading
        ttk.Label(self, text="Scrapy eBay Search (Sold Listings):").grid(
            row=0, column=0, columnspan=5, sticky=tk.W, **pad
        )

        # Search input section (row 1)
        ttk.Label(self, text="Search query:").grid(row=1, column=0, sticky=tk.W, **pad)
        browserless_entry = ttk.Entry(
            self, textvariable=self.browserless_query_var, width=32
        )
        browserless_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, **pad)

        # Max results setting
        ttk.Label(self, text="Max results:").grid(row=1, column=3, sticky=tk.W, **pad)
        max_results_combo = ttk.Combobox(
            self,
            textvariable=self.browserless_max_results,
            values=["5", "10", "20", "30", "45", "60"],
            width=5,
            state="readonly"
        )
        max_results_combo.grid(row=1, column=4, sticky=tk.W, **pad)

        # Action buttons (row 2)
        ttk.Button(
            self, text="Search", command=self._run_search
        ).grid(row=2, column=0, sticky=tk.W, **pad)
        ttk.Button(
            self, text="Clear Results", command=self._clear_results
        ).grid(row=2, column=1, sticky=tk.W, **pad)

        # Alert Thresholds frame (row 3)
        self._build_alert_threshold_frame(pad)

        # Progress bar (row 4)
        self.browserless_progress = ttk.Progressbar(self, mode='indeterminate')
        self.browserless_progress.grid(row=4, column=0, columnspan=6, sticky=tk.EW, **pad)

        # Create PanedWindow to split eBay results and CSV comparison sections (row 5)
        self.ebay_paned = tk.PanedWindow(
            self, orient=tk.VERTICAL, sashwidth=5, sashrelief=tk.RAISED
        )
        self.ebay_paned.grid(row=5, column=0, columnspan=6, sticky=tk.NSEW, **pad)

        # Configure grid weights for proper resizing
        self.rowconfigure(5, weight=1)
        self.columnconfigure(2, weight=1)

        # Build eBay results section (top pane)
        self._build_ebay_results_section()

        # Build CSV comparison section (bottom pane)
        self._build_csv_comparison_section()

    def _build_alert_threshold_frame(self, pad):
        """Build the alert threshold configuration frame."""
        alert_threshold_frame = ttk.LabelFrame(
            self, text="Alert Threshold", padding=5
        )
        alert_threshold_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, **pad)

        # Active checkbox
        ttk.Checkbutton(
            alert_threshold_frame, text="Active", variable=self.alert_threshold_active
        ).pack(side=tk.LEFT, padx=5)

        # Min Similarity
        ttk.Label(alert_threshold_frame, text="Min Similarity %:").pack(
            side=tk.LEFT, padx=5
        )
        ttk.Spinbox(
            alert_threshold_frame,
            from_=0,
            to=100,
            textvariable=self.alert_min_similarity,
            width=8
        ).pack(side=tk.LEFT, padx=5)
        self.alert_min_similarity.trace_add("write", lambda *args: self._save_alert_settings())

        # Min Profit
        ttk.Label(alert_threshold_frame, text="Min Profit %:").pack(side=tk.LEFT, padx=5)
        ttk.Spinbox(
            alert_threshold_frame,
            from_=-100,
            to=1000,
            textvariable=self.alert_min_profit,
            width=8
        ).pack(side=tk.LEFT, padx=5)
        self.alert_min_profit.trace_add("write", lambda *args: self._save_alert_settings())

    def _build_ebay_results_section(self):
        """Build the eBay search results treeview section."""
        # TODO: Extract from gui_config.py lines 797-879
        pass

    def _build_csv_comparison_section(self):
        """Build the CSV batch comparison section."""
        # TODO: Extract from gui_config.py lines 881-995
        pass

    # Placeholder methods - to be implemented during extraction
    def _run_search(self):
        """Run eBay Scrapy search."""
        # TODO: Extract from gui_config.py
        pass

    def _clear_results(self):
        """Clear eBay search results."""
        # TODO: Extract from gui_config.py
        pass

    def _save_alert_settings(self):
        """Save alert threshold settings."""
        try:
            self.settings.save_alert_settings(
                ebay_send_min_similarity=self.alert_min_similarity.get(),
                ebay_send_min_profit=self.alert_min_profit.get()
            )
        except:
            pass  # Ignore errors during saving
