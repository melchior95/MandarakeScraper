#!/usr/bin/env python3
"""Mandarake Scraper GUI configuration tool - Refactored version."""

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


class ScraperGUI(tk.Tk):
    """GUI wrapper for Mandarake scraper configuration - Refactored."""

    def __init__(self):
        super().__init__()

        # Initialize settings manager
        self.settings = get_settings_manager()

        # Fetch current USD/JPY exchange rate using refactored utility
        self.usd_jpy_rate = utils.fetch_exchange_rate()
        print(f"[EXCHANGE RATE] USD/JPY: {self.usd_jpy_rate}")

        self.title("Mandarake Scraper GUI (Refactored)")

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

        # State variables
        self.scraper_thread = None
        self.scraper_queue = queue.Queue()
        self.cancel_flag = threading.Event()

        # Create menu bar
        self._create_menu_bar()

        # Create main UI
        self._build_widgets()

        # Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start queue polling
        self._poll_queue()

    def _create_menu_bar(self):
        """Create menu bar - placeholder for full implementation."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Config", command=self.load_config)
        file_menu.add_command(label="Save Config", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

    def _build_widgets(self):
        """Build main UI - simplified for demonstration."""
        # Create notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Search tab
        search_frame = ttk.Frame(notebook)
        notebook.add(search_frame, text="Search")

        # Keyword input
        ttk.Label(search_frame, text="Keyword:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.keyword_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.keyword_var, width=40).grid(row=0, column=1, sticky='ew', padx=5, pady=5)

        # Category selection
        ttk.Label(search_frame, text="Main Category:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.main_category_var = tk.StringVar()
        category_combo = ttk.Combobox(search_frame, textvariable=self.main_category_var, width=37)
        category_combo['values'] = [f"{code} - {name}" for code, name in MAIN_CATEGORY_OPTIONS]
        category_combo.grid(row=1, column=1, sticky='ew', padx=5, pady=5)

        # Shop selection
        ttk.Label(search_frame, text="Shop:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.shop_var = tk.StringVar(value="0")
        shop_combo = ttk.Combobox(search_frame, textvariable=self.shop_var, width=37)
        shop_combo['values'] = [f"{code} - {name}" for code, name in STORE_OPTIONS]
        shop_combo.grid(row=2, column=1, sticky='ew', padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(search_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Run Now", command=self.run_now).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Load Config", command=self.load_config).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Save Config", command=self.save_config).pack(side='left', padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(search_frame, textvariable=self.status_var, relief='sunken').grid(row=4, column=0, columnspan=2, sticky='ew', padx=5, pady=5)

        search_frame.columnconfigure(1, weight=1)

    def load_config(self):
        """Load configuration from file."""
        file_path = filedialog.askopenfilename(
            title="Load Configuration",
            initialdir="configs",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Populate UI from config
            self.keyword_var.set(config.get('keyword', ''))
            self.shop_var.set(str(config.get('shop', '0')))

            self.status_var.set(f"Loaded: {Path(file_path).name}")
            messagebox.showinfo("Success", f"Configuration loaded from {Path(file_path).name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def save_config(self):
        """Save configuration to file using refactored utilities."""
        config = self._collect_config()

        # Use refactored utility to suggest filename
        suggested = utils.suggest_config_filename(config)

        file_path = filedialog.asksaveasfilename(
            title="Save Configuration",
            initialdir="configs",
            initialfile=suggested,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.status_var.set(f"Saved: {Path(file_path).name}")
            messagebox.showinfo("Success", f"Configuration saved to {Path(file_path).name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def run_now(self):
        """Execute scraper using refactored worker."""
        if self.scraper_thread and self.scraper_thread.is_alive():
            messagebox.showwarning("Warning", "Scraper is already running")
            return

        config = self._collect_config()

        # Validate config
        if not config.get('keyword'):
            messagebox.showerror("Error", "Please enter a search keyword")
            return

        # Clear cancel flag
        self.cancel_flag.clear()

        # Start worker thread using refactored workers module
        self.scraper_thread = threading.Thread(
            target=workers.run_scraper_worker,
            args=(self.scraper_queue, config, self.cancel_flag),
            daemon=True
        )
        self.scraper_thread.start()
        self.status_var.set("Scraping in progress...")

    def _collect_config(self) -> dict:
        """Collect configuration from UI."""
        # Extract category code
        category_text = self.main_category_var.get()
        category_code = utils.extract_code(category_text) if category_text else None

        # Extract shop code
        shop_text = self.shop_var.get()
        shop_code = utils.extract_code(shop_text) if shop_text else "0"

        config = {
            'keyword': self.keyword_var.get().strip(),
            'category': [category_code] if category_code else [],
            'shop': shop_code or "0",
            'output_csv': True,
            'csv_path': str(Path('results') / utils.generate_csv_filename({
                'keyword': self.keyword_var.get().strip(),
                'category': [category_code] if category_code else [],
                'shop': shop_code or "0",
            })),
        }

        return config

    def _poll_queue(self):
        """Poll queue for worker messages."""
        try:
            while True:
                msg = self.scraper_queue.get_nowait()
                msg_type = msg.get('type')

                if msg_type == 'status':
                    self.status_var.set(msg.get('message', ''))
                elif msg_type == 'complete':
                    self.status_var.set("Scraping complete!")
                    messagebox.showinfo("Success", msg.get('message', 'Scraping completed'))
                elif msg_type == 'error':
                    self.status_var.set("Error occurred")
                    messagebox.showerror("Error", msg.get('message', 'Unknown error'))

        except queue.Empty:
            pass

        # Schedule next poll
        self.after(100, self._poll_queue)

    def on_closing(self):
        """Handle window close."""
        # Save window settings
        self._save_window_settings()

        # Cancel any running threads
        self.cancel_flag.set()

        # Wait for threads to finish (with timeout)
        if self.scraper_thread and self.scraper_thread.is_alive():
            self.scraper_thread.join(timeout=2.0)

        self.destroy()

    def _save_window_settings(self):
        """Save window geometry and state."""
        try:
            # Parse geometry
            geometry = self.geometry()
            width, height, x, y = utils.parse_geometry(geometry) if hasattr(utils, 'parse_geometry') else (780, 760, 100, 100)

            window_settings = {
                'width': width,
                'height': height,
                'x': x,
                'y': y,
                'maximized': self.state() == 'zoomed'
            }

            self.settings.save_window_settings(window_settings)
        except Exception as e:
            print(f"Error saving window settings: {e}")


def main():
    """Entry point for refactored GUI."""
    app = ScraperGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
