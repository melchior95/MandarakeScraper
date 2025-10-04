#!/usr/bin/env python3
"""Mandarake Scraper GUI configuration tool."""

import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
import re
from tkinter import filedialog, messagebox, ttk
from typing import Optional
from urllib.parse import quote
import csv
import webbrowser
import logging
from PIL import Image, ImageTk

from mandarake_scraper import MandarakeScraper, schedule_scraper
from settings_manager import get_settings_manager
from mandarake_codes import (
    MANDARAKE_STORES,
    MANDARAKE_MAIN_CATEGORIES,
    MANDARAKE_ALL_CATEGORIES,
    STORE_SLUG_TO_NAME,
)

# Import refactored modules
from gui.constants import (
    STORE_OPTIONS,
    MAIN_CATEGORY_OPTIONS,
    RECENT_OPTIONS,
    SETTINGS_PATH,
    CATEGORY_KEYWORDS,
)
from gui import utils
from gui import workers
from gui.alert_tab import AlertTab
from gui.mandarake_tab import MandarakeTab
from gui.schedule_executor import ScheduleExecutor
from gui.schedule_frame import ScheduleFrame
from gui.configuration_manager import ConfigurationManager
from gui.tree_manager import TreeManager
from gui.ebay_search_manager import EbaySearchManager
from gui.csv_comparison_manager import CSVComparisonManager


