#!/usr/bin/env python3
"""
Unified Settings Dialog

Provides a centralized interface for managing all application settings:
- General preferences
- Scraper defaults (Mandarake, Suruga-ya)
- eBay integration
- Image comparison
- Alerts
- Output directories
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class SettingsDialog(tk.Toplevel):
    """Unified settings dialog with tabbed interface."""

    def __init__(self, parent, settings_manager):
        """
        Initialize settings dialog.

        Args:
            parent: Parent window
            settings_manager: SettingsManager instance
        """
        super().__init__(parent)
        self.parent = parent
        self.settings = settings_manager
        self.logger = logging.getLogger(__name__)

        # Dialog settings
        self.title("Preferences")
        self.geometry("700x600")
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 700) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 600) // 2
        self.geometry(f"+{x}+{y}")

        # Variables to hold settings
        self._init_variables()

        # Build UI
        self._build_ui()

        # Load current settings
        self._load_settings()

        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _init_variables(self):
        """Initialize tkinter variables for all settings."""
        # General
        self.language_var = tk.StringVar(value="en")
        self.thumbnail_width_var = tk.StringVar(value="400")
        self.csv_thumbnails_var = tk.BooleanVar(value=True)
        self.auto_save_configs_var = tk.BooleanVar(value=True)
        self.recent_files_limit_var = tk.StringVar(value="10")

        # Mandarake Scraper
        self.mand_max_pages_var = tk.StringVar(value="2")
        self.mand_results_per_page_var = tk.StringVar(value="48")
        self.mand_resume_var = tk.BooleanVar(value=True)
        self.mand_browser_mimic_var = tk.BooleanVar(value=True)
        self.mand_max_csv_items_var = tk.StringVar(value="0")

        # Suruga-ya Scraper
        self.suruga_max_pages_var = tk.StringVar(value="2")
        self.suruga_results_per_page_var = tk.StringVar(value="50")
        self.suruga_show_out_of_stock_var = tk.BooleanVar(value=False)
        self.suruga_translate_var = tk.BooleanVar(value=True)

        # eBay Integration
        self.ebay_client_id_var = tk.StringVar(value="")
        self.ebay_client_secret_var = tk.StringVar(value="")
        self.ebay_search_method_var = tk.StringVar(value="scrapy")
        self.ebay_max_results_var = tk.StringVar(value="10")
        self.ebay_sold_listings_var = tk.BooleanVar(value=True)
        self.ebay_days_back_var = tk.StringVar(value="90")

        # Image Comparison - weights only
        self.img_template_weight_var = tk.StringVar(value="60")
        self.img_orb_weight_var = tk.StringVar(value="25")
        self.img_ssim_weight_var = tk.StringVar(value="10")
        self.img_histogram_weight_var = tk.StringVar(value="5")

        # Proxy Settings
        self.proxy_enabled_var = tk.BooleanVar(value=False)
        self.proxy_ebay_enabled_var = tk.BooleanVar(value=True)
        self.proxy_mandarake_enabled_var = tk.BooleanVar(value=True)
        self.proxy_surugaya_enabled_var = tk.BooleanVar(value=True)
        self.proxy_api_key_var = tk.StringVar(value="")
        self.proxy_country_var = tk.StringVar(value="us")
        self.proxy_render_js_var = tk.BooleanVar(value=False)

        # Output
        self.output_csv_dir_var = tk.StringVar(value="results")
        self.output_images_dir_var = tk.StringVar(value="images")
        self.output_debug_dir_var = tk.StringVar(value="debug_comparison")

    def _build_ui(self):
        """Build the dialog UI."""
        # Main container
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create tabs
        self._create_general_tab()
        self._create_scrapers_tab()
        self._create_ebay_tab()
        self._create_proxy_tab()
        self._create_images_tab()
        self._create_output_tab()

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # Left side buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)

        ttk.Button(
            left_buttons,
            text="Import Settings...",
            command=self._on_import
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            left_buttons,
            text="Export Settings...",
            command=self._on_export
        ).pack(side=tk.LEFT)

        # Right side buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)

        ttk.Button(
            right_buttons,
            text="Cancel",
            command=self._on_cancel
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            right_buttons,
            text="Apply",
            command=self._on_apply
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            right_buttons,
            text="OK",
            command=self._on_ok
        ).pack(side=tk.LEFT)

    def _create_general_tab(self):
        """Create General settings tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="General")

        row = 0

        # Language
        ttk.Label(tab, text="Language:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        lang_frame = ttk.Frame(tab)
        lang_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0))
        ttk.Radiobutton(
            lang_frame, text="English", variable=self.language_var, value="en"
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            lang_frame, text="日本語", variable=self.language_var, value="ja"
        ).pack(side=tk.LEFT)
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # Thumbnails
        ttk.Label(tab, text="Thumbnails:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        ttk.Label(tab, text="Default thumbnail width (px):").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.thumbnail_width_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Checkbutton(
            tab, text="Show CSV thumbnails by default", variable=self.csv_thumbnails_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # Preferences
        ttk.Label(tab, text="Preferences:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        ttk.Checkbutton(
            tab, text="Auto-save configs on change", variable=self.auto_save_configs_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

        ttk.Label(tab, text="Recent files limit:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.recent_files_limit_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

    def _create_scrapers_tab(self):
        """Create Scrapers settings tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Scrapers")

        row = 0

        # Mandarake
        ttk.Label(tab, text="Mandarake Defaults:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        ttk.Label(tab, text="Max pages:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.mand_max_pages_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Label(tab, text="Results per page:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Combobox(
            tab, textvariable=self.mand_results_per_page_var,
            values=["48", "120", "240"], width=8, state='readonly'
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        ttk.Checkbutton(
            tab, text="Resume interrupted runs", variable=self.mand_resume_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

        ttk.Checkbutton(
            tab, text="Use browser mimic (recommended)", variable=self.mand_browser_mimic_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

        ttk.Label(tab, text="Max CSV items (0 = unlimited):").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.mand_max_csv_items_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # Suruga-ya
        ttk.Label(tab, text="Suruga-ya Defaults:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        ttk.Label(tab, text="Max pages:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.suruga_max_pages_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Label(tab, text="Results per page:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.suruga_results_per_page_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Checkbutton(
            tab, text="Show out of stock items", variable=self.suruga_show_out_of_stock_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

        ttk.Checkbutton(
            tab, text="Auto-translate titles to English", variable=self.suruga_translate_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

    def _create_ebay_tab(self):
        """Create eBay Integration settings tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="eBay")

        row = 0

        # API Credentials
        ttk.Label(tab, text="API Credentials:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        ttk.Label(tab, text="Client ID (App ID):").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.ebay_client_id_var, width=40).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Label(tab, text="Client Secret (Cert ID):").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.ebay_client_secret_var, width=40, show="*").grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        # Help link
        help_label = ttk.Label(
            tab, text="Get credentials at developer.ebay.com",
            foreground='blue', cursor='hand2', font=('TkDefaultFont', 8)
        )
        help_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        help_label.bind("<Button-1>", lambda e: self._open_ebay_dev())
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # Search Settings
        ttk.Label(tab, text="Search Settings:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        ttk.Label(tab, text="Search method:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        method_frame = ttk.Frame(tab)
        method_frame.grid(row=row, column=1, sticky=tk.W, pady=2)
        ttk.Radiobutton(
            method_frame, text="Scrapy (Sold)", variable=self.ebay_search_method_var, value="scrapy"
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            method_frame, text="API (Active)", variable=self.ebay_search_method_var, value="api"
        ).pack(side=tk.LEFT)
        row += 1

        ttk.Label(tab, text="Max results:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.ebay_max_results_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Checkbutton(
            tab, text="Search sold listings (Scrapy only)", variable=self.ebay_sold_listings_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

        ttk.Label(tab, text="Days back for sold listings:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.ebay_days_back_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

    def _create_proxy_tab(self):
        """Create Proxy Rotation settings tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Proxy Rotation")

        row = 0

        # Header
        ttk.Label(
            tab,
            text="ScrapeOps Proxy Configuration:",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1

        # Enable proxy
        ttk.Checkbutton(
            tab,
            text="Enable ScrapeOps proxy rotation",
            variable=self.proxy_enabled_var,
            command=self._toggle_proxy_fields
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=5)
        row += 1

        # Info label
        info_label = ttk.Label(
            tab,
            text="Prevents IP bans by rotating through different proxy IPs for each request.",
            foreground='gray',
            font=('TkDefaultFont', 8)
        )
        info_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(40, 0), pady=(0, 10))
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # Use proxy for
        ttk.Label(
            tab,
            text="Use proxy for:",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1

        self.proxy_ebay_check = ttk.Checkbutton(
            tab,
            text="eBay scraping (Scrapy spider)",
            variable=self.proxy_ebay_enabled_var
        )
        self.proxy_ebay_check.grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2
        )
        row += 1

        self.proxy_mandarake_check = ttk.Checkbutton(
            tab,
            text="Mandarake scraping (BrowserMimic)",
            variable=self.proxy_mandarake_enabled_var
        )
        self.proxy_mandarake_check.grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2
        )
        row += 1

        self.proxy_surugaya_check = ttk.Checkbutton(
            tab,
            text="Suruga-ya scraping (BrowserMimic)",
            variable=self.proxy_surugaya_enabled_var
        )
        self.proxy_surugaya_check.grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2
        )
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # API Key
        ttk.Label(tab, text="API Key:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        self.proxy_api_key_entry = ttk.Entry(
            tab,
            textvariable=self.proxy_api_key_var,
            width=50,
            show="*"
        )
        self.proxy_api_key_entry.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # Help link
        help_label = ttk.Label(
            tab,
            text="Get free API key at scrapeops.io/app/register",
            foreground='blue',
            cursor='hand2',
            font=('TkDefaultFont', 8)
        )
        help_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        help_label.bind("<Button-1>", lambda e: self._open_scrapeops_signup())
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # Advanced Settings
        ttk.Label(
            tab,
            text="Advanced Settings:",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1

        # Country
        ttk.Label(tab, text="Proxy country:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        self.proxy_country_combo = ttk.Combobox(
            tab,
            textvariable=self.proxy_country_var,
            values=["us", "uk", "ca", "au", "de", "fr", "jp"],
            width=10,
            state='readonly'
        )
        self.proxy_country_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # Render JavaScript
        self.proxy_render_js_check = ttk.Checkbutton(
            tab,
            text="Enable JavaScript rendering (slower, more expensive)",
            variable=self.proxy_render_js_var
        )
        self.proxy_render_js_check.grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2
        )
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # Usage Info
        ttk.Label(
            tab,
            text="Usage Information:",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1

        usage_text = (
            "Free Plan: 1,000 requests/month, 1 concurrent request\n"
            "Hobby Plan: $29/mo, 100,000 requests, 10 concurrent\n"
            "Startup Plan: $99/mo, 500,000 requests, 25 concurrent\n\n"
            "Monitor usage: scrapeops.io/app/dashboard"
        )
        usage_label = ttk.Label(
            tab,
            text=usage_text,
            foreground='gray',
            font=('TkDefaultFont', 8),
            justify=tk.LEFT
        )
        usage_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10
        )
        row += 1

        # When to Use
        ttk.Label(
            tab,
            text="When to Enable:",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1

        when_text = (
            "✅ Auto-purchase monitoring (prevents bans from repeated checks)\n"
            "✅ High-volume scraping (100+ pages in a session)\n"
            "✅ After getting IP banned (immediate workaround)\n\n"
            "❌ Single searches (wastes quota)\n"
            "❌ Low-volume usage (<10 searches/day)\n"
            "❌ Testing (save requests for production)"
        )
        when_label = ttk.Label(
            tab,
            text=when_text,
            foreground='gray',
            font=('TkDefaultFont', 8),
            justify=tk.LEFT
        )
        when_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=2)
        row += 1

    def _create_images_tab(self):
        """Create Image Comparison settings tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Image Comparison")

        row = 0

        # Weights (Advanced)
        ttk.Label(tab, text="Algorithm Weights:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        ttk.Label(tab, text="Template matching weight (%):").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.img_template_weight_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Label(tab, text="ORB features weight (%):").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.img_orb_weight_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Label(tab, text="SSIM weight (%):").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.img_ssim_weight_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        ttk.Label(tab, text="Histogram weight (%):").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.img_histogram_weight_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        # Note and Reset button
        note_frame = ttk.Frame(tab)
        note_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=(20, 0), pady=(5, 0))

        ttk.Label(
            note_frame, text="Weights must sum to 100%",
            foreground='gray', font=('TkDefaultFont', 8)
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            note_frame,
            text="Reset to Defaults",
            command=self._reset_weights_to_defaults,
            width=15
        ).pack(side=tk.LEFT)
        row += 1

    def _create_output_tab(self):
        """Create Output settings tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Output")

        row = 0

        # Directories
        ttk.Label(tab, text="Output Directories:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        ttk.Label(tab, text="CSV output directory:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.output_csv_dir_var, width=30).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        ttk.Button(
            tab, text="Browse...", width=10,
            command=lambda: self._browse_directory(self.output_csv_dir_var)
        ).grid(row=row, column=2, sticky=tk.W, padx=(5, 0), pady=2)
        row += 1

        ttk.Label(tab, text="Image download directory:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.output_images_dir_var, width=30).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        ttk.Button(
            tab, text="Browse...", width=10,
            command=lambda: self._browse_directory(self.output_images_dir_var)
        ).grid(row=row, column=2, sticky=tk.W, padx=(5, 0), pady=2)
        row += 1

        ttk.Label(tab, text="Debug comparison directory:").grid(
            row=row, column=0, sticky=tk.W, padx=(20, 0), pady=2
        )
        ttk.Entry(tab, textvariable=self.output_debug_dir_var, width=30).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        ttk.Button(
            tab, text="Browse...", width=10,
            command=lambda: self._browse_directory(self.output_debug_dir_var)
        ).grid(row=row, column=2, sticky=tk.W, padx=(5, 0), pady=2)
        row += 1

    def _toggle_proxy_fields(self):
        """Enable/disable proxy fields based on checkbox."""
        enabled = self.proxy_enabled_var.get()
        state = 'normal' if enabled else 'disabled'

        self.proxy_ebay_check.config(state=state)
        self.proxy_mandarake_check.config(state=state)
        self.proxy_surugaya_check.config(state=state)
        self.proxy_api_key_entry.config(state=state)
        self.proxy_country_combo.config(state='readonly' if enabled else 'disabled')
        self.proxy_render_js_check.config(state=state)

    def _open_scrapeops_signup(self):
        """Open ScrapeOps signup page."""
        import webbrowser
        webbrowser.open("https://scrapeops.io/app/register")

    def _load_settings(self):
        """Load current settings into dialog."""
        # General
        self.language_var.set(self.settings.get_setting('general.language', 'en'))
        self.thumbnail_width_var.set(str(self.settings.get_setting('general.thumbnail_width', 400)))
        self.csv_thumbnails_var.set(self.settings.get_setting('general.csv_thumbnails_enabled', True))
        self.auto_save_configs_var.set(self.settings.get_setting('general.auto_save_configs', True))
        self.recent_files_limit_var.set(str(self.settings.get_setting('general.recent_files_limit', 10)))

        # Mandarake
        self.mand_max_pages_var.set(str(self.settings.get_setting('scrapers.mandarake.max_pages', 2)))
        self.mand_results_per_page_var.set(str(self.settings.get_setting('scrapers.mandarake.results_per_page', 48)))
        self.mand_resume_var.set(self.settings.get_setting('scrapers.mandarake.resume', True))
        self.mand_browser_mimic_var.set(self.settings.get_setting('scrapers.mandarake.browser_mimic', True))
        self.mand_max_csv_items_var.set(str(self.settings.get_setting('scraper.max_csv_items', 0)))

        # Suruga-ya
        self.suruga_max_pages_var.set(str(self.settings.get_setting('scrapers.surugaya.max_pages', 2)))
        self.suruga_results_per_page_var.set(str(self.settings.get_setting('scrapers.surugaya.results_per_page', 50)))
        self.suruga_show_out_of_stock_var.set(self.settings.get_setting('scrapers.surugaya.show_out_of_stock', False))
        self.suruga_translate_var.set(self.settings.get_setting('scrapers.surugaya.translate_titles', True))

        # eBay
        credentials = self.settings.get_ebay_credentials()
        self.ebay_client_id_var.set(credentials.get('client_id', ''))
        self.ebay_client_secret_var.set(credentials.get('client_secret', ''))
        self.ebay_search_method_var.set(self.settings.get_setting('ebay.search_method', 'scrapy'))
        self.ebay_max_results_var.set(str(self.settings.get_setting('ebay.max_results', 10)))
        self.ebay_sold_listings_var.set(self.settings.get_setting('ebay.sold_listings', True))
        self.ebay_days_back_var.set(str(self.settings.get_setting('ebay.days_back', 90)))

        # Image Comparison - weights only
        weights = self.settings.get_setting('image_comparison.weights', {})
        self.img_template_weight_var.set(str(weights.get('template', 60)))
        self.img_orb_weight_var.set(str(weights.get('orb', 25)))
        self.img_ssim_weight_var.set(str(weights.get('ssim', 10)))
        self.img_histogram_weight_var.set(str(weights.get('histogram', 5)))

        # Proxy Settings
        self.proxy_enabled_var.set(self.settings.get_setting('proxy.enabled', False))
        self.proxy_ebay_enabled_var.set(self.settings.get_setting('proxy.ebay_enabled', True))
        self.proxy_mandarake_enabled_var.set(self.settings.get_setting('proxy.mandarake_enabled', True))
        self.proxy_surugaya_enabled_var.set(self.settings.get_setting('proxy.surugaya_enabled', True))
        self.proxy_api_key_var.set(self.settings.get_setting('proxy.api_key', ''))
        self.proxy_country_var.set(self.settings.get_setting('proxy.country', 'us'))
        self.proxy_render_js_var.set(self.settings.get_setting('proxy.render_js', False))

        # Toggle proxy fields based on enabled state
        self._toggle_proxy_fields()

        # Output
        self.output_csv_dir_var.set(self.settings.get_setting('output.csv_dir', 'results'))
        self.output_images_dir_var.set(self.settings.get_setting('output.images_dir', 'images'))
        self.output_debug_dir_var.set(self.settings.get_setting('output.debug_dir', 'debug_comparison'))

    def _save_settings(self) -> bool:
        """Save all settings from dialog."""
        try:
            # Validate numeric inputs
            if not self._validate_inputs():
                return False

            # General
            self.settings.set_setting('general.language', self.language_var.get())
            self.settings.set_setting('general.thumbnail_width', int(self.thumbnail_width_var.get()))
            self.settings.set_setting('general.csv_thumbnails_enabled', self.csv_thumbnails_var.get())
            self.settings.set_setting('general.auto_save_configs', self.auto_save_configs_var.get())
            self.settings.set_setting('general.recent_files_limit', int(self.recent_files_limit_var.get()))

            # Mandarake
            self.settings.set_setting('scrapers.mandarake.max_pages', int(self.mand_max_pages_var.get()))
            self.settings.set_setting('scrapers.mandarake.results_per_page', int(self.mand_results_per_page_var.get()))
            self.settings.set_setting('scrapers.mandarake.resume', self.mand_resume_var.get())
            self.settings.set_setting('scrapers.mandarake.browser_mimic', self.mand_browser_mimic_var.get())
            self.settings.set_setting('scraper.max_csv_items', int(self.mand_max_csv_items_var.get()))

            # Suruga-ya
            self.settings.set_setting('scrapers.surugaya.max_pages', int(self.suruga_max_pages_var.get()))
            self.settings.set_setting('scrapers.surugaya.results_per_page', int(self.suruga_results_per_page_var.get()))
            self.settings.set_setting('scrapers.surugaya.show_out_of_stock', self.suruga_show_out_of_stock_var.get())
            self.settings.set_setting('scrapers.surugaya.translate_titles', self.suruga_translate_var.get())

            # eBay
            self.settings.save_ebay_credentials(
                self.ebay_client_id_var.get().strip(),
                self.ebay_client_secret_var.get().strip()
            )
            self.settings.set_setting('ebay.search_method', self.ebay_search_method_var.get())
            self.settings.set_setting('ebay.max_results', int(self.ebay_max_results_var.get()))
            self.settings.set_setting('ebay.sold_listings', self.ebay_sold_listings_var.get())
            self.settings.set_setting('ebay.days_back', int(self.ebay_days_back_var.get()))

            # Image Comparison - weights only
            self.settings.set_setting('image_comparison.weights', {
                'template': int(self.img_template_weight_var.get()),
                'orb': int(self.img_orb_weight_var.get()),
                'ssim': int(self.img_ssim_weight_var.get()),
                'histogram': int(self.img_histogram_weight_var.get())
            })

            # Proxy Settings
            self.settings.set_setting('proxy.enabled', self.proxy_enabled_var.get())
            self.settings.set_setting('proxy.ebay_enabled', self.proxy_ebay_enabled_var.get())
            self.settings.set_setting('proxy.mandarake_enabled', self.proxy_mandarake_enabled_var.get())
            self.settings.set_setting('proxy.surugaya_enabled', self.proxy_surugaya_enabled_var.get())
            self.settings.set_setting('proxy.api_key', self.proxy_api_key_var.get().strip())
            self.settings.set_setting('proxy.country', self.proxy_country_var.get())
            self.settings.set_setting('proxy.render_js', self.proxy_render_js_var.get())

            # Output
            self.settings.set_setting('output.csv_dir', self.output_csv_dir_var.get())
            self.settings.set_setting('output.images_dir', self.output_images_dir_var.get())
            self.settings.set_setting('output.debug_dir', self.output_debug_dir_var.get())

            # Save to file
            return self.settings.save_settings()

        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")
            return False

    def _validate_inputs(self) -> bool:
        """Validate all numeric inputs."""
        try:
            # Validate integers
            int(self.thumbnail_width_var.get())
            int(self.recent_files_limit_var.get())
            int(self.mand_max_pages_var.get())
            int(self.mand_results_per_page_var.get())
            int(self.mand_max_csv_items_var.get())
            int(self.suruga_max_pages_var.get())
            int(self.suruga_results_per_page_var.get())
            int(self.ebay_max_results_var.get())
            int(self.ebay_days_back_var.get())

            # Validate weights
            template_w = int(self.img_template_weight_var.get())
            orb_w = int(self.img_orb_weight_var.get())
            ssim_w = int(self.img_ssim_weight_var.get())
            hist_w = int(self.img_histogram_weight_var.get())

            total = template_w + orb_w + ssim_w + hist_w
            if total != 100:
                messagebox.showerror(
                    "Validation Error",
                    f"Image comparison weights must sum to 100%.\nCurrent total: {total}%"
                )
                self.notebook.select(3)  # Switch to Images tab
                return False

            return True

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid numeric value:\n{e}")
            return False

    def _browse_directory(self, var: tk.StringVar):
        """Browse for directory."""
        current = var.get()
        directory = filedialog.askdirectory(
            title="Select Directory",
            initialdir=current if current else "."
        )
        if directory:
            var.set(directory)

    def _open_ebay_dev(self):
        """Open eBay developer portal."""
        import webbrowser
        webbrowser.open("https://developer.ebay.com/my/keys")

    def _reset_weights_to_defaults(self):
        """Reset image comparison weights to default values."""
        self.img_template_weight_var.set("60")
        self.img_orb_weight_var.set("25")
        self.img_ssim_weight_var.set("10")
        self.img_histogram_weight_var.set("5")
        messagebox.showinfo("Reset", "Algorithm weights reset to defaults (60/25/10/5)")

    def _on_import(self):
        """Import settings from file."""
        file_path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            if messagebox.askyesno(
                "Import Settings",
                "Importing will replace all current settings.\n\nContinue?"
            ):
                if self.settings.import_settings(file_path):
                    self._load_settings()  # Reload UI
                    messagebox.showinfo("Success", "Settings imported successfully!")
                else:
                    messagebox.showerror("Error", "Failed to import settings.")

    def _on_export(self):
        """Export settings to file."""
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

    def _on_apply(self):
        """Apply settings without closing."""
        if self._save_settings():
            messagebox.showinfo("Success", "Settings saved successfully!")

    def _on_ok(self):
        """Save and close."""
        if self._save_settings():
            self.destroy()

    def _on_cancel(self):
        """Close without saving."""
        if messagebox.askyesno("Cancel", "Discard changes?"):
            self.destroy()
