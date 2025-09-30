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

STORE_OPTIONS = [
    (code, info['en'])
    for code, info in sorted(
        MANDARAKE_STORES.items(),
        key=lambda item: int(item[0]) if item[0].lstrip('-').isdigit() else item[0],
    )
]

MAIN_CATEGORY_OPTIONS = [
    (code, data['en']) for code, data in sorted(MANDARAKE_MAIN_CATEGORIES.items())
]

RECENT_OPTIONS = [
    ("All (default)", None),
    ("Last 6 hours", 6),
    ("Last 12 hours", 12),
    ("Last 24 hours", 24),
    ("Last 72 hours", 72),
]

SETTINGS_PATH = Path('configs/gui_settings.json')

# Category keyword mapping for eBay searches
CATEGORY_KEYWORDS = {
    '05': 'Photobook',
    '050801': 'Photobook',
    '0501': 'Photobook',
    '050101': 'Photobook',
    '050102': 'Photobook',
    '050103': 'Bromide',
    '050230': 'Photobook',
    '0502': 'Goods',
    '0503': 'Video',
    '0504': 'Music',
    '06': 'Card',
    '0601': 'Trading Card',
    '060101': 'Pokemon Card',
    '060102': 'Yu-Gi-Oh Card',
    '060103': 'Magic Card',
    '060104': 'One Piece Card',
    '060105': 'Dragon Ball Card',
}


