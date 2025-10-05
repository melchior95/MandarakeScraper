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
import logging
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

        # Initialize variables - load from settings
        self.browserless_query_var = tk.StringVar(value="")
        default_max_results = str(settings_manager.get_setting('ebay.max_results', 10))
        self.browserless_max_results = tk.StringVar(value=default_max_results)
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

        # CSV comparison variables - load from settings
        self.csv_newly_listed_only = tk.BooleanVar(value=False)
        self.csv_in_stock_only = tk.BooleanVar(value=False)
        self.csv_add_secondary_keyword = tk.BooleanVar(value=False)
        default_ransac = settings_manager.get_setting('image_comparison.enable_ransac', False)
        self.ransac_var = tk.BooleanVar(value=default_ransac)

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
        # Results frame (top pane)
        browserless_results_frame = ttk.LabelFrame(self.ebay_paned, text="eBay Search Results")
        browserless_results_frame.rowconfigure(0, weight=1)
        browserless_results_frame.columnconfigure(0, weight=1)

        # Results treeview with thumbnail support
        browserless_columns = ('title', 'price', 'shipping', 'store_price', 'profit_margin',
                              'sold_date', 'similarity', 'url', 'store_url')

        # Create custom style for eBay results treeview with thumbnails
        style = ttk.Style()
        style.configure('Browserless.Treeview', rowheight=70)

        self.browserless_tree = ttk.Treeview(
            browserless_results_frame,
            columns=browserless_columns,
            show='tree headings',
            height=8,
            style='Browserless.Treeview'
        )

        self.browserless_tree.heading('#0', text='Thumb')
        self.browserless_tree.column('#0', width=130, stretch=False)

        browserless_headings = {
            'title': 'Title',
            'price': 'eBay Price',
            'shipping': 'Shipping',
            'store_price': 'Store ¥',
            'profit_margin': 'Profit %',
            'sold_date': 'Sold Date',
            'similarity': 'Similarity %',
            'url': 'eBay URL',
            'store_url': 'Store URL'
        }

        browserless_widths = {
            'title': 280,
            'price': 80,
            'shipping': 70,
            'store_price': 90,
            'profit_margin': 80,
            'sold_date': 100,
            'similarity': 90,
            'url': 180,
            'store_url': 180
        }

        for col, heading in browserless_headings.items():
            self.browserless_tree.heading(col, text=heading)
            width = browserless_widths.get(col, 100)
            self.browserless_tree.column(col, width=width, stretch=False)

        self.browserless_tree.grid(row=0, column=0, sticky=tk.NSEW)

        # Scrollbars for results
        browserless_v_scroll = ttk.Scrollbar(
            browserless_results_frame,
            orient=tk.VERTICAL,
            command=self.browserless_tree.yview
        )
        browserless_v_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.browserless_tree.configure(yscrollcommand=browserless_v_scroll.set)

        browserless_h_scroll = ttk.Scrollbar(
            browserless_results_frame,
            orient=tk.HORIZONTAL,
            command=self.browserless_tree.xview
        )
        browserless_h_scroll.grid(row=1, column=0, sticky=tk.EW)
        self.browserless_tree.configure(xscrollcommand=browserless_h_scroll.set)

        # Status area for browserless search
        browserless_status_label = ttk.Label(
            browserless_results_frame,
            textvariable=self.browserless_status,
            relief=tk.SUNKEN,
            anchor='w'
        )
        browserless_status_label.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(5, 0))

        # Initialize eBay search manager
        from gui.ebay_search_manager import EbaySearchManager
        self.ebay_search_manager = EbaySearchManager(
            self.browserless_tree,
            self.browserless_progress,
            self.browserless_status,
            self.main_window
        )

        # Bind double-click to open URL
        self.browserless_tree.bind('<Double-1>', self._open_browserless_url)
        # Bind right-click for context menu
        self.browserless_tree.bind('<Button-3>', self._show_browserless_context_menu)
        # Allow deselect by clicking empty area
        self.browserless_tree.bind("<Button-1>", lambda e: self._deselect_if_empty(e, self.browserless_tree))

        # Enable column drag-to-reorder for browserless tree
        self.main_window._setup_column_drag(self.browserless_tree)

        # Add the results frame to the paned window
        self.ebay_paned.add(browserless_results_frame, minsize=200)

    def _build_csv_comparison_section(self):
        """Build the CSV batch comparison section."""
        pad = {'padx': 5, 'pady': 5}

        # CSV Batch Comparison section (bottom pane)
        csv_compare_frame = ttk.LabelFrame(self.ebay_paned, text="CSV Batch Comparison")
        csv_compare_frame.rowconfigure(1, weight=1)
        csv_compare_frame.columnconfigure(3, weight=1)

        # CSV controls - all left-justified
        ttk.Checkbutton(
            csv_compare_frame,
            text="Newly listed",
            variable=self.csv_newly_listed_only,
            command=self._on_csv_filter_changed
        ).grid(row=0, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            csv_compare_frame,
            text="In-stock only",
            variable=self.csv_in_stock_only,
            command=self._on_csv_filter_changed
        ).grid(row=0, column=1, sticky=tk.W, **pad)

        ttk.Button(
            csv_compare_frame,
            text="Load CSV...",
            command=self._load_csv_for_comparison
        ).grid(row=0, column=2, sticky=tk.W, **pad)

        self.csv_compare_label = ttk.Label(csv_compare_frame, text="No file loaded", foreground="gray")
        self.csv_compare_label.grid(row=0, column=3, columnspan=2, sticky=tk.W, **pad)

        # CSV items treeview
        csv_items_frame = ttk.Frame(csv_compare_frame)
        csv_items_frame.grid(row=1, column=0, columnspan=7, sticky=tk.NSEW, **pad)

        # Create custom style for CSV treeview with thumbnails
        style = ttk.Style()
        style.configure('CSV.Treeview', rowheight=70)

        csv_columns = ('title', 'price', 'shop', 'stock', 'category', 'compared', 'url')
        self.csv_items_tree = ttk.Treeview(
            csv_items_frame,
            columns=csv_columns,
            show='tree headings',
            height=6,
            style='CSV.Treeview'
        )

        self.csv_items_tree.heading('#0', text='Thumb')
        self.csv_items_tree.column('#0', width=70, stretch=False)

        csv_headings = {
            'title': 'Title',
            'price': 'Store Price',
            'shop': 'Shop',
            'stock': 'Stock',
            'category': 'Category',
            'compared': 'eBay✓',
            'url': 'URL'
        }

        for col, heading in csv_headings.items():
            self.csv_items_tree.heading(col, text=heading)

        self.csv_items_tree.column('title', width=280)
        self.csv_items_tree.column('price', width=100)
        self.csv_items_tree.column('shop', width=80)
        self.csv_items_tree.column('stock', width=60)
        self.csv_items_tree.column('category', width=120)
        self.csv_items_tree.column('compared', width=50)
        self.csv_items_tree.column('url', width=300)

        self.csv_items_tree.grid(row=0, column=0, sticky=tk.NSEW)
        csv_items_frame.rowconfigure(0, weight=1)
        csv_items_frame.columnconfigure(0, weight=1)

        # Scrollbars
        csv_v_scroll = ttk.Scrollbar(
            csv_items_frame,
            orient=tk.VERTICAL,
            command=self.csv_items_tree.yview
        )
        csv_v_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.csv_items_tree.configure(yscrollcommand=csv_v_scroll.set)

        csv_h_scroll = ttk.Scrollbar(
            csv_items_frame,
            orient=tk.HORIZONTAL,
            command=self.csv_items_tree.xview
        )
        csv_h_scroll.grid(row=1, column=0, sticky=tk.EW)
        self.csv_items_tree.configure(xscrollcommand=csv_h_scroll.set)

        # Bind selection to auto-fill search query
        self.csv_items_tree.bind('<<TreeviewSelect>>', self._on_csv_item_selected)

        # Bind column resize to reload thumbnails with new size
        self.csv_items_tree.bind('<ButtonRelease-1>', self._on_csv_column_resize)

        # Enable column drag-to-reorder for CSV items tree
        self.main_window._setup_column_drag(self.csv_items_tree)

        # Add right-click context menu for CSV tree
        self.csv_tree_menu = tk.Menu(self.csv_items_tree, tearoff=0)
        self.csv_tree_menu.add_command(label="Add Full Title to Search", command=self._add_full_title_to_search)
        self.csv_tree_menu.add_command(label="Add Secondary Keyword", command=self._add_secondary_keyword_from_csv)
        self.csv_tree_menu.add_separator()
        self.csv_tree_menu.add_command(label="Delete Selected Items", command=self._delete_csv_items)
        self.csv_tree_menu.add_separator()
        self.csv_tree_menu.add_command(label="Download Missing Images", command=self._download_missing_csv_images)
        self.csv_tree_menu.add_separator()
        self.csv_tree_menu.add_command(label="Search by Image on eBay (API)", command=self._search_csv_by_image_api)
        self.csv_tree_menu.add_command(label="Search by Image on eBay (Web)", command=self._search_csv_by_image_web)
        self.csv_items_tree.bind("<Button-3>", self._show_csv_tree_menu)
        self.csv_items_tree.bind('<Double-1>', self._on_csv_double_click)
        # Allow deselect by clicking empty area
        self.csv_items_tree.bind("<Button-1>", lambda e: self._deselect_if_empty(e, self.csv_items_tree))

        # Comparison action buttons
        button_frame = ttk.Frame(csv_compare_frame)
        button_frame.grid(row=2, column=0, columnspan=7, sticky=tk.W, **pad)

        # Add 2nd keyword toggle before compare buttons
        ttk.Checkbutton(
            button_frame,
            text="2nd keyword",
            variable=self.csv_add_secondary_keyword
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 15))

        # RANSAC toggle before compare buttons
        ransac_check = ttk.Checkbutton(button_frame, text="RANSAC", variable=self.ransac_var)
        ransac_check.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))

        # Info label for RANSAC
        ransac_info = ttk.Label(button_frame, text="ℹ️", foreground="blue", cursor="hand2")
        ransac_info.grid(row=0, column=2, sticky=tk.W, padx=(0, 15))
        ransac_info.bind("<Button-1>", lambda e: self.main_window._show_ransac_info())

        ttk.Button(
            button_frame,
            text="Compare Selected",
            command=self._compare_selected_csv_item
        ).grid(row=0, column=3, sticky=tk.W, **pad)

        ttk.Button(
            button_frame,
            text="Compare All",
            command=self._compare_all_csv_items
        ).grid(row=0, column=4, sticky=tk.W, **pad)

        # Second row for smart comparison controls
        ttk.Button(
            button_frame,
            text="Compare New Only",
            command=self._compare_new_csv_items
        ).grid(row=1, column=3, sticky=tk.W, **pad)

        ttk.Button(
            button_frame,
            text="Image Compare All",
            command=self._image_compare_all_csv_items
        ).grid(row=1, column=4, sticky=tk.W, **pad)

        ttk.Button(
            button_frame,
            text="Clear Results",
            command=self._clear_comparison_results
        ).grid(row=1, column=5, sticky=tk.W, **pad)

        self.csv_compare_progress = ttk.Progressbar(button_frame, mode='indeterminate', length=200)
        self.csv_compare_progress.grid(row=0, column=5, rowspan=2, sticky=tk.W, padx=(10, 5))

        # Add the CSV comparison frame to the paned window
        self.ebay_paned.add(csv_compare_frame, minsize=200)

        # Initialize CSV comparison manager
        from gui.csv_comparison_manager import CSVComparisonManager
        self.csv_comparison_manager = CSVComparisonManager(self)

    # ==================== eBay Search Methods ====================

    def _run_search(self):
        """Run eBay Scrapy search."""
        return self.main_window.run_scrapy_text_search()

    def _clear_results(self):
        """Clear eBay search results."""
        return self.main_window.clear_browserless_results()

    def _open_browserless_url(self, event):
        """Open eBay URL in browser."""
        return self.main_window.open_browserless_url(event)

    def _show_browserless_context_menu(self, event):
        """Show context menu for eBay results."""
        return self.main_window._show_browserless_context_menu(event)

    def _deselect_if_empty(self, event, tree):
        """Deselect tree items if clicking on empty area."""
        return self.main_window._deselect_if_empty(event, tree)

    # ==================== CSV Comparison Methods ====================

    def _load_csv_for_comparison(self):
        """Load CSV file for comparison."""
        return self.main_window.load_csv_for_comparison()

    def _on_csv_filter_changed(self):
        """Handle CSV filter change."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager.on_csv_filter_changed()

    def _on_csv_item_selected(self, event):
        """Handle CSV item selection."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager.on_csv_item_selected(event)

    def _on_csv_column_resize(self, event):
        """Handle CSV column resize."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager.on_csv_column_resize(event)

    def _on_csv_double_click(self, event):
        """Handle CSV item double-click."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager._on_csv_item_double_click(event)

    def _show_csv_tree_menu(self, event):
        """Show CSV tree context menu."""
        try:
            self.csv_tree_menu.post(event.x_root, event.y_root)
        except tk.TclError as e:
            logging.debug(f"Failed to show CSV tree menu: {e}")

    def _add_full_title_to_search(self):
        """Add full CSV title to search query."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager._add_full_title_to_search()

    def _add_secondary_keyword_from_csv(self):
        """Add secondary keyword from CSV to search."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager._add_secondary_keyword_from_csv()

    def _delete_csv_items(self):
        """Delete selected CSV items."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager._delete_csv_items()

    def _download_missing_csv_images(self):
        """Download missing images for CSV items."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager._download_missing_csv_images()

    def _search_csv_by_image_api(self):
        """Search eBay by image using API."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager._search_csv_by_image_api()

    def _search_csv_by_image_web(self):
        """Search eBay by image using web scraping."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager._search_csv_by_image_web()

    def _compare_selected_csv_item(self):
        """Compare selected CSV item with eBay."""
        return self.main_window.compare_selected_csv_item()

    def _compare_all_csv_items(self):
        """Compare all CSV items with eBay."""
        return self.main_window.compare_all_csv_items()

    def _compare_new_csv_items(self):
        """Compare new CSV items only."""
        return self.main_window.compare_new_csv_items()

    def _image_compare_all_csv_items(self):
        """Image compare all CSV items using eBay API."""
        if self.csv_comparison_manager:
            return self.csv_comparison_manager._image_compare_all_csv_items()

    def _clear_comparison_results(self):
        """Clear CSV comparison results."""
        return self.main_window.clear_comparison_results()

    # ==================== Settings ====================

    def _save_alert_settings(self):
        """Save alert threshold settings."""
        try:
            self.settings.save_alert_settings(
                ebay_send_min_similarity=self.alert_min_similarity.get(),
                ebay_send_min_profit=self.alert_min_profit.get()
            )
        except Exception as e:
            logging.warning(f"Failed to save eBay alert settings: {e}")
