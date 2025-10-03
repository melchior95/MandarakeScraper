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
from gui.schedule_executor import ScheduleExecutor
from gui.schedule_frame import ScheduleFrame


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

        basic_frame = ttk.Frame(notebook)
        browserless_frame = ttk.Frame(notebook)
        advanced_frame = ttk.Frame(notebook)

        notebook.add(basic_frame, text="Mandarake")
        notebook.add(browserless_frame, text="eBay Search & CSV")

        # Alert/Review tab
        self.alert_tab = AlertTab(notebook)
        notebook.add(self.alert_tab, text="Review/Alerts")

        notebook.add(advanced_frame, text="Advanced")

        # Initialize schedule executor (background thread)
        self.schedule_executor = ScheduleExecutor(self)
        self.schedule_executor.start()

        # Search tab ----------------------------------------------------
        # Create vertical PanedWindow to split top section from bottom sections
        self.vertical_paned = tk.PanedWindow(basic_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5)
        self.vertical_paned.pack(fill=tk.BOTH, expand=True)

        # Top pane: Form fields and listboxes (resizable)
        top_pane = ttk.Frame(self.vertical_paned)
        self.vertical_paned.add(top_pane, minsize=200)

        # Bottom container: Options + Configs (not resizable internally)
        bottom_container = ttk.Frame(self.vertical_paned)
        self.vertical_paned.add(bottom_container, minsize=200)

        # Mandarake URL input
        self.mandarake_url_var = tk.StringVar()
        ttk.Label(top_pane, text="Mandarake URL:").grid(row=0, column=0, sticky=tk.W, **pad)
        url_entry = ttk.Entry(top_pane, textvariable=self.mandarake_url_var, width=60)
        url_entry.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E), **pad)
        ttk.Button(top_pane, text="Load URL", command=self._load_from_url).grid(row=0, column=4, sticky=tk.W, **pad)

        self.keyword_var = tk.StringVar()
        ttk.Label(top_pane, text="Keyword:").grid(row=1, column=0, sticky=tk.W, **pad)
        self.keyword_entry = ttk.Entry(top_pane, textvariable=self.keyword_var, width=42)
        self.keyword_entry.grid(row=1, column=1, columnspan=3, sticky=tk.W, **pad)
        self.keyword_var.trace_add("write", self._update_preview)

        # Commit/trim keyword when focus leaves the field
        self.keyword_entry.bind("<FocusOut>", self._commit_keyword_changes)

        # Autosave with new filename when Enter is pressed
        self.keyword_entry.bind("<Return>", self._save_config_on_enter)

        # Add right-click context menu to keyword entry
        self.keyword_menu = tk.Menu(self.keyword_entry, tearoff=0)
        self.keyword_menu.add_command(label="Add Selected Text to Publisher List", command=self._add_to_publisher_list)
        self.keyword_entry.bind("<Button-3>", self._show_keyword_menu)

        self.main_category_var = tk.StringVar()
        ttk.Label(top_pane, text="Main category:").grid(row=2, column=0, sticky=tk.W, **pad)
        self.main_category_combo = ttk.Combobox(
            top_pane,
            textvariable=self.main_category_var,
            state="readonly",
            width=42,
            values=[f"{name} ({code})" for code, name in MAIN_CATEGORY_OPTIONS],
        )
        self.main_category_combo.grid(row=2, column=1, columnspan=3, sticky=tk.W, **pad)
        self.main_category_combo.bind("<<ComboboxSelected>>", self._on_main_category_selected)

        # Create labels row for both listboxes
        labels_frame = ttk.Frame(top_pane)
        labels_frame.grid(row=3, column=0, columnspan=7, sticky=(tk.W, tk.E), **pad)
        ttk.Label(labels_frame, text="Detailed categories:").pack(side=tk.LEFT)
        ttk.Label(labels_frame, text="Shop:", anchor='e').pack(side=tk.RIGHT, padx=(0, 50))

        # Create PanedWindow for resizable listboxes
        self.listbox_paned = tk.PanedWindow(top_pane, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self.listbox_paned.grid(row=4, column=0, columnspan=7, sticky=(tk.W, tk.E, tk.N, tk.S), **pad)

        # Left pane: Detailed categories
        detail_frame = ttk.Frame(self.listbox_paned)
        self.detail_listbox = tk.Listbox(
            detail_frame,
            selectmode=tk.SINGLE,
            height=10,
            exportselection=False,
        )
        self.detail_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_listbox.yview)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_listbox.configure(yscrollcommand=detail_scroll.set)
        self.detail_listbox.bind("<<ListboxSelect>>", lambda _: self._update_preview())
        self._populate_detail_categories()
        self.listbox_paned.add(detail_frame, minsize=200)

        # Right pane: Shop listbox
        shop_frame = ttk.Frame(self.listbox_paned)
        self.shop_listbox = tk.Listbox(
            shop_frame,
            selectmode=tk.SINGLE,
            height=10,
            exportselection=False,
        )
        self.shop_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        shop_scroll = ttk.Scrollbar(shop_frame, orient=tk.VERTICAL, command=self.shop_listbox.yview)
        shop_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.shop_listbox.configure(yscrollcommand=shop_scroll.set)
        self.shop_listbox.bind("<<ListboxSelect>>", self._on_shop_selected)
        self._populate_shop_list()
        self.listbox_paned.add(shop_frame, minsize=150)

        # Track user's sash position
        self._user_sash_ratio = None  # Track the last valid user position

        # Bind to track user changes
        self.listbox_paned.bind('<ButtonRelease-1>', self._on_listbox_sash_moved)

        # Restore position after the window is fully mapped and sized
        self.bind('<Map>', self._on_window_mapped, add='+')

        # Configure top pane grid weights
        top_pane.rowconfigure(4, weight=1)  # Listbox row expands
        top_pane.columnconfigure(6, weight=1)  # Last column expands to fill width

        # Middle pane: Options (fixed, no sash below it)
        middle_pane = ttk.Frame(bottom_container)
        middle_pane.pack(fill=tk.X, padx=5, pady=5)

        # --- URL Options (affect Mandarake search) - All in one row ---
        self.hide_sold_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(middle_pane, text="Hide sold", variable=self.hide_sold_var,
                        command=self._update_preview).grid(row=0, column=0, sticky=tk.W, **pad)

        self.results_per_page_var = tk.StringVar(value="48")
        ttk.Label(middle_pane, text="Results/page:").grid(row=0, column=1, sticky=tk.W, padx=(15, 5), pady=5)
        results_per_page_combo = ttk.Combobox(
            middle_pane,
            textvariable=self.results_per_page_var,
            state="readonly",
            width=6,
            values=["48", "120", "240"]
        )
        results_per_page_combo.grid(row=0, column=2, sticky=tk.W, **pad)
        self.results_per_page_var.trace_add("write", self._update_preview)

        self.max_pages_var = tk.StringVar()
        ttk.Label(middle_pane, text="Max pages:").grid(row=0, column=3, sticky=tk.W, padx=(15, 5), pady=5)
        ttk.Entry(middle_pane, textvariable=self.max_pages_var, width=8).grid(row=0, column=4, sticky=tk.W, **pad)
        self.max_pages_var.trace_add("write", self._auto_save_config)

        self.recent_hours_var = tk.StringVar(value=RECENT_OPTIONS[0][0])
        ttk.Label(middle_pane, text="Latest:").grid(row=0, column=5, sticky=tk.W, padx=(15, 5), pady=5)
        self.recent_combo = ttk.Combobox(
            middle_pane,
            textvariable=self.recent_hours_var,
            state="readonly",
            width=15,
            values=[label for label, _ in RECENT_OPTIONS],
        )
        self.recent_combo.grid(row=0, column=6, sticky=tk.W, **pad)
        self.recent_hours_var.trace_add("write", self._update_preview)
        self.recent_hours_var.trace_add("write", self._on_recent_hours_changed)

        # Initialize CSV variables if not already done (for backward compatibility with CSV comparison tab)
        if not hasattr(self, 'csv_newly_listed_only'):
            self.csv_newly_listed_only = tk.BooleanVar(value=False)
        if not hasattr(self, 'csv_in_stock_only'):
            self.csv_in_stock_only = tk.BooleanVar(value=True)
        if not hasattr(self, 'csv_add_secondary_keyword'):
            self.csv_add_secondary_keyword = tk.BooleanVar(value=False)

        # --- Language (rarely used) - Same row ---
        self.language_var = tk.StringVar(value="en")
        ttk.Label(middle_pane, text="Language:").grid(row=1, column=0, sticky=tk.W, **pad)
        lang_combo = ttk.Combobox(middle_pane, textvariable=self.language_var, values=["en", "ja"], width=6, state="readonly")
        lang_combo.grid(row=1, column=1, sticky=tk.W, **pad)
        self.language_var.trace_add("write", self._update_preview)


        # Bottom pane: Configs/Schedules and buttons (fills remaining space)
        bottom_pane = ttk.Frame(bottom_container)
        bottom_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Configs/Schedules tabbed interface
        config_schedule_notebook = ttk.Notebook(bottom_pane)
        config_schedule_notebook.grid(row=0, column=0, columnspan=7, sticky=tk.NSEW, **pad)

        # Configs tab
        tree_frame = ttk.Frame(config_schedule_notebook)
        config_schedule_notebook.add(tree_frame, text="Configs")
        columns = ('file', 'keyword', 'category', 'shop', 'hide_sold', 'results_per_page', 'max_pages', 'latest_additions', 'language')
        self.config_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=6)
        headings = {
            'file': 'File',
            'keyword': 'Keyword',
            'category': 'Category',
            'shop': 'Shop',
            'hide_sold': 'Hide Sold',
            'results_per_page': 'Results/Page',
            'max_pages': 'Max Pages',
            'latest_additions': 'Latest',
            'language': 'Lang',
        }
        widths = {
            'file': 200,
            'keyword': 120,
            'category': 120,
            'shop': 120,
            'hide_sold': 80,
            'results_per_page': 80,
            'max_pages': 70,
            'latest_additions': 70,
            'language': 50,
        }
        for col, heading in headings.items():
            self.config_tree.heading(col, text=heading)
            width = widths.get(col, 100)
            self.config_tree.column(col, width=width, stretch=False)

        # Add vertical scrollbar
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.config_tree.yview)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Add horizontal scrollbar
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.config_tree.xview)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.config_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        # Single click to load config
        self.config_tree.bind('<<TreeviewSelect>>', self._on_config_selected)
        # Prevent space from affecting tree selection when it has focus
        # Space key handled globally via bind_class
        # Allow deselect by clicking empty area
        self.config_tree.bind("<Button-1>", lambda e: self._deselect_if_empty(e, self.config_tree))

        # Add right-click context menu for config tree
        self.config_tree_menu = tk.Menu(self.config_tree, tearoff=0)
        self.config_tree_menu.add_command(label="Load CSV", command=self._load_csv_from_config)
        self.config_tree.bind("<Button-3>", self._show_config_tree_menu)

        # Enable column drag-to-reorder
        self._setup_column_drag(self.config_tree)

        # Schedules tab
        self.schedule_frame = ScheduleFrame(config_schedule_notebook, self.schedule_executor)
        config_schedule_notebook.add(self.schedule_frame, text="Schedules")

        # Bind tab change to show/hide appropriate buttons
        config_schedule_notebook.bind("<<NotebookTabChanged>>", self._on_config_schedule_tab_changed)
        self.config_schedule_notebook = config_schedule_notebook

        # Config management buttons (row 1)
        self.config_buttons_frame = ttk.Frame(bottom_pane)
        self.config_buttons_frame.grid(row=1, column=0, columnspan=5, sticky=tk.W, **pad)
        ttk.Button(self.config_buttons_frame, text="New Config", command=self._new_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.config_buttons_frame, text="Delete Selected", command=self._delete_selected_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.config_buttons_frame, text="Move Up", command=lambda: self._move_config(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.config_buttons_frame, text="Move Down", command=lambda: self._move_config(1)).pack(side=tk.LEFT, padx=5)

        # Action buttons for Mandarake scraper (row 2)
        self.action_buttons_frame = ttk.Frame(bottom_pane)
        self.action_buttons_frame.grid(row=2, column=0, columnspan=5, sticky=tk.W, **pad)
        ttk.Button(self.action_buttons_frame, text="Search Mandarake", command=self.run_now).pack(side=tk.LEFT, padx=5)
        self.cancel_button = ttk.Button(self.action_buttons_frame, text="Cancel Search", command=self.cancel_search, state='disabled')
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        # Configure bottom pane grid
        bottom_pane.rowconfigure(0, weight=1)  # Tree row expands
        for i in range(7):
            bottom_pane.columnconfigure(i, weight=1)

        self._load_config_tree()
        basic_frame.columnconfigure(3, weight=1)

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

        # Min Similarity
        ttk.Label(alert_threshold_frame, text="Min Similarity %:").pack(side=tk.LEFT, padx=5)
        self.alert_min_similarity = tk.DoubleVar(value=70.0)
        ttk.Spinbox(alert_threshold_frame, from_=0, to=100, textvariable=self.alert_min_similarity, width=8).pack(side=tk.LEFT, padx=5)

        # Min Profit
        ttk.Label(alert_threshold_frame, text="Min Profit %:").pack(side=tk.LEFT, padx=5)
        self.alert_min_profit = tk.DoubleVar(value=20.0)
        ttk.Spinbox(alert_threshold_frame, from_=-100, to=1000, textvariable=self.alert_min_profit, width=8).pack(side=tk.LEFT, padx=5)

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
        browserless_columns = ('title', 'price', 'shipping', 'mandarake_price', 'profit_margin', 'sold_date', 'similarity', 'url')

        # Create custom style for eBay results treeview with thumbnails
        style = ttk.Style()
        style.configure('Browserless.Treeview', rowheight=70)  # Match output tree height

        self.browserless_tree = ttk.Treeview(browserless_results_frame, columns=browserless_columns, show='tree headings', height=8, style='Browserless.Treeview')

        self.browserless_tree.heading('#0', text='Thumb')
        self.browserless_tree.column('#0', width=70, stretch=False)  # Match output tree width

        browserless_headings = {
            'title': 'Title',
            'price': 'eBay Price',
            'shipping': 'Shipping',
            'mandarake_price': 'Mandarake ¥',
            'profit_margin': 'Profit %',
            'sold_date': 'Sold Date',
            'similarity': 'Similarity %',
            'url': 'eBay URL'
        }

        browserless_widths = {
            'title': 280,
            'price': 80,
            'shipping': 70,
            'mandarake_price': 90,
            'profit_margin': 80,
            'sold_date': 100,
            'similarity': 90,
            'url': 180
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

        # Bind double-click to open URL
        self.browserless_tree.bind('<Double-1>', self.open_browserless_url)
        # Prevent space from affecting tree selection when it has focus
        # Space key handled globally via bind_class
        # Allow deselect by clicking empty area
        self.browserless_tree.bind("<Button-1>", lambda e: self._deselect_if_empty(e, self.browserless_tree))

        # Enable column drag-to-reorder for browserless tree
        self._setup_column_drag(self.browserless_tree)

        # Status area for browserless search
        self.browserless_status = tk.StringVar(value="Ready for eBay text search")
        browserless_status_label = ttk.Label(browserless_results_frame, textvariable=self.browserless_status, relief=tk.SUNKEN, anchor='w')
        browserless_status_label.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(5, 0))

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

        csv_columns = ('title', 'price', 'shop', 'stock', 'category')
        self.csv_items_tree = ttk.Treeview(csv_items_frame, columns=csv_columns, show='tree headings', height=6, style='CSV.Treeview')

        self.csv_items_tree.heading('#0', text='Thumb')
        self.csv_items_tree.column('#0', width=70, stretch=False)

        csv_headings = {
            'title': 'Title',
            'price': 'Mandarake Price',
            'shop': 'Shop',
            'stock': 'Stock',
            'category': 'Category'
        }

        for col, heading in csv_headings.items():
            self.csv_items_tree.heading(col, text=heading)

        self.csv_items_tree.column('title', width=280)
        self.csv_items_tree.column('price', width=100)
        self.csv_items_tree.column('shop', width=80)
        self.csv_items_tree.column('stock', width=60)
        self.csv_items_tree.column('category', width=120)

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

        self.csv_compare_progress = ttk.Progressbar(button_frame, mode='indeterminate', length=200)
        self.csv_compare_progress.grid(row=0, column=5, sticky=tk.W, padx=(10, 5))

        # Add the CSV comparison frame to the paned window
        self.ebay_paned.add(csv_compare_frame, minsize=200)

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
        self.destroy()

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
        if not value:
            return 'all'
        value = str(value).strip()

        # Handle Unicode characters better - create readable ASCII representation
        import unicodedata
        try:
            # Try to normalize and convert to ASCII
            normalized = unicodedata.normalize('NFKD', value)
            ascii_value = normalized.encode('ascii', 'ignore').decode('ascii')
            if ascii_value.strip():
                value = ascii_value
        except:
            pass

        # If still contains non-ASCII, use a hash-based approach for unique identification
        if not value.isascii():
            import hashlib
            hash_part = hashlib.md5(value.encode('utf-8')).hexdigest()[:8]
            # Try to extract any ASCII parts
            ascii_parts = re.findall(r'[a-zA-Z0-9]+', value)
            if ascii_parts:
                value = '_'.join(ascii_parts) + '_' + hash_part
            else:
                value = 'unicode_' + hash_part

        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", '_', value)
        value = value.strip('_')
        return value or 'all'

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
        # Don't strip keyword here - let it be stripped only on commit (FocusOut)
        keyword = self.keyword_var.get()

        config: dict[str, object] = {
            'keyword': keyword,
            'hide_sold_out': self.hide_sold_var.get(),
            'csv_show_in_stock_only': self.csv_in_stock_only.get() if hasattr(self, 'csv_in_stock_only') else False,
            'csv_add_secondary_keyword': self.csv_add_secondary_keyword.get() if hasattr(self, 'csv_add_secondary_keyword') else False,
            'language': self.language_var.get(),
            'fast': self.fast_var.get(),
            'resume': self.resume_var.get(),
            'debug': self.debug_var.get(),
        }

        categories = self._get_selected_categories()
        if categories:
            category_code = categories[0]
            # Save as category name instead of code
            from mandarake_codes import get_category_name
            category_name = get_category_name(category_code, language='en')
            # Store both for reference
            config['category'] = category_code
            config['category_name'] = category_name

        max_pages = self.max_pages_var.get().strip()
        if max_pages:
            try:
                config['max_pages'] = int(max_pages)
            except ValueError:
                messagebox.showerror("Validation", "Max pages must be an integer.")
                return None

        # Results per page
        results_per_page = self.results_per_page_var.get().strip()
        if results_per_page:
            try:
                config['results_per_page'] = int(results_per_page)
            except ValueError:
                config['results_per_page'] = 48  # Default
        else:
            config['results_per_page'] = 48  # Default

        recent_hours = self._get_recent_hours_value()
        if recent_hours:
            config['recent_hours'] = recent_hours

        shop_value = self._resolve_shop()
        if shop_value:
            config['shop'] = shop_value
            # Store shop name for readable filenames
            from mandarake_codes import get_store_name
            shop_name = get_store_name(shop_value, language='en')
            config['shop_name'] = shop_name

        csv_path = self.csv_path_var.get().strip()
        if csv_path:
            config['csv'] = csv_path

        download_dir = self.download_dir_var.get().strip()
        if download_dir:
            config['download_images'] = download_dir

        thumbs = self.thumbnails_var.get().strip()
        if thumbs:
            try:
                config['thumbnails'] = int(thumbs)
            except ValueError:
                messagebox.showerror("Validation", "Thumbnail width must be an integer.")
                return None

        return config

    def _resolve_shop(self):
        """Get the selected shop code from the listbox."""
        selection = self.shop_listbox.curselection()
        if not selection:
            return "all"  # Default to all stores if nothing selected

        index = selection[0]
        shop_code = self.shop_code_map[index]

        return shop_code if shop_code else "all"

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

            # Load config to check for Japanese text
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                keyword = config.get('keyword', '')
                print(f"[GUI DEBUG] Keyword from config loaded")
                print(f"[GUI DEBUG] Keyword has {len(keyword)} characters")

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
        if not hasattr(self, 'listbox_paned'):
            return
        try:
            total_width = self.listbox_paned.winfo_width()
            if total_width > 500:
                sash_pos = self.listbox_paned.sash_coord(0)[0]
                self._user_sash_ratio = sash_pos / total_width
        except Exception:
            pass

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
        # Stop schedule executor
        if hasattr(self, 'schedule_executor'):
            self.schedule_executor.stop()

        self._save_gui_settings()
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

    def _on_main_category_selected(self, event=None):
        code = utils.extract_code(self.main_category_var.get())
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
        self.detail_listbox.selection_clear(0, tk.END)
        if not categories:
            self.main_category_var.set('')
            self._populate_detail_categories()
            return

        # Select main category
        first_code = categories[0]
        main_code = utils.match_main_code(first_code)
        if main_code:
            # Find the exact matching value from the combobox list
            # This ensures the value matches the dropdown format exactly
            for code, name in MAIN_CATEGORY_OPTIONS:
                if code == main_code:
                    label = f"{name} ({code})"
                    self.main_category_var.set(label)
                    break
        else:
            self.main_category_var.set('')

        # Populate detail categories based on main category
        self._populate_detail_categories(utils.extract_code(self.main_category_var.get()))

        # Select detail categories and scroll to first selected
        first_selected_idx = None
        for idx, code in enumerate(self.detail_code_map):
            if code in categories:
                self.detail_listbox.selection_set(idx)
                if first_selected_idx is None:
                    first_selected_idx = idx

        # Scroll to make the first selected category visible
        if first_selected_idx is not None:
            self.detail_listbox.see(first_selected_idx)

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
        selection = self.csv_items_tree.selection()
        if selection:
            self.csv_tree_menu.post(event.x_root, event.y_root)

    def _delete_csv_items(self):
        """Delete selected CSV items (supports multi-select)"""
        selection = self.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select items to delete")
            return

        # Confirm deletion
        count = len(selection)
        item_word = "item" if count == 1 else "items"
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete {count} {item_word}?\n\nThis will also delete associated images from disk."):
            return

        try:
            # Get the titles and image paths of selected items
            items_to_delete = []
            images_to_delete = []
            for item_id in selection:
                values = self.csv_items_tree.item(item_id)['values']
                if values:
                    title = values[0]  # Title is first column
                    items_to_delete.append(title)

                    # Find the corresponding row in csv_compare_data to get image path
                    for row in self.csv_compare_data:
                        if row.get('title', '') == title:
                            local_image = row.get('local_image', '')
                            if local_image:
                                images_to_delete.append(local_image)
                            break

            # Remove from csv_compare_data by matching titles
            original_count = len(self.csv_compare_data)
            self.csv_compare_data = [
                row for row in self.csv_compare_data
                if row.get('title', '') not in items_to_delete
            ]
            deleted_count = original_count - len(self.csv_compare_data)

            # Delete associated image files
            images_deleted = 0
            for image_path in images_to_delete:
                try:
                    img_file = Path(image_path)
                    if img_file.exists():
                        img_file.unlink()
                        images_deleted += 1
                        print(f"[CSV DELETE] Deleted image: {image_path}")
                except Exception as e:
                    print(f"[CSV DELETE] Failed to delete image {image_path}: {e}")

            # Refresh the display
            self.filter_csv_items()

            # Update status
            status_msg = f"Deleted {deleted_count} {item_word}"
            if images_deleted > 0:
                status_msg += f" and {images_deleted} image{'s' if images_deleted != 1 else ''}"
            self.status_var.set(status_msg)
            print(f"[CSV DELETE] Removed {deleted_count} items and {images_deleted} images from disk")

            # Save updated CSV if a file is loaded
            if hasattr(self, 'csv_compare_path') and self.csv_compare_path:
                self._save_updated_csv()

        except Exception as e:
            messagebox.showerror("Delete Error", f"Failed to delete items: {str(e)}")
            print(f"[CSV DELETE] Error: {e}")

    def _on_csv_double_click(self, event=None):
        """Open product link on double click"""
        selection = self.csv_items_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                link = items_list[index].get('product_url', '')
                if link:
                    webbrowser.open(link)
        except Exception as e:
            print(f"[CSV] Error opening link: {e}")

    def _search_csv_by_image_api(self):
        """Search selected CSV item by image using eBay API"""
        selection = self.csv_items_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                item_data = items_list[index]
                local_image_path = item_data.get('local_image', '')
                if not local_image_path or not Path(local_image_path).exists():
                    messagebox.showerror("Error", "Local image not found for this item.")
                    return

                from mandarake_scraper import EbayAPI
                # Note: eBay API credentials removed from GUI - using web scraping instead
                ebay_api = EbayAPI("", "")

                self.browserless_status.set("Searching by image on eBay (API)...")
                url = ebay_api.search_by_image_api(local_image_path)
                if url:
                    webbrowser.open(url)
                    self.browserless_status.set("Search by image (API) complete.")
                else:
                    messagebox.showerror("Error", "Could not find results using eBay API.")
                    self.browserless_status.set("Search by image (API) failed.")
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")

    def _search_csv_by_image_web(self):
        """Search selected CSV item by image using web method"""
        selection = self.csv_items_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                item_data = items_list[index]
                local_image_path = item_data.get('local_image', '')
                if not local_image_path or not Path(local_image_path).exists():
                    messagebox.showerror("Error", "Local image not found for this item.")
                    return

                self.browserless_status.set("Searching by image on eBay (Web)...")
                self._start_thread(self._run_csv_web_image_search, local_image_path)
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")

    def _run_csv_web_image_search(self, image_path):
        from ebay_image_search import run_ebay_image_search
        url = run_ebay_image_search(image_path)
        if "Error" not in url:
            webbrowser.open(url)
            self.run_queue.put(("browserless_status", "Search by image (Web) complete."))
        else:
            self.run_queue.put(("error", "Could not find results using web search."))

    def _download_missing_csv_images(self):
        """Download missing images from web and save them locally"""
        if not self.csv_compare_data or not self.csv_compare_path:
            messagebox.showwarning("No CSV", "Please load a CSV file first.")
            return

        # Count items missing local images
        missing_count = 0
        for row in self.csv_compare_data:
            local_image = row.get('local_image', '')
            image_url = row.get('image_url', '')
            if image_url and (not local_image or not Path(local_image).exists()):
                missing_count += 1

        if missing_count == 0:
            messagebox.showinfo("Complete", "All items already have local images!")
            return

        response = messagebox.askyesno(
            "Download Images",
            f"Download {missing_count} missing images from web and save them locally?\n\nThis will update the CSV file."
        )

        if not response:
            return

        # Start download in background
        self.browserless_status.set(f"Downloading {missing_count} missing images...")
        self._start_thread(self._download_missing_images_worker)

    def _download_missing_images_worker(self):
        """Background worker to download missing images"""
        download_dir = self.download_dir_var.get().strip()

        def update_callback(message):
            self.after(0, lambda: self.browserless_status.set(message))

        def save_callback():
            self._save_updated_csv()

        def reload_callback():
            self.after(0, self.filter_csv_items)

        workers.download_missing_images_worker(
            self.csv_compare_data,
            download_dir,
            update_callback,
            save_callback,
            reload_callback
        )

    def _save_updated_csv(self):
        """Save the updated CSV with new local_image paths"""
        try:
            # Get fieldnames from first row
            if not self.csv_compare_data:
                return

            fieldnames = list(self.csv_compare_data[0].keys())

            # Write to CSV
            with open(self.csv_compare_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.csv_compare_data)

            print(f"[CSV IMAGES] Updated CSV file: {self.csv_compare_path}")

        except Exception as e:
            print(f"[CSV IMAGES] Error saving CSV: {e}")
            raise

    def _update_tree_item(self, path: Path, config: dict):
        """Update a specific tree item's values without reloading the entire tree, or add if new"""
        # Find the tree item that matches this path
        existing_item = None
        for item in self.config_tree.get_children():
            if self.config_paths.get(item) == path:
                existing_item = item
                break

        # Prepare values
        keyword = config.get('keyword', '')

        # Use category name if available, otherwise show code
        category = config.get('category_name', config.get('category', ''))

        # Use shop name if available, otherwise show code
        shop = config.get('shop_name', config.get('shop', ''))

        # Hide sold out (affects search URL)
        hide_sold = 'Yes' if config.get('hide_sold_out') else 'No'

        # Results per page (default 48)
        results_per_page = config.get('results_per_page', 48)

        # Max pages (empty if not set)
        max_pages = config.get('max_pages', '')

        # Latest additions timeframe
        recent_hours = config.get('recent_hours')
        latest_additions = self._label_for_recent_hours(recent_hours) if recent_hours else ''

        # Language (default to english)
        language = config.get('language', 'en')

        values = (path.name, keyword, category, shop, hide_sold, results_per_page, max_pages, latest_additions, language)

        if existing_item:
            # Update existing item
            self.config_tree.item(existing_item, values=values)
        else:
            # Add new item at the end
            new_item = self.config_tree.insert('', 'end', values=values)
            self.config_paths[new_item] = path
            # Select the newly added item
            self.config_tree.selection_set(new_item)
            self.config_tree.see(new_item)
            print(f"[CONFIG TREE] Added new config: {path.name}")

    def _load_config_tree(self):
        if not hasattr(self, 'config_tree'):
            return
        for item in self.config_tree.get_children():
            self.config_tree.delete(item)
        self.config_paths.clear()

        configs_dir = Path('configs')
        if not configs_dir.exists():
            return

        # Get all config files
        config_files = list(configs_dir.glob('*.json'))

        # Load custom order from metadata file
        order_file = Path('.config_order.json')
        custom_order = []
        if order_file.exists():
            try:
                with order_file.open('r', encoding='utf-8') as f:
                    custom_order = json.load(f)
            except:
                pass

        # Sort: custom ordered items first, then new items by modification time
        config_file_names = {f.name: f for f in config_files}
        sorted_files = []

        # Add files in custom order if they still exist
        for name in custom_order:
            if name in config_file_names:
                sorted_files.append(config_file_names[name])
                del config_file_names[name]

        # Add any new files not in custom order (sorted by modification time, newest first)
        new_files = sorted(config_file_names.values(), key=lambda p: p.stat().st_mtime, reverse=True)
        sorted_files.extend(new_files)

        config_files = sorted_files

        for cfg_path in config_files:
            try:
                with cfg_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                continue

            # Skip if data is not a dictionary (malformed config)
            if not isinstance(data, dict):
                continue

            keyword = data.get('keyword', '')

            # Use category name if available, otherwise show code
            category = data.get('category_name', data.get('category', ''))
            if isinstance(category, list):
                category = ', '.join(category)

            # Use shop name if available, otherwise show code
            shop = data.get('shop_name', data.get('shop', ''))

            # Hide sold out (affects search URL)
            hide_sold = 'Yes' if data.get('hide_sold_out') else 'No'

            # Results per page (default 48)
            results_per_page = data.get('results_per_page', 48)

            # Max pages (empty if not set)
            max_pages = data.get('max_pages', '')

            # Latest additions timeframe
            recent_hours = data.get('recent_hours')
            latest_additions = self._label_for_recent_hours(recent_hours) if recent_hours else ''

            # Language (default to english)
            language = data.get('language', 'en')

            values = (cfg_path.name, keyword, category, shop, hide_sold, results_per_page, max_pages, latest_additions, language)
            item = self.config_tree.insert('', tk.END, values=values)
            self.config_paths[item] = cfg_path

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
            self.config_tree_menu.post(event.x_root, event.y_root)

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
        try:
            # Get keyword from config
            keyword = config.get('keyword', '').strip()
            if not keyword:
                return

            # Check if secondary keyword should be added
            add_secondary = hasattr(self, 'csv_add_secondary_keyword') and self.csv_add_secondary_keyword.get()

            if add_secondary and self.csv_filtered_items:
                # Get first filtered item and extract secondary keyword
                first_item = self.csv_filtered_items[0]
                title = first_item.get('title', '')
                if title:
                    secondary = self._extract_secondary_keyword(title, keyword)
                    if secondary:
                        query = f"{keyword} {secondary}"
                        self.browserless_query_var.set(query)
                        print(f"[CSV AUTOFILL] Set eBay query with secondary: {query}")
                        return

            # No secondary keyword, just use primary keyword
            self.browserless_query_var.set(keyword)
            print(f"[CSV AUTOFILL] Set eBay query: {keyword}")

        except Exception as e:
            print(f"[CSV AUTOFILL] Error: {e}")

    def _autofill_search_query_from_csv(self):
        """Auto-fill eBay search query from first CSV item's keyword and optionally add secondary keyword"""
        try:
            if not self.csv_filtered_items:
                return

            # Get first filtered item
            first_item = self.csv_filtered_items[0]
            keyword = first_item.get('keyword', '').strip()
            category = first_item.get('category', '')

            # If no keyword field, try to extract from title
            if not keyword:
                title = first_item.get('title', '')
                keyword = ' '.join(title.split()[:3]) if title else ''

            if not keyword:
                return

            # Get category keyword from mapping
            category_keyword = CATEGORY_KEYWORDS.get(category, '')

            # Build search query: keyword + category keyword
            search_query = f"{keyword} {category_keyword}".strip()

            # Check if secondary keyword should be added
            add_secondary = hasattr(self, 'csv_add_secondary_keyword') and self.csv_add_secondary_keyword.get()

            if add_secondary:
                title = first_item.get('title', '')
                if title:
                    secondary = self._extract_secondary_keyword(title, keyword)
                    if secondary:
                        search_query = f"{search_query} {secondary}".strip()
                        print(f"[CSV AUTOFILL] Added secondary keyword: {secondary}")

            # Set the final query
            self.browserless_query_var.set(search_query)
            print(f"[CSV AUTOFILL] Set eBay query: {search_query}")

        except Exception as e:
            print(f"[CSV AUTOFILL] Error: {e}")

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
        try:
            config = self._collect_config()
            if config:
                # Save the current selection before updating tree
                current_selection = self.config_tree.selection()

                # Save without renaming - just update the file in place
                self._save_config_to_path(config, self.last_saved_path, update_tree=True)

                # Restore the selection after tree update
                if current_selection:
                    # Find the item with the same path
                    for item in self.config_tree.get_children():
                        if self.config_paths.get(item) == self.last_saved_path:
                            self.config_tree.selection_set(item)
                            self.config_tree.see(item)
                            break

                # Silently saved (no console spam)
        except Exception as e:
            print(f"[AUTO-SAVE] Error: {e}")

    def _commit_keyword_changes(self, event=None):
        """Trim trailing spaces from keyword and rename file if needed (called on blur)"""
        if not hasattr(self, 'last_saved_path') or not self.last_saved_path:
            return

        # Don't rename during initial load
        if not getattr(self, '_settings_loaded', False):
            return

        # Don't rename while loading a config
        if getattr(self, '_loading_config', False):
            return

        try:
            # Trim trailing spaces from keyword
            current_keyword = self.keyword_var.get()
            trimmed_keyword = current_keyword.rstrip()

            # Only update if there were trailing spaces
            if current_keyword != trimmed_keyword:
                self.keyword_var.set(trimmed_keyword)

            # Now check if filename should be updated
            config = self._collect_config()
            if config:
                suggested_filename = utils.suggest_config_filename(config)
                current_filename = self.last_saved_path.name

                # If the suggested filename is different, rename the file
                if suggested_filename != current_filename:
                    new_path = self.last_saved_path.parent / suggested_filename

                    # Only rename if new path doesn't exist or is the same file
                    if not new_path.exists() or new_path == self.last_saved_path:
                        old_path = self.last_saved_path

                        # Find the tree item with the old path and update its mapping
                        for item in self.config_tree.get_children():
                            if self.config_paths.get(item) == old_path:
                                self.config_paths[item] = new_path
                                break

                        # Delete old file if renaming
                        if new_path != self.last_saved_path and self.last_saved_path.exists():
                            self.last_saved_path.unlink()

                        # Update the path
                        self.last_saved_path = new_path
                        print(f"[COMMIT] Renamed config to: {suggested_filename}")

                        # Save and update tree
                        self._save_config_to_path(config, self.last_saved_path, update_tree=True)
        except Exception as e:
            print(f"[COMMIT] Error: {e}")

    def _on_config_selected(self, event=None):
        """Load config when selected (single click)"""
        selection = self.config_tree.selection()
        if not selection:
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
        max_pages = config.get('max_pages', '')
        recent_hours = config.get('recent_hours')
        timeframe = self._label_for_recent_hours(recent_hours) if recent_hours else ''
        language = config.get('language', 'en')

        values = (path.name, keyword, category, shop, hide, results_per_page, max_pages, timeframe, language)
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
        """Delete the selected config file(s)"""
        selection = self.config_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a config file to delete")
            return

        # Get all selected paths
        paths = [self.config_paths.get(item) for item in selection if self.config_paths.get(item)]
        if not paths:
            return

        # Confirm deletion
        if len(paths) == 1:
            message = f"Are you sure you want to delete:\n{paths[0].name}?"
        else:
            file_list = '\n'.join(p.name for p in paths)
            message = f"Are you sure you want to delete {len(paths)} configs?\n\n{file_list}"

        response = messagebox.askyesno("Confirm Delete", message)

        if response:
            deleted_count = 0
            errors = []
            for path in paths:
                try:
                    path.unlink()  # Delete the file
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"{path.name}: {e}")

            self._load_config_tree()  # Reload the tree

            if errors:
                messagebox.showerror("Errors", f"Failed to delete:\n" + '\n'.join(errors))

            self.status_var.set(f"Deleted {deleted_count} config(s)")

    def _move_config(self, direction):
        """Move selected config up (-1) or down (1) in the list"""
        selection = self.config_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a config file to move")
            return

        item = selection[0]
        path = self.config_paths.get(item)
        if not path:
            return

        # Get current order from treeview
        tree_children = self.config_tree.get_children()
        current_order = [self.config_paths.get(child).name for child in tree_children]

        try:
            current_index = current_order.index(path.name)
        except ValueError:
            return

        new_index = current_index + direction

        # Check bounds
        if new_index < 0 or new_index >= len(current_order):
            return

        # Swap positions in order list
        current_order[current_index], current_order[new_index] = current_order[new_index], current_order[current_index]

        # Save new order to metadata file
        order_file = Path('.config_order.json')
        try:
            with order_file.open('w', encoding='utf-8') as f:
                json.dump(current_order, f, indent=2)

            self._load_config_tree()  # Reload the tree

            # Re-select the moved item
            for tree_item in self.config_tree.get_children():
                if self.config_paths.get(tree_item) == path:
                    self.config_tree.selection_set(tree_item)
                    self.config_tree.see(tree_item)
                    break

            self.status_var.set(f"Moved: {path.name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to move file: {e}")

    def _load_from_url(self):
        """Parse Mandarake URL and populate config fields"""
        url = self.mandarake_url_var.get().strip()
        if not url:
            messagebox.showinfo("No URL", "Please enter a Mandarake URL")
            return

        try:
            from mandarake_scraper import parse_mandarake_url
            config = parse_mandarake_url(url)
            self._populate_from_config(config)
            self.status_var.set(f"Loaded URL parameters")
            # Don't clear the URL - keep it in the field
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse URL: {e}")

    def _populate_from_config(self, config: dict):
        self.keyword_var.set(config.get('keyword', ''))

        category = config.get('category')
        if isinstance(category, list):
            categories = category
        elif category:
            categories = [category]
        else:
            categories = []
        self._select_categories(categories)

        self.max_pages_var.set(str(config.get('max_pages', '')))
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
        # Note: eBay API credentials removed from GUI

        self.csv_path_var.set(config.get('csv', ''))
        self.download_dir_var.set(config.get('download_images', ''))
        self.thumbnails_var.set(str(config.get('thumbnails', '')))
        self.results_per_page_var.set(str(config.get('results_per_page', '240')))

        self.schedule_var.set(config.get('schedule', ''))
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
        if not query:
            messagebox.showerror("Error", "Please enter a search query")
            return

        # Start search in background thread
        self.browserless_progress.start()
        self.browserless_status.set("Searching eBay...")
        self._start_thread(self._run_scrapy_text_search_worker)

    def run_scrapy_search_with_compare(self):
        """Run Scrapy eBay search WITH image comparison"""
        query = self.browserless_query_var.get().strip()
        if not query:
            messagebox.showerror("Error", "Please enter a search query")
            return

        if not hasattr(self, 'browserless_image_path') or not self.browserless_image_path or not Path(self.browserless_image_path).exists():
            messagebox.showerror("Error", "Please select a reference image first for comparison")
            return

        # Check if we have cached eBay results
        has_cached_results = hasattr(self, 'browserless_results_data') and self.browserless_results_data and len(self.browserless_results_data) > 0

        if has_cached_results:
            # State 1: Use cached results - just run comparison
            print(f"[SCRAPY COMPARE] Using {len(self.browserless_results_data)} cached eBay results")
            self.browserless_progress.start()
            self.browserless_status.set("Comparing cached results with reference image...")
            self._start_thread(self._run_cached_compare_worker)
        else:
            # State 2: No cached results - run full search and compare
            print(f"[SCRAPY COMPARE] No cached results, running full eBay search")
            self.browserless_progress.start()
            self.browserless_status.set("Searching eBay and comparing images...")
            self._start_thread(self._run_scrapy_search_with_compare_worker)

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
            self.after(0, lambda: messagebox.showinfo(title, message))
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
            self.after(0, lambda: messagebox.showinfo(title, message))
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
        """Clear browserless search results"""
        for item in self.browserless_tree.get_children():
            self.browserless_tree.delete(item)
        self.browserless_results_data = []
        self.browserless_status.set("Ready for eBay text search")

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
        file_path = filedialog.askopenfilename(
            title="Select CSV file for comparison",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir="results"
        )

        if file_path:
            success = self._load_csv_worker(Path(file_path))
            if not success:
                messagebox.showerror("Error", f"Failed to load CSV: {file_path}")

    def filter_csv_items(self):
        """Filter and display CSV items based on in-stock filter - fast load, thumbnails loaded on demand"""
        # Clear existing items and images
        for item in self.csv_items_tree.get_children():
            self.csv_items_tree.delete(item)
        self.csv_images.clear()

        if not self.csv_compare_data:
            return

        # Apply filters
        from datetime import datetime, timedelta
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=24)  # 24 hours for newly listed filter

        in_stock_only = self.csv_in_stock_only.get()
        newly_listed_only = self.csv_newly_listed_only.get()
        filtered_items = []

        for row in self.csv_compare_data:
            # In-stock filter
            stock = row.get('in_stock', '').lower()
            if in_stock_only and stock not in ('true', 'yes', '1'):
                continue

            # Newly listed filter (24 hours)
            if newly_listed_only:
                first_seen_str = row.get('first_seen', '')
                if first_seen_str:
                    try:
                        first_seen = datetime.fromisoformat(first_seen_str)
                        if first_seen < cutoff_time:
                            continue  # Skip items older than 24 hours
                    except:
                        continue  # Skip items with invalid dates
                else:
                    continue  # Skip items without first_seen date

            filtered_items.append(row)

        # Display filtered items WITHOUT thumbnails first (fast load)
        # Use recent_hours setting for CSV "new items" visual indicator
        recent_hours = self._get_recent_hours_value()
        new_indicator_cutoff = current_time - timedelta(hours=recent_hours) if recent_hours else current_time - timedelta(hours=12)

        # Store NEW status for each item for thumbnail border rendering
        self.csv_new_items = set()

        for i, row in enumerate(filtered_items):
            # Calculate NEW indicator dynamically
            first_seen_str = row.get('first_seen', '')
            if first_seen_str:
                try:
                    first_seen = datetime.fromisoformat(first_seen_str)
                    if first_seen >= new_indicator_cutoff:
                        self.csv_new_items.add(str(i))  # Mark as new
                except:
                    pass

            title = row.get('title', '')
            price = row.get('price_text', row.get('price', ''))
            shop = row.get('shop', row.get('shop_text', ''))
            stock_display = 'Yes' if row.get('in_stock', '').lower() in ('true', 'yes', '1') else 'No'
            category = row.get('category', '')

            # Insert WITHOUT image for fast loading (use 0-based index as iid for proper mapping)
            self.csv_items_tree.insert('', 'end', iid=str(i), text=str(i+1),
                                      values=(title, price, shop, stock_display, category))

        print(f"[CSV COMPARE] Displayed {len(filtered_items)} items (newly listed: {newly_listed_only}, in-stock: {in_stock_only})")

        # Store filtered items for thumbnail toggling
        self.csv_filtered_items = filtered_items

        # Load thumbnails in background thread if enabled
        if self.csv_show_thumbnails.get():
            self._start_thread(self._load_csv_thumbnails_worker, filtered_items)
        else:
            print(f"[CSV THUMBNAILS] Thumbnails disabled, skipping load")

    def _load_csv_thumbnails_worker(self, filtered_items):
        """Background worker to load CSV thumbnails without blocking UI"""
        def update_image_callback(item_id, img):
            def update_image():
                try:
                    # item_id is the tree item's iid (0-based index as string)
                    if item_id in self.csv_items_tree.get_children():
                        self.csv_items_tree.item(item_id, image=img, text='')
                        self.csv_images[item_id] = img
                except Exception as e:
                    print(f"[CSV THUMBNAILS] Error updating image for {item_id}: {e}")
            self.after(0, update_image)

        # Get current thumbnail column width
        thumb_width = self.csv_items_tree.column('#0', 'width')

        workers.load_csv_thumbnails_worker(
            filtered_items,
            self.csv_new_items,
            update_image_callback,
            thumb_width
        )

    def _on_csv_filter_changed(self):
        """Handle CSV filter changes - filter items (settings saved on close)"""
        self.filter_csv_items()

    def _on_recent_hours_changed(self, *args):
        """Handle latest additions timeframe change - refresh CSV view if loaded"""
        # Only refresh if CSV is loaded
        if hasattr(self, 'csv_compare_data') and self.csv_compare_data:
            self.filter_csv_items()

    def _on_csv_column_resize(self, event):
        """Handle column resize event to reload thumbnails with new size"""
        # Only handle if we're resizing the thumbnail column (#0)
        # Use a timer to avoid reloading on every pixel change
        if hasattr(self, '_resize_timer'):
            self.after_cancel(self._resize_timer)

        def reload_thumbnails():
            # Check if thumbnail column was resized and thumbnails are enabled
            if self.csv_show_thumbnails.get() and hasattr(self, 'csv_filtered_items') and self.csv_filtered_items:
                current_width = self.csv_items_tree.column('#0', 'width')
                # Only reload if width changed significantly (more than 5px)
                if not hasattr(self, '_last_thumb_width') or abs(current_width - self._last_thumb_width) > 5:
                    self._last_thumb_width = current_width
                    print(f"[CSV THUMBNAILS] Column resized to {current_width}px, reloading thumbnails...")
                    self._start_thread(self._load_csv_thumbnails_worker, self.csv_filtered_items)

        # Debounce: wait 300ms after user stops dragging
        self._resize_timer = self.after(300, reload_thumbnails)

    def toggle_csv_thumbnails(self):
        """Toggle visibility of thumbnails in CSV treeview"""
        show_thumbnails = self.csv_show_thumbnails.get()

        if show_thumbnails:
            # Show thumbnails - set column width and rowheight
            self.csv_items_tree.column('#0', width=70, stretch=False)
            style = ttk.Style()
            style.configure('CSV.Treeview', rowheight=70)

            # Reload thumbnails if we have CSV items loaded
            if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items:
                print(f"[CSV THUMBNAILS] Loading thumbnails for {len(self.csv_filtered_items)} items...")
                self._start_thread(self._load_csv_thumbnails_worker, self.csv_filtered_items)
        else:
            # Hide thumbnails - set column width to 0
            self.csv_items_tree.column('#0', width=0, stretch=False)
            style = ttk.Style()
            style.configure('CSV.Treeview', rowheight=25)

        print(f"[CSV THUMBNAILS] Thumbnails {'shown' if show_thumbnails else 'hidden'}")

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
        try:
            # Always show menu - user can select text before right-clicking
            self.keyword_menu.post(event.x_root, event.y_root)
        except:
            pass

    def _add_to_publisher_list(self):
        """Add selected text from keyword entry to publisher list"""
        try:
            if self.keyword_entry.selection_present():
                selected_text = self.keyword_entry.selection_get().strip()
                if selected_text and len(selected_text) > 1:
                    self.publisher_list.add(selected_text)
                    self._save_publisher_list()
                    messagebox.showinfo("Publisher Added", f"'{selected_text}' has been added to the publisher list.")
                    print(f"[PUBLISHERS] Added: {selected_text}")
        except Exception as e:
            print(f"[PUBLISHERS] Error adding publisher: {e}")

    def _set_keyword_field(self, text):
        """Helper function to reliably set the keyword field"""
        # Method 1: Use StringVar
        self.keyword_var.set(text)

        # Method 2: Direct widget manipulation (more reliable)
        self.keyword_entry.delete(0, tk.END)
        self.keyword_entry.insert(0, text)

        # Force update
        self.keyword_entry.update_idletasks()

    def _add_full_title_to_search(self):
        """Replace eBay search query with full title from selected CSV item"""
        selection = self.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item from the CSV tree")
            return

        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                row = items_list[index]

                # Get the full title
                title = row.get('title', '')
                if title:
                    # Update the eBay search query field
                    self.browserless_query_var.set(title)
                    print(f"[CSV MENU] Set eBay search query to full title: {title}")
        except Exception as e:
            print(f"[CSV MENU] Error setting full title: {e}")

    def _add_secondary_keyword_from_csv(self):
        """Add selected CSV item's secondary keyword to the eBay search query field"""
        selection = self.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item from the CSV tree")
            return

        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)

            # Use filtered items if available, otherwise use full list
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data

            if 0 <= index < len(items_list):
                row = items_list[index]

                # Get the title and primary keyword
                title = row.get('title', '')
                primary_keyword = row.get('keyword', '')

                # Extract secondary keyword using the extraction algorithm
                if title and primary_keyword:
                    secondary = self._extract_secondary_keyword(title, primary_keyword)
                elif title:
                    # No primary keyword, use first few words of title
                    secondary = ' '.join(title.split()[:3])
                else:
                    secondary = ''

                if secondary:
                    # Get current eBay search query value
                    current_query = self.browserless_query_var.get().strip()

                    # Append secondary keyword to eBay search query
                    if current_query:
                        new_query = f"{current_query} {secondary}"
                    else:
                        new_query = secondary

                    # Update the eBay search query field
                    self.browserless_query_var.set(new_query)
                    print(f"[CSV MENU] Added secondary keyword to eBay query: {secondary}")
        except Exception as e:
            print(f"[CSV MENU] Error adding secondary keyword: {e}")

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
        selection = self.csv_items_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                row = items_list[index]

                # Extract core word from title and category keyword
                title = row.get('title', '')
                category = row.get('category', '')
                keyword = row.get('keyword', '')  # Use extracted keyword if available

                # Use keyword if available, otherwise extract from title
                if keyword:
                    core_words = keyword
                else:
                    core_words = ' '.join(title.split()[:3]) if title else ''

                # Get category keyword from mapping
                category_keyword = CATEGORY_KEYWORDS.get(category, '')

                # Build search query: keyword + category keyword
                search_query = f"{core_words} {category_keyword}".strip()

                # Add secondary keyword if toggle is on
                if hasattr(self, 'csv_add_secondary_keyword') and self.csv_add_secondary_keyword.get():
                    if title and keyword:
                        secondary = self._extract_secondary_keyword(title, keyword)
                        if secondary:
                            search_query = f"{search_query} {secondary}".strip()
                            print(f"[CSV COMPARE] Added secondary keyword: {secondary}")

                if search_query:
                    self.browserless_query_var.set(search_query)
                    print(f"[CSV COMPARE] Auto-filled search: {search_query}")

        except (ValueError, IndexError) as e:
            print(f"[CSV COMPARE] Error selecting item: {e}")

    def compare_selected_csv_item(self):
        """Compare selected CSV item with eBay"""
        selection = self.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to compare")
            return

        # Get selected item data
        item_id = selection[0]
        try:
            # Need to find the actual item from filtered display
            # The iid in tree might not match csv_compare_data index due to filtering
            values = self.csv_items_tree.item(item_id)['values']
            if not values:
                messagebox.showerror("Error", "Could not get item data")
                return

            # Find matching item in csv_compare_data by title
            title_prefix = values[0]  # Truncated title from display
            item = None
            for row in self.csv_compare_data:
                if row.get('title', '').startswith(title_prefix.replace('...', '')):
                    item = row
                    break

            if not item:
                messagebox.showerror("Error", "Could not find selected item")
                return

            # Extract search query from eBay query field
            search_query = self.browserless_query_var.get().strip()
            if not search_query:
                messagebox.showwarning("No Query", "Please enter a search query")
                return

            # Run comparison in background
            self.csv_compare_progress.start()
            self._start_thread(lambda: self._compare_csv_items_worker([item], search_query))

        except Exception as e:
            messagebox.showerror("Error", f"Invalid selection: {e}")

    def _run_csv_comparison_async(self):
        """Run CSV comparison without confirmation (for scheduled tasks)"""
        self.compare_all_csv_items(skip_confirmation=True)

    def compare_all_csv_items(self, skip_confirmation=False):
        """Compare all visible CSV items with eBay

        Args:
            skip_confirmation: If True, skip confirmation dialogs (for scheduled tasks)
        """
        if not self.csv_compare_data:
            if not skip_confirmation:
                messagebox.showinfo("No Data", "Please load a CSV file first")
            return

        # Use already filtered items from the display
        # This respects both in-stock and newly listed filters
        items_to_compare = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') else self.csv_compare_data

        if not items_to_compare:
            if not skip_confirmation:
                messagebox.showinfo("No Items", "No items to compare (check filter settings)")
            return

        # Extract search query from the eBay query field (already populated by CSV load)
        search_query = self.browserless_query_var.get().strip()
        if not search_query:
            messagebox.showwarning("No Query", "Please load a CSV or enter a search query")
            return

        # Check if 2nd keyword is enabled
        add_secondary = hasattr(self, 'csv_add_secondary_keyword') and self.csv_add_secondary_keyword.get()

        # Choose comparison method based on 2nd keyword setting
        if add_secondary:
            # With 2nd keyword: Each item needs individual eBay search (different keywords)
            if skip_confirmation:
                response = True
            else:
                response = messagebox.askyesno(
                    "Individual Batch Comparison",
                    f"Compare {len(items_to_compare)} items with individual eBay searches?\n\n"
                    f"2nd keyword is enabled, so each item will have a separate search.\n"
                    f"This will take longer."
                )
            if response:
                self.csv_compare_progress.start()
                self._start_thread(lambda: self._compare_csv_items_individually_worker(items_to_compare, search_query))
        else:
            # Without 2nd keyword: Use single cached eBay search for all items
            if skip_confirmation:
                response = True
            else:
                response = messagebox.askyesno(
                    "Batch Comparison",
                    f"Compare {len(items_to_compare)} items with cached eBay search?\n\n"
                    f"All items use the same keyword, so we'll reuse eBay results."
                )
            if response:
                self.csv_compare_progress.start()
                self._start_thread(lambda: self._compare_csv_items_worker(items_to_compare, search_query))


    def _compare_csv_items_worker(self, items, search_query):
        """Worker to compare CSV items with eBay - OPTIMIZED with caching (runs in background thread)

        Args:
            items: List of items to compare
            search_query: Pre-built search query (keyword + category keyword)
        """
        max_results = int(self.browserless_max_results.get())

        def update_callback(message):
            self.after(0, lambda: self.browserless_status.set(message))

        def display_callback(comparison_results):
            self.all_comparison_results = comparison_results
            # Display results sorted by similarity/profit
            self.after(0, self.apply_results_filter)
            # Auto-send to alerts if threshold is active
            if self.alert_threshold_active.get():
                min_sim = self.alert_min_similarity.get()
                min_profit = self.alert_min_profit.get()
                self.after(0, lambda: self._send_to_alerts_with_thresholds(comparison_results, min_sim, min_profit))
            self.after(0, self.csv_compare_progress.stop)

        def show_message_callback(title, message, msg_type='info'):
            if msg_type == 'error':
                self.after(0, lambda: messagebox.showerror(title, message))
            else:
                self.after(0, lambda: messagebox.showinfo(title, message))
            self.after(0, self.csv_compare_progress.stop)

        workers.compare_csv_items_worker(
            items,
            max_results,
            self.browserless_results_data if hasattr(self, 'browserless_results_data') else [],
            search_query,
            self.usd_jpy_rate,
            update_callback,
            display_callback,
            show_message_callback
        )

    def _compare_csv_items_individually_worker(self, items, base_search_query):
        """Worker to compare CSV items individually - each item gets its own eBay search

        Args:
            items: List of items to compare
            base_search_query: Base search query (keyword + category keyword)
        """
        max_results = int(self.browserless_max_results.get())
        add_secondary = hasattr(self, 'csv_add_secondary_keyword') and self.csv_add_secondary_keyword.get()

        def update_callback(message):
            self.after(0, lambda: self.browserless_status.set(message))

        def display_callback(comparison_results):
            self.all_comparison_results = comparison_results
            # Display results sorted by similarity/profit
            self.after(0, self.apply_results_filter)
            # Auto-send to alerts if threshold is active
            if self.alert_threshold_active.get():
                min_sim = self.alert_min_similarity.get()
                min_profit = self.alert_min_profit.get()
                self.after(0, lambda: self._send_to_alerts_with_thresholds(comparison_results, min_sim, min_profit))
            self.after(0, self.csv_compare_progress.stop)

        def show_message_callback(title, message):
            self.after(0, lambda: messagebox.showerror(title, message))
            self.after(0, self.csv_compare_progress.stop)

        def create_debug_folder_callback(query):
            return self._create_debug_folder(query)

        def extract_secondary_callback(title, keyword):
            return self._extract_secondary_keyword(title, keyword)

        workers.compare_csv_items_individually_worker(
            items,
            max_results,
            add_secondary,
            self.usd_jpy_rate,
            update_callback,
            display_callback,
            show_message_callback,
            create_debug_folder_callback,
            extract_secondary_callback
        )

    def _fetch_exchange_rate(self):
        """Fetch current USD to JPY exchange rate"""
        try:
            import requests
            # Use exchangerate-api.com (free, no API key needed)
            response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=5)
            if response.status_code == 200:
                data = response.json()
                rate = data['rates']['JPY']
                return rate
        except Exception as e:
            print(f"[EXCHANGE RATE] Error fetching rate: {e}")

        # Fallback to a reasonable default if fetch fails
        return 150.0

    def _extract_price(self, price_text):
        """Extract numeric price from text"""
        import re
        if not price_text:
            return 0.0
        # Remove currency symbols and commas, extract number
        match = re.search(r'[\d,]+\.?\d*', str(price_text).replace(',', ''))
        if match:
            return float(match.group(0))
        return 0.0

    def _compare_images(self, ref_image, compare_image):
        """
        Compare two images and return similarity score (0-100).
        Uses SSIM (70%) + Histogram (30%) for robust comparison.

        Args:
            ref_image: Reference image (numpy array)
            compare_image: Image to compare (numpy array)

        Returns:
            float: Similarity score from 0-100
        """
        import cv2
        from skimage.metrics import structural_similarity as ssim

        try:
            # Resize images to same size for comparison
            ref_resized = cv2.resize(ref_image, (300, 300))
            compare_resized = cv2.resize(compare_image, (300, 300))

            # Convert to grayscale for SSIM
            ref_gray = cv2.cvtColor(ref_resized, cv2.COLOR_BGR2GRAY)
            compare_gray = cv2.cvtColor(compare_resized, cv2.COLOR_BGR2GRAY)

            # Calculate SSIM (Structural Similarity Index)
            ssim_score = ssim(ref_gray, compare_gray)

            # Calculate histogram similarity as secondary metric
            ref_hist = cv2.calcHist([ref_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            compare_hist = cv2.calcHist([compare_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            cv2.normalize(ref_hist, ref_hist)
            cv2.normalize(compare_hist, compare_hist)
            hist_score = cv2.compareHist(ref_hist, compare_hist, cv2.HISTCMP_CORREL)

            # Weighted combination: SSIM (70%) + Histogram (30%)
            similarity = (ssim_score * 0.7 + hist_score * 0.3) * 100

            return similarity

        except Exception as e:
            print(f"[IMAGE COMPARE] Error: {e}")
            return 0.0

    def _create_debug_folder(self, query):
        """
        Create debug folder for saving comparison images.

        Args:
            query: Search query string

        Returns:
            Path: Debug folder path
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
        debug_folder = Path(f"debug_comparison/{safe_query}_{timestamp}")
        debug_folder.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] Debug folder: {debug_folder}")
        return debug_folder

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
                'image_url': r['thumbnail']
            })

        self._display_browserless_results(display_results)

    def open_browserless_url(self, event):
        """Open selected eBay URL in browser"""
        selection = self.browserless_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.browserless_results_data):
                url = self.browserless_results_data[index]['url']
                if url and not any(x in url for x in ["No URL available", "Placeholder URL", "Invalid URL", "URL Error"]):
                    print(f"[BROWSERLESS SEARCH] Opening URL: {url}")
                    webbrowser.open(url)
                else:
                    messagebox.showwarning("Invalid URL", f"Cannot open URL: {url}")
        except (ValueError, IndexError) as e:
            print(f"[BROWSERLESS SEARCH] Error opening URL: {e}")
            pass

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
                result['url']  # Show full URL, no truncation
            )

            # Try to load thumbnail
            image_url = result.get('image_url', '')
            photo = None

            if image_url:
                try:
                    import requests
                    from io import BytesIO
                    response = requests.get(image_url, timeout=5)
                    response.raise_for_status()
                    pil_img = Image.open(BytesIO(response.content))
                    pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(pil_img)
                except Exception as e:
                    print(f"[SCRAPY SEARCH] Failed to load thumbnail {i}: {e}")
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
        if not url:
            return "No URL available"

        # Handle descriptive URLs (like search results pages)
        if url.startswith("Search Results Page:"):
            return url  # Return as-is for descriptive URLs

        try:
            from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
            import re

            # Remove any placeholder URLs
            if ("listing/" in url and url.count("/") < 4) or re.match(r'https://www\.ebay\.com/listing/\d+$', url):
                return "Placeholder URL - not accessible"

            # Handle relative URLs
            if url.startswith("/"):
                url = f"https://www.ebay.com{url}"
            elif not url.startswith("http"):
                url = f"https://www.ebay.com/{url}"

            # Parse the URL
            parsed = urlparse(url)

            # Extract item ID from various eBay URL formats
            item_id = None

            # Try to extract from /itm/ URLs
            itm_match = re.search(r'/itm/([^/?]+)', parsed.path)
            if itm_match:
                item_id = itm_match.group(1)

            # Try to extract from query parameters
            if not item_id and parsed.query:
                query_params = parse_qs(parsed.query)
                if 'item' in query_params:
                    item_id = query_params['item'][0]

            # If we found an item ID, construct a clean URL
            if item_id:
                # Remove non-numeric characters from item ID to get core ID
                clean_item_id = re.sub(r'[^0-9]', '', item_id)
                if clean_item_id:
                    return f"https://www.ebay.com/itm/{clean_item_id}"

            # If no item ID found, return the cleaned original URL
            if parsed.netloc and 'ebay.com' in parsed.netloc.lower():
                # Remove tracking parameters but keep essential ones
                essential_params = ['_nkw', '_sacat', 'item', 'hash']
                if parsed.query:
                    query_params = parse_qs(parsed.query, keep_blank_values=True)
                    cleaned_params = {k: v for k, v in query_params.items() if k in essential_params}
                    clean_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ""
                else:
                    clean_query = ""

                return urlunparse((
                    parsed.scheme or 'https',
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    clean_query,
                    ''  # Remove fragment
                ))

            # Fallback - return original if it looks like a valid URL
            return url if url.startswith('http') else f"Invalid URL: {url}"

        except Exception as e:
            print(f"[BROWSERLESS SEARCH] URL cleaning error: {e}")
            return f"URL Error: {url}"

    def _update_preview(self, *args):
        # Also trigger auto-save when preview updates
        self._auto_save_config()

        keyword = self.keyword_var.get().strip()

        params: list[tuple[str, str]] = []
        notes: list[str] = []

        # Add keyword if present
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

        # Build URL even if no params (will show base URL)
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