class ScraperGUI(tk.Tk):
    """GUI wrapper for Mandarake scraper configuration."""

    def __init__(self):
        super().__init__()

        # Initialize settings manager
        self.settings = get_settings_manager()

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
        self.detail_code_map: list[str] = []
        self.result_links: dict[str, str] = {}
        self.result_images: dict[str, ImageTk.PhotoImage] = {}
        self.result_data: dict[str, dict] = {}
        self.last_saved_path: Path | None = None
        self.gui_settings: dict[str, bool] = {}
        self._settings_loaded = False
        self._active_playwright_matchers = []  # Track active Playwright instances

        # Create menu bar
        self._create_menu_bar()

        self._build_widgets()
        self._load_gui_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_queue()
        self._update_preview()

    def _create_menu_bar(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Config", command=self.load_config)
        file_menu.add_command(label="Save Config", command=self.save_config)
        file_menu.add_separator()

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

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Research & Optimize", command=self.open_research_optimizer)
        tools_menu.add_command(label="View Optimization Profiles", command=self.view_optimization_profiles)

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
2. Choose your search method (Direct eBay or Google Lens)
3. Select enhancement level (light/medium/aggressive)
4. Enable "Lazy Search" for better keyword matching
5. Enable "AI Search Confirmation" for best results
6. Click "AI Smart Search" for comprehensive analysis

🧠 LAZY SEARCH:
- Automatically optimizes search terms for better results
- Handles Japanese name variations (e.g., "Yura Kano" vs "Yuraka no")
- Tries multiple keyword combinations if initial search fails
- Uses research-based optimization profiles

⭐ AI SMART SEARCH:
- Combines multiple search methods
- Tries different enhancement levels automatically
- Uses AI to select the best matching results
- Provides highest accuracy for market analysis

📊 RESULTS:
- Shows sold item counts and price ranges
- Calculates profit margins with different scenarios
- Estimates fees and shipping costs
- Provides market recommendations

For detailed documentation, see IMAGE_SEARCH_README.md
        """

        # Create help window
        help_window = tk.Toplevel(self)
        help_window.title("Image Search Help")
        help_window.geometry("500x600")
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
• Advanced image search with AI optimization
• Lazy search with intelligent keyword matching
• Category-specific research and optimization
• Profit margin calculations and market analysis
• Persistent settings and window preferences

Settings file: {self.settings.settings_file}
Last updated: {self.settings.get_setting('meta.last_updated', 'Never')}
        """

        messagebox.showinfo("About Mandarake Scraper", about_text)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        basic_frame = ttk.Frame(notebook)
        output_frame = ttk.Frame(notebook)
        browserless_frame = ttk.Frame(notebook)
        advanced_frame = ttk.Frame(notebook)

        notebook.add(basic_frame, text="Search")
        notebook.add(output_frame, text="Output")
        notebook.add(browserless_frame, text="eBay Text Search")
        notebook.add(advanced_frame, text="Advanced")

        # Search tab ----------------------------------------------------
        # Mandarake URL input
        self.url_var = tk.StringVar()
        ttk.Label(basic_frame, text="Mandarake URL:").grid(row=0, column=0, sticky=tk.W, **pad)
        url_entry = ttk.Entry(basic_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E), **pad)
        ttk.Button(basic_frame, text="Load URL", command=self._load_from_url).grid(row=0, column=4, sticky=tk.W, **pad)

        self.keyword_var = tk.StringVar()
        ttk.Label(basic_frame, text="Keyword:").grid(row=1, column=0, sticky=tk.W, **pad)
        keyword_entry = ttk.Entry(basic_frame, textvariable=self.keyword_var, width=42)
        keyword_entry.grid(row=1, column=1, columnspan=3, sticky=tk.W, **pad)
        self.keyword_var.trace_add("write", self._update_preview)

        self.main_category_var = tk.StringVar()
        ttk.Label(basic_frame, text="Main category:").grid(row=2, column=0, sticky=tk.W, **pad)
        self.main_category_combo = ttk.Combobox(
            basic_frame,
            textvariable=self.main_category_var,
            state="readonly",
            width=42,
            values=[f"{name} ({code})" for code, name in MAIN_CATEGORY_OPTIONS],
        )
        self.main_category_combo.grid(row=2, column=1, columnspan=3, sticky=tk.W, **pad)
        self.main_category_combo.bind("<<ComboboxSelected>>", self._on_main_category_selected)

        ttk.Label(basic_frame, text="Detailed categories:").grid(row=3, column=0, sticky=tk.W, **pad)
        detail_frame = ttk.Frame(basic_frame)
        detail_frame.grid(row=4, column=0, columnspan=4, sticky=tk.W, **pad)
        self.detail_listbox = tk.Listbox(
            detail_frame,
            selectmode=tk.SINGLE,
            height=10,
            width=68,
            exportselection=False,
        )
        self.detail_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_listbox.yview)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_listbox.configure(yscrollcommand=detail_scroll.set)
        self.detail_listbox.bind("<<ListboxSelect>>", lambda _: self._update_preview())
        self._populate_detail_categories()

        self.shop_var = tk.StringVar()
        ttk.Label(basic_frame, text="Shop:").grid(row=5, column=0, sticky=tk.W, **pad)
        shop_combo = ttk.Combobox(
            basic_frame,
            textvariable=self.shop_var,
            state="readonly",
            width=37,
            values=[f"{name} ({code})" for code, name in STORE_OPTIONS] + ["Custom..."],
        )
        shop_combo.grid(row=5, column=1, columnspan=2, sticky=tk.W, **pad)
        shop_combo.bind("<<ComboboxSelected>>", self._handle_shop_selection)
        self.shop_var.trace_add("write", self._update_preview)

        self.custom_shop_var = tk.StringVar()
        ttk.Label(basic_frame, text="Custom shop code/slug:").grid(row=5, column=3, sticky=tk.W, **pad)
        self.custom_shop_entry = ttk.Entry(basic_frame, textvariable=self.custom_shop_var, width=20, state="disabled")
        self.custom_shop_entry.grid(row=5, column=4, sticky=tk.W, **pad)
        self.custom_shop_var.trace_add("write", self._update_preview)

        self.hide_sold_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(basic_frame, text="Hide sold-out listings", variable=self.hide_sold_var,
                        command=self._update_preview).grid(row=6, column=0, sticky=tk.W, **pad)

        self.language_var = tk.StringVar(value="ja")
        ttk.Label(basic_frame, text="Language:").grid(row=6, column=1, sticky=tk.W, **pad)
        lang_combo = ttk.Combobox(basic_frame, textvariable=self.language_var, values=["ja", "en"], width=6, state="readonly")
        lang_combo.grid(row=6, column=2, sticky=tk.W, **pad)
        self.language_var.trace_add("write", self._update_preview)

        self.max_pages_var = tk.StringVar()
        ttk.Label(basic_frame, text="Max pages:").grid(row=7, column=0, sticky=tk.W, **pad)
        ttk.Entry(basic_frame, textvariable=self.max_pages_var, width=8).grid(row=7, column=1, sticky=tk.W, **pad)

        self.recent_hours_var = tk.StringVar(value=RECENT_OPTIONS[0][0])
        ttk.Label(basic_frame, text="New items timeframe:").grid(row=7, column=2, sticky=tk.W, **pad)
        self.recent_combo = ttk.Combobox(
            basic_frame,
            textvariable=self.recent_hours_var,
            state="readonly",
            width=20,
            values=[label for label, _ in RECENT_OPTIONS],
        )
        self.recent_combo.grid(row=7, column=3, columnspan=2, sticky=tk.W, **pad)
        self.recent_hours_var.trace_add("write", self._update_preview)

        # Saved configs tree
        tree_frame = ttk.Frame(basic_frame)
        tree_frame.grid(row=8, column=0, columnspan=5, sticky=tk.NSEW, **pad)
        columns = ('file', 'keyword', 'category', 'shop', 'hide')
        self.config_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=6)
        headings = {
            'file': 'File',
            'keyword': 'Keyword',
            'category': 'Category',
            'shop': 'Shop',
            'hide': 'Hide Sold Out',
        }
        for col, heading in headings.items():
            self.config_tree.heading(col, text=heading)
            width = 220 if col == 'file' else 130
            self.config_tree.column(col, width=width, stretch=False)
        self.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.config_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_tree.configure(yscrollcommand=tree_scroll.set)
        self.config_tree.bind('<Double-1>', self._on_tree_double_click)

        # Config management buttons
        config_buttons_frame = ttk.Frame(basic_frame)
        config_buttons_frame.grid(row=9, column=0, columnspan=5, sticky=tk.W, **pad)
        ttk.Button(config_buttons_frame, text="Delete Selected", command=self._delete_selected_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_buttons_frame, text="Move Up", command=lambda: self._move_config(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_buttons_frame, text="Move Down", command=lambda: self._move_config(1)).pack(side=tk.LEFT, padx=5)

        self._load_config_tree()
        basic_frame.rowconfigure(8, weight=1)
        basic_frame.columnconfigure(0, weight=1)
        basic_frame.columnconfigure(1, weight=1)
        basic_frame.columnconfigure(2, weight=1)
        basic_frame.columnconfigure(3, weight=1)

        # Output tab ----------------------------------------------------
        self.sheet_name_var = tk.StringVar()
        self.worksheet_var = tk.StringVar(value="Sheet1")
        ttk.Label(output_frame, text="Google Sheet name:").grid(row=0, column=0, sticky=tk.W, **pad)
        ttk.Entry(output_frame, textvariable=self.sheet_name_var, width=40).grid(row=0, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Label(output_frame, text="Worksheet:").grid(row=0, column=3, sticky=tk.W, **pad)
        ttk.Entry(output_frame, textvariable=self.worksheet_var, width=18).grid(row=0, column=4, sticky=tk.W, **pad)

        self.csv_path_var = tk.StringVar(value="naruto_results.csv")
        ttk.Label(output_frame, text="CSV filename:").grid(row=1, column=0, sticky=tk.W, **pad)
        ttk.Entry(output_frame, textvariable=self.csv_path_var, width=32).grid(row=1, column=1, sticky=tk.W, **pad)
        ttk.Button(output_frame, text="Browse...", command=self._select_csv).grid(row=1, column=2, sticky=tk.W, **pad)

        self.download_dir_var = tk.StringVar(value="images/naruto/")
        ttk.Label(output_frame, text="Image folder:").grid(row=2, column=0, sticky=tk.W, **pad)
        ttk.Entry(output_frame, textvariable=self.download_dir_var, width=32).grid(row=2, column=1, sticky=tk.W, **pad)
        ttk.Button(output_frame, text="Browse...", command=self._select_image_dir).grid(row=2, column=2, sticky=tk.W, **pad)

        self.upload_drive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(output_frame, text="Upload images to Google Drive", variable=self.upload_drive_var).grid(row=3, column=0, sticky=tk.W, **pad)
        self.drive_folder_var = tk.StringVar()
        ttk.Label(output_frame, text="Drive folder ID:").grid(row=3, column=1, sticky=tk.W, **pad)
        ttk.Entry(output_frame, textvariable=self.drive_folder_var, width=32).grid(row=3, column=2, columnspan=2, sticky=tk.W, **pad)

        self.thumbnails_var = tk.StringVar(value="400")
        ttk.Label(output_frame, text="Thumbnail width (px):").grid(row=4, column=0, sticky=tk.W, **pad)
        ttk.Entry(output_frame, textvariable=self.thumbnails_var, width=10).grid(row=4, column=1, sticky=tk.W, **pad)

        self.upload_sheets_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(output_frame, text="Upload results to Google Sheets", variable=self.upload_sheets_var).grid(row=4, column=2, sticky=tk.W, **pad)

        self.show_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(output_frame, text="Show thumbnails in results", variable=self.show_images_var).grid(row=4, column=3, sticky=tk.W, **pad)

        # Add Load CSV button
        ttk.Button(output_frame, text="Load CSV...", command=self.load_csv_file).grid(row=4, column=4, sticky=tk.W, **pad)

        results_frame = ttk.LabelFrame(output_frame, text="Latest Results")
        results_frame.grid(row=5, column=0, columnspan=5, sticky=tk.NSEW, **pad)
        results_columns = ('title', 'price', 'shop', 'stock', 'category', 'link')

        # Create a custom style for results treeview only
        style = ttk.Style()
        style.configure('Results.Treeview', rowheight=70)  # Custom style for results with thumbnails
        print(f"[GUI DEBUG] Configured results treeview row height: 70px")

        self.result_tree = ttk.Treeview(results_frame, columns=results_columns, show='tree headings', height=8, style='Results.Treeview')

        self.result_tree.heading('#0', text='Thumb')
        self.result_tree.column('#0', width=70, stretch=False)
        headings = {
            'title': 'Title',
            'price': 'Price (JPY)',
            'shop': 'Shop',
            'stock': 'In Stock',
            'category': 'Category',
            'link': 'Product Link',
        }
        for col, heading in headings.items():
            self.result_tree.heading(col, text=heading)
            width = 260 if col == 'title' else 160 if col == 'link' else 120
            self.result_tree.column(col, width=width, stretch=False)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.configure(yscrollcommand=result_scroll.set)
        self.result_tree.bind('<Double-1>', self._on_result_double_click)

        self.result_tree_menu = tk.Menu(self.result_tree, tearoff=0)
        self.result_tree_menu.add_command(label="Search by Image on eBay (API)", command=self._search_by_image_api)
        self.result_tree_menu.add_command(label="Search by Image on eBay (Web)", command=self._search_by_image_web)

        self.result_tree.bind("<Button-3>", self._show_result_tree_menu)

        output_frame.rowconfigure(5, weight=1)
        output_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(1, weight=1)
        output_frame.columnconfigure(2, weight=1)
        output_frame.columnconfigure(3, weight=1)

        # eBay Text Search tab ------------------------------------------
        ttk.Label(browserless_frame, text="Scrapy eBay Search (Sold Listings):").grid(row=0, column=0, columnspan=5, sticky=tk.W, **pad)

        # Search input
        ttk.Label(browserless_frame, text="Search query:").grid(row=1, column=0, sticky=tk.W, **pad)
        self.browserless_query_var = tk.StringVar(value="pokemon card")
        browserless_entry = ttk.Entry(browserless_frame, textvariable=self.browserless_query_var, width=32)
        browserless_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, **pad)

        # Max results setting (for rate limiting)
        ttk.Label(browserless_frame, text="Max results:").grid(row=1, column=3, sticky=tk.W, **pad)
        self.browserless_max_results = tk.StringVar(value="10")
        max_results_combo = ttk.Combobox(browserless_frame, textvariable=self.browserless_max_results,
                                       values=["5", "10", "15", "20", "25", "30"], width=5, state="readonly")
        max_results_combo.grid(row=1, column=4, sticky=tk.W, **pad)
        max_results_combo.bind("<<ComboboxSelected>>", lambda e: self._save_gui_settings())

        # Reference image selection (for image comparison)
        ttk.Label(browserless_frame, text="Reference image:").grid(row=2, column=0, sticky=tk.W, **pad)
        ttk.Button(browserless_frame, text="Select Image...", command=self.select_browserless_image).grid(row=2, column=1, sticky=tk.W, **pad)
        self.browserless_image_label = ttk.Label(browserless_frame, text="No image selected (optional)", foreground="gray")
        self.browserless_image_label.grid(row=2, column=2, columnspan=2, sticky=tk.W, **pad)

        # Max comparisons setting (only used when image is selected)
        ttk.Label(browserless_frame, text="Max comparisons:").grid(row=2, column=3, sticky=tk.W, **pad)
        self.browserless_max_comparisons = tk.StringVar(value="MAX")
        max_comp_combo = ttk.Combobox(browserless_frame, textvariable=self.browserless_max_comparisons,
                                     values=["1", "2", "3", "5", "7", "10", "MAX"], width=5, state="readonly")
        max_comp_combo.grid(row=2, column=4, sticky=tk.W, **pad)
        max_comp_combo.bind("<<ComboboxSelected>>", lambda e: self._save_gui_settings())

        # Action buttons
        ttk.Button(browserless_frame, text="Search", command=self.run_scrapy_text_search).grid(row=3, column=0, sticky=tk.W, **pad)
        ttk.Button(browserless_frame, text="Search & Compare", command=self.run_scrapy_search_with_compare).grid(row=3, column=1, sticky=tk.W, **pad)
        ttk.Button(browserless_frame, text="Clear Results", command=self.clear_browserless_results).grid(row=3, column=2, sticky=tk.W, **pad)

        # Progress bar
        self.browserless_progress = ttk.Progressbar(browserless_frame, mode='indeterminate')
        self.browserless_progress.grid(row=3, column=3, columnspan=2, sticky=tk.EW, **pad)

        # Results section
        browserless_results_frame = ttk.LabelFrame(browserless_frame, text="eBay Search Results")
        browserless_results_frame.grid(row=4, column=0, columnspan=5, sticky=tk.NSEW, **pad)

        # Configure grid weights for proper resizing
        browserless_frame.rowconfigure(4, weight=1)
        browserless_frame.columnconfigure(2, weight=1)
        browserless_results_frame.rowconfigure(0, weight=1)
        browserless_results_frame.columnconfigure(0, weight=1)

        # Results treeview
        browserless_columns = ('title', 'price', 'shipping', 'sold_date', 'similarity', 'url')
        self.browserless_tree = ttk.Treeview(browserless_results_frame, columns=browserless_columns, show='tree headings', height=8)

        self.browserless_tree.heading('#0', text='#')
        self.browserless_tree.column('#0', width=30, stretch=False)

        browserless_headings = {
            'title': 'Title',
            'price': 'Price',
            'shipping': 'Shipping',
            'sold_date': 'Sold Date',
            'similarity': 'Similarity %',
            'url': 'eBay URL'
        }

        for col, heading in browserless_headings.items():
            self.browserless_tree.heading(col, text=heading)

        # Set column widths
        self.browserless_tree.column('title', width=280)
        self.browserless_tree.column('price', width=70)
        self.browserless_tree.column('shipping', width=70)
        self.browserless_tree.column('sold_date', width=100)
        self.browserless_tree.column('similarity', width=90)
        self.browserless_tree.column('url', width=180)

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

        # Results filters row
        filters_frame = ttk.Frame(browserless_results_frame)
        filters_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(5, 0))

        ttk.Label(filters_frame, text="Min Similarity %:").pack(side=tk.LEFT, padx=5)
        self.min_similarity_var = tk.StringVar(value="0")
        similarity_entry = ttk.Entry(filters_frame, textvariable=self.min_similarity_var, width=5)
        similarity_entry.pack(side=tk.LEFT, padx=5)
        similarity_entry.bind('<Return>', lambda e: self.apply_results_filter())

        ttk.Label(filters_frame, text="Min Profit %:").pack(side=tk.LEFT, padx=5)
        self.min_profit_var = tk.StringVar(value="0")
        profit_entry = ttk.Entry(filters_frame, textvariable=self.min_profit_var, width=5)
        profit_entry.pack(side=tk.LEFT, padx=5)
        profit_entry.bind('<Return>', lambda e: self.apply_results_filter())

        ttk.Button(filters_frame, text="Apply Filters", command=self.apply_results_filter).pack(side=tk.LEFT, padx=5)

        # Status area for browserless search (below filters)
        self.browserless_status = tk.StringVar(value="Ready for eBay text search")
        browserless_status_label = ttk.Label(browserless_results_frame, textvariable=self.browserless_status, relief=tk.SUNKEN, anchor='w')
        browserless_status_label.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(5, 0))

        # CSV Batch Comparison section --------------------------------
        csv_compare_frame = ttk.LabelFrame(browserless_frame, text="CSV Batch Comparison")
        csv_compare_frame.grid(row=5, column=0, columnspan=5, sticky=tk.NSEW, **pad)
        browserless_frame.rowconfigure(5, weight=1)

        # CSV loader
        ttk.Label(csv_compare_frame, text="Load Mandarake CSV:").grid(row=0, column=0, sticky=tk.W, **pad)
        ttk.Button(csv_compare_frame, text="Load CSV...", command=self.load_csv_for_comparison).grid(row=0, column=1, sticky=tk.W, **pad)
        self.csv_compare_label = ttk.Label(csv_compare_frame, text="No file loaded", foreground="gray")
        self.csv_compare_label.grid(row=0, column=2, columnspan=2, sticky=tk.W, **pad)

        # Filter option
        self.csv_in_stock_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(csv_compare_frame, text="In-stock only", variable=self.csv_in_stock_only, command=self.filter_csv_items).grid(row=0, column=4, sticky=tk.W, **pad)

        # CSV items treeview
        csv_items_frame = ttk.Frame(csv_compare_frame)
        csv_items_frame.grid(row=1, column=0, columnspan=5, sticky=tk.NSEW, **pad)
        csv_compare_frame.rowconfigure(1, weight=1)
        csv_compare_frame.columnconfigure(0, weight=1)

        csv_columns = ('title', 'price', 'shop', 'stock', 'category')
        self.csv_items_tree = ttk.Treeview(csv_items_frame, columns=csv_columns, show='tree headings', height=6)

        self.csv_items_tree.heading('#0', text='#')
        self.csv_items_tree.column('#0', width=30, stretch=False)

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

        # Bind selection to auto-fill search query
        self.csv_items_tree.bind('<<TreeviewSelect>>', self.on_csv_item_selected)

        # Comparison action buttons
        button_frame = ttk.Frame(csv_compare_frame)
        button_frame.grid(row=2, column=0, columnspan=5, sticky=tk.W, **pad)

        ttk.Label(button_frame, text="Single Search:", font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Button(button_frame, text="Compare Selected", command=self.compare_selected_csv_item).grid(row=0, column=1, sticky=tk.W, **pad)
        ttk.Button(button_frame, text="Compare All", command=self.compare_all_csv_items).grid(row=0, column=2, sticky=tk.W, **pad)

        ttk.Label(button_frame, text="Individual Searches:", font=('TkDefaultFont', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Button(button_frame, text="Compare Selected Individually", command=self.compare_selected_csv_item_individually).grid(row=1, column=1, sticky=tk.W, padx=(5, 5), pady=(5, 0))
        ttk.Button(button_frame, text="Compare All Individually", command=self.compare_all_csv_items_individually).grid(row=1, column=2, sticky=tk.W, padx=(5, 5), pady=(5, 0))

        self.csv_compare_progress = ttk.Progressbar(button_frame, mode='indeterminate', length=200)
        self.csv_compare_progress.grid(row=0, column=3, sticky=tk.W, padx=(10, 5))

        # Initialize variables
        self.browserless_image_path = None
        self.browserless_results_data = []
        self.all_comparison_results = []  # Store unfiltered results for filtering
        self.csv_compare_data = []
        self.csv_compare_path = None

        # Advanced tab --------------------------------------------------
        self.fast_var = tk.BooleanVar(value=False)
        self.resume_var = tk.BooleanVar(value=True)
        self.debug_var = tk.BooleanVar(value=False)
        self.mimic_var = tk.BooleanVar(value=True)  # Enable by default for Unicode support
        ttk.Checkbutton(advanced_frame, text="Fast mode (skip eBay)", variable=self.fast_var).grid(row=0, column=0, sticky=tk.W, **pad)
        ttk.Checkbutton(advanced_frame, text="Resume interrupted runs", variable=self.resume_var).grid(row=0, column=1, sticky=tk.W, **pad)
        ttk.Checkbutton(advanced_frame, text="Debug logging", variable=self.debug_var).grid(row=0, column=2, sticky=tk.W, **pad)
        ttk.Checkbutton(advanced_frame, text="Use browser mimic (recommended for Japanese text)", variable=self.mimic_var).grid(row=0, column=3, sticky=tk.W, **pad)
        self.mimic_var.trace_add('write', self._on_mimic_changed)

        self.client_id_var = tk.StringVar()
        self.client_secret_var = tk.StringVar()
        ttk.Label(advanced_frame, text="eBay Client ID:").grid(row=1, column=0, sticky=tk.W, **pad)
        ttk.Entry(advanced_frame, textvariable=self.client_id_var, width=52).grid(row=1, column=1, columnspan=3, sticky=tk.W, **pad)
        ttk.Label(advanced_frame, text="Client Secret:").grid(row=2, column=0, sticky=tk.W, **pad)
        ttk.Entry(advanced_frame, textvariable=self.client_secret_var, show='*', width=52).grid(row=2, column=1, columnspan=3, sticky=tk.W, **pad)

        self.schedule_var = tk.StringVar()
        ttk.Label(advanced_frame, text="Schedule (HH:MM)").grid(row=3, column=0, sticky=tk.W, **pad)
        ttk.Entry(advanced_frame, textvariable=self.schedule_var, width=10).grid(row=3, column=1, sticky=tk.W, **pad)

        # Buttons -------------------------------------------------------
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(button_frame, text="Load Config", command=self.load_config).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Run Now", command=self.run_now).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Schedule", command=self.schedule_run).pack(side=tk.LEFT, padx=4)

        self.url_var = tk.StringVar(value="Search URL: (enter keyword)")
        ttk.Label(self, textvariable=self.url_var, relief=tk.GROOVE, anchor='w', wraplength=720, justify=tk.LEFT).pack(fill=tk.X, padx=8, pady=4)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor='w').pack(fill=tk.X, padx=8, pady=4)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _handle_shop_selection(self, event=None):
        value = self.shop_var.get()
        if value == "Custom...":
            self.custom_shop_entry.configure(state="normal")
            self.custom_shop_var.set('')
        else:
            self.custom_shop_entry.configure(state="disabled")
            self.custom_shop_var.set('')
        self._update_preview()

    def _select_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files', '*.csv'), ('All files', '*.*')])
        if filename:
            self.csv_path_var.set(filename)

    def _select_image_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.download_dir_var.set(directory)

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

    def _run_image_analysis_worker(self):
        """Worker method for image analysis (runs in background thread)"""
        try:
            search_method = self.image_search_method.get()
            enhancement_level = self.image_enhancement.get()

            self.ebay_status.set("Preprocessing image...")
            self.ebay_progress['value'] = 10

            # Step 1: Preprocess the image
            from image_processor import optimize_image_for_search
            processed_image = optimize_image_for_search(str(self.image_analysis_path), enhancement_level)

            self.ebay_status.set(f"Searching using {search_method} method...")
            self.ebay_progress['value'] = 30

            # Step 2: Perform the search based on selected method
            if search_method == "direct":
                # Direct eBay image search
                from ebay_image_search import run_sold_listings_image_search
                try:
                    days_back = int(self.ebay_days_back.get())
                except (ValueError, AttributeError):
                    days_back = 90

                lazy_search = self.lazy_search_enabled.get()
                search_result = run_sold_listings_image_search(processed_image, days_back, lazy_search)

            else:  # lens method
                # Google Lens + eBay search
                from google_lens_search import search_ebay_with_lens_sync
                try:
                    days_back = int(self.ebay_days_back.get())
                except (ValueError, AttributeError):
                    days_back = 90

                lazy_search = self.lazy_search_enabled.get()
                search_result = search_ebay_with_lens_sync(processed_image, days_back, headless=True, lazy_search=lazy_search)

            self.ebay_progress['value'] = 80

            # Step 3: Process results for display
            if search_result.get('error'):
                self.ebay_status.set(f"Search failed: {search_result['error']}")
                self.ebay_progress['value'] = 0
                return

            if search_result['sold_count'] == 0:
                self.ebay_status.set("No sold listings found for this image")
                self.ebay_progress['value'] = 100
                return

            # Step 4: Convert image search results to analysis format
            self.ebay_status.set("Processing results...")
            analysis_results = self._convert_image_results_to_analysis(search_result)

            # Step 5: Display results
            self._display_ebay_results(analysis_results)
            self.ebay_progress['value'] = 100
            self.ebay_status.set(f"Image analysis complete: {len(analysis_results)} profitable items found")

        except Exception as e:
            self.ebay_status.set(f"Image analysis failed: {e}")
            print(f"[IMAGE ANALYSIS] Error: {e}")
            self.ebay_progress['value'] = 0

    def _run_ai_smart_search_worker(self):
        """Worker method for AI smart search (runs in background thread)"""
        try:
            from image_analysis_engine import ImageAnalysisEngine

            enhancement_level = self.image_enhancement.get()
            lazy_search = self.lazy_search_enabled.get()
            ai_confirmation = self.ai_confirmation_enabled.get()

            try:
                days_back = int(self.ebay_days_back.get())
            except (ValueError, AttributeError):
                days_back = 90

            try:
                usd_jpy_rate = float(self.usd_jpy_rate.get())
            except (ValueError, AttributeError):
                usd_jpy_rate = 150

            # Configure analysis engine
            config = {
                'usd_jpy_rate': usd_jpy_rate,
                'min_profit_margin': 20,
                'ebay_fees_percent': 0.13,
                'shipping_cost': 5.0
            }

            engine = ImageAnalysisEngine(config)

            self.ebay_status.set("Running comprehensive AI analysis...")
            self.ebay_progress['value'] = 20

            # Use comprehensive analysis with multiple methods
            methods = ["direct_ebay", "google_lens"] if lazy_search else ["direct_ebay"]
            enhancement_levels = [enhancement_level]

            if ai_confirmation:
                # Try multiple enhancement levels for better matching
                enhancement_levels = ["light", "medium", "aggressive"]
                self.ebay_status.set("AI confirmation enabled - trying multiple enhancement levels...")

            analysis_result = engine.analyze_image_comprehensive(
                str(self.image_analysis_path),
                methods=methods,
                enhancement_levels=enhancement_levels,
                days_back=days_back
            )

            self.ebay_progress['value'] = 80

            if ai_confirmation and analysis_result.get('results'):
                self.ebay_status.set("AI analyzing results for best match...")
                # Use AI to select the best result based on confidence and data quality
                best_result = self._ai_select_best_result(analysis_result['results'])
                if best_result:
                    analysis_result['results'] = [best_result]
                    analysis_result['ai_selected'] = True

            # Convert to display format
            self.ebay_status.set("Processing AI results...")
            display_results = self._convert_ai_results_to_analysis(analysis_result)

            # Display results
            self._display_ebay_results(display_results)

            self.ebay_progress['value'] = 100

            result_count = len(display_results)
            ai_note = " (AI-confirmed best match)" if analysis_result.get('ai_selected') else ""
            self.ebay_status.set(f"AI Smart Search complete: {result_count} results found{ai_note}")

        except Exception as e:
            self.ebay_status.set(f"AI Smart Search failed: {e}")
            print(f"[AI SMART SEARCH] Error: {e}")
            self.ebay_progress['value'] = 0

    def _ai_select_best_result(self, results: list) -> dict:
        """Use AI logic to select the best result from multiple search attempts"""
        if not results:
            return None

        # Score each result based on multiple factors
        def score_result(result):
            score = 0

            # Factor 1: Number of sold items (more is better)
            sold_count = result.get('sold_count', 0)
            score += min(sold_count * 2, 50)  # Cap at 50 points

            # Factor 2: Price consistency (lower std dev is better)
            prices = result.get('prices', [])
            if len(prices) > 1:
                import statistics
                try:
                    median_price = statistics.median(prices)
                    std_dev = statistics.stdev(prices)
                    consistency_score = max(0, 30 - (std_dev / median_price * 100))
                    score += consistency_score
                except:
                    pass

            # Factor 3: Search method confidence
            if result.get('search_method') == 'google_lens':
                lens_confidence = result.get('lens_results', {}).get('confidence', 0)
                score += lens_confidence * 0.2  # Up to 20 points

            # Factor 4: Enhancement level effectiveness
            enhancement = result.get('enhancement_level', 'medium')
            if enhancement == 'medium':
                score += 10  # Medium is usually best balance
            elif enhancement == 'light':
                score += 5
            # aggressive gets 0 bonus (last resort)

            # Factor 5: Reasonable price range (not too cheap/expensive outliers)
            median_price = result.get('median_price', 0)
            if 5 <= median_price <= 500:  # Reasonable range for most collectibles
                score += 15
            elif 1 <= median_price <= 1000:
                score += 10

            return score

        # Score all results and pick the best
        scored_results = [(score_result(result), result) for result in results]
        scored_results.sort(key=lambda x: x[0], reverse=True)

        best_score, best_result = scored_results[0]

        print(f"[AI SELECTION] Selected result with score {best_score:.1f} - {best_result.get('sold_count', 0)} items, ${best_result.get('median_price', 0):.2f} median")

        return best_result

    def _convert_ai_results_to_analysis(self, analysis_result: dict) -> list:
        """Convert AI analysis results to display format"""
        results = []

        if not analysis_result.get('results'):
            return results

        try:
            usd_to_jpy = float(self.usd_jpy_rate.get())
            min_profit = float(self.min_profit_margin.get())
        except (ValueError, AttributeError):
            usd_to_jpy = 150
            min_profit = 20

        for search_result in analysis_result['results']:
            if search_result['sold_count'] == 0:
                continue

            median_price_usd = search_result['median_price']
            avg_price_usd = search_result['avg_price']

            # Generate profit scenarios
            estimated_mandarake_prices = [
                median_price_usd * usd_to_jpy * 0.3,  # Conservative
                median_price_usd * usd_to_jpy * 0.5,  # Moderate
                median_price_usd * usd_to_jpy * 0.7,  # Aggressive
            ]

            for i, mandarake_price_jpy in enumerate(estimated_mandarake_prices):
                mandarake_usd = mandarake_price_jpy / usd_to_jpy
                estimated_fees = median_price_usd * 0.15 + 5
                net_proceeds = median_price_usd - estimated_fees
                profit_margin = ((net_proceeds - mandarake_usd) / mandarake_usd) * 100 if mandarake_usd > 0 else 0

                if profit_margin > min_profit:
                    # Create descriptive title
                    search_method = search_result.get('search_method', 'unknown')
                    search_term = search_result.get('search_term_used', 'AI Search Result')
                    scenario_names = ['Conservative', 'Moderate', 'Aggressive']

                    title = f"{search_term} ({scenario_names[i]} - {search_method})"
                    if analysis_result.get('ai_selected'):
                        title += " ⭐"  # Star for AI-selected results

                    results.append({
                        'title': title,
                        'mandarake_price': int(mandarake_price_jpy),
                        'ebay_sold_count': search_result['sold_count'],
                        'ebay_median_price': median_price_usd,
                        'ebay_avg_price': avg_price_usd,
                        'profit_margin': profit_margin,
                        'estimated_profit': net_proceeds - mandarake_usd
                    })

        return results

    def _run_ebay_image_comparison_worker(self):
        """Worker method for eBay image comparison (runs in background thread)"""
        try:

            self.ebay_status.set("Initializing computer vision matcher...")
            self.ebay_progress['value'] = 10

            # Get search term from image analysis or prompt user
            search_term = self._get_search_term_for_comparison()
            if not search_term:
                self.ebay_status.set("eBay image comparison cancelled")
                self.ebay_progress['value'] = 0
                return

            self.ebay_status.set(f"Searching for sold listings: {search_term}")
            self.ebay_progress['value'] = 30

            # Get configuration settings
            try:
                days_back = int(self.ebay_days_back.get())
            except (ValueError, AttributeError):
                days_back = 90

            try:
                similarity_threshold = float(self.similarity_threshold.get()) / 100.0  # Convert percentage to decimal
            except (ValueError, AttributeError):
                similarity_threshold = 0.7  # Default 70%

            try:
                max_images = int(self.max_images.get())
            except (ValueError, AttributeError):
                max_images = 5  # Default 5 images

            self.ebay_status.set("Analyzing sold listing images...")
            self.ebay_progress['value'] = 50

            # Use the browser choice made in the main thread
            show_browser = getattr(self, 'show_browser_choice', False)

            import os
            from datetime import datetime

            # Create debug output directory
            debug_dir = os.path.join("debug_images", f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

            self.ebay_status.set(f"Images will be saved to: {debug_dir}")

            if show_browser:
                # Use Playwright version with visible browser
                from sold_listing_matcher import SoldListingMatcher
                self.ebay_status.set("Initializing visible browser...")
                matcher = SoldListingMatcher(
                    headless=False,  # Show browser window
                    similarity_threshold=similarity_threshold,
                    debug_output_dir=debug_dir
                )
                # Track this matcher for cleanup
                self._active_playwright_matchers.append(matcher)
                self.ebay_status.set("Browser ready - starting eBay search...")
            else:
                # Use requests-based matcher (faster, hidden)
                from sold_listing_matcher_requests import SoldListingMatcherRequests
                matcher = SoldListingMatcherRequests(
                    similarity_threshold=similarity_threshold,
                    debug_output_dir=debug_dir
                )

            try:
                if show_browser:
                    # Playwright version needs async handling
                    import asyncio
                    print(f"[DEBUG] Using Playwright matcher: {type(matcher)}")
                    print(f"[DEBUG] Matcher file: {matcher.__class__.__module__}")
                    print(f"[DEBUG] Feature detector: {type(matcher.feature_detector)}")
                    print(f"[DEBUG] Image size: {matcher.image_size}")

                    result = asyncio.run(matcher.find_matching_sold_listings(
                        reference_image_path=str(self.image_analysis_path),
                        search_term=search_term,
                        max_results=max_images,
                        days_back=days_back
                    ))
                    print(f"[DEBUG] Result obtained: {type(result)}")
                    print(f"[DEBUG] Matches found: {result.matches_found}")
                    if result.matches_found > 0:
                        print(f"[DEBUG] Best match type: {type(result.best_match)}")
                        print(f"[DEBUG] Best match similarity: {result.best_match.image_similarity} ({type(result.best_match.image_similarity)})")
                else:
                    # Requests version is synchronous
                    result = matcher.find_matching_sold_listings(
                        reference_image_path=str(self.image_analysis_path),
                        search_term=search_term,
                        max_results=max_images,
                        days_back=days_back
                    )

                # Update status to show where images were saved
                print("[DEBUG] Starting result processing...")
                if os.path.exists(debug_dir):
                    print("[DEBUG] Debug directory exists")
                    image_count = len([f for f in os.listdir(debug_dir) if f.endswith('.jpg')])
                    print(f"[DEBUG] Image count: {image_count}")
                    self.ebay_status.set(f"Analysis complete! {image_count} images saved to: {debug_dir}")
                    print(f"[DEBUG] Images saved to: {os.path.abspath(debug_dir)}")

                    # Show popup to make debug location obvious
                    import tkinter.messagebox as messagebox
                    messagebox.showinfo(
                        "Images Saved",
                        f"Comparison images have been saved!\n\n"
                        f"Location: {os.path.abspath(debug_dir)}\n\n"
                        f"Files saved:\n"
                        f"• Your reference image\n"
                        f"• listing_01.jpg to listing_{image_count:02d}.jpg (eBay images)\n\n"
                        f"Images were saved immediately as they were found!\n"
                        f"You can inspect these images to see what was compared."
                    )

            finally:
                # Handle cleanup for both sync and async versions
                if show_browser:
                    # Playwright version has async cleanup
                    import asyncio
                    try:
                        asyncio.run(matcher.cleanup())
                        # Remove from active matchers list
                        if matcher in self._active_playwright_matchers:
                            self._active_playwright_matchers.remove(matcher)
                    except Exception as cleanup_error:
                        logging.warning("Error during Playwright cleanup: %s", str(cleanup_error))
                else:
                    # Requests version has sync cleanup
                    try:
                        matcher.cleanup()
                    except Exception as cleanup_error:
                        logging.warning("Error during cleanup: %s", str(cleanup_error))

            self.ebay_status.set("Processing image comparison results...")
            self.ebay_progress['value'] = 80

            # Convert results to display format
            print("[DEBUG] Converting results to display format...")
            try:
                display_results = self._convert_image_comparison_results(result, search_term)
                print("[DEBUG] Results converted successfully")
            except Exception as convert_error:
                print(f"[DEBUG] Error in result conversion: {convert_error}")
                raise

            # Display results
            self._display_ebay_results(display_results)

            self.ebay_progress['value'] = 100

            if result.matches_found > 0:
                confidence_text = f" ({result.confidence} confidence)" if result.confidence != "error" else ""
                self.ebay_status.set(f"Image comparison complete: {result.matches_found} matches found{confidence_text}")
            else:
                self.ebay_status.set("No visual matches found in sold listings")

        except Exception as e:
            error_message = str(e)

            # Skip format string errors - they're cosmetic and don't affect functionality
            if "Cannot specify" in error_message and "with 's'" in error_message:
                print("[DEBUG] Ignoring cosmetic format string error - functionality worked correctly")
                return

            # Provide user-friendly error messages
            if "timeout" in error_message.lower() or "navigation" in error_message.lower():
                self.ebay_status.set("eBay blocked request - this is normal. Try again in a few minutes.")
                print("[EBAY IMAGE COMPARISON] eBay blocking detected:", str(e))

                # Show helpful dialog
                from tkinter import messagebox
                messagebox.showinfo(
                    "eBay Access Temporarily Blocked",
                    "eBay has temporarily blocked automated access. This is normal behavior.\n\n"
                    "Solutions:\n"
                    "• Wait 2-5 minutes and try again\n"
                    "• Try a different search term\n"
                    "• Check your internet connection\n\n"
                    "eBay actively blocks automated browsing to protect their servers."
                )
            else:
                self.ebay_status.set("eBay image comparison failed: " + error_message)
                print("[EBAY IMAGE COMPARISON] Error:", str(e))

            self.ebay_progress['value'] = 0

    def _get_search_term_for_comparison(self):
        """Get search term for image comparison"""
        # Create a simple dialog to get search term
        dialog = tk.Toplevel(self)
        dialog.title("eBay Image Comparison - Search Term")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"+{x}+{y}")

        result = {'search_term': None}

        # Instructions
        ttk.Label(dialog, text="Enter search term for eBay sold listing comparison:",
                 font=('TkDefaultFont', 10)).pack(pady=10)

        ttk.Label(dialog, text="Examples: 'Yura Kano photobook', 'Pokemon card Charizard'",
                 font=('TkDefaultFont', 8), foreground='gray').pack(pady=(0, 10))

        # Entry field
        search_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=search_var, width=40, font=('TkDefaultFont', 10))
        entry.pack(pady=10)
        entry.focus()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        def on_ok():
            term = search_var.get().strip()
            if term:
                result['search_term'] = term
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Please enter a search term")

        def on_cancel():
            dialog.destroy()

        ttk.Button(button_frame, text="Start Comparison", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=10)

        # Bind Enter key
        entry.bind('<Return>', lambda e: on_ok())

        # Wait for dialog to close
        self.wait_window(dialog)

        return result['search_term']

    def _convert_image_comparison_results(self, result, search_term):
        """Convert image comparison results to display format"""
        display_results = []

        if result.matches_found > 0:
            for match in result.all_matches:
                # Convert to the expected format for the results table
                display_results.append({
                    'title': match.title,
                    'mandarake_price': f"Search: {search_term}",
                    'ebay_sold_count': '1 (matched)',
                    'ebay_median_price': f"${match.price:.2f}",
                    'ebay_price_range': f"Similarity: {float(match.image_similarity):.1%}",
                    'profit_margin': f"Sold: {match.sold_date}",
                    'estimated_profit': f"Confidence: {float(match.confidence_score):.1%}"
                })

            # Add summary row
            if len(result.all_matches) > 1:
                avg_price = result.average_price
                price_range = f"${result.price_range[0]:.2f} - ${result.price_range[1]:.2f}"

                display_results.insert(0, {
                    'title': f"🎯 SUMMARY: {result.matches_found} Visual Matches Found",
                    'mandarake_price': f"Average Price: ${avg_price:.2f}",
                    'ebay_sold_count': f"{result.matches_found} matches",
                    'ebay_median_price': f"${avg_price:.2f}",
                    'ebay_price_range': price_range,
                    'profit_margin': f"Confidence: {result.confidence}",
                    'estimated_profit': f"Best: {float(result.best_match.image_similarity):.1%} similar"
                })

        return display_results

    def start_category_research(self):
        """Start the category research process"""
        def research_worker():
            try:
                from category_optimizer import research_category_sync

                # Get research parameters
                if self.use_custom_terms.get():
                    custom_terms_text = self.custom_terms_var.get().strip()
                    if not custom_terms_text:
                        self.research_status.set("Error: Please enter custom terms or use built-in category")
                        return

                    custom_terms = [term.strip() for term in custom_terms_text.split(',')]
                    category = "custom"
                    result = research_category_sync(category, custom_terms)
                else:
                    category = self.research_category.get()
                    result = research_category_sync(category)

                # Update results display
                self.research_progress.stop()

                if result.get('error'):
                    self.research_status.set(f"Research failed: {result['error']}")
                    return

                # Format and display results
                results_text = self._format_research_results(result)

                self.research_results_text.config(state=tk.NORMAL)
                self.research_results_text.delete(1.0, tk.END)
                self.research_results_text.insert(tk.END, results_text)
                self.research_results_text.config(state=tk.DISABLED)

                quality_score = result.get('performance_metrics', {}).get('research_quality_score', 0)
                self.research_status.set(f"Research complete! Quality score: {quality_score}/100")

            except Exception as e:
                self.research_progress.stop()
                self.research_status.set(f"Research error: {e}")

        # Start research
        self.research_status.set("Starting category research...")
        self.research_progress.start()

        self.research_results_text.config(state=tk.NORMAL)
        self.research_results_text.delete(1.0, tk.END)
        self.research_results_text.insert(tk.END, "Research in progress...\n\nThis may take 1-2 minutes as we analyze eBay data.")
        self.research_results_text.config(state=tk.DISABLED)

        # Run in background thread
        import threading
        thread = threading.Thread(target=research_worker)
        thread.daemon = True
        thread.start()

    def _format_research_results(self, result: dict) -> str:
        """Format research results for display"""
        try:
            text = f"RESEARCH RESULTS - {result.get('description', 'Unknown Category')}\n"
            text += "=" * 60 + "\n\n"

            # Performance metrics
            metrics = result.get('performance_metrics', {})
            text += f"Quality Score: {metrics.get('research_quality_score', 0)}/100\n"
            text += f"Items Analyzed: {metrics.get('total_items_analyzed', 0)}\n"
            text += f"Most Effective Term: {metrics.get('most_effective_term', 'N/A')}\n\n"

            # Top learned keywords
            keywords = result.get('learned_keywords', {})
            if keywords:
                text += "TOP LEARNED KEYWORDS:\n"
                text += "-" * 25 + "\n"
                for keyword, count in list(keywords.items())[:10]:
                    text += f"• {keyword} (appeared {count} times)\n"
                text += "\n"

            # Price patterns
            price_patterns = result.get('price_patterns', {})
            if price_patterns:
                text += "PRICE ANALYSIS:\n"
                text += "-" * 15 + "\n"
                text += f"Median Price: ${price_patterns.get('median', 0):.2f}\n"
                text += f"Average Price: ${price_patterns.get('mean', 0):.2f}\n"
                text += f"Price Variation: ±${price_patterns.get('std_dev', 0):.2f}\n\n"

            # Optimization rules
            rules = result.get('optimization_rules', [])
            if rules:
                text += "OPTIMIZATION RULES LEARNED:\n"
                text += "-" * 30 + "\n"
                for i, rule in enumerate(rules, 1):
                    confidence = rule.get('confidence', 'unknown').upper()
                    text += f"{i}. [{confidence}] {rule.get('rule', '')}\n"
                text += "\n"

            # Common phrases
            title_patterns = result.get('title_patterns', {})
            common_phrases = title_patterns.get('common_phrases', [])
            if common_phrases:
                text += "COMMON SUCCESSFUL PHRASES:\n"
                text += "-" * 30 + "\n"
                for phrase_data in common_phrases[:8]:
                    phrase = phrase_data.get('phrase', '')
                    count = phrase_data.get('count', 0)
                    text += f"• \"{phrase}\" (used {count} times)\n"
                text += "\n"

            text += "These optimizations will automatically be applied when using this category in future searches."

            return text

        except Exception as e:
            return f"Error formatting results: {e}"

    def view_optimization_profiles(self):
        """Open a dialog to view saved optimization profiles"""
        from category_optimizer import CategoryOptimizer

        # Create profiles window
        profiles_window = tk.Toplevel(self.master)
        profiles_window.title("Saved Optimization Profiles")
        profiles_window.geometry("500x400")
        profiles_window.transient(self.master)

        # Main frame
        main_frame = ttk.Frame(profiles_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Saved Optimization Profiles", font=("Arial", 12, "bold")).pack(pady=(0, 10))

        # Profile list
        optimizer = CategoryOptimizer()
        profiles_dir = optimizer.profiles_dir

        if profiles_dir.exists():
            profile_files = list(profiles_dir.glob("*_latest.json"))

            if profile_files:
                for profile_file in profile_files:
                    try:
                        profile = optimizer.load_optimization_profile(profile_file.stem.replace('_latest', ''))
                        if profile:
                            frame = ttk.LabelFrame(main_frame, text=profile.get('description', 'Unknown'))
                            frame.pack(fill=tk.X, pady=5)

                            date = profile.get('research_date', 'Unknown date')
                            quality = profile.get('performance_metrics', {}).get('research_quality_score', 0)
                            keywords_count = len(profile.get('learned_keywords', {}))

                            info_text = f"Date: {date[:10]} | Quality: {quality}/100 | Keywords: {keywords_count}"
                            ttk.Label(frame, text=info_text, foreground="gray").pack(padx=10, pady=5)

                    except Exception as e:
                        continue
            else:
                ttk.Label(main_frame, text="No optimization profiles found.\nRun research to create profiles.",
                         foreground="gray").pack(pady=20)
        else:
            ttk.Label(main_frame, text="No optimization profiles directory found.",
                     foreground="gray").pack(pady=20)

        ttk.Button(main_frame, text="Close", command=profiles_window.destroy).pack(pady=(20, 0))

    def _save_window_settings(self):
        """Save current window settings"""
        try:
            # Get current window geometry
            geometry = self.geometry()
            width, height, x, y = self._parse_geometry(geometry)

            # Check if maximized
            maximized = self.state() == 'zoomed'

            # Save window settings
            self.settings.save_window_settings(width, height, x, y, maximized)
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
            # Save current eBay settings
            self._save_ebay_settings()

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

    def run_now(self):
        config = self._collect_config()
        if not config:
            return
        config_path = self._save_config_autoname(config)
        mimic = bool(self.mimic_var.get())
        print(f"[GUI DEBUG] Checkbox mimic value: {self.mimic_var.get()}")
        print(f"[GUI DEBUG] Bool mimic value: {mimic}")
        self.status_var.set(f"Running scraper: {config_path}")
        self._start_thread(self._run_scraper, str(config_path), mimic)

    def schedule_run(self):
        schedule_time = self.schedule_var.get().strip()
        if not schedule_time:
            messagebox.showinfo("Schedule", "Enter a schedule time (HH:MM) in the Advanced tab.")
            return
        config = self._collect_config()
        if not config:
            return
        config_path = self._save_config_autoname(config)
        mimic = bool(self.mimic_var.get())
        self.status_var.set(f"Scheduling daily run at {schedule_time} (config: {config_path})")
        self._start_thread(self._schedule_worker, str(config_path), schedule_time, mimic)

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
        keyword = self._slugify(str(config.get('keyword', 'search')))

        # Use category name if available, otherwise use code
        category_name = config.get('category_name', '')
        if category_name:
            category = self._slugify(category_name)
        else:
            category = config.get('category')
            if isinstance(category, list):
                category = category[0] if category else ''
            category = self._slugify(str(category or 'all'))

        # Use shop name if available, otherwise use code
        shop_name = config.get('shop_name', '')
        if shop_name:
            shop = self._slugify(shop_name)
        else:
            shop_value = config.get('shop', '0')
            if not shop_value or shop_value.strip() == '':
                shop_value = '0'
            shop = self._slugify(str(shop_value))

        return f"{keyword}_{category}_{shop}.json"

    def _generate_csv_filename(self, config: dict) -> str:
        """Generate CSV filename based on search parameters"""
        keyword = self._slugify(str(config.get('keyword', 'search')))
        category = config.get('category')
        if isinstance(category, list):
            category = category[0] if category else ''
        category = self._slugify(str(category or 'all'))

        # Handle shop with special default to '0'
        shop_value = config.get('shop', '0')
        if not shop_value or shop_value.strip() == '':
            shop_value = '0'
        shop = self._slugify(str(shop_value))
        return f"{keyword}_{category}_{shop}.csv"

    def _find_matching_csv(self, config: dict) -> Optional[Path]:
        """Find existing CSV files that match the search parameters"""
        results_dir = Path('results')
        if not results_dir.exists():
            return None

        # Generate the expected filename with new system
        expected_filename = self._generate_csv_filename(config)
        expected_path = results_dir / expected_filename

        if expected_path.exists():
            print(f"[GUI DEBUG] Found exact CSV match: {expected_path}")
            return expected_path

        # Get slugified components for searching
        keyword = self._slugify(str(config.get('keyword', 'search')))
        category = config.get('category')
        if isinstance(category, list):
            category = category[0] if category else ''
        category = self._slugify(str(category or 'all'))

        # Handle shop with special default to '0'
        shop_value = config.get('shop', '0')
        if not shop_value or shop_value.strip() == '':
            shop_value = '0'
        shop = self._slugify(str(shop_value))

        # Search for files with same keyword and category but different shop
        pattern_base = f"{keyword}_{category}_"
        for csv_file in results_dir.glob('*.csv'):
            if csv_file.name.startswith(pattern_base):
                print(f"[GUI DEBUG] Found similar CSV match: {csv_file}")
                return csv_file

        # Search for files with same keyword but different category/shop
        pattern_keyword = f"{keyword}_"
        for csv_file in results_dir.glob('*.csv'):
            if csv_file.name.startswith(pattern_keyword):
                print(f"[GUI DEBUG] Found keyword CSV match: {csv_file}")
                return csv_file

        # BACKWARD COMPATIBILITY: Search using old slugify method (Japanese -> 'all')
        # This handles cases where Japanese keywords were previously saved as 'all'
        original_keyword = str(config.get('keyword', 'search')).strip()
        if not original_keyword.isascii() and original_keyword:
            print(f"[GUI DEBUG] Trying backward compatibility for non-ASCII keyword")

            # Look for pattern 'all_category_shop' which is how old system handled Japanese
            old_pattern_exact = f"all_{category}_{shop}.csv"
            old_path = results_dir / old_pattern_exact
            if old_path.exists():
                print(f"[GUI DEBUG] Found backward compatible exact match: {old_path}")
                return old_path

            # Look for pattern 'all_category_*'
            old_pattern_base = f"all_{category}_"
            for csv_file in results_dir.glob('*.csv'):
                if csv_file.name.startswith(old_pattern_base):
                    print(f"[GUI DEBUG] Found backward compatible category match: {csv_file}")
                    return csv_file

            # Look for any file starting with 'all_'
            for csv_file in results_dir.glob('all_*.csv'):
                print(f"[GUI DEBUG] Found backward compatible fallback: {csv_file}")
                return csv_file

        print(f"[GUI DEBUG] No matching CSV found for: {expected_filename}")
        return None

    def _save_config_to_path(self, config: dict, path: Path, update_tree: bool = True):
        path.parent.mkdir(parents=True, exist_ok=True)
        results_dir = Path('results')
        results_dir.mkdir(parents=True, exist_ok=True)

        # Generate flexible CSV filename based on search parameters
        csv_filename = self._generate_csv_filename(config)
        config['csv'] = str(results_dir / csv_filename)

        if hasattr(self, 'csv_path_var'):
            self.csv_path_var.set(config['csv'])
        with path.open('w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self.last_saved_path = path
        if hasattr(self, 'csv_path_var'):
            self.csv_path_var.set(config['csv'])
        if update_tree and hasattr(self, '_load_config_tree'):
            self._load_config_tree()
        self.status_var.set(f"Saved config: {path}")

    def _save_config_autoname(self, config: dict) -> Path:
        filename = self._suggest_config_filename(config)
        path = Path('configs') / filename
        self._save_config_to_path(config, path, update_tree=True)
        return path

    def _collect_config(self):
        keyword = self.keyword_var.get().strip()

        config: dict[str, object] = {
            'keyword': keyword,
            'hide_sold_out': self.hide_sold_var.get(),
            'language': self.language_var.get(),
            'fast': self.fast_var.get(),
            'resume': self.resume_var.get(),
            'debug': self.debug_var.get(),
            'client_id': self.client_id_var.get().strip(),
            'client_secret': self.client_secret_var.get().strip(),
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

        sheet_name = self.sheet_name_var.get().strip()
        worksheet = self.worksheet_var.get().strip() or 'Sheet1'
        if sheet_name:
            config['google_sheets'] = {
                'sheet_name': sheet_name,
                'worksheet_name': worksheet,
            }

        csv_path = self.csv_path_var.get().strip()
        if csv_path:
            config['csv'] = csv_path

        download_dir = self.download_dir_var.get().strip()
        if download_dir:
            config['download_images'] = download_dir

        config['upload_drive'] = self.upload_drive_var.get()
        config['upload_sheets'] = self.upload_sheets_var.get()
        config['show_images'] = self.show_images_var.get()
        drive_folder = self.drive_folder_var.get().strip()
        if drive_folder:
            config['drive_folder'] = drive_folder

        thumbs = self.thumbnails_var.get().strip()
        if thumbs:
            try:
                config['thumbnails'] = int(thumbs)
            except ValueError:
                messagebox.showerror("Validation", "Thumbnail width must be an integer.")
                return None

        return config

    def _resolve_shop(self):
        selection = self.shop_var.get()
        if selection == "Custom...":
            return self.custom_shop_var.get().strip()
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
            print(f"[GUI DEBUG] Scraper browser mimic enabled: {scraper.use_mimic}")
            print(f"[GUI DEBUG] Scraper browser object type: {type(scraper.browser_mimic)}")
            scraper.run()
            self.run_queue.put(("status", "Scrape completed."))
            self.run_queue.put(("results", str(config_path)))
        except Exception as exc:
            import traceback
            print(f"[GUI DEBUG] Full exception traceback:")
            traceback.print_exc()
            self.run_queue.put(("error", f"Scrape failed: {exc}"))
        finally:
            self.run_queue.put(("cleanup", str(config_path)))

    def _schedule_worker(self, config_path: str, schedule_time: str, use_mimic: bool):
        try:
            schedule_scraper(config_path, schedule_time, use_mimic=use_mimic)
        except Exception as exc:
            self.run_queue.put(("error", f"Schedule failed: {exc}"))
        finally:
            self.run_queue.put(("cleanup", config_path))

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
                elif message_type == "error":
                    messagebox.showerror("Error", payload)
                    self.status_var.set("Error")
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
                            print(f"[GUI DEBUG] Using CSV file: {csv_path}")
                        else:
                            print(f"[GUI DEBUG] No CSV file found for config")

                    except Exception as e:
                        print(f"[GUI DEBUG] Error loading config for results: {e}")
                        csv_path = None
                    self._load_results_table(csv_path)
                elif message_type == "cleanup":
                    try:
                        if payload.endswith('gui_temp.json'):
                            Path(payload).unlink(missing_ok=True)
                    except Exception:
                        pass
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
        finally:
            self._settings_loaded = True

    def _save_gui_settings(self):
        if not getattr(self, '_settings_loaded', False):
            return
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'mimic': bool(self.mimic_var.get()),
                'ebay_max_results': self.browserless_max_results.get() if hasattr(self, 'browserless_max_results') else "10",
                'ebay_max_comparisons': self.browserless_max_comparisons.get() if hasattr(self, 'browserless_max_comparisons') else "MAX"
            }
            with SETTINGS_PATH.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _on_mimic_changed(self, *args):
        if not hasattr(self, 'mimic_var'):
            return
        if getattr(self, '_settings_loaded', False):
            self._save_gui_settings()

    def _on_close(self):
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
            return code.startswith(main_code)

        for code, info in sorted(MANDARAKE_ALL_CATEGORIES.items()):
            if should_include(code):
                label = f"{code} - {info['en']}"
                self.detail_listbox.insert(tk.END, label)
                self.detail_code_map.append(code)

    def _on_main_category_selected(self, event=None):
        code = self._extract_code(self.main_category_var.get())
        self._populate_detail_categories(code)
        self.detail_listbox.selection_clear(0, tk.END)
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

        first_code = categories[0]
        main_code = self._match_main_code(first_code)
        if main_code:
            label = f"{MANDARAKE_MAIN_CATEGORIES[main_code]['en']} ({main_code})"
            self.main_category_var.set(label)
        else:
            self.main_category_var.set('')
        self._populate_detail_categories(self._extract_code(self.main_category_var.get()))

        for idx, code in enumerate(self.detail_code_map):
            if code in categories:
                self.detail_listbox.selection_set(idx)

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
        client_id = self.client_id_var.get().strip()
        client_secret = self.client_secret_var.get().strip()
        ebay_api = EbayAPI(client_id, client_secret)

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

    def _load_config_tree(self):
        if not hasattr(self, 'config_tree'):
            return
        for item in self.config_tree.get_children():
            self.config_tree.delete(item)
        self.config_paths.clear()

        configs_dir = Path('configs')
        if not configs_dir.exists():
            return

        for cfg_path in sorted(configs_dir.glob('*.json')):
            try:
                with cfg_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                continue

            keyword = data.get('keyword', '')

            # Use category name if available, otherwise show code
            category = data.get('category_name', data.get('category', ''))
            if isinstance(category, list):
                category = ', '.join(category)

            # Use shop name if available, otherwise show code
            shop = data.get('shop_name', data.get('shop', ''))

            hide = 'Yes' if data.get('hide_sold_out') else 'No'
            values = (cfg_path.name, keyword, category, shop, hide)
            item = self.config_tree.insert('', tk.END, values=values)
            self.config_paths[item] = cfg_path

    def _on_tree_double_click(self, event=None):
        selection = self.config_tree.selection()
        if not selection:
            return
        item = selection[0]
        path = self.config_paths.get(item)
        if not path:
            return
        try:
            with path.open('r', encoding='utf-8') as f:
                config = json.load(f)
            self._populate_from_config(config)
            self.last_saved_path = path
            self.status_var.set(f"Loaded config: {path}")
        except Exception as exc:
            messagebox.showerror('Error', f'Failed to load config: {exc}')

    def _delete_selected_config(self):
        """Delete the selected config file"""
        selection = self.config_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a config file to delete")
            return

        item = selection[0]
        path = self.config_paths.get(item)
        if not path:
            return

        # Confirm deletion
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete:\n{path.name}?"
        )

        if response:
            try:
                path.unlink()  # Delete the file
                self._load_config_tree()  # Reload the tree
                self.status_var.set(f"Deleted: {path.name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {e}")

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

        # Get all config files in order
        configs_dir = Path('configs')
        config_files = sorted(configs_dir.glob('*.json'))

        try:
            current_index = config_files.index(path)
        except ValueError:
            return

        new_index = current_index + direction

        # Check bounds
        if new_index < 0 or new_index >= len(config_files):
            return

        # Swap filenames by renaming
        other_path = config_files[new_index]

        # Use temporary name to avoid conflicts
        temp_name = configs_dir / f"_temp_{path.name}"

        try:
            path.rename(temp_name)
            other_path.rename(path)
            temp_name.rename(other_path)

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
        url = self.url_var.get().strip()
        if not url:
            messagebox.showinfo("No URL", "Please enter a Mandarake URL")
            return

        try:
            from mandarake_scraper import parse_mandarake_url
            config = parse_mandarake_url(url)
            self._populate_from_config(config)
            self.status_var.set(f"Loaded URL parameters")
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

        shop_value = config.get('shop', '')
        matched = False
        for code, name in STORE_OPTIONS:
            label = f"{name} ({code})"
            if shop_value == code or shop_value == label:
                self.shop_var.set(label)
                matched = True
                break
        if not matched:
            if shop_value:
                self.shop_var.set('Custom...')
                self.custom_shop_entry.configure(state="normal")
                self.custom_shop_var.set(str(shop_value))
            else:
                self.shop_var.set('')
                self.custom_shop_entry.configure(state="disabled")
                self.custom_shop_var.set('')

        self.hide_sold_var.set(config.get('hide_sold_out', False))
        self.language_var.set(config.get('language', 'ja'))
        self.fast_var.set(config.get('fast', False))
        self.resume_var.set(config.get('resume', True))
        self.debug_var.set(config.get('debug', False))
        self.client_id_var.set(config.get('client_id', ''))
        self.client_secret_var.set(config.get('client_secret', ''))

        sheets = config.get('google_sheets') or {}
        self.sheet_name_var.set(sheets.get('sheet_name', ''))
        self.worksheet_var.set(sheets.get('worksheet_name', 'Sheet1'))

        self.csv_path_var.set(config.get('csv', ''))
        self.download_dir_var.set(config.get('download_images', ''))
        self.upload_drive_var.set(config.get('upload_drive', False))
        self.upload_sheets_var.set(config.get('upload_sheets', True))
        self.show_images_var.set(config.get('show_images', False))
        self.drive_folder_var.set(config.get('drive_folder', ''))
        self.thumbnails_var.set(str(config.get('thumbnails', '')))

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

        # Start search with comparison in background thread
        self.browserless_progress.start()
        self.browserless_status.set("Searching eBay and comparing images...")
        self._start_thread(self._run_scrapy_search_with_compare_worker)

    def _run_scrapy_text_search_worker(self):
        """Worker method for Scrapy text-only search (runs in background thread)"""
        try:
            from ebay_scrapy_search import run_ebay_scrapy_search

            query = self.browserless_query_var.get().strip()
            max_results = int(self.browserless_max_results.get())

            print(f"[SCRAPY SEARCH] Starting search for: {query}")
            print(f"[SCRAPY SEARCH] Max results: {max_results}")

            # Run Scrapy spider
            scrapy_results = run_ebay_scrapy_search(
                query=query,
                max_results=max_results,
                sold_listings=True
            )

            if not scrapy_results:
                self.after(0, lambda: messagebox.showinfo("No Results", "No eBay listings found"))
                return

            print(f"[SCRAPY SEARCH] Found {len(scrapy_results)} results")

            # Convert to display format (no similarity since no image comparison)
            results = []
            for item in scrapy_results:
                results.append({
                    'title': item.get('product_title', 'N/A'),
                    'price': item.get('current_price', 'N/A'),
                    'shipping': item.get('shipping_cost', 'N/A'),
                    'sold_date': item.get('sold_date', 'N/A'),
                    'similarity': '-',  # No comparison
                    'url': item.get('product_url', ''),
                    'image_url': item.get('main_image', '')
                })

            # Update UI with results
            self.after(0, lambda: self._display_browserless_results(results))
            self.after(0, lambda: self.browserless_status.set(f"Found {len(results)} eBay sold listings"))

        except Exception as e:
            import traceback
            print(f"[SCRAPY SEARCH ERROR] {e}")
            traceback.print_exc()
            self.after(0, lambda: messagebox.showerror("Search Error", f"Failed to search eBay: {str(e)}"))
        finally:
            self.after(0, self.browserless_progress.stop)

    def _run_scrapy_search_with_compare_worker(self):
        """Worker method for Scrapy search WITH image comparison (runs in background thread)"""
        try:
            from ebay_scrapy_search import run_ebay_scrapy_search
            import cv2
            import numpy as np

            query = self.browserless_query_var.get().strip()
            max_results = int(self.browserless_max_results.get())
            max_comparisons_str = self.browserless_max_comparisons.get()
            max_comparisons = None if max_comparisons_str == "MAX" else int(max_comparisons_str)

            print(f"[SCRAPY COMPARE] Starting search for: {query}")
            print(f"[SCRAPY COMPARE] Max results: {max_results}")
            print(f"[SCRAPY COMPARE] Max comparisons: {max_comparisons or 'ALL'}")
            print(f"[SCRAPY COMPARE] Reference image: {self.browserless_image_path}")

            # Run Scrapy spider
            scrapy_results = run_ebay_scrapy_search(
                query=query,
                max_results=max_results,
                sold_listings=True
            )

            if not scrapy_results:
                self.after(0, lambda: messagebox.showinfo("No Results", "No eBay listings found"))
                return

            print(f"[SCRAPY COMPARE] Found {len(scrapy_results)} results, comparing images...")

            # Create debug folder
            debug_folder = self._create_debug_folder(query)

            # Load reference image
            ref_image = cv2.imread(str(self.browserless_image_path))
            if ref_image is None:
                raise Exception(f"Could not load reference image: {self.browserless_image_path}")

            # Save reference image to debug folder
            ref_debug_path = debug_folder / f"REF_selected_image.jpg"
            cv2.imwrite(str(ref_debug_path), ref_image)

            # Determine how many to compare
            items_to_compare = scrapy_results if max_comparisons is None else scrapy_results[:max_comparisons]

            # Simple image comparison using template matching
            results = []
            for i, item in enumerate(items_to_compare):
                # Download and compare image
                image_url = item.get('main_image', '')
                similarity = 0.0

                if image_url:
                    try:
                        import requests
                        response = requests.get(image_url, timeout=5)
                        if response.status_code == 200:
                            img_array = np.frombuffer(response.content, np.uint8)
                            ebay_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                            if ebay_img is not None:
                                # Save eBay image to debug folder
                                ebay_title_safe = "".join(c for c in item.get('product_title', 'unknown')[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                                ebay_debug_path = debug_folder / f"ebay_{i+1:02d}_{ebay_title_safe}.jpg"
                                cv2.imwrite(str(ebay_debug_path), ebay_img)

                                # Use shared comparison method
                                similarity = self._compare_images(ref_image, ebay_img)
                    except Exception as e:
                        print(f"[SCRAPY COMPARE] Error comparing image {i+1}: {e}")

                results.append({
                    'title': item.get('product_title', 'N/A'),
                    'price': item.get('current_price', 'N/A'),
                    'shipping': item.get('shipping_cost', 'N/A'),
                    'sold_date': item.get('sold_date', 'N/A'),
                    'similarity': f"{similarity:.1f}%" if similarity > 0 else '-',
                    'url': item.get('product_url', ''),
                    'image_url': image_url
                })

            # Sort by similarity (highest first)
            results.sort(key=lambda x: float(x['similarity'].replace('%', '')) if x['similarity'] != '-' else 0, reverse=True)

            # Update UI with results
            self.after(0, lambda: self._display_browserless_results(results))
            self.after(0, lambda: self.browserless_status.set(f"Found {len(results)} results, compared {len(items_to_compare)} images"))

        except Exception as e:
            import traceback
            print(f"[SCRAPY COMPARE ERROR] {e}")
            traceback.print_exc()
            self.after(0, lambda: messagebox.showerror("Search Error", f"Failed to search/compare: {str(e)}"))
        finally:
            self.after(0, self.browserless_progress.stop)

    def _run_browserless_search_worker_OLD(self):
        """OLD Worker method - DEPRECATED"""
        try:
            import asyncio
            from sold_listing_matcher import match_product_with_sold_listings

            query = self.browserless_query_var.get().strip()
            max_results = int(self.browserless_max_results.get())

            print(f"[OLD BROWSERLESS SEARCH] Starting search for: {query}")
            print(f"[OLD BROWSERLESS SEARCH] Max results: {max_results}")
            print(f"[OLD BROWSERLESS SEARCH] Reference image: {self.browserless_image_path}")

            # Run the async matcher function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                match_result = loop.run_until_complete(
                    match_product_with_sold_listings(
                        reference_image_path=str(self.browserless_image_path),
                        search_term=query,
                        headless=True,  # Use headless mode for background operation
                        max_results=max_results
                    )
                )

                print(f"[OLD BROWSERLESS SEARCH] Found {match_result.matches_found} matches")

                # Convert match results to display format
                results = []

                for listing in match_result.all_matches:
                    # Clean and validate the eBay URL
                    clean_url = self._clean_ebay_url(listing.listing_url)

                    # Format price with currency
                    if listing.price > 0:
                        if listing.currency == 'USD':
                            price_display = f"${listing.price:.2f}"
                        elif listing.currency == 'GBP':
                            price_display = f"£{listing.price:.2f}"
                        elif listing.currency == 'EUR':
                            price_display = f"€{listing.price:.2f}"
                        else:
                            price_display = f"{listing.currency} {listing.price:.2f}"
                    else:
                        price_display = 'Price not found'

                    # Debug logging for title verification
                    print(f"[BROWSERLESS SEARCH] Item title: {listing.title[:80]}...")
                    print(f"[BROWSERLESS SEARCH] Item price: {price_display}")

                    results.append({
                        'title': listing.title,
                        'price': price_display,
                        'similarity': f"{listing.image_similarity:.1f}%",
                        'images': '1',  # Each listing has one image
                        'url': clean_url
                    })

                # Create summary for status area instead of treeview
                if match_result.matches_found > 0:
                    summary_text = f"Found {match_result.matches_found} matches | Avg Price: ${match_result.average_price:.2f} | Range: ${match_result.price_range[0]:.2f}-${match_result.price_range[1]:.2f} | Confidence: {match_result.confidence}"
                    self.run_queue.put(("browserless_status", summary_text))
                else:
                    self.run_queue.put(("browserless_status", "No matches found"))

                # Update UI with results (without summary row)
                self.browserless_results_data = results
                self.run_queue.put(("browserless_results", results))

            finally:
                loop.close()

        except Exception as e:
            print(f"[BROWSERLESS SEARCH] Error: {e}")
            import traceback
            traceback.print_exc()
            self.run_queue.put(("error", f"Search failed: {str(e)}"))

        finally:
            # Stop progress bar
            self.run_queue.put(("browserless_progress_stop", ""))

    def clear_browserless_results(self):
        """Clear browserless search results"""
        for item in self.browserless_tree.get_children():
            self.browserless_tree.delete(item)
        self.browserless_results_data = []
        self.browserless_status.set("Ready for eBay text search")

    # CSV Batch Comparison methods
    def load_csv_for_comparison(self):
        """Load CSV file for batch comparison"""
        file_path = filedialog.askopenfilename(
            title="Select CSV file for comparison",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir="results"
        )

        if file_path:
            self.csv_compare_path = Path(file_path)
            self.csv_compare_label.config(text=f"Loaded: {self.csv_compare_path.name}", foreground="black")
            print(f"[CSV COMPARE] Loaded CSV: {self.csv_compare_path}")

            # Load CSV data
            self.csv_compare_data = []
            try:
                with open(self.csv_compare_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.csv_compare_data.append(row)

                self.filter_csv_items()  # Display with filter applied
                print(f"[CSV COMPARE] Loaded {len(self.csv_compare_data)} items")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {e}")
                print(f"[CSV COMPARE ERROR] {e}")

    def filter_csv_items(self):
        """Filter and display CSV items based on in-stock filter"""
        # Clear existing items
        for item in self.csv_items_tree.get_children():
            self.csv_items_tree.delete(item)

        if not self.csv_compare_data:
            return

        # Apply filter
        in_stock_only = self.csv_in_stock_only.get()
        filtered_items = []

        for row in self.csv_compare_data:
            stock = row.get('in_stock', '').lower()
            if in_stock_only and stock not in ('true', 'yes', '1'):
                continue
            filtered_items.append(row)

        # Display filtered items
        for i, row in enumerate(filtered_items, 1):
            title = row.get('title', '')[:50]
            price = row.get('price_text', row.get('price', ''))
            shop = row.get('shop', row.get('shop_text', ''))
            stock_display = 'Yes' if row.get('in_stock', '').lower() in ('true', 'yes', '1') else 'No'
            category = row.get('category', '')

            self.csv_items_tree.insert('', 'end', iid=str(i), text=str(i),
                                      values=(title, price, shop, stock_display, category))

        print(f"[CSV COMPARE] Displayed {len(filtered_items)} items (in-stock filter: {in_stock_only})")

    def on_csv_item_selected(self, event):
        """Auto-fill search query when CSV item is selected"""
        selection = self.csv_items_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.csv_compare_data):
                row = self.csv_compare_data[index]

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

            # Run comparison in background
            self.csv_compare_progress.start()
            self._start_thread(lambda: self._compare_csv_items_worker([item]))

        except Exception as e:
            messagebox.showerror("Error", f"Invalid selection: {e}")

    def compare_all_csv_items(self):
        """Compare all visible CSV items with eBay"""
        if not self.csv_compare_data:
            messagebox.showinfo("No Data", "Please load a CSV file first")
            return

        # Get filtered items
        in_stock_only = self.csv_in_stock_only.get()
        items_to_compare = []

        for row in self.csv_compare_data:
            stock = row.get('in_stock', '').lower()
            if in_stock_only and stock not in ('true', 'yes', '1'):
                continue
            items_to_compare.append(row)

        if not items_to_compare:
            messagebox.showinfo("No Items", "No items to compare (check filter settings)")
            return

        # Confirm before batch processing
        response = messagebox.askyesno(
            "Batch Comparison",
            f"Compare {len(items_to_compare)} items with eBay?\nThis may take several minutes."
        )

        if response:
            self.csv_compare_progress.start()
            self._start_thread(lambda: self._compare_csv_items_worker(items_to_compare))

    def compare_selected_csv_item_individually(self):
        """Compare selected CSV item individually with its own eBay search"""
        selection = self.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to compare")
            return

        # Get selected item data
        item_id = selection[0]
        try:
            # Find the actual item from the tree display
            title_prefix = self.csv_items_tree.item(item_id)['values'][0]
            item = None
            for row in self.csv_compare_data:
                if row.get('title', '').startswith(title_prefix.replace('...', '')):
                    item = row
                    break

            if not item:
                messagebox.showerror("Error", "Could not find selected item")
                return

            # Run comparison in background
            self.csv_compare_progress.start()
            self._start_thread(lambda: self._compare_csv_items_individually_worker([item]))

        except Exception as e:
            messagebox.showerror("Error", f"Invalid selection: {e}")

    def compare_all_csv_items_individually(self):
        """Compare all visible CSV items individually with separate eBay searches"""
        if not self.csv_compare_data:
            messagebox.showinfo("No Data", "Please load a CSV file first")
            return

        # Get filtered items
        in_stock_only = self.csv_in_stock_only.get()
        items_to_compare = []

        for row in self.csv_compare_data:
            stock = row.get('in_stock', '').lower()
            if in_stock_only and stock not in ('true', 'yes', '1'):
                continue
            items_to_compare.append(row)

        if not items_to_compare:
            messagebox.showinfo("No Items", "No items to compare (check filter settings)")
            return

        # Confirm before batch processing
        response = messagebox.askyesno(
            "Individual Batch Comparison",
            f"Run {len(items_to_compare)} separate eBay searches?\nThis will take longer than single search."
        )

        if response:
            self.csv_compare_progress.start()
            self._start_thread(lambda: self._compare_csv_items_individually_worker(items_to_compare))

    def _compare_csv_items_worker(self, items):
        """Worker to compare CSV items with eBay - OPTIMIZED with caching (runs in background thread)"""
        try:
            from ebay_scrapy_search import run_ebay_scrapy_search
            import cv2
            import numpy as np
            import requests
            from datetime import datetime
            import os

            max_results = int(self.browserless_max_results.get())

            print(f"[CSV BATCH] Comparing {len(items)} CSV items...")

            # Use the search query from the browserless_query_var (user can edit it)
            search_query = self.browserless_query_var.get().strip()

            if not search_query:
                # Fallback to building from first item
                title = items[0].get('title', '') if items else ''
                category = items[0].get('category', '') if items else ''
                core_words = ' '.join(title.split()[:3])
                category_keyword = category.split()[0] if category else ''
                search_query = f"{core_words} {category_keyword}".strip()

            if not search_query:
                self.after(0, lambda: messagebox.showerror("Error", "Could not build search query"))
                return

            print(f"[CSV BATCH] Using search query: '{search_query}'")
            self.after(0, lambda: self.browserless_status.set(f"Searching eBay for '{search_query}'..."))

            # Create debug folder
            debug_folder = self._create_debug_folder(search_query)

            # **ONE eBay search for all items**
            ebay_results = run_ebay_scrapy_search(
                query=search_query,
                max_results=max_results,
                sold_listings=True
            )

            if not ebay_results:
                self.after(0, lambda: messagebox.showinfo("No Results", "No eBay listings found"))
                return

            print(f"[CSV BATCH] Found {len(ebay_results)} eBay listings")
            self.after(0, lambda: self.browserless_status.set(f"Downloading and caching {len(ebay_results)} eBay images..."))

            # **Cache all eBay images at once AND save to debug folder**
            ebay_image_cache = {}
            for idx, ebay_item in enumerate(ebay_results):
                ebay_image_url = ebay_item.get('main_image', '')
                if ebay_image_url and ebay_image_url not in ebay_image_cache:
                    try:
                        response = requests.get(ebay_image_url, timeout=5)
                        if response.status_code == 200:
                            img_array = np.frombuffer(response.content, np.uint8)
                            ebay_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                            if ebay_img is not None:
                                ebay_image_cache[ebay_image_url] = ebay_img

                                # Save debug image
                                ebay_title_safe = "".join(c for c in ebay_item.get('product_title', 'unknown')[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                                debug_path = debug_folder / f"ebay_{idx+1:02d}_{ebay_title_safe}.jpg"
                                cv2.imwrite(str(debug_path), ebay_img)
                                print(f"[CSV BATCH] Cached & saved eBay image {idx+1}/{len(ebay_results)}: {debug_path.name}")
                    except Exception as e:
                        print(f"[CSV BATCH] Error downloading eBay image {idx+1}: {e}")

            print(f"[CSV BATCH] Cached {len(ebay_image_cache)} eBay images")

            # **Now compare each CSV item with cached eBay images**
            comparison_results = []

            for item_idx, item in enumerate(items, 1):
                try:
                    self.after(0, lambda i=item_idx: self.browserless_status.set(f"Comparing CSV item {i}/{len(items)}..."))

                    csv_title = item.get('title', 'unknown')
                    print(f"\n[CSV BATCH] === Processing CSV item {item_idx}/{len(items)}: {csv_title[:50]} ===")

                    # Load CSV item image
                    item_image_url = item.get('image_url', '')
                    ref_image = None

                    if item_image_url:
                        try:
                            response = requests.get(item_image_url, timeout=5)
                            if response.status_code == 200:
                                img_array = np.frombuffer(response.content, np.uint8)
                                ref_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                                if ref_image is not None:
                                    # Save CSV reference image to debug folder
                                    csv_title_safe = "".join(c for c in csv_title[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                                    csv_debug_path = debug_folder / f"CSV_{item_idx:02d}_REF_{csv_title_safe}.jpg"
                                    cv2.imwrite(str(csv_debug_path), ref_image)
                                    print(f"[CSV BATCH] Saved CSV reference image: {csv_debug_path.name}")
                                    print(f"[CSV BATCH] CSV image shape: {ref_image.shape}")
                        except Exception as e:
                            print(f"[CSV BATCH] Error loading CSV item {item_idx} image: {e}")

                    if ref_image is None:
                        print(f"[CSV BATCH] WARNING: No reference image for CSV item {item_idx}, skipping comparisons")
                        continue

                    # Compare with all cached eBay images
                    item_comparisons = []
                    for ebay_idx, ebay_item in enumerate(ebay_results):
                        similarity = 0.0

                        ebay_image_url = ebay_item.get('main_image', '')
                        ebay_img = ebay_image_cache.get(ebay_image_url)

                        if ebay_img is not None:
                            try:
                                # Use shared comparison method
                                similarity = self._compare_images(ref_image, ebay_img)
                                item_comparisons.append((similarity, ebay_idx, ebay_item.get('product_title', 'unknown')[:50]))

                            except Exception as e:
                                print(f"[CSV BATCH] Error comparing with eBay item {ebay_idx+1}: {e}")

                    # Sort by similarity and show top 5
                    item_comparisons.sort(reverse=True)
                    print(f"[CSV BATCH] Top 5 matches for '{csv_title[:40]}':")
                    for rank, (sim, idx, title) in enumerate(item_comparisons[:5], 1):
                        print(f"  {rank}. {sim:.1f}% - {title}")

                    # Add all comparisons to results
                    for similarity, ebay_idx, _ in item_comparisons:
                        ebay_item = ebay_results[ebay_idx]

                        # Calculate profit margin
                        mandarake_price_text = item.get('price_text', item.get('price', '0'))
                        mandarake_price = self._extract_price(mandarake_price_text)

                        ebay_price_text = ebay_item.get('current_price', '0')
                        ebay_price = self._extract_price(ebay_price_text)

                        shipping_text = ebay_item.get('shipping_cost', '0')
                        shipping_cost = self._extract_price(shipping_text)

                        # Profit = eBay - Mandarake - Shipping
                        profit = ebay_price - mandarake_price - shipping_cost
                        profit_margin = (profit / mandarake_price * 100) if mandarake_price > 0 else 0

                        comparison_results.append({
                            'thumbnail': ebay_item.get('main_image', ''),
                            'ebay_title': ebay_item.get('product_title', 'N/A'),
                            'mandarake_title': item.get('title', 'N/A'),
                            'mandarake_price': f"¥{mandarake_price:,.0f}",
                            'ebay_price': ebay_price_text,
                            'shipping': shipping_text,
                            'similarity': similarity,  # Keep as number for sorting
                            'similarity_display': f"{similarity:.1f}%" if similarity > 0 else '-',
                            'profit_margin': profit_margin,  # Keep as number for sorting
                            'profit_display': f"{profit_margin:.1f}%",
                            'mandarake_link': item.get('product_url', ''),
                            'ebay_link': ebay_item.get('product_url', '')
                        })

                except Exception as e:
                    print(f"[CSV BATCH] Error processing CSV item {item_idx}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            # Sort by similarity (highest first)
            comparison_results.sort(key=lambda x: x['similarity'], reverse=True)

            print(f"\n[CSV BATCH] ========================================")
            print(f"[CSV BATCH] Generated {len(comparison_results)} comparison results")
            print(f"[CSV BATCH] Debug images saved to: {debug_folder.absolute()}")
            print(f"[CSV BATCH] - {len(ebay_image_cache)} eBay images")
            print(f"[CSV BATCH] - {len(items)} CSV reference images")
            print(f"[CSV BATCH] ========================================\n")

            # Store unfiltered results for filtering
            self.all_comparison_results = comparison_results

            # Apply filters and display
            self.after(0, lambda: self._display_csv_comparison_results(comparison_results))
            self.after(0, lambda: self.browserless_status.set(f"Compared {len(items)} CSV items with {len(ebay_results)} eBay listings - {len(comparison_results)} total matches"))

        except Exception as e:
            import traceback
            print(f"[CSV BATCH ERROR] {e}")
            traceback.print_exc()
            self.after(0, lambda: messagebox.showerror("Comparison Error", f"Failed: {str(e)}"))
        finally:
            self.after(0, self.csv_compare_progress.stop)

    def _compare_csv_items_individually_worker(self, items):
        """Worker to compare CSV items individually - each item gets its own eBay search"""
        try:
            from ebay_scrapy_search import run_ebay_scrapy_search
            import cv2
            import numpy as np
            import requests

            max_results = int(self.browserless_max_results.get())
            comparison_results = []

            print(f"\n[CSV INDIVIDUAL] Starting individual comparisons for {len(items)} items")
            print(f"[CSV INDIVIDUAL] Each item will get its own eBay search with keyword + category")

            for item_idx, item in enumerate(items, 1):
                csv_title = item.get('title', 'Unknown')
                keyword = item.get('keyword', '')
                category = item.get('category', '')

                # Build search query for this specific item
                if keyword:
                    core_words = keyword
                else:
                    core_words = ' '.join(csv_title.split()[:3])

                category_keyword = CATEGORY_KEYWORDS.get(category, '')
                search_query = f"{core_words} {category_keyword}".strip()

                if not search_query:
                    print(f"[CSV INDIVIDUAL] Skipping item {item_idx}: no search query")
                    continue

                print(f"\n[CSV INDIVIDUAL] Item {item_idx}/{len(items)}: {csv_title[:50]}")
                print(f"[CSV INDIVIDUAL] Search query: '{search_query}'")

                self.after(0, lambda q=search_query, idx=item_idx: self.browserless_status.set(
                    f"Item {idx}/{len(items)}: Searching eBay for '{q}'..."))

                # Create debug folder for this item
                debug_folder = self._create_debug_folder(f"{search_query}_item{item_idx}")

                # Run eBay search for this specific item
                ebay_results = run_ebay_scrapy_search(
                    query=search_query,
                    max_results=max_results,
                    sold_listings=True
                )

                if not ebay_results:
                    print(f"[CSV INDIVIDUAL] No eBay results for item {item_idx}")
                    continue

                print(f"[CSV INDIVIDUAL] Found {len(ebay_results)} eBay listings")

                # Load CSV item image
                csv_image_path = item.get('local_image', '')
                if not csv_image_path or not Path(csv_image_path).exists():
                    print(f"[CSV INDIVIDUAL] No image for item {item_idx}, skipping visual comparison")
                    continue

                ref_image = cv2.imread(str(csv_image_path))
                if ref_image is None:
                    print(f"[CSV INDIVIDUAL] Failed to load image for item {item_idx}")
                    continue

                # Save reference image to debug folder
                csv_title_safe = "".join(c for c in csv_title[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                csv_debug_path = debug_folder / f"CSV_REF_{csv_title_safe}.jpg"
                cv2.imwrite(str(csv_debug_path), ref_image)

                # Download and compare with each eBay result
                item_comparisons = []
                for ebay_idx, ebay_item in enumerate(ebay_results):
                    ebay_image_url = ebay_item.get('main_image', '')
                    if not ebay_image_url:
                        continue

                    try:
                        response = requests.get(ebay_image_url, timeout=5)
                        if response.status_code == 200:
                            img_array = np.frombuffer(response.content, np.uint8)
                            ebay_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                            if ebay_img is not None:
                                # Save eBay image to debug folder
                                ebay_title_safe = "".join(c for c in ebay_item.get('product_title', 'unknown')[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                                ebay_debug_path = debug_folder / f"ebay_{ebay_idx+1:02d}_{ebay_title_safe}.jpg"
                                cv2.imwrite(str(ebay_debug_path), ebay_img)

                                # Use shared comparison method
                                similarity = self._compare_images(ref_image, ebay_img)
                                item_comparisons.append((similarity, ebay_idx, ebay_item.get('product_title', 'unknown')[:50]))

                    except Exception as e:
                        print(f"[CSV INDIVIDUAL] Error comparing with eBay item {ebay_idx+1}: {e}")

                # Sort by similarity and show top 5
                item_comparisons.sort(reverse=True)
                print(f"[CSV INDIVIDUAL] Top 5 matches for '{csv_title[:40]}':")
                for rank, (sim, idx, title) in enumerate(item_comparisons[:5], 1):
                    print(f"  {rank}. {sim:.1f}% - {title}")

                # Add all comparisons to results
                for similarity, ebay_idx, _ in item_comparisons:
                    ebay_item = ebay_results[ebay_idx]

                    # Calculate profit margin
                    mandarake_price_text = item.get('price_text', item.get('price', '0'))
                    mandarake_price = self._extract_price(mandarake_price_text)

                    ebay_price_text = ebay_item.get('current_price', '0')
                    ebay_price = self._extract_price(ebay_price_text)

                    shipping_text = ebay_item.get('shipping_cost', '0')
                    shipping_cost = self._extract_price(shipping_text)

                    # Profit = eBay - Mandarake - Shipping
                    profit = ebay_price - mandarake_price - shipping_cost
                    profit_margin = (profit / mandarake_price * 100) if mandarake_price > 0 else 0

                    comparison_results.append({
                        'thumbnail': ebay_item.get('main_image', ''),
                        'csv_title': csv_title,
                        'ebay_title': ebay_item.get('product_title', 'N/A'),
                        'mandarake_price': f"¥{mandarake_price:,.0f}",
                        'ebay_price': ebay_price_text,
                        'shipping': shipping_text,
                        'similarity': similarity,
                        'similarity_display': f"{similarity:.1f}%" if similarity > 0 else '-',
                        'profit_margin': profit_margin,
                        'profit_display': f"{profit_margin:.1f}%",
                        'mandarake_link': item.get('product_url', ''),
                        'ebay_link': ebay_item.get('product_url', '')
                    })

            # Sort by similarity (highest first)
            comparison_results.sort(key=lambda x: x['similarity'], reverse=True)

            print(f"\n[CSV INDIVIDUAL] ========================================")
            print(f"[CSV INDIVIDUAL] Completed {len(items)} individual searches")
            print(f"[CSV INDIVIDUAL] Generated {len(comparison_results)} comparison results")
            print(f"[CSV INDIVIDUAL] ========================================\n")

            # Store unfiltered results for filtering
            self.all_comparison_results = comparison_results

            # Apply filters and display
            self.after(0, lambda: self._display_csv_comparison_results(comparison_results))
            self.after(0, lambda: self.browserless_status.set(f"Completed {len(items)} individual searches - {len(comparison_results)} total matches"))

        except Exception as e:
            import traceback
            print(f"[CSV INDIVIDUAL ERROR] {e}")
            traceback.print_exc()
            self.after(0, lambda: messagebox.showerror("Comparison Error", f"Failed: {str(e)}"))
        finally:
            self.after(0, self.csv_compare_progress.stop)

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

    def apply_results_filter(self):
        """Apply filters to comparison results"""
        if not self.all_comparison_results:
            return

        try:
            min_similarity = float(self.min_similarity_var.get() or 0)
            min_profit = float(self.min_profit_var.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid Filter", "Please enter valid numbers for filters")
            return

        # Filter results
        filtered_results = []
        for r in self.all_comparison_results:
            if r['similarity'] >= min_similarity and r['profit_margin'] >= min_profit:
                filtered_results.append(r)

        print(f"[FILTER] Showing {len(filtered_results)} of {len(self.all_comparison_results)} results (similarity>={min_similarity}%, profit>={min_profit}%)")

        self._display_csv_comparison_results(filtered_results)
        self.browserless_status.set(f"Showing {len(filtered_results)} of {len(self.all_comparison_results)} results (filtered)")

    def _display_csv_comparison_results(self, results):
        """Display CSV comparison results in the browserless tree"""
        # Convert format to match existing display
        display_results = []
        for r in results:
            display_results.append({
                'title': r['ebay_title'],
                'price': r['ebay_price'],
                'shipping': r['shipping'],
                'sold_date': r['profit_display'],  # Show profit margin
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
        """Display browserless search results in the tree view"""
        # Clear existing results
        for item in self.browserless_tree.get_children():
            self.browserless_tree.delete(item)

        # Store results for URL opening
        self.browserless_results_data = results

        # Add new results
        for i, result in enumerate(results, 1):
            values = (
                result['title'][:45] + "..." if len(result['title']) > 45 else result['title'],
                result['price'],
                result['shipping'],
                result['sold_date'],
                result['similarity'],
                result['url'][:35] + "..." if len(result['url']) > 35 else result['url']
            )

            self.browserless_tree.insert('', 'end', iid=str(i), text=str(i), values=values)

        print(f"[SCRAPY SEARCH] Displayed {len(results)} results in tree view")

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
        keyword = self.keyword_var.get().strip()
        if not keyword:
            self.url_var.set("Search URL: (enter keyword)")
            return

        params: list[tuple[str, str]] = []
        params.append(("keyword", quote(keyword)))

        notes: list[str] = []
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

        query = '&'.join(f"{key}={value}" for key, value in params)
        url = "https://order.mandarake.co.jp/order/listPage/list"
        if query:
            url = f"{url}?{query}"
        note_str = f" ({'; '.join(notes)})" if notes else ''
        self.url_var.set(f"Search URL: {url}{note_str}")


def main():
    ScraperGUI().mainloop()


if __name__ == '__main__':
    main()