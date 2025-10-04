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
from gui.ebay_tab import EbayTab
from gui.advanced_tab import AdvancedTab
from gui.schedule_executor import ScheduleExecutor
from gui.schedule_frame import ScheduleFrame
from gui.configuration_manager import ConfigurationManager
from gui.tree_manager import TreeManager
from gui.config_tree_manager import ConfigTreeManager
from gui.ebay_search_manager import EbaySearchManager
from gui.csv_comparison_manager import CSVComparisonManager
from gui.surugaya_manager import SurugayaManager


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

        # Initialize Suruga-ya manager (after run_queue is created)
        self.surugaya_manager = SurugayaManager(self.run_queue, self.settings)
        self.detail_code_map: list[str] = []
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

            # Initialize ConfigTreeManager after config_tree is created by MandarakeTab
            self.config_tree_manager = ConfigTreeManager(
                self.config_tree,
                self.config_paths,
                self
            )

        # eBay Search & CSV tab - Create using EbayTab module
        if marketplace_toggles.get('ebay', True):
            self.ebay_tab = EbayTab(browserless_frame, self.settings, self.alert_tab, self)
            self.ebay_tab.pack(fill=tk.BOTH, expand=True)

        # Advanced tab - Create using AdvancedTab module
        self.advanced_tab = AdvancedTab(advanced_frame, self.settings, self)
        self.advanced_tab.pack(fill=tk.BOTH, expand=True)

        # Restore paned window positions after widgets are created
        self.after(100, self._restore_paned_position)
        self.after(100, self._restore_vertical_paned_position)
        self.after(100, self._restore_listbox_paned_position)

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
                self.ebay_tab.ebay_paned.sash_place(0, 0, ebay_paned_pos)
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
                    sash_coords = self.ebay_tab.ebay_paned.sash_coord(0)  # First sash
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
                ebay_send_min_similarity=self.ebay_tab.alert_min_similarity.get(),
                ebay_send_min_profit=self.ebay_tab.alert_min_profit.get()
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
        if hasattr(self, 'csv_compare_path') and self.ebay_tab.csv_compare_path:
            # Try to find the matching config by CSV path
            csv_filename = self.ebay_tab.csv_compare_path.stem  # Get filename without extension
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

        mimic = bool(self.advanced_tab.mimic_var.get())
        print(f"[GUI DEBUG] Checkbox mimic value: {self.advanced_tab.mimic_var.get()}")
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
        """Run Mandarake scraper in background thread - delegated to workers.run_scraper_worker"""
        cancel_flag = threading.Event()
        if self.cancel_requested:
            cancel_flag.set()
        workers.run_scraper_worker(config_path, use_mimic, self.run_queue, cancel_flag)

    def _run_surugaya_scraper(self, config_path: str):
        """Run Suruga-ya scraper in background thread - delegated to SurugayaManager"""
        cancel_flag = threading.Event()
        if self.cancel_requested:
            cancel_flag.set()
        self.surugaya_manager.run_scraper(config_path, cancel_flag)

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
                    self.ebay_tab.browserless_status.set(payload)
                elif message_type == "browserless_progress_stop":
                    self.ebay_tab.browserless_progress.stop()
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
            self.advanced_tab.mimic_var.set(settings.get('mimic', True))  # Default to True for Unicode support

            # Load eBay search settings if they exist
            if hasattr(self, 'browserless_max_results'):
                self.ebay_tab.browserless_max_results.set(settings.get('ebay_max_results', "10"))
            if hasattr(self, 'browserless_max_comparisons'):
                self.browserless_max_comparisons.set(settings.get('ebay_max_comparisons', "MAX"))

            # Load CSV filter settings
            if hasattr(self, 'csv_in_stock_only'):
                self.ebay_tab.csv_in_stock_only.set(settings.get('csv_in_stock_only', True))
            if hasattr(self, 'csv_add_secondary_keyword'):
                self.ebay_tab.csv_add_secondary_keyword.set(settings.get('csv_add_secondary_keyword', False))
        finally:
            self._settings_loaded = True

    def _on_listbox_sash_moved(self, event=None):
        """Track when user manually moves the sash."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._on_listbox_sash_moved(event)

    def _restore_vertical_paned_position(self):
        """Restore the vertical paned window sash position from saved settings."""
        if not hasattr(self, 'mandarake_tab') or not hasattr(self.mandarake_tab, 'vertical_paned'):
            return
        try:
            ratio = self.gui_settings.get('vertical_paned_ratio', 0.5)  # Default 50/50 split
            total_height = self.mandarake_tab.vertical_paned.winfo_height()

            # If height is too small, the window hasn't been laid out yet - schedule retry
            if total_height < 100:
                print(f"[VERTICAL PANED] Height too small ({total_height}px), retrying in 200ms...")
                self.after(200, self._restore_vertical_paned_position)
                return

            sash_pos = int(total_height * ratio)
            self.mandarake_tab.vertical_paned.sash_place(0, 0, sash_pos)
            self._user_vertical_sash_ratio = ratio  # Initialize user ratio to the restored value
            print(f"[VERTICAL PANED] Restored position with ratio: {ratio:.2f} (height={total_height}px, sash={sash_pos}px)")
        except Exception as e:
            print(f"[VERTICAL PANED] Error restoring position: {e}")
            import traceback
            traceback.print_exc()

    def _restore_listbox_paned_position(self):
        """Restore the listbox paned window sash position from saved settings."""
        if not hasattr(self, 'mandarake_tab') or not hasattr(self.mandarake_tab, 'listbox_paned'):
            print(f"[LISTBOX PANED] Widget not found - skipping restore")
            return
        try:
            ratio = self.gui_settings.get('listbox_paned_ratio', 0.65)  # Default 65% for categories, 35% for shops
            total_width = self.mandarake_tab.listbox_paned.winfo_width()

            # If width is too small, the window hasn't been laid out yet - schedule retry
            if total_width < 100:
                print(f"[LISTBOX PANED] Width too small ({total_width}px), retrying in 200ms...")
                self.after(200, self._restore_listbox_paned_position)
                return

            sash_pos = int(total_width * ratio)
            self.mandarake_tab.listbox_paned.sash_place(0, sash_pos, 0)
            self._user_sash_ratio = ratio  # Initialize user ratio to the restored value
            print(f"[LISTBOX PANED] Restored position with ratio: {ratio:.2f} (width={total_width}px, sash={sash_pos}px)")
        except Exception as e:
            print(f"[LISTBOX PANED] Error restoring position: {e}")
            import traceback
            traceback.print_exc()

    def _save_gui_settings(self):
        if not getattr(self, '_settings_loaded', False):
            return
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Save paned positions - use tracked user ratios if available
            listbox_ratio = self.gui_settings.get('listbox_paned_ratio', 0.65)
            if hasattr(self, '_user_sash_ratio') and self._user_sash_ratio is not None:
                listbox_ratio = self._user_sash_ratio

            vertical_ratio = self.gui_settings.get('vertical_paned_ratio', 0.5)
            if hasattr(self, '_user_vertical_sash_ratio') and self._user_vertical_sash_ratio is not None:
                vertical_ratio = self._user_vertical_sash_ratio

            data = {
                'mimic': bool(self.advanced_tab.mimic_var.get()),
                'ebay_max_results': self.ebay_tab.browserless_max_results.get() if hasattr(self, 'browserless_max_results') else "10",
                'ebay_max_comparisons': self.browserless_max_comparisons.get() if hasattr(self, 'browserless_max_comparisons') else "MAX",
                'csv_in_stock_only': bool(self.ebay_tab.csv_in_stock_only.get()) if hasattr(self, 'csv_in_stock_only') else True,
                'csv_add_secondary_keyword': bool(self.ebay_tab.csv_add_secondary_keyword.get()) if hasattr(self, 'csv_add_secondary_keyword') else False,
                'listbox_paned_ratio': listbox_ratio,
                'vertical_paned_ratio': vertical_ratio
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
        value = self.advanced_tab.max_csv_items_var.get().strip()

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
            self.advanced_tab.max_csv_items_var.set(str(current_value))

    def _on_marketplace_toggle(self):
        """Handle marketplace toggle changes"""
        # Save toggle state
        toggles = {
            'mandarake': self.advanced_tab.mandarake_enabled.get(),
            'ebay': self.advanced_tab.ebay_enabled.get(),
            'surugaya': self.advanced_tab.surugaya_enabled.get(),
            'dejapan': self.advanced_tab.dejapan_enabled.get(),
            'alerts': self.advanced_tab.alerts_enabled.get()
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
        """Populate detail categories listbox."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._populate_detail_categories(main_code)

    def _populate_shop_list(self):
        """Populate shop listbox with all available stores."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._populate_shop_list()

    def _on_shop_selected(self, event=None):
        """Handle shop selection from listbox."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._on_shop_selected(event)

    def _on_store_changed(self, event=None):
        """Handle store selection change - reload categories and shops."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._on_store_changed(event)

    def _populate_surugaya_categories(self, main_code=None):
        """Populate detail categories listbox with Suruga-ya categories based on main category."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._populate_surugaya_categories(main_code)

    def _populate_surugaya_shops(self):
        """Populate shop listbox with Suruga-ya shops."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._populate_surugaya_shops()

    def _on_main_category_selected(self, event=None):
        """Handle main category selection."""
        if hasattr(self, 'mandarake_tab'):
            return self.mandarake_tab._on_main_category_selected(event)

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
        """Load results table - delegated to MandarakeTab"""
        if hasattr(self, 'mandarake_tab'):
            self.mandarake_tab.load_results_table(csv_path)

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
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._show_csv_tree_menu(event)

    def _delete_csv_items(self):
        """Delete selected CSV items (supports multi-select)"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._delete_csv_items()

    def _on_csv_double_click(self, event=None):
        """Open product link on double click"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.on_csv_item_double_click(event)

    def _search_csv_by_image_api(self):
        """Search selected CSV item by image using eBay API"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._search_csv_by_image_api()

    def _search_csv_by_image_web(self):
        """Search selected CSV item by image using web method"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._search_csv_by_image_web()

    def _run_csv_web_image_search(self, image_path):
        """Run CSV web image search (helper for threaded execution)"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._run_csv_web_image_search(image_path)

    def _download_missing_csv_images(self):
        """Download missing images from web and save them locally"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._download_missing_csv_images()

    def _download_missing_images_worker(self):
        """Background worker to download missing images"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._download_missing_images_worker()

    def _save_updated_csv(self):
        """Save the updated CSV with new local_image paths"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._save_updated_csv()

    def _save_comparison_results_to_csv(self, comparison_results):
        """Save eBay comparison results back to the CSV file

        Args:
            comparison_results: List of dicts with comparison data including 'mandarake_item', 'similarity', 'best_match', etc.
        """
        if not self.ebay_tab.csv_compare_path or not self.ebay_tab.csv_compare_data:
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
            for row in self.ebay_tab.csv_compare_data:
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
        """Filter config tree based on store filter selection - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager') and hasattr(self, 'config_store_filter'):
            filter_value = self.config_store_filter.get()
            self.config_tree_manager.filter_tree(filter_value)

    def _setup_column_drag(self, tree):
        """Enable drag-to-reorder for treeview columns - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager'):
            self.config_tree_manager.setup_column_drag(tree)

    def _reorder_columns(self, tree, src_col, dst_col):
        """Reorder treeview columns while preserving headings and widths - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager'):
            self.config_tree_manager.reorder_columns(tree, src_col, dst_col)

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
        """Show context menu on config tree - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager'):
            self.config_tree_manager.show_context_menu(event, self.config_tree_menu)

    def _edit_category_from_menu(self):
        """Edit category from right-click menu - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager'):
            self.config_tree_manager.edit_category_from_menu()

    def _show_edit_category_dialog(self, config_path, config, category_code, store, event):
        """Show dialog to edit/add category name - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager'):
            self.config_tree_manager.show_edit_category_dialog(config_path, config, category_code, store, event)

    def _on_config_tree_double_click(self, event):
        """Handle double-click on config tree to edit category - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager'):
            self.config_tree_manager.on_double_click(event)

    def _load_csv_from_config(self):
        """Load CSV file associated with selected config - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager'):
            self.config_tree_manager.load_csv_from_config()

    def _autofill_search_query_from_config(self, config):
        """Auto-fill eBay search query from config keyword - delegated to ConfigTreeManager"""
        if hasattr(self, 'config_tree_manager'):
            self.config_tree_manager.autofill_search_query_from_config(config)

    def _autofill_search_query_from_csv(self):
        """Auto-fill eBay search query from first CSV item's keyword and optionally add secondary keyword"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._autofill_search_query_from_csv()

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
        """Create a new config - delegated to ConfigurationManager"""
        path = self.config_manager.create_new_config(self)
        if not path:
            return

        # Load config to get values for tree
        config = self.config_manager.load_config_from_path(path)
        if not config:
            return

        # Add to tree
        if hasattr(self, 'tree_manager'):
            self.tree_manager.update_tree_item(path, config)

        # Select the new item in config tree
        for item in self.config_tree.get_children():
            if self.config_paths.get(item) == path:
                self.config_tree.selection_set(item)
                self.config_tree.see(item)
                break

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
        """Populate GUI from config - delegated to ConfigurationManager"""
        self.config_manager.populate_gui_from_config(config, self)

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
            self.ebay_tab.browserless_image_path = Path(file_path)
            self.browserless_image_label.config(text=f"Selected: {self.ebay_tab.browserless_image_path.name}", foreground="black")
            print(f"[BROWSERLESS SEARCH] Loaded reference image: {self.ebay_tab.browserless_image_path}")

    def run_scrapy_text_search(self):
        """Run Scrapy eBay search (text only, no image comparison)"""
        query = self.ebay_tab.browserless_query_var.get().strip()
        max_results = int(self.ebay_tab.browserless_max_results.get())
        search_method = self.advanced_tab.ebay_search_method.get()  # "scrapy" or "api"
        
        if self.ebay_tab.ebay_search_manager:
            self.ebay_tab.ebay_search_manager.run_text_search(query, max_results, search_method)

    def run_scrapy_search_with_compare(self):
        """Run Scrapy eBay search WITH image comparison"""
        query = self.ebay_tab.browserless_query_var.get().strip()
        max_results = int(self.ebay_tab.browserless_max_results.get())
        max_comparisons_str = self.browserless_max_comparisons.get()
        max_comparisons = None if max_comparisons_str == "MAX" else int(max_comparisons_str)
        reference_image_path = getattr(self, 'browserless_image_path', None)
        
        if self.ebay_tab.ebay_search_manager:
            self.ebay_tab.ebay_search_manager.run_search_with_compare(query, max_results, max_comparisons, reference_image_path)

    def _run_scrapy_text_search_worker(self):
        """Worker method for eBay text-only search (runs in background thread)"""
        query = self.ebay_tab.browserless_query_var.get().strip()
        max_results = int(self.ebay_tab.browserless_max_results.get())
        search_method = self.advanced_tab.ebay_search_method.get()  # "scrapy" or "api"

        def update_callback(message):
            self.after(0, lambda: self.ebay_tab.browserless_status.set(message))

        def display_callback(results):
            self.after(0, lambda: self._display_browserless_results(results))
            self.after(0, self.ebay_tab.browserless_progress.stop)

        def show_message_callback(title, message):
            # Log to status instead of popup
            self.after(0, lambda: self.ebay_tab.browserless_status.set(message))
            self.after(0, self.ebay_tab.browserless_progress.stop)

        workers.run_scrapy_text_search_worker(
            query, max_results,
            update_callback,
            display_callback,
            show_message_callback,
            search_method=search_method
        )

    def _run_scrapy_search_with_compare_worker(self):
        """Worker method for Scrapy search WITH image comparison (runs in background thread)"""
        query = self.ebay_tab.browserless_query_var.get().strip()
        max_results = int(self.ebay_tab.browserless_max_results.get())
        max_comparisons_str = self.browserless_max_comparisons.get()
        max_comparisons = None if max_comparisons_str == "MAX" else int(max_comparisons_str)

        def update_callback(message):
            self.after(0, lambda: self.ebay_tab.browserless_status.set(message))

        def display_callback(results):
            self.after(0, lambda: self._display_browserless_results(results))
            self.after(0, self.ebay_tab.browserless_progress.stop)

        def show_message_callback(title, message):
            # Log to status instead of popup
            self.after(0, lambda: self.ebay_tab.browserless_status.set(message))
            self.after(0, self.ebay_tab.browserless_progress.stop)

        def create_debug_folder_callback(query):
            return self._create_debug_folder(query)

        workers.run_scrapy_search_with_compare_worker(
            query, max_results, max_comparisons,
            self.ebay_tab.browserless_image_path,
            update_callback,
            display_callback,
            show_message_callback,
            create_debug_folder_callback
        )

    def _run_cached_compare_worker(self):
        """Worker method to compare reference image with CACHED eBay results (State 1)"""
        query = self.ebay_tab.browserless_query_var.get().strip()
        max_comparisons_str = self.browserless_max_comparisons.get()
        max_comparisons = None if max_comparisons_str == "MAX" else int(max_comparisons_str)

        def update_callback(message):
            self.after(0, lambda: self.ebay_tab.browserless_status.set(message))

        def display_callback(results):
            self.after(0, lambda: self._display_browserless_results(results))
            self.after(0, self.ebay_tab.browserless_progress.stop)

        def show_message_callback(title, message):
            self.after(0, lambda: messagebox.showerror(title, message))
            self.after(0, self.ebay_tab.browserless_progress.stop)

        def create_debug_folder_callback(query):
            return self._create_debug_folder(query)

        workers.run_cached_compare_worker(
            query, max_comparisons,
            self.ebay_tab.browserless_image_path,
            self.ebay_tab.browserless_results_data,
            update_callback,
            display_callback,
            show_message_callback,
            create_debug_folder_callback
        )

    def clear_browserless_results(self):
        """Clear browserless search results using eBay search manager."""
        if self.ebay_tab.ebay_search_manager:
            self.ebay_tab.ebay_search_manager.clear_results()

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
            self.ebay_tab.csv_compare_path = csv_path
            self.ebay_tab.csv_compare_label.config(text=f"Loaded: {csv_path.name}", foreground="black")
            print(f"[CSV WORKER] Loading CSV: {csv_path}")

            # Load CSV data
            self.ebay_tab.csv_compare_data = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.ebay_tab.csv_compare_data.append(row)

            # Set in-stock filter from config if provided
            if autofill_from_config:
                show_in_stock_only = autofill_from_config.get('csv_show_in_stock_only', False)
                self.ebay_tab.csv_in_stock_only.set(show_in_stock_only)
                print(f"[CSV WORKER] Set in-stock filter to: {show_in_stock_only}")

            # Display with filter applied
            self.filter_csv_items()

            # Auto-fill eBay search query
            if autofill_from_config:
                self._autofill_search_query_from_config(autofill_from_config)
            else:
                self._autofill_search_query_from_csv()

            print(f"[CSV WORKER] Loaded {len(self.ebay_tab.csv_compare_data)} items")
            return True

        except Exception as e:
            print(f"[CSV WORKER ERROR] {e}")
            return False

    def load_csv_for_comparison(self):
        """Load CSV file for batch comparison"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.load_csv_for_comparison()
        else:
            messagebox.showerror("Error", "CSV comparison manager not initialized")

    def filter_csv_items(self):
        """Filter and display CSV items based on in-stock filter - fast load, thumbnails loaded on demand"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.filter_csv_items()

    def _load_csv_thumbnails_worker(self, filtered_items):
        """Background worker to load CSV thumbnails without blocking UI"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._load_csv_thumbnails_worker(filtered_items)

    def _on_csv_filter_changed(self):
        """Handle CSV filter changes - filter items (settings saved on close)"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.on_csv_filter_changed()

    def _on_recent_hours_changed(self, *args):
        """Handle latest additions timeframe change - refresh CSV view if loaded"""
        # Don't refresh while loading a config
        if getattr(self, '_loading_config', False):
            return
        # Only refresh if CSV is loaded
        if hasattr(self, 'csv_compare_data') and self.ebay_tab.csv_compare_data:
            self.filter_csv_items()

    def _on_csv_column_resize(self, event):
        """Handle column resize event to reload thumbnails with new size"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.on_csv_column_resize(event)

    def _on_csv_item_double_click(self, event):
        """Handle double-click on CSV item to open URL in browser"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.on_csv_item_double_click(event)

    def toggle_csv_thumbnails(self):
        """Toggle visibility of thumbnails in CSV treeview"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.toggle_csv_thumbnails()

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
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._add_full_title_to_search()

    def _add_secondary_keyword_from_csv(self):
        """Add selected CSV item's secondary keyword to the eBay search query field"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._add_secondary_keyword_from_csv()

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
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.on_csv_item_selected(event)

    def compare_selected_csv_item(self):
        """Compare selected CSV item with eBay"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.compare_selected_csv_item()

    def _run_csv_comparison_async(self):
        """Run CSV comparison without confirmation (for scheduled tasks)"""
        self.compare_all_csv_items(skip_confirmation=True)

    def compare_all_csv_items(self, skip_confirmation=False):
        """Compare all visible CSV items with eBay"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.compare_all_csv_items(skip_confirmation)

    def compare_new_csv_items(self):
        """Compare only items that haven't been compared yet"""
        if self.ebay_tab.csv_comparison_manager:
            # CSV manager's method has slightly different logic than compare_all
            # It tracks which items have been compared before
            # For now, delegate to compare_all as a fallback
            # TODO: Implement proper compare_new_items() in CSV manager if needed
            self.ebay_tab.csv_comparison_manager.compare_all_csv_items(skip_confirmation=False)

    def clear_comparison_results(self):
        """Clear all eBay comparison results from the loaded CSV"""
        if not self.ebay_tab.csv_compare_data or not self.ebay_tab.csv_compare_path:
            messagebox.showwarning("No CSV", "Please load a CSV file first")
            return

        # Count items with comparison results
        compared_count = sum(1 for item in self.ebay_tab.csv_compare_data if item.get('ebay_compared'))

        if compared_count == 0:
            # Log to status instead of popup
            self.ebay_tab.browserless_status.set("No comparison results to clear")
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
                for item in self.ebay_tab.csv_compare_data:
                    item['ebay_compared'] = ''
                    item['ebay_match_found'] = ''
                    item['ebay_best_match_title'] = ''
                    item['ebay_similarity'] = ''
                    item['ebay_price'] = ''
                    item['ebay_profit_margin'] = ''

                # Save updated CSV
                self._save_updated_csv()

                # Log to status instead of popup
                self.ebay_tab.browserless_status.set(f"Cleared comparison results for {compared_count} items")
                print(f"[CLEAR RESULTS] Cleared comparison results for {compared_count} items")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear results: {e}")
                print(f"[CLEAR RESULTS ERROR] {e}")

    def _compare_csv_items_worker(self, items, search_query):
        """Worker to compare CSV items with eBay - OPTIMIZED with caching (runs in background thread)"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._compare_csv_items_worker(items, search_query)

    def _compare_csv_items_individually_worker(self, items, base_search_query):
        """Worker to compare CSV items individually - each item gets its own eBay search"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager._compare_csv_items_individually_worker(items, base_search_query)

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
        if not self.ebay_tab.all_comparison_results:
            return

        # Check if results have similarity/profit data (from comparison)
        has_comparison_data = any('similarity' in r and 'profit_margin' in r for r in self.ebay_tab.all_comparison_results)

        if has_comparison_data:
            # Sort results by similarity (descending), then by profit margin (descending)
            sorted_results = sorted(
                self.ebay_tab.all_comparison_results,
                key=lambda x: (x.get('similarity', 0), x.get('profit_margin', 0)),
                reverse=True
            )
            self._display_csv_comparison_results(sorted_results)
        else:
            # No comparison data yet, show all results
            self._display_csv_comparison_results(self.ebay_tab.all_comparison_results)

    def _display_csv_comparison_results(self, results):
        """Display CSV comparison results - delegated to CSVComparisonManager"""
        if self.ebay_tab.csv_comparison_manager:
            self.ebay_tab.csv_comparison_manager.display_csv_comparison_results(results)

    def open_browserless_url(self, event):
        """Open eBay or Mandarake URL based on which column is double-clicked"""
        selection = self.ebay_tab.browserless_tree.selection()
        if not selection:
            return

        item_id = selection[0]

        # Identify which column was clicked
        column = self.ebay_tab.browserless_tree.identify_column(event.x)
        # Column format is '#0', '#1', '#2', etc. where #0 is thumbnail, #1 is first data column

        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.ebay_tab.browserless_results_data):
                result = self.ebay_tab.browserless_results_data[index]

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
                print(f"[URL DEBUG] Index {index} out of range (data length: {len(self.ebay_tab.browserless_results_data)})")
        except (ValueError, IndexError) as e:
            print(f"[BROWSERLESS SEARCH] Error opening URL: {e}")
            pass

    def _show_browserless_context_menu(self, event):
        """Show context menu for eBay results treeview"""
        # Select the item under cursor
        item = self.ebay_tab.browserless_tree.identify_row(event.y)
        if item:
            self.ebay_tab.browserless_tree.selection_set(item)

            # Create context menu
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Send to Review/Alerts", command=self._send_browserless_to_review)
            menu.add_separator()
            menu.add_command(label="Open eBay URL", command=lambda: self.open_browserless_url(event))
            if self.ebay_tab.browserless_results_data and int(item) - 1 < len(self.ebay_tab.browserless_results_data):
                result = self.ebay_tab.browserless_results_data[int(item) - 1]
                if result.get('mandarake_url'):
                    menu.add_command(label="Open Mandarake URL", command=lambda: webbrowser.open(result['mandarake_url']))

            # Show menu at cursor position
            menu.post(event.x_root, event.y_root)

    def _send_browserless_to_review(self):
        """Send selected eBay result to Review/Alerts tab"""
        selection = self.ebay_tab.browserless_tree.selection()
        if not selection:
            self.ebay_tab.browserless_status.set("No item selected")
            return

        item_id = selection[0]
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.ebay_tab.browserless_results_data):
                result = self.ebay_tab.browserless_results_data[index]

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
                        self.ebay_tab.browserless_status.set(f"Sent '{result['title'][:50]}...' to Review/Alerts")
                        print(f"[SEND TO REVIEW] Added item to alerts: {result['title']}")
                    else:
                        self.ebay_tab.browserless_status.set("Could not find comparison data for this item")
                else:
                    # This is a raw eBay search result without comparison data
                    self.ebay_tab.browserless_status.set("Item has no comparison data - use 'Compare Selected' first")
                    print("[SEND TO REVIEW] Item has no comparison data")
        except (ValueError, IndexError) as e:
            print(f"[SEND TO REVIEW] Error: {e}")
            self.ebay_tab.browserless_status.set(f"Error sending to review: {e}")

    def _display_browserless_results(self, results):
        """Display browserless search results - delegated to EbaySearchManager"""
        if self.ebay_tab.ebay_search_manager:
            self.ebay_tab.ebay_search_manager.display_browserless_results(results)

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