class ScraperGUI(tk.Tk):
    """GUI wrapper for Mandarake scraper configuration."""

    def __init__(self):
        super().__init__()

        # Initialize settings manager
        self.settings = get_settings_manager()

        # Set default exchange rate immediately (don't block GUI launch)
        self.usd_jpy_rate = 150.0

        # Fetch current USD/JPY exchange rate in background after GUI initializes
        self._fetch_exchange_rate_async()

        self.title("Mandarake Scraper GUI")

        # Load window settings or use defaults
        window_settings = self.settings.get_window_settings()
        width = window_settings.get('width', 780)
        height = window_settings.get('height', 760)
        x = window_settings.get('x', 100)
        y = window_settings.get('y', 100)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(True, True)
        self.minsize(780, 600)

        # Restore maximized state if it was maximized
        if window_settings.get('maximized', False):
            self.state('zoomed')  # Windows/Linux
            # For macOS, use: self.attributes('-zoomed', True)

        # Bind window close event to save settings
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.run_thread = None
        self.run_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self.config_paths: dict[str, Path] = {}
        self.current_scraper = None  # Track current scraper instance for cancellation
        self.cancel_requested = False  # Flag to signal cancellation
        self.detail_code_map: list[str] = []
        self.browserless_images: dict[str, ImageTk.PhotoImage] = {}  # Store eBay search thumbnails
        self.csv_images: dict[str, ImageTk.PhotoImage] = {}  # Store CSV comparison thumbnails
        self.last_saved_path: Path | None = None
        self.gui_settings: dict[str, bool] = {}
        self._settings_loaded = False
        self._active_playwright_matchers = []  # Track active Playwright instances

        # Initialize output-related variables (needed for config save/load)
        self.csv_path_var = tk.StringVar(value="results.csv")
        self.download_dir_var = tk.StringVar(value="images/")
        self.thumbnails_var = tk.StringVar(value="400")

        # Load publisher list
        self.publisher_list = self._load_publisher_list()

        # Initialize modular components
        self.config_manager = ConfigurationManager(self.settings)
        self.tree_manager = None  # Will be initialized after tree widget is created
        self.ebay_search_manager = None  # Will be initialized after eBay tree widget is created
        self.csv_comparison_manager = None  # Will be initialized after CSV tree widget is created

        # Create menu bar
        self._create_menu_bar()

        self._build_widgets()
        self._load_gui_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_queue()
        self._update_preview()

    def _fetch_exchange_rate_async(self):
        """Fetch exchange rate in background thread without blocking GUI launch."""
        def fetch_rate():
            try:
                rate = utils.fetch_exchange_rate()
                # Update the rate on the main thread
                self.after(0, lambda: self._update_exchange_rate(rate))
            except Exception as e:
                print(f"[EXCHANGE RATE] Background fetch failed: {e}")

        # Start background thread
        thread = threading.Thread(target=fetch_rate, daemon=True)
        thread.start()

    def _update_exchange_rate(self, rate: float):
        """Update exchange rate on main thread."""
        self.usd_jpy_rate = rate
        print(f"[EXCHANGE RATE] Updated USD/JPY: {self.usd_jpy_rate}")

    def _create_menu_bar(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        # Recent files submenu
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Configs", menu=self.recent_menu)
        self._update_recent_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="View Settings Summary", command=self._show_settings_summary)
        settings_menu.add_command(label="Reset to Defaults", command=self._reset_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Export Settings", command=self._export_settings)
        settings_menu.add_command(label="Import Settings", command=self._import_settings)


        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Image Search Guide", command=self._show_image_search_help)
        help_menu.add_command(label="About", command=self._show_about)

    def _update_recent_menu(self):
        """Update the recent files menu"""
        self.recent_menu.delete(0, tk.END)
        recent_files = self.settings.get_recent_config_files()

        if recent_files:
            for file_path in recent_files:
                file_name = Path(file_path).name
                self.recent_menu.add_command(
                    label=file_name,
                    command=lambda path=file_path: self._load_recent_config(path)
                )
        else:
            self.recent_menu.add_command(label="No recent files", state=tk.DISABLED)

    def _load_recent_config(self, file_path: str):
        """Load a recent config file"""
        try:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._populate_from_config(config)
                self.last_saved_path = Path(file_path)
                self.status_var.set(f"Loaded recent config: {Path(file_path).name}")
            else:
                messagebox.showerror("Error", f"File not found: {file_path}")
                # Remove from recent files
                recent_files = self.settings.get_recent_config_files()
                if file_path in recent_files:
                    recent_files.remove(file_path)
                    self.settings.set_setting("recent.config_files", recent_files)
                    self._update_recent_menu()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def _show_settings_summary(self):
        """Show a dialog with current settings summary"""
        summary = self.settings.get_settings_summary()

        # Create summary window
        summary_window = tk.Toplevel(self)
        summary_window.title("Settings Summary")
        summary_window.geometry("600x500")
        summary_window.transient(self)

        # Text widget with scrollbar
        text_frame = ttk.Frame(summary_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.insert(tk.END, summary)
        text_widget.config(state=tk.DISABLED)

        ttk.Button(summary_window, text="Close", command=summary_window.destroy).pack(pady=10)

    def _reset_settings(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?\n\nThis action cannot be undone."):
            if self.settings.reset_to_defaults():
                messagebox.showinfo("Success", "Settings have been reset to defaults.\n\nRestart the application to see all changes.")
            else:
                messagebox.showerror("Error", "Failed to reset settings.")

    def _export_settings(self):
        """Export current settings to a file"""
        file_path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            if self.settings.export_settings(file_path):
                messagebox.showinfo("Success", f"Settings exported to:\n{file_path}")
            else:
                messagebox.showerror("Error", "Failed to export settings.")

    def _import_settings(self):
        """Import settings from a file"""
        file_path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            if messagebox.askyesno("Import Settings", "Importing settings will overwrite your current settings.\n\nAre you sure you want to continue?"):
                if self.settings.import_settings(file_path):
                    messagebox.showinfo("Success", "Settings imported successfully.\n\nRestart the application to see all changes.")
                else:
                    messagebox.showerror("Error", "Failed to import settings.")

    def _show_image_search_help(self):
        """Show image search help dialog"""
        help_text = """
IMAGE SEARCH HELP

🎯 QUICK START:
1. Click "Select Image..." to upload a product photo
2. Use the search functionality to find similar items

📊 RESULTS:
- Shows sold item counts and price ranges
- Calculates profit margins with different scenarios
- Estimates fees and shipping costs
- Provides market recommendations
        """

        # Create help window
        help_window = tk.Toplevel(self)
        help_window.title("Image Search Help")
        help_window.geometry("500x400")
        help_window.transient(self)

        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        ttk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)

    def _show_about(self):
        """Show about dialog"""
        about_text = f"""
Mandarake Scraper GUI v1.0.0

A comprehensive tool for analyzing Mandarake listings
and comparing prices with eBay sold listings.

Features:
• Advanced image search with comparison methods
• Profit margin calculations and market analysis
• Persistent settings and window preferences

Settings file: {self.settings.settings_file}
Last updated: {self.settings.get_setting('meta.last_updated', 'Never')}
        """

        messagebox.showinfo("About Mandarake Scraper", about_text)

    def _show_ransac_info(self):
        """Show RANSAC information dialog"""
        info_text = """
RANSAC GEOMETRIC VERIFICATION

What it does:
• Verifies that matched image features have consistent spatial relationships
• Uses RANSAC (Random Sample Consensus) algorithm to detect true matches
• Adds ~40-50% processing time but significantly improves accuracy

When to use:
✓ When you need maximum accuracy for difficult matches
✓ When comparing similar-looking items that are different editions
✓ When false positives are costly (e.g., expensive items)

When to skip:
• For quick exploratory searches
• When processing large batches (hundreds of items)
• When visual similarity is good enough

Current algorithm (without RANSAC):
• Template matching: 60% weight
• Feature matching: 25% weight
• SSIM: 10% weight
• Histogram: 5% weight
• Consistency bonus: up to 25% boost

With RANSAC enabled:
• Adds geometric coherence verification (15-20% weight)
• Penalizes random/scattered feature matches
• Increases match confidence scores
        """

        messagebox.showinfo("RANSAC Geometric Verification", info_text)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_widgets(self):
        pad = {"padx": 3, "pady": 4}

        # Create status bar
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor='w')
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)

        # Create clickable URL label (pack at bottom, above status)
        self.url_var = tk.StringVar(value="(enter keyword)")
        self.url_label = tk.Label(self, textvariable=self.url_var, relief=tk.GROOVE, anchor='w',
                                   wraplength=720, justify=tk.LEFT, cursor="hand2", fg="blue")
        self.url_label.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)
        self.url_label.bind("<Button-1>", self._open_search_url)

        # Now create notebook (will fill remaining space)
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Get marketplace toggles
        marketplace_toggles = self.settings.get_marketplace_toggles()

        # Create tabs based on toggles
        basic_frame = ttk.Frame(notebook)
        browserless_frame = ttk.Frame(notebook)
        advanced_frame = ttk.Frame(notebook)

        # Always create alert tab first (other tabs may reference it)
        self.alert_tab = AlertTab(notebook, settings_manager=self.settings)

        if marketplace_toggles.get('mandarake', True):
            notebook.add(basic_frame, text="Stores")

        if marketplace_toggles.get('ebay', True):
            notebook.add(browserless_frame, text="eBay Search & CSV")

        # Add Alert/Review tab if enabled
        if marketplace_toggles.get('alerts', True):
            notebook.add(self.alert_tab, text="Review/Alerts")

        notebook.add(advanced_frame, text="Advanced")

        # Initialize schedule executor (background thread)
        self.schedule_executor = ScheduleExecutor(self)
        self.schedule_executor.start()

        # Mandarake/Stores tab - Create using MandarakeTab module
        if marketplace_toggles.get('mandarake', True):
            self.mandarake_tab = MandarakeTab(basic_frame, self)
            self.mandarake_tab.pack(fill=tk.BOTH, expand=True)

        # eBay Search & CSV tab ------------------------------------------
        ttk.Label(browserless_frame, text="Scrapy eBay Search (Sold Listings):").grid(row=0, column=0, columnspan=5, sticky=tk.W, **pad)

        # Search input
        ttk.Label(browserless_frame, text="Search query:").grid(row=1, column=0, sticky=tk.W, **pad)
        self.browserless_query_var = tk.StringVar(value="")
        browserless_entry = ttk.Entry(browserless_frame, textvariable=self.browserless_query_var, width=32)
        browserless_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, **pad)

        # Max results setting (for rate limiting)
        ttk.Label(browserless_frame, text="Max results:").grid(row=1, column=3, sticky=tk.W, **pad)
        self.browserless_max_results = tk.StringVar(value="10")
        max_results_combo = ttk.Combobox(browserless_frame, textvariable=self.browserless_max_results,
                                       values=["5", "10", "20", "30", "45", "60"], width=5, state="readonly")
        max_results_combo.grid(row=1, column=4, sticky=tk.W, **pad)
        max_results_combo.bind("<<ComboboxSelected>>", lambda e: None)  # Settings saved on close

        # Action buttons
        ttk.Button(browserless_frame, text="Search", command=self.run_scrapy_text_search).grid(row=2, column=0, sticky=tk.W, **pad)
        ttk.Button(browserless_frame, text="Clear Results", command=self.clear_browserless_results).grid(row=2, column=1, sticky=tk.W, **pad)

        # Alert Thresholds frame (row 3) - left side in labeled frame
        alert_threshold_frame = ttk.LabelFrame(browserless_frame, text="Alert Threshold", padding=5)
        alert_threshold_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, **pad)

        # Toggle for alert thresholds
        self.alert_threshold_active = tk.BooleanVar(value=True)
        ttk.Checkbutton(alert_threshold_frame, text="Active", variable=self.alert_threshold_active).pack(side=tk.LEFT, padx=5)

        # Load saved alert send settings
        alert_settings = self.settings.get_alert_settings()
        ebay_send_sim = alert_settings.get('ebay_send_min_similarity', 70.0)
        ebay_send_profit = alert_settings.get('ebay_send_min_profit', 20.0)

        # Min Similarity
        ttk.Label(alert_threshold_frame, text="Min Similarity %:").pack(side=tk.LEFT, padx=5)
        self.alert_min_similarity = tk.DoubleVar(value=ebay_send_sim)
        ttk.Spinbox(alert_threshold_frame, from_=0, to=100, textvariable=self.alert_min_similarity, width=8).pack(side=tk.LEFT, padx=5)
        self.alert_min_similarity.trace_add("write", lambda *args: self._save_ebay_alert_settings())

        # Min Profit
        ttk.Label(alert_threshold_frame, text="Min Profit %:").pack(side=tk.LEFT, padx=5)
        self.alert_min_profit = tk.DoubleVar(value=ebay_send_profit)
        ttk.Spinbox(alert_threshold_frame, from_=-100, to=1000, textvariable=self.alert_min_profit, width=8).pack(side=tk.LEFT, padx=5)
        self.alert_min_profit.trace_add("write", lambda *args: self._save_ebay_alert_settings())

        # Progress bar (row 4)
        self.browserless_progress = ttk.Progressbar(browserless_frame, mode='indeterminate')
        self.browserless_progress.grid(row=4, column=0, columnspan=6, sticky=tk.EW, **pad)

        # Create PanedWindow to split eBay results and CSV comparison sections
        self.ebay_paned = tk.PanedWindow(browserless_frame, orient=tk.VERTICAL, sashwidth=5, sashrelief=tk.RAISED)
        self.ebay_paned.grid(row=5, column=0, columnspan=6, sticky=tk.NSEW, **pad)

        # Configure grid weights for proper resizing
        browserless_frame.rowconfigure(5, weight=1)
        browserless_frame.columnconfigure(2, weight=1)

        # Results section (top pane)
        browserless_results_frame = ttk.LabelFrame(self.ebay_paned, text="eBay Search Results")
        browserless_results_frame.rowconfigure(0, weight=1)
        browserless_results_frame.columnconfigure(0, weight=1)

        # Results treeview with thumbnail support
        browserless_columns = ('title', 'price', 'shipping', 'mandarake_price', 'profit_margin', 'sold_date', 'similarity', 'url', 'mandarake_url')

        # Create custom style for eBay results treeview with thumbnails
        style = ttk.Style()
        style.configure('Browserless.Treeview', rowheight=70)  # Match output tree height

        self.browserless_tree = ttk.Treeview(browserless_results_frame, columns=browserless_columns, show='tree headings', height=8, style='Browserless.Treeview')

        self.browserless_tree.heading('#0', text='Thumb')
        self.browserless_tree.column('#0', width=130, stretch=False)  # Wide enough for side-by-side thumbnails

        browserless_headings = {
            'title': 'Title',
            'price': 'eBay Price',
            'shipping': 'Shipping',
            'mandarake_price': 'Mandarake ¥',
            'profit_margin': 'Profit %',
            'sold_date': 'Sold Date',
            'similarity': 'Similarity %',
            'url': 'eBay URL',
            'mandarake_url': 'Mandarake URL'
        }

        browserless_widths = {
            'title': 280,
            'price': 80,
            'shipping': 70,
            'mandarake_price': 90,
            'profit_margin': 80,
            'sold_date': 100,
            'similarity': 90,
            'url': 180,
            'mandarake_url': 180
        }

        for col, heading in browserless_headings.items():
            self.browserless_tree.heading(col, text=heading)
            width = browserless_widths.get(col, 100)
            self.browserless_tree.column(col, width=width, stretch=False)

        self.browserless_tree.grid(row=0, column=0, sticky=tk.NSEW)

        # Scrollbars for results
        browserless_v_scroll = ttk.Scrollbar(browserless_results_frame, orient=tk.VERTICAL, command=self.browserless_tree.yview)
        browserless_v_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.browserless_tree.configure(yscrollcommand=browserless_v_scroll.set)

        browserless_h_scroll = ttk.Scrollbar(browserless_results_frame, orient=tk.HORIZONTAL, command=self.browserless_tree.xview)
        browserless_h_scroll.grid(row=1, column=0, sticky=tk.EW)
        self.browserless_tree.configure(xscrollcommand=browserless_h_scroll.set)

        # Status area for browserless search
        self.browserless_status = tk.StringVar(value="Ready for eBay text search")
        browserless_status_label = ttk.Label(browserless_results_frame, textvariable=self.browserless_status, relief=tk.SUNKEN, anchor='w')
        browserless_status_label.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(5, 0))

        # Initialize eBay search manager after eBay tree widget is created
        self.ebay_search_manager = EbaySearchManager(
            self.browserless_tree, 
            self.browserless_progress, 
            self.browserless_status, 
            self
        )
        
        # Bind double-click to open URL
        self.browserless_tree.bind('<Double-1>', self.open_browserless_url)
        # Bind right-click for context menu
        self.browserless_tree.bind('<Button-3>', self._show_browserless_context_menu)
        # Prevent space from affecting tree selection when it has focus
        # Space key handled globally via bind_class
        # Allow deselect by clicking empty area
        self.browserless_tree.bind("<Button-1>", lambda e: self._deselect_if_empty(e, self.browserless_tree))

        # Enable column drag-to-reorder for browserless tree
        self._setup_column_drag(self.browserless_tree)

        # Add the results frame to the paned window
        self.ebay_paned.add(browserless_results_frame, minsize=200)

        # CSV Batch Comparison section (bottom pane) --------------------------------
        csv_compare_frame = ttk.LabelFrame(self.ebay_paned, text="CSV Batch Comparison")
        csv_compare_frame.rowconfigure(1, weight=1)
        csv_compare_frame.columnconfigure(3, weight=1)  # Weight on filename column instead

        # CSV controls - all left-justified
        ttk.Checkbutton(csv_compare_frame, text="Newly listed", variable=self.csv_newly_listed_only, command=self._on_csv_filter_changed).grid(row=0, column=0, sticky=tk.W, **pad)
        ttk.Checkbutton(csv_compare_frame, text="In-stock only", variable=self.csv_in_stock_only, command=self._on_csv_filter_changed).grid(row=0, column=1, sticky=tk.W, **pad)
        ttk.Button(csv_compare_frame, text="Load CSV...", command=self.load_csv_for_comparison).grid(row=0, column=2, sticky=tk.W, **pad)
        self.csv_compare_label = ttk.Label(csv_compare_frame, text="No file loaded", foreground="gray")
        self.csv_compare_label.grid(row=0, column=3, columnspan=2, sticky=tk.W, **pad)

        # CSV items treeview
        csv_items_frame = ttk.Frame(csv_compare_frame)
        csv_items_frame.grid(row=1, column=0, columnspan=7, sticky=tk.NSEW, **pad)

        # Create custom style for CSV treeview with thumbnails
        style.configure('CSV.Treeview', rowheight=70)  # Match other trees

        csv_columns = ('title', 'price', 'shop', 'stock', 'category', 'compared', 'url')
        self.csv_items_tree = ttk.Treeview(csv_items_frame, columns=csv_columns, show='tree headings', height=6, style='CSV.Treeview')

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
        csv_v_scroll = ttk.Scrollbar(csv_items_frame, orient=tk.VERTICAL, command=self.csv_items_tree.yview)
        csv_v_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.csv_items_tree.configure(yscrollcommand=csv_v_scroll.set)

        csv_h_scroll = ttk.Scrollbar(csv_items_frame, orient=tk.HORIZONTAL, command=self.csv_items_tree.xview)
        csv_h_scroll.grid(row=1, column=0, sticky=tk.EW)
        self.csv_items_tree.configure(xscrollcommand=csv_h_scroll.set)

        # Bind selection to auto-fill search query
        self.csv_items_tree.bind('<<TreeviewSelect>>', self.on_csv_item_selected)

        # Bind column resize to reload thumbnails with new size
        self.csv_items_tree.bind('<ButtonRelease-1>', self._on_csv_column_resize)

        # Enable column drag-to-reorder for CSV items tree
        self._setup_column_drag(self.csv_items_tree)

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
        # Prevent space from affecting tree selection when it has focus
        # Space key handled globally via bind_class
        # Allow deselect by clicking empty area
        self.csv_items_tree.bind("<Button-1>", lambda e: self._deselect_if_empty(e, self.csv_items_tree))

        # Comparison action buttons
        button_frame = ttk.Frame(csv_compare_frame)
        button_frame.grid(row=2, column=0, columnspan=7, sticky=tk.W, **pad)

        # Add 2nd keyword toggle before compare buttons
        ttk.Checkbutton(button_frame, text="2nd keyword", variable=self.csv_add_secondary_keyword).grid(row=0, column=0, sticky=tk.W, padx=(0, 15))

        # RANSAC toggle before compare buttons
        self.ransac_var = tk.BooleanVar(value=False)
        ransac_check = ttk.Checkbutton(button_frame, text="RANSAC", variable=self.ransac_var)
        ransac_check.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))

        # Info label for RANSAC
        ransac_info = ttk.Label(button_frame, text="ℹ️", foreground="blue", cursor="hand2")
        ransac_info.grid(row=0, column=2, sticky=tk.W, padx=(0, 15))
        ransac_info.bind("<Button-1>", lambda e: self._show_ransac_info())

        ttk.Button(button_frame, text="Compare Selected", command=self.compare_selected_csv_item).grid(row=0, column=3, sticky=tk.W, **pad)
        ttk.Button(button_frame, text="Compare All", command=self.compare_all_csv_items).grid(row=0, column=4, sticky=tk.W, **pad)

        # Second row for smart comparison controls
        ttk.Button(button_frame, text="Compare New Only", command=self.compare_new_csv_items).grid(row=1, column=3, sticky=tk.W, **pad)
        ttk.Button(button_frame, text="Clear Results", command=self.clear_comparison_results).grid(row=1, column=4, sticky=tk.W, **pad)

        self.csv_compare_progress = ttk.Progressbar(button_frame, mode='indeterminate', length=200)
        self.csv_compare_progress.grid(row=0, column=5, rowspan=2, sticky=tk.W, padx=(10, 5))

        # Add the CSV comparison frame to the paned window
        self.ebay_paned.add(csv_compare_frame, minsize=200)

        # Initialize CSV comparison manager
        self.csv_comparison_manager = CSVComparisonManager(self)

        # Initialize variables
        self.browserless_image_path = None
        self.browserless_results_data = []
        self.all_comparison_results = []  # Store unfiltered results for filtering
        self.csv_compare_data = []
        self.csv_compare_path = None

        # Advanced tab --------------------------------------------------
        current_row = 0

        # Scraper Options Section
        ttk.Label(advanced_frame, text="Scraper Options", font=('TkDefaultFont', 9, 'bold')).grid(
            row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        self.fast_var = tk.BooleanVar(value=False)
        self.resume_var = tk.BooleanVar(value=True)
        self.debug_var = tk.BooleanVar(value=False)
        self.mimic_var = tk.BooleanVar(value=True)  # Enable by default for Unicode support

        ttk.Checkbutton(advanced_frame, text="Fast mode (skip eBay)", variable=self.fast_var).grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Checkbutton(advanced_frame, text="Resume interrupted runs", variable=self.resume_var).grid(
            row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(advanced_frame, text="Debug logging", variable=self.debug_var).grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Checkbutton(advanced_frame, text="Use browser mimic (recommended for Japanese text)",
                       variable=self.mimic_var).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        self.mimic_var.trace_add('write', self._on_mimic_changed)
        current_row += 1

        # Max CSV items control
        ttk.Label(advanced_frame, text="Max CSV items (0 = unlimited):").grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        self.max_csv_items_var = tk.StringVar(value=str(self.settings.get_setting('scraper.max_csv_items', 0)))
        max_csv_entry = ttk.Entry(advanced_frame, textvariable=self.max_csv_items_var, width=10)
        max_csv_entry.grid(row=current_row, column=1, sticky=tk.W, **pad)
        self.max_csv_items_var.trace_add('write', self._on_max_csv_items_changed)
        current_row += 1

        # Separator
        ttk.Separator(advanced_frame, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10)
        current_row += 1

        # eBay Search Method Section
        ttk.Label(advanced_frame, text="eBay Search Method", font=('TkDefaultFont', 9, 'bold')).grid(
            row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        self.ebay_search_method = tk.StringVar(value="scrapy")
        ttk.Radiobutton(advanced_frame, text="Scrapy (Sold Listings - slower, more complete)",
                       variable=self.ebay_search_method, value="scrapy").grid(
            row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1
        ttk.Radiobutton(advanced_frame, text="eBay API (Active Listings - faster, official API)",
                       variable=self.ebay_search_method, value="api").grid(
            row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        # Separator
        ttk.Separator(advanced_frame, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10)
        current_row += 1

        # Marketplace Toggles Section
        ttk.Label(advanced_frame, text="Enabled Marketplaces", font=('TkDefaultFont', 9, 'bold')).grid(
            row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        # Load current toggles
        marketplace_toggles = self.settings.get_marketplace_toggles()

        # Create toggle variables
        self.mandarake_enabled = tk.BooleanVar(value=marketplace_toggles.get('mandarake', True))
        self.ebay_enabled = tk.BooleanVar(value=marketplace_toggles.get('ebay', True))
        self.surugaya_enabled = tk.BooleanVar(value=marketplace_toggles.get('surugaya', False))
        self.dejapan_enabled = tk.BooleanVar(value=marketplace_toggles.get('dejapan', False))
        self.alerts_enabled = tk.BooleanVar(value=marketplace_toggles.get('alerts', True))

        # Create checkboxes
        ttk.Checkbutton(advanced_frame, text="Mandarake", variable=self.mandarake_enabled,
                       command=self._on_marketplace_toggle).grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Checkbutton(advanced_frame, text="eBay", variable=self.ebay_enabled,
                       command=self._on_marketplace_toggle).grid(
            row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(advanced_frame, text="Suruga-ya", variable=self.surugaya_enabled,
                       command=self._on_marketplace_toggle).grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Checkbutton(advanced_frame, text="DejaJapan", variable=self.dejapan_enabled,
                       command=self._on_marketplace_toggle).grid(
            row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(advanced_frame, text="Review/Alerts Tab", variable=self.alerts_enabled,
                       command=self._on_marketplace_toggle).grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        current_row += 1

        # Restart warning
        ttk.Label(advanced_frame, text="(Restart required for changes to take effect)",
                 foreground='gray', font=('TkDefaultFont', 8)).grid(
            row=current_row, column=0, columnspan=2, sticky=tk.W, padx=5)
        current_row += 1

        # Separator
        ttk.Separator(advanced_frame, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10)
        current_row += 1

        # Scheduling Section
        ttk.Label(advanced_frame, text="Scheduling", font=('TkDefaultFont', 9, 'bold')).grid(
            row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        self.schedule_var = tk.StringVar()
        ttk.Label(advanced_frame, text="Schedule (HH:MM):").grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Entry(advanced_frame, textvariable=self.schedule_var, width=10).grid(
            row=current_row, column=1, sticky=tk.W, **pad)
        ttk.Label(advanced_frame, text="(Daily run time)", foreground='gray').grid(
            row=current_row, column=2, sticky=tk.W, padx=(5, 0))
        current_row += 1

        # Separator
        ttk.Separator(advanced_frame, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10)
        current_row += 1

        # Output Settings Section
        ttk.Label(advanced_frame, text="Output Settings", font=('TkDefaultFont', 9, 'bold')).grid(
            row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        ttk.Label(advanced_frame, text="CSV Output:").grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Entry(advanced_frame, textvariable=self.csv_path_var, width=32, state='readonly').grid(
            row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Label(advanced_frame, text="(Auto-generated)", foreground='gray').grid(
            row=current_row, column=3, sticky=tk.W, padx=(5, 0))
        current_row += 1

        ttk.Label(advanced_frame, text="Image Download Folder:").grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Entry(advanced_frame, textvariable=self.download_dir_var, width=32, state='readonly').grid(
            row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Label(advanced_frame, text="(Auto-generated)", foreground='gray').grid(
            row=current_row, column=3, sticky=tk.W, padx=(5, 0))
        current_row += 1

        ttk.Label(advanced_frame, text="Thumbnail width (px):").grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Entry(advanced_frame, textvariable=self.thumbnails_var, width=10).grid(
            row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        # CSV Thumbnails toggle
        self.csv_show_thumbnails = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Show CSV thumbnails", variable=self.csv_show_thumbnails, command=self.toggle_csv_thumbnails).grid(
            row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        # Restore paned window position after widgets are created
        self.after(100, self._restore_paned_position)

        # Global space key handler - must be at end of __init__
        # Bind to all widgets to intercept before widget-specific handlers
        self.bind_all("<space>", self._global_space_handler)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------


    def load_csv_file(self):
        """Load a CSV file and display results with thumbnails"""
        file_path = filedialog.askopenfilename(
            title="Select CSV file to load",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ],
            initialdir="results"  # Start in results directory
        )

        if file_path:
            csv_path = Path(file_path)
            print(f"[GUI DEBUG] User selected CSV file: {csv_path}")
            self._load_results_table(csv_path)
            self.status_var.set(f"Loaded CSV: {csv_path.name}")

    def _search_ebay_sold(self, title):
        """Search eBay for sold listings of an item with optional lazy search optimization"""
        try:
            # Import required modules
            from mandarake_scraper import EbayAPI

            # Create a dummy EbayAPI instance. No credentials needed for web scraping.
            ebay_api = EbayAPI("", "")

            # Get settings
            try:
                days_back = int(self.ebay_days_back.get())
            except (ValueError, AttributeError):
                days_back = 90

            # Check if lazy search is enabled
            lazy_search_enabled = getattr(self, 'lazy_search_enabled', None)
            use_lazy_search = lazy_search_enabled.get() if lazy_search_enabled else False

            print(f"[EBAY DEBUG] Searching eBay for: '{title}' (last {days_back} days) using WEB SCRAPING")
            if use_lazy_search:
                print(f"[LAZY SEARCH] Enabled - will try optimized terms if initial search fails")

            # Search for sold listings using web scraping
            result = ebay_api.search_sold_listings_web(title, days_back=days_back)

            # If lazy search is enabled and we got poor results OR eBay is blocking, try optimized search terms
            if use_lazy_search and (not result or result.get('sold_count', 0) < 3 or result.get('error')):
                error_info = f" (Error: {result.get('error')})" if result and result.get('error') else ""
                print(f"[LAZY SEARCH] Initial search yielded {result.get('sold_count', 0) if result else 0} results{error_info} - trying optimized terms")

                try:
                    from search_optimizer import SearchOptimizer
                    optimizer = SearchOptimizer()

                    # Get optimized search terms
                    optimization = optimizer.optimize_search_term(title, lazy_mode=True)
                    optimized_terms = optimization['confidence_order'][:5]  # Try top 5 optimized terms

                    print(f"[LAZY SEARCH] Trying {len(optimized_terms)} optimized terms: {optimized_terms}")

                    best_result = result  # Keep original result as fallback
                    best_count = result.get('sold_count', 0) if result else 0

                    for optimized_term in optimized_terms:
                        if optimized_term != title:  # Skip if same as original
                            print(f"[LAZY SEARCH] Trying optimized term: '{optimized_term}'")

                            opt_result = ebay_api.search_sold_listings_web(optimized_term, days_back=days_back)

                            if opt_result and opt_result.get('sold_count', 0) > best_count:
                                print(f"[LAZY SEARCH] Better result found: {opt_result['sold_count']} items vs {best_count}")
                                best_result = opt_result
                                best_result['search_term_used'] = optimized_term
                                best_count = opt_result['sold_count']

                                # If we found good results (5+ items), stop searching
                                if best_count >= 5:
                                    break

                    result = best_result

                except Exception as e:
                    print(f"[LAZY SEARCH] Error during optimization: {e}")
                    # Continue with original result

                    # If eBay is blocking, explain why lazy search can't help
                    if result and result.get('error') and any(term in str(result.get('error')).lower() for term in ['captcha', 'blocked', 'error page']):
                        print(f"[LAZY SEARCH] Note: eBay is blocking automated access entirely. Lazy search cannot overcome CAPTCHA/blocking issues.")
                        print(f"[LAZY SEARCH] Recommendation: Use the regular eBay Analysis tab with manual product titles instead.")

            if result and result.get('error'):
                print(f"[EBAY DEBUG] eBay web scrape error: {result['error']}")
                return None

            if not result or result.get('sold_count', 0) == 0:
                search_term_used = result.get('search_term_used', title) if result else title
                print(f"[EBAY DEBUG] No sold listings found for: {search_term_used}")
                return None

            search_term_used = result.get('search_term_used', title)
            if search_term_used != title:
                print(f"[LAZY SEARCH] Success! Used optimized term: '{search_term_used}'")

            print(f"[EBAY DEBUG] Found {result['sold_count']} sold items, median price: ${result['median_price']}")
            return result

        except Exception as e:
            print(f"[EBAY DEBUG] eBay search error: {e}")
            return None

    def _display_ebay_results(self, results):
        """Display eBay analysis results in the treeview"""
        # Clear existing results
        for item in self.ebay_results_tree.get_children():
            self.ebay_results_tree.delete(item)

        # Check if these are image comparison results (have string values) or regular eBay results (have numeric values)
        is_image_comparison = results and isinstance(results[0].get('mandarake_price'), str)

        if is_image_comparison:
            # Image comparison results - display as-is without numeric formatting
            for result in results:
                values = (
                    result['title'][:40] + ('...' if len(result['title']) > 40 else ''),
                    result['mandarake_price'],  # Already formatted string
                    str(result['ebay_sold_count']),
                    result['ebay_median_price'],  # Already formatted string
                    result.get('ebay_price_range', 'N/A'),
                    result['profit_margin'],  # Already formatted string
                    result.get('estimated_profit', 'N/A')  # Already formatted string
                )
                self.ebay_results_tree.insert('', tk.END, values=values)
        else:
            # Regular eBay results - format as numbers
            # Sort by profit margin (highest first)
            results.sort(key=lambda x: x['profit_margin'], reverse=True)

            # Add results to treeview
            for result in results:
                values = (
                    result['title'][:40] + ('...' if len(result['title']) > 40 else ''),
                    f"¥{result['mandarake_price']:,}",
                    str(result['ebay_sold_count']),
                    f"${result['ebay_median_price']:.2f}",
                    result.get('ebay_price_range', 'N/A'),
                    f"{result['profit_margin']:+.1f}%",
                    f"${result.get('estimated_profit', 0):.2f}"
                )
                self.ebay_results_tree.insert('', tk.END, values=values)


    def _restore_paned_position(self):
        """Restore the paned window sash position from saved settings"""
        try:
            if not hasattr(self, 'ebay_paned'):
                return

            window_settings = self.settings.get_window_settings()
            ebay_paned_pos = window_settings.get('ebay_paned_pos')

            if ebay_paned_pos is not None:
                # Set the sash position
                self.ebay_paned.sash_place(0, 0, ebay_paned_pos)
                print(f"[GUI] Restored eBay paned window position: {ebay_paned_pos}")
        except Exception as e:
            print(f"[GUI] Could not restore paned position: {e}")

    def _save_window_settings(self):
        """Save current window settings"""
        try:
            # Get current window geometry
            geometry = self.geometry()
            width, height, x, y = self._parse_geometry(geometry)

            # Check if maximized
            maximized = self.state() == 'zoomed'

            # Get paned window sash position (if it exists)
            ebay_paned_pos = None
            if hasattr(self, 'ebay_paned'):
                try:
                    # Get sash position (distance from top)
                    sash_coords = self.ebay_paned.sash_coord(0)  # First sash
                    if sash_coords:
                        ebay_paned_pos = sash_coords[1]  # Y coordinate
                except:
                    pass

            # Save window settings with paned position
            settings_dict = {
                'width': width,
                'height': height,
                'x': x,
                'y': y,
                'maximized': maximized
            }
            if ebay_paned_pos is not None:
                settings_dict['ebay_paned_pos'] = ebay_paned_pos

            self.settings.save_window_settings(**settings_dict)
            self.settings.save_settings()

        except Exception as e:
            logging.error(f"Error saving window settings: {e}")

    def _parse_geometry(self, geometry_string: str) -> tuple:
        """Parse tkinter geometry string into width, height, x, y"""
        try:
            # Format: "800x600+100+50"
            import re
            match = re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', geometry_string)
            if match:
                return int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            else:
                return 780, 760, 100, 100
        except:
            return 780, 760, 100, 100

    def _save_ebay_alert_settings(self):
        """Save eBay alert threshold settings when they change."""
        try:
            self.settings.save_alert_settings(
                ebay_send_min_similarity=self.alert_min_similarity.get(),
                ebay_send_min_profit=self.alert_min_profit.get()
            )
        except:
            pass  # Ignore errors during saving

    def on_closing(self):
        """Handle application closing - save settings and cleanup resources"""
        try:
            # Save window settings
            self._save_window_settings()

            # Save any recent paths
            if hasattr(self, 'image_analysis_path'):
                self.settings.save_recent_paths(image_analysis_path=str(self.image_analysis_path))

            logging.info("Settings saved on application exit")

        except Exception as e:
            logging.error(f"Error saving settings on exit: {e}")

        # Clean up any running threads and Playwright instances
        try:
            # Stop any running background threads
            if hasattr(self, 'run_thread') and self.run_thread and self.run_thread.is_alive():
                logging.info("Waiting for background thread to complete...")
                # Give thread a moment to finish gracefully
                self.run_thread.join(timeout=2.0)

            # Force cleanup of any remaining Playwright processes
            self._cleanup_playwright_processes()

        except Exception as e:
            logging.error(f"Error during resource cleanup: {e}")

        # Close the application
        self.quit()  # Exit the mainloop first
        self.destroy()  # Then destroy all widgets

    def _cleanup_playwright_processes(self):
        """Cleanup any remaining tracked Playwright instances"""
        try:
            import asyncio

            # Clean up any tracked Playwright matchers
            if self._active_playwright_matchers:
                logging.info(f"Cleaning up {len(self._active_playwright_matchers)} active Playwright matchers...")

                for matcher in self._active_playwright_matchers[:]:  # Copy list to avoid modification during iteration
                    try:
                        # Try to cleanup each matcher with proper event loop handling
                        loop = None
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            # No running loop, safe to use asyncio.run
                            asyncio.run(matcher.cleanup())
                        else:
                            # Running loop exists, create new task
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, matcher.cleanup())
                                future.result(timeout=5)  # 5 second timeout

                        self._active_playwright_matchers.remove(matcher)
                        logging.debug("Successfully cleaned up Playwright matcher")
                    except Exception as e:
                        logging.debug(f"Error cleaning up specific matcher: {e}")
                        continue

            # Clear the list
            self._active_playwright_matchers.clear()
            logging.info("Playwright cleanup completed")

        except Exception as e:
            logging.debug(f"Playwright cleanup error (non-critical): {e}")
            pass  # Don't let cleanup errors prevent app exit

    def _convert_image_results_to_analysis(self, search_result: dict) -> list:
        """Convert image search results to the format expected by the analysis display"""
        results = []

        # Get configuration values
        try:
            usd_to_jpy = float(self.usd_jpy_rate.get())
            min_profit = float(self.min_profit_margin.get())
            min_sold = int(self.min_sold_items.get())
        except (ValueError, AttributeError):
            usd_to_jpy = 150
            min_profit = 20
            min_sold = 3

        # Check if we have enough sold items
        if search_result['sold_count'] < min_sold:
            return results

        # Calculate profit margins for the image search result
        median_price_usd = search_result['median_price']
        avg_price_usd = search_result['avg_price']

        # Estimate various Mandarake price points for comparison
        # (since we don't have a specific Mandarake price for the image)
        estimated_mandarake_prices = [
            median_price_usd * usd_to_jpy * 0.3,  # 30% of USD median
            median_price_usd * usd_to_jpy * 0.5,  # 50% of USD median
            median_price_usd * usd_to_jpy * 0.7,  # 70% of USD median
        ]

        for i, mandarake_price_jpy in enumerate(estimated_mandarake_prices):
            mandarake_usd = mandarake_price_jpy / usd_to_jpy

            # Estimate shipping and fees
            estimated_fees = median_price_usd * 0.15 + 5
            net_proceeds = median_price_usd - estimated_fees

            profit_margin = ((net_proceeds - mandarake_usd) / mandarake_usd) * 100 if mandarake_usd > 0 else 0

            if profit_margin > min_profit:
                # Create search term info
                search_term = search_result.get('search_term', 'Image search result')
                if search_result.get('lens_results', {}).get('product_names'):
                    search_term = search_result['lens_results']['product_names'][0]

                title = f"{search_term} (Est. {int((i+1)*30)}% of eBay price)"

                results.append({
                    'title': title,
                    'mandarake_price': int(mandarake_price_jpy),
                    'ebay_sold_count': search_result['sold_count'],
                    'ebay_median_price': median_price_usd,
                    'ebay_avg_price': avg_price_usd,
                    'ebay_price_range': f"${search_result['min_price']:.2f} - ${search_result['max_price']:.2f}",
                    'profit_margin': profit_margin,
                    'estimated_profit': net_proceeds - mandarake_usd
                })

        # Sort by profit margin (highest first)
        results.sort(key=lambda x: x['profit_margin'], reverse=True)

        return results[:5]  # Return top 5 scenarios

    # ------------------------------------------------------------------
    # Config load/save/run
    # ------------------------------------------------------------------
    def load_config(self):
        path = filedialog.askopenfilename(filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self._populate_from_config(config)
            self.last_saved_path = Path(path)
            self.status_var.set(f"Loaded config: {path}")
            # Add to recent files
            self.settings.add_recent_config_file(str(Path(path)))
            self._update_recent_menu()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load config: {exc}")

    def save_config(self):
        config = self._collect_config()
        if not config:
            return

        # Save directly without prompts
        try:
            config_path = self._save_config_autoname(config)
            # Add to recent files
            self.settings.add_recent_config_file(str(config_path))
            self._update_recent_menu()
            self.status_var.set(f"Saved: {config_path.name}")
        except Exception as exc:
            messagebox.showerror('Error', f'Failed to save config: {exc}')

    def _save_config_on_enter(self, event=None):
        """Autosave config with new filename when Enter is pressed in keyword field."""
        # Commit keyword changes first
        self._commit_keyword_changes(event)

        # Save config with autoname
        config = self._collect_config()
        if not config:
            return

        try:
            config_path = self._save_config_autoname(config)
            # Add to recent files
            self.settings.add_recent_config_file(str(config_path))
            self._update_recent_menu()

            # Reload the tree to ensure the new file appears
            self._load_config_tree()

            # Select the newly saved config in the tree
            for item in self.config_tree.get_children():
                values = self.config_tree.item(item, 'values')
                if values and values[0] == config_path.name:
                    self.config_tree.selection_set(item)
                    self.config_tree.see(item)
                    break

            self.status_var.set(f"✓ Saved: {config_path.name}")
        except Exception as exc:
            self.status_var.set(f"Save failed: {exc}")

    def run_now(self):
        # Check which store is selected
        store = self.current_store.get()

        if store == "Suruga-ya":
            # Run Suruga-ya scraper
            config = self._collect_config()
            if not config:
                return
            config_path = self._save_config_autoname(config)
            self.status_var.set(f"Running Suruga-ya scraper: {config_path}")
            self.cancel_requested = False
            self.cancel_button.config(state='normal')
            self._start_thread(self._run_surugaya_scraper, str(config_path))
            return

        # Check if a CSV is loaded - if so, use its corresponding config
        if hasattr(self, 'csv_compare_path') and self.csv_compare_path:
            # Try to find the matching config by CSV path
            csv_filename = self.csv_compare_path.stem  # Get filename without extension
            potential_config = Path('configs') / f"{csv_filename}.json"

            if potential_config.exists():
                # Use the existing config associated with the loaded CSV
                config_path = potential_config
                print(f"[GUI DEBUG] Using config for loaded CSV: {config_path.name}")
                self.status_var.set(f"Re-running scraper for loaded CSV: {config_path.name}")
            else:
                # CSV loaded but no matching config found, use current GUI settings
                print(f"[GUI DEBUG] No matching config for CSV, using GUI settings")
                config = self._collect_config()
                if not config:
                    return
                config_path = self._save_config_autoname(config)
                self.status_var.set(f"Running scraper: {config_path}")
        else:
            # No CSV loaded, use current GUI settings
            config = self._collect_config()
            if not config:
                return
            config_path = self._save_config_autoname(config)
            self.status_var.set(f"Running scraper: {config_path}")

        mimic = bool(self.mimic_var.get())
        print(f"[GUI DEBUG] Checkbox mimic value: {self.mimic_var.get()}")
        print(f"[GUI DEBUG] Bool mimic value: {mimic}")
        self.cancel_requested = False  # Reset cancel flag
        self.cancel_button.config(state='normal')  # Enable cancel button
        self._start_thread(self._run_scraper, str(config_path), mimic)

    def cancel_search(self):
        """Cancel the currently running search"""
        self.cancel_requested = True
        if self.current_scraper:
            # Set a flag on the scraper to stop it
            self.current_scraper._cancel_requested = True
        self.status_var.set("Cancellation requested...")
        self.cancel_button.config(state='disabled')

    def _open_search_url(self, event=None):
        """Open the search URL in the default browser"""
        url_text = self.url_var.get()
        # Extract URL (remove any notes in parentheses)
        url = url_text.split(" (")[0].strip()
        if url and url.startswith("http"):
            import webbrowser
            webbrowser.open(url)
        else:
            messagebox.showinfo("No URL", "Enter search criteria to generate a URL")

    def schedule_run(self):
        """Switch to schedules tab in Mandarake tab."""
        # Switch to Mandarake tab
        main_notebook = self.children['!notebook']
        main_notebook.select(0)  # Select Mandarake tab (index 0)

        # Find and select schedules tab in config/schedule notebook
        for widget in self.children.values():
            if isinstance(widget, ttk.Frame):  # Mandarake tab frame
                for child in widget.children.values():
                    if isinstance(child, ttk.Notebook):  # Config/Schedule notebook
                        child.select(1)  # Select Schedules tab (index 1)
                        break
                break

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _slugify(self, value: str) -> str:
        """Convert string to filesystem-safe slug."""
        return utils.slugify(value)

    def _suggest_config_filename(self, config: dict) -> str:
        return utils.suggest_config_filename(config)

    def _generate_csv_filename(self, config: dict) -> str:
        """Generate CSV filename based on search parameters"""
        return utils.generate_csv_filename(config)

    def _find_matching_csv(self, config: dict) -> Optional[Path]:
        """Find existing CSV files that match the search parameters"""
        return utils.find_matching_csv(config)

    def _save_config_to_path(self, config: dict, path: Path, update_tree: bool = True):
        path.parent.mkdir(parents=True, exist_ok=True)

        # Generate paths for CSV and images, but DON'T create folders yet
        # Folders will be created when scraper actually runs
        results_dir = Path('results')
        csv_filename = self._generate_csv_filename(config)
        config['csv'] = str(results_dir / csv_filename)

        # Auto-generate download_images path based on config filename
        config_stem = path.stem  # Filename without extension
        images_dir = Path('images') / config_stem
        config['download_images'] = str(images_dir) + '/'

        if hasattr(self, 'csv_path_var'):
            self.csv_path_var.set(config['csv'])
        if hasattr(self, 'download_dir_var'):
            self.download_dir_var.set(config['download_images'])

        with path.open('w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self.last_saved_path = path
        if hasattr(self, 'csv_path_var'):
            self.csv_path_var.set(config['csv'])
        if update_tree and hasattr(self, '_update_tree_item'):
            self._update_tree_item(path, config)
        self.status_var.set(f"Saved config: {path}")

    def _save_config_autoname(self, config: dict) -> Path:
        filename = self._suggest_config_filename(config)
        path = Path('configs') / filename
        self._save_config_to_path(config, path, update_tree=True)
        return path

    def _collect_config(self):
        """Collect configuration data from GUI widgets using configuration manager."""
        return self.config_manager.collect_config_from_gui(self)

    def _resolve_shop(self):
        """Get the selected shop code from the listbox."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._resolve_shop()
        return "all"

    def _resolve_shop_old(self):
        """Old method - keeping for reference during migration."""
        for code, name in STORE_OPTIONS:
            label = f"{name} ({code})"
            if selection == label:
                return code
        # Default to shop '0' instead of searching all shops
        resolved = selection.strip()
        return resolved if resolved else '0'

    def _write_temp_config(self, config: dict) -> str:
        Path('configs').mkdir(exist_ok=True)
        temp_path = Path('configs/gui_temp.json')
        with temp_path.open('w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return str(temp_path)

    def _run_scraper(self, config_path: str, use_mimic: bool):
        config_path = Path(config_path)
        try:
            print(f"[GUI DEBUG] Starting scraper with use_mimic={use_mimic}")

            # Load config to check for Japanese text and URL
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                keyword = config.get('keyword', '')
                provided_url = config.get('search_url')
                print(f"[GUI DEBUG] Keyword from config loaded")
                print(f"[GUI DEBUG] Keyword has {len(keyword)} characters")

                if provided_url and 'mandarake.co.jp' in provided_url:
                    print(f"[MANDARAKE SEARCH] Using provided URL: {provided_url}")
                else:
                    print(f"[MANDARAKE SEARCH] Building URL from config params")

            scraper = MandarakeScraper(str(config_path), use_mimic=use_mimic)
            self.current_scraper = scraper  # Track scraper instance
            scraper._cancel_requested = False  # Initialize cancel flag
            print(f"[GUI DEBUG] Scraper browser mimic enabled: {scraper.use_mimic}")
            print(f"[GUI DEBUG] Scraper browser object type: {type(scraper.browser_mimic)}")
            scraper.run()

            # Check if cancelled
            if self.cancel_requested:
                self.run_queue.put(("status", "Scrape cancelled by user."))
            else:
                self.run_queue.put(("status", "Scrape completed."))
                self.run_queue.put(("results", str(config_path)))
        except Exception as exc:
            import traceback
            print(f"[GUI DEBUG] Full exception traceback:")
            traceback.print_exc()
            if self.cancel_requested:
                self.run_queue.put(("status", "Scrape cancelled."))
            else:
                self.run_queue.put(("error", f"Scrape failed: {exc}"))
        finally:
            self.current_scraper = None
            self.run_queue.put(("cleanup", str(config_path)))

    def _run_surugaya_scraper(self, config_path: str):
        """Run Suruga-ya scraper in background thread"""
        config_path = Path(config_path)
        try:
            # Load config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Check if URL was provided directly
            provided_url = config.get('search_url')

            keyword = config.get('keyword', '')
            category1 = config.get('category1', '7')  # Main category - default to Books
            category2 = config.get('category2')  # Detailed category
            shop_code = config.get('shop', 'all')
            max_pages = config.get('max_pages', 2)
            show_out_of_stock = config.get('show_out_of_stock', False)
            exclude_word = config.get('exclude_word', '')
            condition = config.get('condition', 'all')
            adult_only = config.get('adult_only', False)

            # Calculate max results from max_pages (assuming ~50 items per page)
            # Ensure max_pages is an integer
            try:
                max_pages = int(max_pages) if max_pages else 2
            except (ValueError, TypeError):
                max_pages = 2
            max_results = max_pages * 50

            # Initialize scraper
            from scrapers.surugaya_scraper import SurugayaScraper
            scraper = SurugayaScraper()
            self.current_scraper = scraper
            scraper._cancel_requested = False

            # Use provided URL or build from params
            if provided_url and 'suruga-ya.jp' in provided_url:
                print(f"[SURUGA-YA SEARCH] Using provided URL: {provided_url}")
                search_desc = f"Searching Suruga-ya with provided URL"

                # Run search with provided URL
                results = scraper.search(
                    keyword=keyword,
                    category1=category1,
                    category2=category2,
                    shop_code=shop_code,
                    exclude_word=exclude_word,
                    condition=condition,
                    max_results=max_results,
                    show_out_of_stock=show_out_of_stock,
                    adult_only=adult_only,
                    search_url=provided_url  # Pass the provided URL directly
                )
            else:
                # Build URL with new parameters
                from store_codes.surugaya_codes import build_surugaya_search_url
                search_url = build_surugaya_search_url(
                    keyword=keyword,
                    category1=category1,
                    category2=category2,
                    shop_code=shop_code,
                    exclude_word=exclude_word,
                    condition=condition,
                    in_stock_only=not show_out_of_stock,
                    adult_only=adult_only
                )
                print(f"[SURUGA-YA SEARCH] Built URL from params: {search_url}")
                search_desc = f"Searching Suruga-ya: {keyword}"
                if exclude_word:
                    search_desc += f" (excluding: {exclude_word})"

                # Run search with built URL
                results = scraper.search(
                    keyword=keyword,
                    category1=category1,
                    category2=category2,
                    shop_code=shop_code,
                    exclude_word=exclude_word,
                    condition=condition,
                    max_results=max_results,
                    show_out_of_stock=show_out_of_stock,
                    adult_only=adult_only
                )

            self.run_queue.put(("status", search_desc))

            # Save results to CSV and download images
            if results:
                csv_filename = config_path.stem + '.csv'
                csv_path = Path('results') / csv_filename
                csv_path.parent.mkdir(exist_ok=True)

                # First, translate all titles quickly (these are fast)
                import requests
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='ja', target='en')

                print(f"[SURUGAYA] Translating {len(results)} titles...", flush=True)
                for i, item in enumerate(results):
                    title = item.get('title', '')
                    if title:
                        try:
                            if len(title) > 4000:
                                title_en = translator.translate(title[:4000])
                            else:
                                title_en = translator.translate(title)
                            item['title_en'] = title_en
                            if (i + 1) % 10 == 0:
                                print(f"[SURUGAYA] Translated {i+1}/{len(results)}", flush=True)
                        except Exception as e:
                            print(f"[SURUGAYA] Failed to translate title {i+1}: {e}", flush=True)
                            item['title_en'] = title
                    else:
                        item['title_en'] = ''

                # Merge with existing CSV if it exists
                from datetime import datetime
                import csv

                current_time = datetime.now()
                existing_items = {}

                if csv_path.exists():
                    try:
                        with open(csv_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                url = row.get('url', '')
                                if url:
                                    existing_items[url] = row
                        print(f"[SURUGA-YA] Loaded {len(existing_items)} existing items from CSV")
                    except Exception as e:
                        print(f"[SURUGA-YA] Could not read existing CSV: {e}")
                        existing_items = {}

                # Merge new results with existing items
                new_count = 0
                updated_count = 0
                merged_items = {}

                # First, add all existing items
                for url, item in existing_items.items():
                    merged_items[url] = item

                # Then add/update with new results
                for result in results:
                    url = result.get('url', '')
                    if not url:
                        continue

                    # Add timestamps
                    if url in existing_items:
                        # Update last_seen but keep first_seen from existing
                        result['first_seen'] = existing_items[url].get('first_seen', current_time.isoformat())
                        result['last_seen'] = current_time.isoformat()
                        # Preserve eBay comparison results if they exist
                        result['ebay_compared'] = existing_items[url].get('ebay_compared', '')
                        result['ebay_match_found'] = existing_items[url].get('ebay_match_found', '')
                        result['ebay_best_match_title'] = existing_items[url].get('ebay_best_match_title', '')
                        result['ebay_similarity'] = existing_items[url].get('ebay_similarity', '')
                        result['ebay_price'] = existing_items[url].get('ebay_price', '')
                        result['ebay_profit_margin'] = existing_items[url].get('ebay_profit_margin', '')
                        updated_count += 1
                    else:
                        # New item
                        result['first_seen'] = current_time.isoformat()
                        result['last_seen'] = current_time.isoformat()
                        result['ebay_compared'] = ''
                        result['ebay_match_found'] = ''
                        result['ebay_best_match_title'] = ''
                        result['ebay_similarity'] = ''
                        result['ebay_price'] = ''
                        result['ebay_profit_margin'] = ''
                        new_count += 1

                    merged_items[url] = result

                # Sort by first_seen (newest first)
                sorted_items = sorted(merged_items.values(), key=lambda x: x.get('first_seen', ''), reverse=True)

                # Trim old items if max_csv_items is set
                max_csv_items = self.settings.get_setting('scraper.max_csv_items', 0)
                if max_csv_items > 0 and len(sorted_items) > max_csv_items:
                    removed_count = len(sorted_items) - max_csv_items
                    sorted_items = sorted_items[:max_csv_items]
                    print(f"[SURUGA-YA] Trimmed {removed_count} old items (keeping newest {max_csv_items})")

                # Write merged results WITHOUT images first (so treeview can load immediately)
                def write_csv():
                    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                        fieldnames = ['first_seen', 'last_seen', 'title', 'title_en', 'price', 'condition', 'stock_status', 'url', 'image_url', 'local_image',
                                      'ebay_compared', 'ebay_match_found', 'ebay_best_match_title', 'ebay_similarity', 'ebay_price', 'ebay_profit_margin']
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writeheader()
                        writer.writerows(sorted_items)

                write_csv()

                self.run_queue.put(("status", f"Found {len(merged_items)} items ({new_count} new, {updated_count} updated) - saved to {csv_path.name}"))

                # Update config with CSV path
                config['csv'] = str(csv_path)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                # DISPLAY RESULTS IMMEDIATELY (before downloading images)
                self.run_queue.put(("results", str(config_path)))

                # Now download images in parallel (like CSV comparison does)
                images_dir = Path('images') / config_path.stem
                images_dir.mkdir(parents=True, exist_ok=True)

                print(f"[SURUGAYA] Downloading {len(results)} images in parallel...", flush=True)
                from concurrent.futures import ThreadPoolExecutor, as_completed

                # Create session with connection pooling
                session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=20,
                    pool_maxsize=20,
                    max_retries=2
                )
                session.mount('http://', adapter)
                session.mount('https://', adapter)

                def download_image(args):
                    i, item = args
                    image_url = item.get('image_url', '')
                    if not image_url:
                        return (i, None)

                    try:
                        response = session.get(image_url, timeout=10)
                        if response.status_code == 200:
                            img_filename = f"thumb_product_{i:04d}.jpg"
                            img_path = images_dir / img_filename
                            with open(img_path, 'wb') as img_file:
                                img_file.write(response.content)
                            return (i, str(img_path))
                    except Exception as e:
                        print(f"[SURUGAYA] Failed to download image {i+1}: {e}", flush=True)
                    return (i, None)

                # Download in parallel with 20 workers
                downloaded_count = 0
                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = {executor.submit(download_image, (i, item)): i for i, item in enumerate(results)}

                    for future in as_completed(futures):
                        i, img_path = future.result()
                        if img_path:
                            # Update the item in sorted_items
                            for item in sorted_items:
                                if item.get('url') == results[i].get('url'):
                                    item['local_image'] = img_path
                                    break
                            downloaded_count += 1

                            if downloaded_count % 20 == 0:
                                print(f"[SURUGAYA] Downloaded {downloaded_count}/{len(results)} images", flush=True)
                                # Update CSV periodically
                                write_csv()

                session.close()

                # Final CSV write with all images
                write_csv()
                print(f"[SURUGAYA] ✓ Downloaded {downloaded_count}/{len(results)} images", flush=True)

                # Reload the results in the treeview (to show images)
                self.run_queue.put(("results", str(config_path)))
            else:
                self.run_queue.put(("status", "No results found"))

        except Exception as exc:
            import traceback
            traceback.print_exc()
            if self.cancel_requested:
                self.run_queue.put(("status", "Search cancelled."))
            else:
                self.run_queue.put(("error", f"Suruga-ya search failed: {exc}"))
        finally:
            self.current_scraper = None
            self.run_queue.put(("cleanup", str(config_path)))

    def _schedule_worker(self, config_path: str, schedule_time: str, use_mimic: bool):
        workers.schedule_worker(config_path, schedule_time, use_mimic, self.run_queue)

    def _start_thread(self, target, *args):
        if self.run_thread and self.run_thread.is_alive():
            messagebox.showinfo("Busy", "A task is already running.")
            return
        self.run_thread = threading.Thread(target=target, args=args, daemon=True)
        self.run_thread.start()

    def _poll_queue(self):
        try:
            while True:
                message_type, payload = self.run_queue.get_nowait()
                if message_type == "status":
                    self.status_var.set(payload)
                    # Disable cancel button when status indicates completion/error
                    if any(word in payload.lower() for word in ["completed", "cancelled", "error", "failed"]):
                        self.cancel_button.config(state='disabled')
                elif message_type == "error":
                    messagebox.showerror("Error", payload)
                    self.status_var.set("Error")
                    self.cancel_button.config(state='disabled')
                elif message_type == "results":
                    config_path = Path(payload)
                    try:
                        with config_path.open('r', encoding='utf-8') as f:
                            config = json.load(f)

                        # First try the CSV path from config
                        csv_value = config.get('csv', '')
                        csv_path = Path(csv_value) if csv_value else None

                        # If CSV doesn't exist, try to find a matching one
                        if not csv_path or not csv_path.exists():
                            print(f"[GUI DEBUG] CSV from config not found: {csv_path}")
                            csv_path = self._find_matching_csv(config)

                        if csv_path:
                            print(f"[GUI DEBUG] Auto-loading CSV into comparison tree: {csv_path}")
                            # Load CSV using modular worker
                            self._load_csv_worker(csv_path)
                        else:
                            print(f"[GUI DEBUG] No CSV file found for config")

                    except Exception as e:
                        print(f"[GUI DEBUG] Error loading results: {e}")
                        import traceback
                        traceback.print_exc()
                    self.cancel_button.config(state='disabled')
                elif message_type == "cleanup":
                    try:
                        if payload.endswith('gui_temp.json'):
                            Path(payload).unlink(missing_ok=True)
                    except Exception:
                        pass
                    self.cancel_button.config(state='disabled')
                elif message_type == "browserless_results":
                    self._display_browserless_results(payload)
                elif message_type == "browserless_status":
                    self.browserless_status.set(payload)
                elif message_type == "browserless_progress_stop":
                    self.browserless_progress.stop()
        except queue.Empty:
            pass
        self.after(500, self._poll_queue)

    # ------------------------------------------------------------------
    def _load_gui_settings(self):
        settings = {'mimic': False}
        try:
            if SETTINGS_PATH.exists():
                with SETTINGS_PATH.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        settings.update(data)
        except Exception:
            settings = {'mimic': False}
        self.gui_settings = settings
        try:
            self._settings_loaded = False
            self.mimic_var.set(settings.get('mimic', True))  # Default to True for Unicode support

            # Load eBay search settings if they exist
            if hasattr(self, 'browserless_max_results'):
                self.browserless_max_results.set(settings.get('ebay_max_results', "10"))
            if hasattr(self, 'browserless_max_comparisons'):
                self.browserless_max_comparisons.set(settings.get('ebay_max_comparisons', "MAX"))

            # Load CSV filter settings
            if hasattr(self, 'csv_in_stock_only'):
                self.csv_in_stock_only.set(settings.get('csv_in_stock_only', True))
            if hasattr(self, 'csv_add_secondary_keyword'):
                self.csv_add_secondary_keyword.set(settings.get('csv_add_secondary_keyword', False))
        finally:
            self._settings_loaded = True

    def _on_window_mapped(self, event=None):
        """Handle window map event - restore sash position once after window is shown."""
        # Unbind after first call
        self.unbind('<Map>')
        # Wait for window to stabilize, then restore
        self.after(100, self._restore_listbox_paned_position)

    def _on_listbox_sash_moved(self, event=None):
        """Track when user manually moves the sash."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._on_listbox_sash_moved(event)

    def _restore_listbox_paned_position(self):
        """Restore the listbox paned window sash position from saved settings."""
        if not hasattr(self, 'listbox_paned'):
            return
        try:
            ratio = self.gui_settings.get('listbox_paned_ratio', 0.65)  # Default 65% for categories, 35% for shops
            total_width = self.listbox_paned.winfo_width()
            sash_pos = int(total_width * ratio)
            self.listbox_paned.sash_place(0, sash_pos, 0)
            self._user_sash_ratio = ratio  # Initialize user ratio to the restored value
        except Exception as e:
            print(f"[LISTBOX PANED] Error restoring position: {e}")

    def _save_gui_settings(self):
        if not getattr(self, '_settings_loaded', False):
            return
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Save listbox paned position - use tracked user ratio if available
            listbox_ratio = self.gui_settings.get('listbox_paned_ratio', 0.65)
            if hasattr(self, '_user_sash_ratio') and self._user_sash_ratio is not None:
                listbox_ratio = self._user_sash_ratio

            data = {
                'mimic': bool(self.mimic_var.get()),
                'ebay_max_results': self.browserless_max_results.get() if hasattr(self, 'browserless_max_results') else "10",
                'ebay_max_comparisons': self.browserless_max_comparisons.get() if hasattr(self, 'browserless_max_comparisons') else "MAX",
                'csv_in_stock_only': bool(self.csv_in_stock_only.get()) if hasattr(self, 'csv_in_stock_only') else True,
                'csv_add_secondary_keyword': bool(self.csv_add_secondary_keyword.get()) if hasattr(self, 'csv_add_secondary_keyword') else False,
                'listbox_paned_ratio': listbox_ratio
            }
            with SETTINGS_PATH.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _on_mimic_changed(self, *args):
        # Settings saved on close, no need to save on every change
        pass

    def _on_max_csv_items_changed(self, *args):
        """Handle max CSV items setting change with validation"""
        value = self.max_csv_items_var.get().strip()

        # Allow empty or numeric values only
        if value == '':
            value = '0'

        try:
            max_items = int(value)
            if max_items < 0:
                max_items = 0

            # Update settings
            self.settings.set_setting('scraper.max_csv_items', max_items)
            self.settings.save_settings()

        except ValueError:
            # Invalid input - reset to current saved value
            current_value = self.settings.get_setting('scraper.max_csv_items', 0)
            self.max_csv_items_var.set(str(current_value))

    def _on_marketplace_toggle(self):
        """Handle marketplace toggle changes"""
        # Save toggle state
        toggles = {
            'mandarake': self.mandarake_enabled.get(),
            'ebay': self.ebay_enabled.get(),
            'surugaya': self.surugaya_enabled.get(),
            'dejapan': self.dejapan_enabled.get(),
            'alerts': self.alerts_enabled.get()
        }
        self.settings.save_marketplace_toggles(toggles)

        # Show restart required message
        messagebox.showinfo(
            "Restart Required",
            "Marketplace changes will take effect after restarting the application."
        )

    def _on_config_schedule_tab_changed(self, event):
        """Handle config/schedule tab change to show appropriate buttons."""
        selected_tab = self.config_schedule_notebook.index(self.config_schedule_notebook.select())

        if selected_tab == 0:  # Configs tab
            # Show config buttons, hide schedule frame buttons
            self.config_buttons_frame.grid()
            self.schedule_frame.hide_buttons()
        else:  # Schedules tab
            # Hide config buttons, show schedule frame buttons
            self.config_buttons_frame.grid_remove()
            self.schedule_frame.show_buttons_in_parent(self.config_buttons_frame.master, row=1)

    def _on_close(self):
        # Cancel any pending auto-save timers
        if hasattr(self, '_auto_save_timer') and self._auto_save_timer:
            try:
                self.after_cancel(self._auto_save_timer)
                self._auto_save_timer = None
            except:
                pass

        # Stop schedule executor
        if hasattr(self, 'schedule_executor'):
            self.schedule_executor.stop()

        self._save_gui_settings()

        # Force kill any lingering Python subprocesses (Scrapy, etc.)
        try:
            import psutil
            import os
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except:
                    pass
        except ImportError:
            # psutil not available, skip subprocess cleanup
            pass
        except Exception as e:
            print(f"[CLEANUP] Error killing subprocesses: {e}")

        # Call our comprehensive closing method
        self.on_closing()

    # ------------------------------------------------------------------
    # Category helpers and preview
    # ------------------------------------------------------------------
    def _populate_detail_categories(self, main_code=None):
        self.detail_listbox.delete(0, tk.END)
        self.detail_code_map = []

        def should_include(code: str) -> bool:
            if not main_code:
                return True
            # If main_code is "00" (Everything), show all categories
            if main_code == "00":
                return True
            return code.startswith(main_code)

        for code, info in sorted(MANDARAKE_ALL_CATEGORIES.items()):
            if should_include(code):
                label = f"{code} - {info['en']}"
                self.detail_listbox.insert(tk.END, label)
                self.detail_code_map.append(code)

    def _populate_shop_list(self):
        """Populate shop listbox with all available stores."""
        self.shop_listbox.delete(0, tk.END)
        self.shop_code_map = []

        # Add "All Stores" option first
        self.shop_listbox.insert(tk.END, "All Stores")
        self.shop_code_map.append("all")

        # Add all individual stores
        for code, name in STORE_OPTIONS:
            label = f"{name} ({code})"
            self.shop_listbox.insert(tk.END, label)
            self.shop_code_map.append(code)

        # Default selection: All Stores
        self.shop_listbox.selection_set(0)

    def _on_shop_selected(self, event=None):
        """Handle shop selection from listbox."""
        selection = self.shop_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        shop_code = self.shop_code_map[index]

        self._update_preview()

    def _on_store_changed(self, event=None):
        """Handle store selection change - reload categories and shops."""
        store = self.current_store.get()

        if store == "Mandarake":
            # Reload Mandarake categories and shops
            self._populate_detail_categories()
            self._populate_shop_list()
            # Update main category dropdown
            self.main_category_combo['values'] = [f"{name} ({code})" for code, name in MAIN_CATEGORY_OPTIONS]
            # Auto-select "Everything" category
            self.main_category_var.set("Everything (00)")
            # Set results per page to 240 (Mandarake default)
            self.results_per_page_var.set('240')
            # Trigger category selection to populate detailed categories
            self._on_main_category_selected()

            # Hide Suruga-ya specific fields
            self.exclude_word_label.grid_remove()
            self.exclude_word_entry.grid_remove()
            self.condition_label.grid_remove()
            self.condition_combo.grid_remove()

        elif store == "Suruga-ya":
            # Load Suruga-ya categories and shops
            from store_codes.surugaya_codes import SURUGAYA_MAIN_CATEGORIES
            # Update main category dropdown with Suruga-ya categories
            category_values = [f"{name} ({code})" for code, name in sorted(SURUGAYA_MAIN_CATEGORIES.items())]
            self.main_category_combo['values'] = category_values
            # Auto-select first category (Games)
            if category_values:
                self.main_category_var.set(category_values[0])
            # Load Suruga-ya shops
            self._populate_surugaya_shops()
            # Set results per page to 50 (Suruga-ya fixed)
            self.results_per_page_var.set('50')
            # Trigger category selection to populate detailed categories
            self._on_main_category_selected()

            # Show Suruga-ya specific fields
            self.exclude_word_label.grid()
            self.exclude_word_entry.grid()
            self.condition_label.grid()
            self.condition_combo.grid()

    def _populate_surugaya_categories(self, main_code=None):
        """Populate detail categories listbox with Suruga-ya categories based on main category."""
        from store_codes.surugaya_codes import SURUGAYA_DETAILED_CATEGORIES
        self.detail_listbox.delete(0, tk.END)
        self.detail_code_map = []

        if not main_code:
            # No main category selected - show nothing or all
            return

        # Get subcategories for selected main category
        subcategories = SURUGAYA_DETAILED_CATEGORIES.get(main_code, {})

        for code, name in sorted(subcategories.items()):
            label = f"{code} - {name}"
            self.detail_listbox.insert(tk.END, label)
            self.detail_code_map.append(code)

    def _populate_surugaya_shops(self):
        """Populate shop listbox with Suruga-ya shops."""
        from store_codes.surugaya_codes import SURUGAYA_SHOPS
        self.shop_listbox.delete(0, tk.END)
        self.shop_code_map = []

        # Add "All Stores" option first
        self.shop_listbox.insert(tk.END, "All Stores")
        self.shop_code_map.append("all")

        # Add all individual stores
        for code, name in sorted(SURUGAYA_SHOPS.items()):
            label = f"{name} ({code})"
            self.shop_listbox.insert(tk.END, label)
            self.shop_code_map.append(code)

        # Default selection: All Stores
        self.shop_listbox.selection_set(0)

    def _on_main_category_selected(self, event=None):
        # Don't auto-select during config loading - let _select_categories handle it
        if getattr(self, '_loading_config', False):
            return

        code = utils.extract_code(self.main_category_var.get())

        # Check which store is selected
        store = self.current_store.get()

        if store == "Suruga-ya":
            # Use Suruga-ya hierarchical categories
            self._populate_surugaya_categories(code)
        else:
            # Use Mandarake categories
            self._populate_detail_categories(code)

        # Auto-select the first detail category (the main category itself)
        if self.detail_listbox.size() > 0:
            self.detail_listbox.selection_clear(0, tk.END)
            self.detail_listbox.selection_set(0)

        self._update_preview()

    def _extract_code(self, label: str | None):
        if not label:
            return None
        if '(' in label and label.endswith(')'):
            return label.split('(')[-1].rstrip(')')
        return label.strip() or None

    def _match_main_code(self, code: str | None):
        if not code:
            return None
        for main_code in sorted(MANDARAKE_MAIN_CATEGORIES.keys()):
            if code.startswith(main_code):
                return main_code
        return None

    def _select_categories(self, categories):
        """Select categories in the detail listbox."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._select_categories(categories)

    def _get_selected_categories(self):
        indices = self.detail_listbox.curselection()
        return [self.detail_code_map[i] for i in indices] if indices else []

    def _get_recent_hours_value(self):
        label = getattr(self, 'recent_hours_var', None)
        label = label.get() if label else None
        for display, hours in RECENT_OPTIONS:
            if display == label:
                return hours
        return None

    def _label_for_recent_hours(self, hours):
        for display, value in RECENT_OPTIONS:
            if value == hours:
                return display
        return RECENT_OPTIONS[0][0]

    def _load_results_table(self, csv_path: Path | None):
        print(f"[GUI DEBUG] Loading results table from: {csv_path}")
        if not hasattr(self, 'result_tree'):
            return
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.result_links.clear()
        self.result_images.clear()
        self.result_data.clear()
        if not csv_path or not csv_path.exists():
            print(f"[GUI DEBUG] CSV not found: {csv_path}")
            self.status_var.set(f'CSV not found: {csv_path}')
            return
        show_images = getattr(self, 'show_images_var', None)
        show_images = show_images.get() if show_images else False
        print(f"[GUI DEBUG] Show images setting: {show_images}")
        try:
            with csv_path.open('r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    title = row.get('title', '')
                    price = row.get('price_text') or row.get('price') or ''
                    shop = row.get('shop') or row.get('shop_text') or ''
                    stock = row.get('in_stock') or row.get('stock_status') or ''
                    if isinstance(stock, str) and stock.lower() in {'true', 'false'}:
                        stock = 'Yes' if stock.lower() == 'true' else 'No'
                    category = row.get('category', '')
                    link = row.get('product_url') or row.get('url') or ''
                    local_image_path = row.get('local_image') or ''
                    web_image_url = row.get('image_url') or ''
                    item_kwargs = {'values': (title, price, shop, stock, category, link)}
                    photo = None

                    if show_images:
                        # Try local image first, then fallback to web image
                        if local_image_path:
                            print(f"[GUI DEBUG] Attempting to load local image: {local_image_path}")
                            try:
                                pil_img = Image.open(local_image_path)
                                pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)  # Slightly smaller for better fit
                                photo = ImageTk.PhotoImage(pil_img)
                                item_kwargs['image'] = photo
                                print(f"[GUI DEBUG] Successfully loaded local thumbnail: {local_image_path}")
                            except Exception as e:
                                print(f"[GUI DEBUG] Failed to load local image {local_image_path}: {e}")
                                photo = None

                        # If no local image or local image failed, try web image
                        if not photo and web_image_url:
                            print(f"[GUI DEBUG] Attempting to download web image: {web_image_url}")
                            try:
                                import requests
                                response = requests.get(web_image_url, timeout=10)
                                response.raise_for_status()
                                from io import BytesIO
                                pil_img = Image.open(BytesIO(response.content))
                                pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)  # Slightly smaller for better fit
                                photo = ImageTk.PhotoImage(pil_img)
                                item_kwargs['image'] = photo
                                print(f"[GUI DEBUG] Successfully downloaded web thumbnail: {web_image_url}")
                            except Exception as e:
                                print(f"[GUI DEBUG] Failed to download web image {web_image_url}: {e}")
                                photo = None

                        if not photo:
                            print(f"[GUI DEBUG] No image available for row: {title}")
                    else:
                        print(f"[GUI DEBUG] Show images disabled")
                    item_id = self.result_tree.insert('', tk.END, **item_kwargs)
                    self.result_data[item_id] = row
                    if photo:
                        self.result_images[item_id] = photo
                    self.result_links[item_id] = link
            self.status_var.set(f'Loaded results from {csv_path}')
        except Exception as exc:
            messagebox.showerror('Error', f'Failed to load results: {exc}')

    def _toggle_thumbnails(self):
        """Toggle thumbnail display in the results tree"""
        show_images = self.show_images_var.get()

        # Iterate through all items in the treeview
        for item_id in self.result_tree.get_children():
            if show_images:
                # Show image if available
                if item_id in self.result_images:
                    self.result_tree.item(item_id, image=self.result_images[item_id])
            else:
                # Hide image by setting empty image
                self.result_tree.item(item_id, image='')

    def _on_result_double_click(self, event=None):
        selection = self.result_tree.selection()
        if not selection:
            return
        item = selection[0]
        link = self.result_links.get(item)
        if link:
            webbrowser.open(link)

    def _show_result_tree_menu(self, event):
        """Show the context menu on the result tree."""
        selection = self.result_tree.selection()
        if selection:
            self.result_tree_menu.post(event.x_root, event.y_root)

    def _search_by_image_api(self):
        selection = self.result_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        item_data = self.result_data.get(item_id)
        if not item_data:
            messagebox.showerror("Error", "Could not find data for the selected item.")
            return

        local_image_path = item_data.get('local_image')
        if not local_image_path or not Path(local_image_path).exists():
            messagebox.showerror("Error", "Local image not found for this item. Please download images first.")
            return

        from mandarake_scraper import EbayAPI
        # Note: eBay API credentials removed from GUI - using web scraping instead
        ebay_api = EbayAPI("", "")

        self.status_var.set("Searching by image on eBay (API)...")
        url = ebay_api.search_by_image_api(local_image_path)
        if url:
            webbrowser.open(url)
            self.status_var.set("Search by image (API) complete.")
        else:
            messagebox.showerror("Error", "Could not find results using eBay API. Check logs for details.")
            self.status_var.set("Search by image (API) failed.")

    def _search_by_image_web(self):
        selection = self.result_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        item_data = self.result_data.get(item_id)
        if not item_data:
            messagebox.showerror("Error", "Could not find data for the selected item.")
            return

        local_image_path = item_data.get('local_image')
        if not local_image_path or not Path(local_image_path).exists():
            messagebox.showerror("Error", "Local image not found for this item. Please download images first.")
            return

        self.status_var.set("Searching by image on eBay (Web)...")
        self._start_thread(self._run_web_image_search, local_image_path)

    def _run_web_image_search(self, image_path):
        from ebay_image_search import run_ebay_image_search
        url = run_ebay_image_search(image_path)
        if "Error" not in url:
            webbrowser.open(url)
            self.run_queue.put(("status", "Search by image (Web) complete."))
        else:
            self.run_queue.put(("error", "Could not find results using web search."))

    # CSV tree methods
    def _show_csv_tree_menu(self, event):
        """Show the context menu on the CSV tree"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._show_csv_tree_menu(event)

    def _delete_csv_items(self):
        """Delete selected CSV items (supports multi-select)"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._delete_csv_items()

    def _on_csv_double_click(self, event=None):
        """Open product link on double click"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.on_csv_item_double_click(event)

    def _search_csv_by_image_api(self):
        """Search selected CSV item by image using eBay API"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._search_csv_by_image_api()

    def _search_csv_by_image_web(self):
        """Search selected CSV item by image using web method"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._search_csv_by_image_web()

    def _run_csv_web_image_search(self, image_path):
        """Run CSV web image search (helper for threaded execution)"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._run_csv_web_image_search(image_path)

    def _download_missing_csv_images(self):
        """Download missing images from web and save them locally"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._download_missing_csv_images()

    def _download_missing_images_worker(self):
        """Background worker to download missing images"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._download_missing_images_worker()

    def _save_updated_csv(self):
        """Save the updated CSV with new local_image paths"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._save_updated_csv()

    def _save_comparison_results_to_csv(self, comparison_results):
        """Save eBay comparison results back to the CSV file

        Args:
            comparison_results: List of dicts with comparison data including 'mandarake_item', 'similarity', 'best_match', etc.
        """
        if not self.csv_compare_path or not self.csv_compare_data:
            print("[COMPARISON SAVE] No CSV loaded, skipping save")
            return

        try:
            from datetime import datetime

            # Create a mapping of URLs to comparison results
            url_to_results = {}
            for result in comparison_results:
                mandarake_item = result.get('mandarake_item', {})
                url = mandarake_item.get('url', mandarake_item.get('product_url', ''))
                if url:
                    best_match = result.get('best_match', {})
                    url_to_results[url] = {
                        'ebay_compared': datetime.now().isoformat(),
                        'ebay_match_found': 'Yes' if best_match else 'No',
                        'ebay_best_match_title': best_match.get('title', '') if best_match else '',
                        'ebay_similarity': f"{result.get('similarity', 0):.1f}" if best_match else '',
                        'ebay_price': f"${best_match.get('price', 0):.2f}" if best_match else '',
                        'ebay_profit_margin': f"{result.get('profit_margin', 0):.1f}%" if best_match else ''
                    }

            # Update csv_compare_data with comparison results
            updated_count = 0
            for row in self.csv_compare_data:
                url = row.get('url', row.get('product_url', ''))
                if url in url_to_results:
                    row.update(url_to_results[url])
                    updated_count += 1

            # Save updated CSV
            if updated_count > 0:
                self._save_updated_csv()
                print(f"[COMPARISON SAVE] Saved comparison results for {updated_count} items to CSV")
            else:
                print("[COMPARISON SAVE] No items matched for saving")

        except Exception as e:
            print(f"[COMPARISON SAVE] Error saving comparison results: {e}")
            import traceback
            traceback.print_exc()

    def _update_tree_item(self, path: Path, config: dict):
        """Update config tree entry using the tree manager."""
        if self.tree_manager:
            self.tree_manager.update_tree_item(path, config)

    def _load_config_tree(self):
        """Load configuration tree using tree manager."""
        if self.tree_manager:
            self.tree_manager.load_config_tree()

    def _filter_config_tree(self):
        """Filter config tree based on store filter selection"""
        if not hasattr(self, 'config_store_filter') or not hasattr(self, 'config_tree'):
            return

        filter_value = self.config_store_filter.get()

        # Get all items
        all_items = list(self.config_paths.keys())

        # Show/hide items based on filter
        for item in all_items:
            # Get the store value (first column)
            values = self.config_tree.item(item, 'values')
            if values:
                store = values[0]  # Store is the first column

                # Show item if it matches filter or filter is "All"
                if filter_value == 'All' or store == filter_value:
                    self.config_tree.reattach(item, '', 'end')
                else:
                    self.config_tree.detach(item)

        print(f"[CONFIG FILTER] Filtered by: {filter_value}")

    def _setup_column_drag(self, tree):
        """Enable drag-to-reorder for treeview columns"""
        tree._drag_data = {'column': None, 'x': 0}

        def on_header_press(event):
            region = tree.identify_region(event.x, event.y)
            if region == 'heading':
                col = tree.identify_column(event.x)
                tree._drag_data['column'] = col
                tree._drag_data['x'] = event.x

        def on_header_motion(event):
            if tree._drag_data['column']:
                col = tree._drag_data['column']
                # Visual feedback: change cursor
                tree.configure(cursor='exchange')

        def on_header_release(event):
            if tree._drag_data['column']:
                src_col = tree._drag_data['column']
                region = tree.identify_region(event.x, event.y)
                if region == 'heading':
                    dst_col = tree.identify_column(event.x)
                    if src_col != dst_col:
                        self._reorder_columns(tree, src_col, dst_col)
                tree.configure(cursor='')
                tree._drag_data['column'] = None

        tree.bind('<ButtonPress-1>', on_header_press, add='+')
        tree.bind('<B1-Motion>', on_header_motion, add='+')
        tree.bind('<ButtonRelease-1>', on_header_release, add='+')

    def _reorder_columns(self, tree, src_col, dst_col):
        """Reorder treeview columns while preserving headings and widths"""
        # Get current column order
        cols = list(tree['columns'])

        # Convert column identifiers (#1, #2, etc.) to indices
        src_idx = int(src_col.replace('#', '')) - 1
        dst_idx = int(dst_col.replace('#', '')) - 1

        # Save current headings and widths for all columns
        column_info = {}
        for col in cols:
            column_info[col] = {
                'heading': tree.heading(col)['text'],
                'width': tree.column(col)['width'],
                'minwidth': tree.column(col)['minwidth'],
                'stretch': tree.column(col)['stretch'],
                'anchor': tree.column(col)['anchor']
            }

        # Reorder the columns list
        col_to_move = cols.pop(src_idx)
        cols.insert(dst_idx, col_to_move)

        # Apply new column order
        tree['columns'] = cols
        tree['displaycolumns'] = cols

        # Restore headings and widths for all columns
        for col in cols:
            info = column_info[col]
            tree.heading(col, text=info['heading'])
            tree.column(col,
                       width=info['width'],
                       minwidth=info['minwidth'],
                       stretch=info['stretch'],
                       anchor=info['anchor'])

    def _global_space_handler(self, event):
        """Global space key handler to prevent treeview selection toggle when typing.

        When an Entry field has focus, we want space to insert a space character.
        When a Treeview/Listbox has focus, we want to prevent selection toggle.
        """
        focus_widget = self.focus_get()

        # If an Entry widget has focus, allow space to work normally
        if isinstance(focus_widget, (tk.Entry, ttk.Entry)):
            return None  # Let space work in entry

        # If a Treeview or Listbox has focus, block space to prevent toggle
        if isinstance(focus_widget, (ttk.Treeview, tk.Listbox)):
            return "break"  # Prevent selection toggle

        # For any other widget, allow default behavior
        return None

    def _deselect_if_empty(self, event, tree):
        """Deselect tree items if clicking on empty area"""
        # Check if click is on an item
        item = tree.identify_row(event.y)
        if not item:
            # Clicked on empty area, deselect all
            tree.selection_remove(tree.selection())

    def _show_config_tree_menu(self, event):
        """Show context menu on config tree"""
        # Select the item under the cursor
        item = self.config_tree.identify_row(event.y)
        if item:
            self.config_tree.selection_set(item)
            # Store event coordinates for Edit Category dialog positioning
            self._last_menu_event = event
            self.config_tree_menu.post(event.x_root, event.y_root)

    def _edit_category_from_menu(self):
        """Edit category from right-click menu"""
        selection = self.config_tree.selection()
        if not selection:
            return

        item = selection[0]
        config_path = self.config_paths.get(item)
        if not config_path:
            return

        # Load config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            return

        # Get category info
        store = config.get('store', 'mandarake')
        category_code = config.get('category', '')
        category_name = config.get('category_name', '')

        # Only show dialog for unknown categories
        if not category_name and category_code:
            # Create a fake event with the stored menu coordinates
            event = self._last_menu_event if hasattr(self, '_last_menu_event') else None
            if not event:
                # Fallback to center of screen if no event stored
                class FakeEvent:
                    x_root = self.winfo_rootx() + 200
                    y_root = self.winfo_rooty() + 200
                event = FakeEvent()

            # Show the same dialog as double-click
            self._show_edit_category_dialog(config_path, config, category_code, store, event)
        else:
            messagebox.showinfo("Info", "This category is already named. Double-click to edit.")

    def _show_edit_category_dialog(self, config_path, config, category_code, store, event):
        """Show dialog to edit/add category name"""
        # Unknown code - allow user to add a name
        dialog = tk.Toplevel(self)
        dialog.title("Add Category Name")
        dialog.transient(self)
        dialog.grab_set()

        # Position dialog near mouse cursor
        x = event.x_root + 10
        y = event.y_root + 10
        dialog.geometry(f"400x150+{x}+{y}")

        ttk.Label(dialog, text=f"Unknown category code: {category_code}").pack(pady=10)
        ttk.Label(dialog, text="Enter a name for this category:").pack(pady=5)

        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        name_entry.focus()

        def save_name():
            name = name_var.get().strip()
            if name:
                # Save to config
                config['category_name'] = name
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                # Add to category codes file
                try:
                    if store == 'suruga-ya':
                        codes_file = Path('store_codes') / 'surugaya_codes.py'
                    else:
                        codes_file = Path('store_codes') / 'mandarake_codes.py'

                    if codes_file.exists():
                        # Read the file as lines
                        with open(codes_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                        # Determine the main category prefix (first 2 digits for most codes)
                        # Examples: '0101' -> '01', '050801' -> '05', '701101' -> '70'
                        main_prefix = category_code[:2] if len(category_code) >= 2 else category_code

                        # Find where to insert this entry
                        # Strategy: Find the last entry with the same main prefix, insert after it
                        insert_index = None
                        last_matching_index = None

                        import re
                        for i, line in enumerate(lines):
                            # Look for category entries: '    'CODE': {'en': 'Name', 'jp': 'Name'},
                            match = re.match(r"\s*'(\d+)':\s*\{", line)
                            if match:
                                code = match.group(1)
                                # Check if this code belongs to the same main category
                                if code.startswith(main_prefix):
                                    last_matching_index = i

                        # Insert after the last matching entry
                        if last_matching_index is not None:
                            insert_index = last_matching_index + 1
                        else:
                            # No matching entries found, try to find the main category comment
                            # and insert after it
                            for i, line in enumerate(lines):
                                if f"'{main_prefix}':" in line and 'everything' in line.lower():
                                    insert_index = i + 1
                                    break

                        if insert_index is not None:
                            # Create new entry with proper indentation
                            new_entry = f"    '{category_code}': {{'en': '{name}', 'jp': '{name}'}},\n"

                            # Insert the new entry
                            lines.insert(insert_index, new_entry)

                            # Write back to file
                            with open(codes_file, 'w', encoding='utf-8') as f:
                                f.writelines(lines)

                            print(f"[CATEGORY] Added {category_code}: {name} to {codes_file.name} under main category {main_prefix}")
                        else:
                            # Fallback: add at the end of the dict (before closing brace)
                            for i in range(len(lines) - 1, -1, -1):
                                if lines[i].strip() == '}':
                                    new_entry = f"    '{category_code}': {{'en': '{name}', 'jp': '{name}'}},\n"
                                    lines.insert(i, new_entry)
                                    with open(codes_file, 'w', encoding='utf-8') as f:
                                        f.writelines(lines)
                                    print(f"[CATEGORY] Added {category_code}: {name} to {codes_file.name} (at end)")
                                    break
                except Exception as e:
                    print(f"[CATEGORY] Could not update category file: {e}")

                # Update tree
                self._update_tree_item(config_path, config)
                dialog.destroy()
                messagebox.showinfo("Success", f"Category '{name}' saved for code {category_code}")

        ttk.Button(dialog, text="Save", command=save_name).pack(pady=10)

    def _on_config_tree_double_click(self, event):
        """Handle double-click on config tree to edit category"""
        # Identify which column was clicked
        column = self.config_tree.identify_column(event.x)
        item = self.config_tree.identify_row(event.y)

        if not item:
            return

        # Check if category column was clicked (column #4, index starts at #1)
        # Columns: store, file, keyword, category, shop...
        if column != '#4':  # Category is the 4th column
            return

        # Get config path
        config_path = self.config_paths.get(item)
        if not config_path:
            return

        # Load config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            return

        # Get current category value and store type
        store = config.get('store', 'mandarake')
        category_code = config.get('category', '')
        category_name = config.get('category_name', '')

        # Only show dialog for unknown categories
        if not category_name and category_code:
            self._show_edit_category_dialog(config_path, config, category_code, store, event)
        else:
            # For known categories, could show a different dialog if needed
            pass

    def _load_csv_from_config(self):
        """Load CSV file associated with selected config"""
        selection = self.config_tree.selection()
        if not selection:
            self.status_var.set("No config selected")
            return

        item = selection[0]
        config_path = self.config_paths.get(item)
        if not config_path:
            self.status_var.set("Config path not found")
            return

        try:
            # Load the config to get the CSV path
            with config_path.open('r', encoding='utf-8') as f:
                config = json.load(f)

            # Get the CSV path from config
            csv_path_str = config.get('csv')
            if not csv_path_str:
                self.status_var.set("No CSV path in config")
                return

            csv_path = Path(csv_path_str)
            if not csv_path.exists():
                self.status_var.set(f"CSV does not exist: {csv_path.name}")
                return

            # Load CSV using modular worker
            success = self._load_csv_worker(csv_path, autofill_from_config=config)

            if success:
                self.status_var.set(f"CSV loaded successfully: {len(self.csv_compare_data)} items")
            else:
                self.status_var.set(f"Error loading CSV: {csv_path.name}")

        except Exception as e:
            self.status_var.set(f"Error loading CSV: {e}")
            print(f"[CONFIG MENU] Error loading CSV: {e}")

    def _autofill_search_query_from_config(self, config):
        """Auto-fill eBay search query from config keyword and optionally add secondary keyword"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._autofill_search_query_from_config(config)

    def _autofill_search_query_from_csv(self):
        """Auto-fill eBay search query from first CSV item's keyword and optionally add secondary keyword"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._autofill_search_query_from_csv()

    def _auto_save_config(self, *args):
        """Auto-save the current config when fields change (with 50ms debounce)"""
        # Only auto-save if we have a loaded config
        if not hasattr(self, 'last_saved_path') or not self.last_saved_path:
            return

        # Don't save during initial load
        if not getattr(self, '_settings_loaded', False):
            return

        # Don't save while loading a config
        if getattr(self, '_loading_config', False):
            return

        # Cancel any pending auto-save
        if hasattr(self, '_auto_save_timer') and self._auto_save_timer:
            self.after_cancel(self._auto_save_timer)

        # Schedule auto-save after 50ms of inactivity (debounce)
        self._auto_save_timer = self.after(50, self._do_auto_save)

    def _do_auto_save(self):
        """Actually perform the auto-save - saves without renaming filename"""
        # Don't auto-save if window is being destroyed
        if not self.winfo_exists():
            return

        try:
            config = self._collect_config()
            if config:
                # Save the current selection before updating tree
                current_selection = self.config_tree.selection()

                # Save without renaming - just update the file in place
                self._save_config_to_path(config, self.last_saved_path, update_tree=True)

                # Restore the selection after tree update
                if current_selection and self.winfo_exists():
                    # Find the item with the same path
                    for item in self.config_tree.get_children():
                        if self.config_paths.get(item) == self.last_saved_path:
                            self.config_tree.selection_set(item)
                            self.config_tree.see(item)
                            break

                # Silently saved (no console spam)
        except Exception as e:
            # Only print error if window still exists (not during shutdown)
            if self.winfo_exists():
                print(f"[AUTO-SAVE] Error: {e}")

    def _commit_keyword_changes(self, event=None):
        """Trim trailing spaces from keyword and rename file if needed (called on blur)"""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._commit_keyword_changes(event)

    def _on_config_selected(self, event=None):
        """Load config when selected (single click)"""
        selection = self.config_tree.selection()
        if not selection:
            return
        # Only auto-load when exactly one item is selected (allows multiselect for bulk operations)
        if len(selection) > 1:
            return
        item = selection[0]
        path = self.config_paths.get(item)
        if not path:
            return
        try:
            # Temporarily disable auto-save during config loading
            self._loading_config = True

            with path.open('r', encoding='utf-8') as f:
                config = json.load(f)
            self._populate_from_config(config)
            self.last_saved_path = path
            self.status_var.set(f"Loaded config: {path.name}")

            # Re-enable auto-save after loading is complete
            self._loading_config = False
        except Exception as exc:
            self._loading_config = False
            messagebox.showerror('Error', f'Failed to load config: {exc}')

    def _new_config(self):
        """Create a new config from current form values"""
        import time

        # Ensure "All Stores" is selected if nothing is selected
        if not self.shop_listbox.curselection():
            self.shop_listbox.selection_clear(0, tk.END)
            self.shop_listbox.selection_set(0)

        # Always collect current form values
        config = self._collect_config()

        # If collection failed, use current GUI values as defaults
        if not config:
            config = {
                'keyword': self.keyword_var.get().strip(),
                'hide_sold_out': self.hide_sold_var.get(),
                'language': self.language_var.get(),
                'fast': self.fast_var.get(),
                'resume': self.resume_var.get(),
                'debug': self.debug_var.get(),
            }
            # Add shop if selected
            shop_value = self._resolve_shop()
            if shop_value:
                config['shop'] = shop_value

        # Generate filename based on current values
        timestamp = int(time.time())
        configs_dir = Path('configs')
        configs_dir.mkdir(parents=True, exist_ok=True)

        # Use auto-generated filename based on settings, or timestamp if no keyword
        has_keyword = bool(config.get('keyword', '').strip())
        if has_keyword:
            suggested_filename = utils.suggest_config_filename(config)
            path = configs_dir / suggested_filename
            # If filename already exists, add timestamp
            if path.exists():
                keyword_part = config.get('keyword', 'new').replace(' ', '_') or 'new'
                filename = f"{keyword_part}_{timestamp}.json"
                path = configs_dir / filename
        else:
            # No keyword - use timestamp-based filename
            filename = f'new_config_{timestamp}.json'
            path = configs_dir / filename

        # Save the config
        self._save_config_to_path(config, path, update_tree=False)

        # Add to tree at the end with correct values
        keyword = config.get('keyword', '')
        category = config.get('category_name', config.get('category', ''))
        shop = config.get('shop_name', config.get('shop', ''))
        hide = 'Yes' if config.get('hide_sold_out') else 'No'
        results_per_page = config.get('results_per_page', 48)
        max_pages = config.get('max_pages', 2)
        recent_hours = config.get('recent_hours')
        timeframe = self._label_for_recent_hours(recent_hours) if recent_hours else ''
        language = config.get('language', 'en')
        store = config.get('store', 'Mandarake').title()

        values = (store, path.name, keyword, category, shop, hide, results_per_page, max_pages, timeframe, language)
        item = self.config_tree.insert('', tk.END, values=values)
        self.config_paths[item] = path

        # Select the new item
        self.config_tree.selection_set(item)
        self.config_tree.see(item)

        # Set this as the current config for auto-save
        self.last_saved_path = path

        # Set status
        self.status_var.set(f"New config created: {path.name}")

        # Focus keyword entry for immediate typing
        self.keyword_entry.focus()

    def _delete_selected_config(self):
        """Delete the selected config file(s)."""
        if not self.tree_manager:
            return

        deleted = self.tree_manager.delete_selected_configs()
        if deleted:
            self.status_var.set(f"Deleted {deleted} config(s)")
            if self.last_saved_path and not self.last_saved_path.exists():
                self.last_saved_path = None

    def _move_config(self, direction):
        """Move selected config up (-1) or down (1) via tree manager."""
        if not self.tree_manager:
            return

        target = self.tree_manager.get_selected_config_path()
        if not target:
            return

        if direction < 0:
            moved = self.tree_manager.move_config_up()
        else:
            moved = self.tree_manager.move_config_down()

        if moved:
            self.status_var.set(f"Moved: {target.name}")

    def _load_from_url(self):
        """Parse URL from either Mandarake or Suruga-ya and populate config fields"""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._load_from_url()

    def _populate_from_config(self, config: dict):
        # Set loading flag to prevent trace callbacks from regenerating URL
        self._loading_config = True

        try:
            # Set store first and trigger UI changes
            store = config.get('store', 'mandarake')
            if store == 'suruga-ya':
                self.current_store.set("Suruga-ya")
                self._on_store_changed()
            else:
                self.current_store.set("Mandarake")
                self._on_store_changed()

            # Store provided URL if present
            if 'search_url' in config:
                self._provided_url = config['search_url']
                self.url_var.set(config['search_url'])
            else:
                self._provided_url = None

            self.keyword_var.set(config.get('keyword', ''))

            category = config.get('category')
            if isinstance(category, list):
                categories = category
            elif category:
                categories = [category]
            else:
                categories = []
            self._select_categories(categories)

            self.max_pages_var.set(str(config.get('max_pages', 2)))
            self.recent_hours_var.set(self._label_for_recent_hours(config.get('recent_hours')))

        # Set shop selection in listbox
            shop_value = config.get('shop', '')
            matched = False

        # Try to find matching shop in listbox
            for idx, code in enumerate(self.shop_code_map):
            # Match by code (primary)
                if str(shop_value) == str(code) or shop_value == 'all':
                    self.shop_listbox.selection_clear(0, tk.END)
                    self.shop_listbox.selection_set(idx)
                    self.shop_listbox.see(idx)
                    matched = True
                    break

        # If not matched, try matching by name from shop_name field
            if not matched and config.get('shop_name'):
                shop_name = config.get('shop_name')
                for idx, code in enumerate(self.shop_code_map):
                    if code == "all" or code == "custom":
                        continue
                # Find the name for this code
                    for store_code, store_name in STORE_OPTIONS:
                        if store_code == code and (shop_name == store_name or shop_name in store_name):
                            self.shop_listbox.selection_clear(0, tk.END)
                            self.shop_listbox.selection_set(idx)
                            self.shop_listbox.see(idx)
                            matched = True
                            break
                    if matched:
                        break

        # If still not matched, default to "All Stores"
            if not matched:
                self.shop_listbox.selection_clear(0, tk.END)
                self.shop_listbox.selection_set(0)

            self.hide_sold_var.set(config.get('hide_sold_out', False))
            if hasattr(self, 'csv_in_stock_only'):
                self.csv_in_stock_only.set(config.get('csv_show_in_stock_only', False))
            if hasattr(self, 'csv_add_secondary_keyword'):
                self.csv_add_secondary_keyword.set(config.get('csv_add_secondary_keyword', False))
            self.language_var.set(config.get('language', 'en'))
            self.fast_var.set(config.get('fast', False))
            self.resume_var.set(config.get('resume', True))
            self.debug_var.set(config.get('debug', False))

        # Load adult filter
            if hasattr(self, 'adult_filter_var'):
                adult_only = config.get('adult_only', False)
                self.adult_filter_var.set("Adult Only" if adult_only else "All")

        # Load Suruga-ya specific fields
            if hasattr(self, 'exclude_word_var'):
                self.exclude_word_var.set(config.get('exclude_word', ''))
            if hasattr(self, 'condition_var'):
                condition = config.get('condition', 'all')
                if condition == '1':
                    self.condition_var.set("New Only")
                elif condition == '2':
                    self.condition_var.set("Used Only")
                else:
                    self.condition_var.set("All")

        # Note: eBay API credentials removed from GUI

            self.csv_path_var.set(config.get('csv', ''))
            self.download_dir_var.set(config.get('download_images', ''))
            self.thumbnails_var.set(str(config.get('thumbnails', '')))

            # Set results_per_page: 50 for Suruga-ya (fixed), 240 default for Mandarake
            if config.get('store') == 'suruga-ya':
                self.results_per_page_var.set('50')
            else:
                self.results_per_page_var.set(str(config.get('results_per_page', '240')))

            self.schedule_var.set(config.get('schedule', ''))
        finally:
            # Always reset loading flag
            self._loading_config = False
            # Update preview after loading flag is cleared so provided URLs take effect
            self._update_preview()

    # Browserless eBay Search methods
    def select_browserless_image(self):
        """Select image for browserless eBay search"""
        file_path = filedialog.askopenfilename(
            title="Select reference image for comparison",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.gif"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            self.browserless_image_path = Path(file_path)
            self.browserless_image_label.config(text=f"Selected: {self.browserless_image_path.name}", foreground="black")
            print(f"[BROWSERLESS SEARCH] Loaded reference image: {self.browserless_image_path}")

    def run_scrapy_text_search(self):
        """Run Scrapy eBay search (text only, no image comparison)"""
        query = self.browserless_query_var.get().strip()
        max_results = int(self.browserless_max_results.get())
        search_method = self.ebay_search_method.get()  # "scrapy" or "api"
        
        if self.ebay_search_manager:
            self.ebay_search_manager.run_text_search(query, max_results, search_method)

    def run_scrapy_search_with_compare(self):
        """Run Scrapy eBay search WITH image comparison"""
        query = self.browserless_query_var.get().strip()
        max_results = int(self.browserless_max_results.get())
        max_comparisons_str = self.browserless_max_comparisons.get()
        max_comparisons = None if max_comparisons_str == "MAX" else int(max_comparisons_str)
        reference_image_path = getattr(self, 'browserless_image_path', None)
        
        if self.ebay_search_manager:
            self.ebay_search_manager.run_search_with_compare(query, max_results, max_comparisons, reference_image_path)

    def _run_scrapy_text_search_worker(self):
        """Worker method for eBay text-only search (runs in background thread)"""
        query = self.browserless_query_var.get().strip()
        max_results = int(self.browserless_max_results.get())
        search_method = self.ebay_search_method.get()  # "scrapy" or "api"

        def update_callback(message):
            self.after(0, lambda: self.browserless_status.set(message))

        def display_callback(results):
            self.after(0, lambda: self._display_browserless_results(results))
            self.after(0, self.browserless_progress.stop)

        def show_message_callback(title, message):
            # Log to status instead of popup
            self.after(0, lambda: self.browserless_status.set(message))
            self.after(0, self.browserless_progress.stop)

        workers.run_scrapy_text_search_worker(
            query, max_results,
            update_callback,
            display_callback,
            show_message_callback,
            search_method=search_method
        )

    def _run_scrapy_search_with_compare_worker(self):
        """Worker method for Scrapy search WITH image comparison (runs in background thread)"""
        query = self.browserless_query_var.get().strip()
        max_results = int(self.browserless_max_results.get())
        max_comparisons_str = self.browserless_max_comparisons.get()
        max_comparisons = None if max_comparisons_str == "MAX" else int(max_comparisons_str)

        def update_callback(message):
            self.after(0, lambda: self.browserless_status.set(message))

        def display_callback(results):
            self.after(0, lambda: self._display_browserless_results(results))
            self.after(0, self.browserless_progress.stop)

        def show_message_callback(title, message):
            # Log to status instead of popup
            self.after(0, lambda: self.browserless_status.set(message))
            self.after(0, self.browserless_progress.stop)

        def create_debug_folder_callback(query):
            return self._create_debug_folder(query)

        workers.run_scrapy_search_with_compare_worker(
            query, max_results, max_comparisons,
            self.browserless_image_path,
            update_callback,
            display_callback,
            show_message_callback,
            create_debug_folder_callback
        )

    def _run_cached_compare_worker(self):
        """Worker method to compare reference image with CACHED eBay results (State 1)"""
        query = self.browserless_query_var.get().strip()
        max_comparisons_str = self.browserless_max_comparisons.get()
        max_comparisons = None if max_comparisons_str == "MAX" else int(max_comparisons_str)

        def update_callback(message):
            self.after(0, lambda: self.browserless_status.set(message))

        def display_callback(results):
            self.after(0, lambda: self._display_browserless_results(results))
            self.after(0, self.browserless_progress.stop)

        def show_message_callback(title, message):
            self.after(0, lambda: messagebox.showerror(title, message))
            self.after(0, self.browserless_progress.stop)

        def create_debug_folder_callback(query):
            return self._create_debug_folder(query)

        workers.run_cached_compare_worker(
            query, max_comparisons,
            self.browserless_image_path,
            self.browserless_results_data,
            update_callback,
            display_callback,
            show_message_callback,
            create_debug_folder_callback
        )

    def clear_browserless_results(self):
        """Clear browserless search results using eBay search manager."""
        if self.ebay_search_manager:
            self.ebay_search_manager.clear_results()

    # CSV Batch Comparison methods
    def _load_csv_worker(self, csv_path: Path, autofill_from_config=None):
        """
        Modular worker to load CSV data into comparison tree.

        Args:
            csv_path: Path to CSV file
            autofill_from_config: Optional config dict to autofill eBay query from config keyword
                                 and set in-stock filter
        """
        try:
            self.csv_compare_path = csv_path
            self.csv_compare_label.config(text=f"Loaded: {csv_path.name}", foreground="black")
            print(f"[CSV WORKER] Loading CSV: {csv_path}")

            # Load CSV data
            self.csv_compare_data = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.csv_compare_data.append(row)

            # Set in-stock filter from config if provided
            if autofill_from_config:
                show_in_stock_only = autofill_from_config.get('csv_show_in_stock_only', False)
                self.csv_in_stock_only.set(show_in_stock_only)
                print(f"[CSV WORKER] Set in-stock filter to: {show_in_stock_only}")

            # Display with filter applied
            self.filter_csv_items()

            # Auto-fill eBay search query
            if autofill_from_config:
                self._autofill_search_query_from_config(autofill_from_config)
            else:
                self._autofill_search_query_from_csv()

            print(f"[CSV WORKER] Loaded {len(self.csv_compare_data)} items")
            return True

        except Exception as e:
            print(f"[CSV WORKER ERROR] {e}")
            return False

    def load_csv_for_comparison(self):
        """Load CSV file for batch comparison"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.load_csv_for_comparison()
        else:
            messagebox.showerror("Error", "CSV comparison manager not initialized")

    def filter_csv_items(self):
        """Filter and display CSV items based on in-stock filter - fast load, thumbnails loaded on demand"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.filter_csv_items()

    def _load_csv_thumbnails_worker(self, filtered_items):
        """Background worker to load CSV thumbnails without blocking UI"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._load_csv_thumbnails_worker(filtered_items)

    def _on_csv_filter_changed(self):
        """Handle CSV filter changes - filter items (settings saved on close)"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.on_csv_filter_changed()

    def _on_recent_hours_changed(self, *args):
        """Handle latest additions timeframe change - refresh CSV view if loaded"""
        # Don't refresh while loading a config
        if getattr(self, '_loading_config', False):
            return
        # Only refresh if CSV is loaded
        if hasattr(self, 'csv_compare_data') and self.csv_compare_data:
            self.filter_csv_items()

    def _on_csv_column_resize(self, event):
        """Handle column resize event to reload thumbnails with new size"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.on_csv_column_resize(event)

    def _on_csv_item_double_click(self, event):
        """Handle double-click on CSV item to open URL in browser"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.on_csv_item_double_click(event)

    def toggle_csv_thumbnails(self):
        """Toggle visibility of thumbnails in CSV treeview"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.toggle_csv_thumbnails()

    def _load_publisher_list(self):
        """Load publisher list from file"""
        publisher_file = Path('publishers.txt')
        publishers = set()

        # Default publishers
        default_publishers = [
            'Takeshobo', 'S-Digital', 'G-WALK', 'Cosplay Fetish Book',
            'First', '1st', '2nd', '3rd', 'Book'
        ]
        publishers.update(default_publishers)

        # Load from file if exists
        if publisher_file.exists():
            try:
                with open(publisher_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        pub = line.strip()
                        if pub:
                            publishers.add(pub)
                print(f"[PUBLISHERS] Loaded {len(publishers)} publishers from file")
            except Exception as e:
                print(f"[PUBLISHERS] Error loading file: {e}")

        return publishers

    def _save_publisher_list(self):
        """Save publisher list to file"""
        try:
            publisher_file = Path('publishers.txt')
            with open(publisher_file, 'w', encoding='utf-8') as f:
                for pub in sorted(self.publisher_list):
                    f.write(f"{pub}\n")
            print(f"[PUBLISHERS] Saved {len(self.publisher_list)} publishers to file")
        except Exception as e:
            print(f"[PUBLISHERS] Error saving file: {e}")

    def _show_keyword_menu(self, event):
        """Show context menu on keyword entry"""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._show_keyword_menu(event)

    def _add_to_publisher_list(self):
        """Add selected text from keyword entry to publisher list"""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._add_to_publisher_list()

    def _set_keyword_field(self, text):
        """Helper function to reliably set the keyword field"""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._set_keyword_field(text)

    def _add_full_title_to_search(self):
        """Replace eBay search query with full title from selected CSV item"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._add_full_title_to_search()

    def _add_secondary_keyword_from_csv(self):
        """Add selected CSV item's secondary keyword to the eBay search query field"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._add_secondary_keyword_from_csv()

    def _extract_secondary_keyword(self, title, primary_keyword):
        """Extract secondary keyword from title by removing primary keyword and common terms"""
        import re

        # Make a working copy
        secondary = title

        # Remove primary keyword (case insensitive), handling name in different orders
        # e.g., "Yura Kano" and "Kano Yura"
        secondary = re.sub(re.escape(primary_keyword), '', secondary, flags=re.IGNORECASE).strip()

        # Also remove reversed name order (split and reverse)
        name_parts = primary_keyword.split()
        if len(name_parts) == 2:
            reversed_name = f"{name_parts[1]} {name_parts[0]}"
            secondary = re.sub(re.escape(reversed_name), '', secondary, flags=re.IGNORECASE).strip()
            # Also remove individual parts if they appear alone
            for part in name_parts:
                if len(part) > 2:  # Don't remove very short words
                    secondary = re.sub(r'\b' + re.escape(part) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

        # Use dynamic publisher list instead of hardcoded
        for pub in self.publisher_list:
            secondary = re.sub(r'\b' + re.escape(pub) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

        # Remove generic suffixes
        generic_terms = ['Photograph Collection', 'Photo Essay', 'Photo Collection',
                        'Photobook', 'autographed', 'Photograph', 'Collection']
        for term in generic_terms:
            secondary = re.sub(r'\b' + re.escape(term) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

        # Remove years (e.g., "2022", "2023")
        secondary = re.sub(r'\b(19|20)\d{2}\b', '', secondary).strip()

        # Remove "Desktop" before "Calendar" to get just "Calendar"
        secondary = re.sub(r'\bDesktop\s+Calendar\b', 'Calendar', secondary, flags=re.IGNORECASE).strip()

        # Clean up extra spaces
        secondary = re.sub(r'\s+', ' ', secondary).strip()

        # If nothing left, return empty
        if not secondary or len(secondary) < 2:
            return ""

        return secondary

    def on_csv_item_selected(self, event):
        """Auto-fill search query when CSV item is selected"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.on_csv_item_selected(event)

    def compare_selected_csv_item(self):
        """Compare selected CSV item with eBay"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.compare_selected_csv_item()

    def _run_csv_comparison_async(self):
        """Run CSV comparison without confirmation (for scheduled tasks)"""
        self.compare_all_csv_items(skip_confirmation=True)

    def compare_all_csv_items(self, skip_confirmation=False):
        """Compare all visible CSV items with eBay"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager.compare_all_csv_items(skip_confirmation)

    def compare_new_csv_items(self):
        """Compare only items that haven't been compared yet"""
        if self.csv_comparison_manager:
            # CSV manager's method has slightly different logic than compare_all
            # It tracks which items have been compared before
            # For now, delegate to compare_all as a fallback
            # TODO: Implement proper compare_new_items() in CSV manager if needed
            self.csv_comparison_manager.compare_all_csv_items(skip_confirmation=False)

    def clear_comparison_results(self):
        """Clear all eBay comparison results from the loaded CSV"""
        if not self.csv_compare_data or not self.csv_compare_path:
            messagebox.showwarning("No CSV", "Please load a CSV file first")
            return

        # Count items with comparison results
        compared_count = sum(1 for item in self.csv_compare_data if item.get('ebay_compared'))

        if compared_count == 0:
            # Log to status instead of popup
            self.browserless_status.set("No comparison results to clear")
            print("[CLEAR RESULTS] No results to clear")
            return

        # Confirm clearing
        response = messagebox.askyesno(
            "Clear Comparison Results",
            f"Clear comparison results for {compared_count} items?\n\n"
            f"This will reset ebay_compared, ebay_match_found, ebay_similarity, etc.\n"
            f"You can recompare items after clearing."
        )

        if response:
            try:
                # Clear comparison fields for all items
                for item in self.csv_compare_data:
                    item['ebay_compared'] = ''
                    item['ebay_match_found'] = ''
                    item['ebay_best_match_title'] = ''
                    item['ebay_similarity'] = ''
                    item['ebay_price'] = ''
                    item['ebay_profit_margin'] = ''

                # Save updated CSV
                self._save_updated_csv()

                # Log to status instead of popup
                self.browserless_status.set(f"Cleared comparison results for {compared_count} items")
                print(f"[CLEAR RESULTS] Cleared comparison results for {compared_count} items")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear results: {e}")
                print(f"[CLEAR RESULTS ERROR] {e}")

    def _compare_csv_items_worker(self, items, search_query):
        """Worker to compare CSV items with eBay - OPTIMIZED with caching (runs in background thread)"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._compare_csv_items_worker(items, search_query)

    def _compare_csv_items_individually_worker(self, items, base_search_query):
        """Worker to compare CSV items individually - each item gets its own eBay search"""
        if self.csv_comparison_manager:
            self.csv_comparison_manager._compare_csv_items_individually_worker(items, base_search_query)

    def _fetch_exchange_rate(self):
        """Fetch current USD to JPY exchange rate"""
        return utils.fetch_exchange_rate()

    def _extract_price(self, price_text):
        """Extract numeric price from text"""
        return utils.extract_price(price_text)

    def _compare_images(self, ref_image, compare_image):
        """Compare two images and return similarity score (0-100)."""
        return utils.compare_images(ref_image, compare_image)

    def _create_debug_folder(self, query):
        """Create debug folder for saving comparison images."""
        return utils.create_debug_folder(query)

    def _send_to_alerts_with_thresholds(self, comparison_results, min_similarity, min_profit):
        """Send comparison results to alerts with specified thresholds."""
        # Filter results based on thresholds
        filtered = [
            r for r in comparison_results
            if r.get('similarity', 0) >= min_similarity and r.get('profit_margin', 0) >= min_profit
        ]

        if filtered:
            # Add filtered results to alerts tab
            self.alert_tab.add_filtered_alerts(filtered)
            messagebox.showinfo(
                "Alerts Created",
                f"Created {len(filtered)} new alerts from {len(comparison_results)} results\n\n"
                f"Thresholds used:\n"
                f"• Similarity ≥ {min_similarity}%\n"
                f"• Profit ≥ {min_profit}%"
            )
        else:
            messagebox.showinfo(
                "No Alerts",
                f"No items met the alert thresholds:\n\n"
                f"• Similarity ≥ {min_similarity}%\n"
                f"• Profit ≥ {min_profit}%"
            )

    def apply_results_filter(self):
        """Display comparison results sorted by similarity and profit"""
        if not self.all_comparison_results:
            return

        # Check if results have similarity/profit data (from comparison)
        has_comparison_data = any('similarity' in r and 'profit_margin' in r for r in self.all_comparison_results)

        if has_comparison_data:
            # Sort results by similarity (descending), then by profit margin (descending)
            sorted_results = sorted(
                self.all_comparison_results,
                key=lambda x: (x.get('similarity', 0), x.get('profit_margin', 0)),
                reverse=True
            )
            self._display_csv_comparison_results(sorted_results)
        else:
            # No comparison data yet, show all results
            self._display_csv_comparison_results(self.all_comparison_results)

    def _display_csv_comparison_results(self, results):
        """Display CSV comparison results in the browserless tree"""
        # Convert format to match existing display
        display_results = []
        for r in results:
            display_results.append({
                'title': r['ebay_title'],
                'price': r['ebay_price'],
                'shipping': r['shipping'],
                'mandarake_price': r.get('mandarake_price', ''),
                'profit_margin': r['profit_display'],
                'sold_date': r.get('sold_date', ''),  # Keep actual sold date
                'similarity': r['similarity_display'],
                'url': r['ebay_link'],
                'mandarake_url': r.get('mandarake_link', ''),
                'image_url': r['thumbnail'],
                'mandarake_image_url': r.get('mandarake_thumbnail', '')
            })

        self._display_browserless_results(display_results)

    def open_browserless_url(self, event):
        """Open eBay or Mandarake URL based on which column is double-clicked"""
        selection = self.browserless_tree.selection()
        if not selection:
            return

        item_id = selection[0]

        # Identify which column was clicked
        column = self.browserless_tree.identify_column(event.x)
        # Column format is '#0', '#1', '#2', etc. where #0 is thumbnail, #1 is first data column

        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.browserless_results_data):
                result = self.browserless_results_data[index]

                # Determine which URL to open based on column
                # Columns: title(#1), price(#2), shipping(#3), mandarake_price(#4), profit_margin(#5),
                #          sold_date(#6), similarity(#7), url(#8), mandarake_url(#9)
                if column == '#9':  # Mandarake URL column
                    url = result.get('mandarake_url', '')
                    url_type = "Mandarake"
                else:  # Default to eBay URL for all other columns
                    url = result.get('url', '')
                    url_type = "eBay"

                if url and not any(x in url for x in ["No URL available", "Placeholder URL", "Invalid URL", "URL Error"]):
                    print(f"[BROWSERLESS SEARCH] Opening {url_type} URL: {url}")
                    webbrowser.open(url)
                else:
                    print(f"[BROWSERLESS SEARCH] Cannot open {url_type} URL: {url}")
            else:
                print(f"[URL DEBUG] Index {index} out of range (data length: {len(self.browserless_results_data)})")
        except (ValueError, IndexError) as e:
            print(f"[BROWSERLESS SEARCH] Error opening URL: {e}")
            pass

    def _show_browserless_context_menu(self, event):
        """Show context menu for eBay results treeview"""
        # Select the item under cursor
        item = self.browserless_tree.identify_row(event.y)
        if item:
            self.browserless_tree.selection_set(item)

            # Create context menu
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Send to Review/Alerts", command=self._send_browserless_to_review)
            menu.add_separator()
            menu.add_command(label="Open eBay URL", command=lambda: self.open_browserless_url(event))
            if self.browserless_results_data and int(item) - 1 < len(self.browserless_results_data):
                result = self.browserless_results_data[int(item) - 1]
                if result.get('mandarake_url'):
                    menu.add_command(label="Open Mandarake URL", command=lambda: webbrowser.open(result['mandarake_url']))

            # Show menu at cursor position
            menu.post(event.x_root, event.y_root)

    def _send_browserless_to_review(self):
        """Send selected eBay result to Review/Alerts tab"""
        selection = self.browserless_tree.selection()
        if not selection:
            self.browserless_status.set("No item selected")
            return

        item_id = selection[0]
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.browserless_results_data):
                result = self.browserless_results_data[index]

                # Check if this is a comparison result (has similarity/profit data)
                if 'similarity' in result or 'profit_margin' in result:
                    # Find the corresponding item in all_comparison_results
                    matching_result = None
                    for comp_result in getattr(self, 'all_comparison_results', []):
                        if comp_result.get('ebay_link') == result.get('url'):
                            matching_result = comp_result
                            break

                    if matching_result:
                        # Send to alerts using existing method
                        self.alert_tab.add_filtered_alerts([matching_result])
                        # Explicitly refresh the alert tab to ensure it displays the new item
                        self.alert_tab._load_alerts()
                        self.browserless_status.set(f"Sent '{result['title'][:50]}...' to Review/Alerts")
                        print(f"[SEND TO REVIEW] Added item to alerts: {result['title']}")
                    else:
                        self.browserless_status.set("Could not find comparison data for this item")
                else:
                    # This is a raw eBay search result without comparison data
                    self.browserless_status.set("Item has no comparison data - use 'Compare Selected' first")
                    print("[SEND TO REVIEW] Item has no comparison data")
        except (ValueError, IndexError) as e:
            print(f"[SEND TO REVIEW] Error: {e}")
            self.browserless_status.set(f"Error sending to review: {e}")

    def _display_browserless_results(self, results):
        """Display browserless search results in the tree view with thumbnails"""
        # Clear existing results and images
        for item in self.browserless_tree.get_children():
            self.browserless_tree.delete(item)
        self.browserless_images.clear()

        # Store results for URL opening
        self.browserless_results_data = results

        # Add new results with thumbnails
        for i, result in enumerate(results, 1):
            values = (
                result['title'],  # Show full title, no truncation
                result['price'],
                result['shipping'],
                result.get('mandarake_price', ''),
                result.get('profit_margin', ''),
                result.get('sold_date', ''),
                result.get('similarity', ''),
                result['url'],  # eBay URL
                result.get('mandarake_url', '')  # Mandarake URL
            )

            # Try to load thumbnails (eBay and Mandarake side-by-side if both exist)
            ebay_image_url = result.get('image_url', '')
            mandarake_image_url = result.get('mandarake_image_url', '')
            photo = None

            try:
                import requests
                from io import BytesIO

                ebay_img = None
                mandarake_img = None

                # Load eBay image
                if ebay_image_url:
                    try:
                        response = requests.get(ebay_image_url, timeout=5)
                        response.raise_for_status()
                        ebay_img = Image.open(BytesIO(response.content))
                        ebay_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                    except Exception as e:
                        print(f"[THUMB] Failed to load eBay thumbnail {i}: {e}")

                # Load Mandarake image
                if mandarake_image_url:
                    try:
                        response = requests.get(mandarake_image_url, timeout=5)
                        response.raise_for_status()
                        mandarake_img = Image.open(BytesIO(response.content))
                        mandarake_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                    except Exception as e:
                        print(f"[THUMB] Failed to load Mandarake thumbnail {i}: {e}")

                # Create composite image if we have both, or use single image
                if ebay_img and mandarake_img:
                    # Side-by-side composite
                    total_width = ebay_img.width + mandarake_img.width + 2  # +2 for separator
                    max_height = max(ebay_img.height, mandarake_img.height)
                    composite = Image.new('RGB', (total_width, max_height), 'white')
                    composite.paste(ebay_img, (0, 0))
                    composite.paste(mandarake_img, (ebay_img.width + 2, 0))
                    photo = ImageTk.PhotoImage(composite)
                elif ebay_img:
                    photo = ImageTk.PhotoImage(ebay_img)
                elif mandarake_img:
                    photo = ImageTk.PhotoImage(mandarake_img)

            except Exception as e:
                print(f"[SCRAPY SEARCH] Failed to load thumbnails {i}: {e}")
                photo = None

            # Insert with or without image
            if photo:
                self.browserless_tree.insert('', 'end', iid=str(i), text='', values=values, image=photo)
                self.browserless_images[str(i)] = photo  # Keep reference to prevent garbage collection
            else:
                self.browserless_tree.insert('', 'end', iid=str(i), text=str(i), values=values)

        print(f"[SCRAPY SEARCH] Displayed {len(results)} results in tree view ({len(self.browserless_images)} with thumbnails)")

    def _clean_ebay_url(self, url: str) -> str:
        """Clean and validate eBay URL"""
        return utils.clean_ebay_url(url)

    def _update_preview(self, *args):
        # Also trigger auto-save when preview updates
        self._auto_save_config()

        # If loading config with a provided URL, don't regenerate - keep the provided URL
        if getattr(self, '_loading_config', False) and hasattr(self, '_provided_url') and self._provided_url:
            return  # Keep the provided URL that was already set

        # Clear provided URL when user makes changes to UI fields
        # This allows regenerating the URL from current field values
        if hasattr(self, '_provided_url') and self._provided_url:
            self._provided_url = None  # Clear so URL gets regenerated

        store = self.current_store.get()
        keyword = self.keyword_var.get().strip()

        params: list[tuple[str, str]] = []
        notes: list[str] = []

        if store == "Suruga-ya":
            # Build Suruga-ya URL
            if keyword:
                params.append(("search_word", quote(keyword)))
            params.append(("searchbox", "1"))

            # Main category (category1)
            main_category_text = self.main_category_var.get()
            if main_category_text:
                from gui import utils
                main_code = utils.extract_code(main_category_text)
                if main_code:
                    params.append(("category1", main_code))

            # Detailed category (category2)
            categories = self._get_selected_categories()
            if categories:
                params.append(("category2", categories[0]))

            # Exclude words
            if hasattr(self, 'exclude_word_var'):
                exclude = self.exclude_word_var.get().strip()
                if exclude:
                    params.append(("exclude_word", quote(exclude)))
                    notes.append(f"exclude: {exclude}")

            # Condition filter
            if hasattr(self, 'condition_var'):
                condition = self.condition_var.get()
                if condition == "New Only":
                    params.append(("sale_classified", "1"))
                    notes.append("new only")
                elif condition == "Used Only":
                    params.append(("sale_classified", "2"))
                    notes.append("used only")

            # Adult filter for Suruga-ya
            if hasattr(self, 'adult_filter_var') and self.adult_filter_var.get() == "Adult Only":
                params.append(("adult_s", "1"))
                notes.append("adult only")

            # Shop filter
            shop_value = self._resolve_shop()
            if shop_value and shop_value != 'all':
                params.append(("tenpo_code", shop_value))

            # Build URL
            query = '&'.join(f"{key}={value}" for key, value in params)
            url = "https://www.suruga-ya.jp/search"
            if query:
                url = f"{url}?{query}"

        else:
            # Build Mandarake URL
            if keyword:
                params.append(("keyword", quote(keyword)))

            # Add category even without keyword
            categories = self._get_selected_categories()
            if categories:
                params.append(("categoryCode", categories[0]))
                if len(categories) > 1:
                    notes.append(f"+{len(categories) - 1} more categories")

            shop_value = self._resolve_shop()
            if shop_value:
                params.append(("shop", quote(shop_value)))

            if self.hide_sold_var.get():
                params.append(("soldOut", '1'))

            if self.language_var.get() == 'en':
                params.append(("lang", "en"))

            recent_hours = self._get_recent_hours_value()
            if recent_hours:
                params.append(("upToMinutes", str(recent_hours * 60)))
                notes.append(f"last {recent_hours}h")

            # Adult content filter for Mandarake
            if hasattr(self, 'adult_filter_var') and self.adult_filter_var.get() == "Adult Only":
                params.append(("r18", "1"))
                notes.append("adult only")

            # Build URL
            query = '&'.join(f"{key}={value}" for key, value in params)
            url = "https://order.mandarake.co.jp/order/listPage/list"
            if query:
                url = f"{url}?{query}"

        note_str = f" ({'; '.join(notes)})" if notes else ''
        self.url_var.set(f"{url}{note_str}")


def main():
    ScraperGUI().mainloop()


if __name__ == '__main__':
    main()
