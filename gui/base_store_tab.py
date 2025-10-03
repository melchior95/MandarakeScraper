"""Base class for store subtabs (Mandarake, Suruga-ya, etc.)"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, List
from abc import ABC, abstractmethod
import threading
import queue

from gui.shared_ui_components import (
    URLKeywordPanel,
    CategoryShopPanel,
    StoreOptionsPanel
)


class BaseStoreTab(ttk.Frame, ABC):
    """Abstract base class for store subtabs"""

    def __init__(self, parent, settings_manager, results_callback, store_name: str):
        super().__init__(parent)

        self.settings = settings_manager
        self.results_callback = results_callback  # Callback to send results to parent
        self.store_name = store_name
        self.store_id = store_name.lower().replace('-', '').replace(' ', '')

        # Queue for thread-safe UI updates
        self.queue = queue.Queue()

        # Search worker thread
        self.worker_thread = None

        # Create UI
        self._create_ui()

        # Start queue processing
        self._process_queue()

    def _create_ui(self):
        """Create standard layout for store tab"""
        # Main container with paned window (3 columns)
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Left panel - Search controls (URL, Keyword, Categories, Shops)
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # URL + Keyword panel
        self.url_keyword_panel = URLKeywordPanel(
            left_frame,
            on_change=self._on_search_change
        )
        self.url_keyword_panel.pack(fill=tk.X, padx=2, pady=2)

        # Category + Shop panel
        self.category_shop_panel = CategoryShopPanel(
            left_frame,
            main_categories=self._get_main_categories(),
            detailed_categories=self._get_detailed_categories(),
            shops=self._get_shops(),
            on_change=self._on_search_change
        )
        self.category_shop_panel.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Middle panel - Store-specific options
        middle_frame = ttk.Frame(main_paned)
        main_paned.add(middle_frame, weight=0)

        # Options panel
        self.options_panel = StoreOptionsPanel(middle_frame)
        self.options_panel.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Add store-specific options
        self._add_store_options()

        # Common options
        common_frame = ttk.LabelFrame(middle_frame, text="Common Options", padding=5)
        common_frame.pack(fill=tk.X, padx=5, pady=5)

        # Max pages spinner
        max_pages_frame = ttk.Frame(common_frame)
        max_pages_frame.pack(anchor=tk.W, padx=5, pady=3)
        ttk.Label(max_pages_frame, text="Max Pages:").pack(side=tk.LEFT)
        self.max_pages_var = tk.IntVar(value=5)
        ttk.Spinbox(max_pages_frame, from_=1, to=100,
                    textvariable=self.max_pages_var, width=10).pack(side=tk.LEFT, padx=5)

        # CSV options frame
        csv_frame = ttk.LabelFrame(common_frame, text="CSV Options", padding=5)
        csv_frame.pack(fill=tk.X, padx=5, pady=5)

        self.csv_show_in_stock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(csv_frame, text="Show in-stock items only",
                        variable=self.csv_show_in_stock_var).pack(anchor=tk.W, padx=5, pady=2)

        self.csv_add_secondary_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(csv_frame, text="Add secondary keyword from title",
                        variable=self.csv_add_secondary_var).pack(anchor=tk.W, padx=5, pady=2)

        # Action buttons
        btn_frame = ttk.Frame(middle_frame)
        btn_frame.pack(anchor=tk.W, padx=10, pady=10)

        self.search_btn = ttk.Button(btn_frame, text="Search", command=self._search)
        self.search_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(btn_frame, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Schedule", command=self._schedule).pack(side=tk.LEFT, padx=2)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            middle_frame,
            mode='indeterminate',
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(middle_frame, textvariable=self.status_var,
                                 relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(fill=tk.X, padx=10, pady=5)

    @abstractmethod
    def _get_main_categories(self) -> Dict[str, str]:
        """Return main categories for this store"""
        pass

    @abstractmethod
    def _get_detailed_categories(self) -> Dict[str, str]:
        """Return detailed categories for this store"""
        pass

    @abstractmethod
    def _get_shops(self) -> Dict[str, str]:
        """Return shops for this store"""
        pass

    @abstractmethod
    def _add_store_options(self):
        """Add store-specific options to options panel"""
        pass

    @abstractmethod
    def _run_scraper(self, config: Dict) -> List[Dict]:
        """Execute scraper with config and return results"""
        pass

    def _search(self):
        """Execute search for this store"""
        # Disable search button
        self.search_btn.config(state='disabled')
        self.progress_bar.start(10)
        self.status_var.set(f"Searching {self.store_name}...")

        # Get current config
        config = self.get_config()

        # Run in background thread
        self.worker_thread = threading.Thread(
            target=self._search_worker,
            args=(config,),
            daemon=True
        )
        self.worker_thread.start()

    def _search_worker(self, config: Dict):
        """Background worker for search"""
        try:
            # Run scraper
            results = self._run_scraper(config)

            # Post results to queue
            self.queue.put(('results', results))
            self.queue.put(('status', f"Found {len(results)} items from {self.store_name}"))

        except Exception as e:
            import traceback
            error_msg = f"Search failed: {e}\n{traceback.format_exc()}"
            self.queue.put(('error', error_msg))

        finally:
            self.queue.put(('complete', None))

    def _process_queue(self):
        """Process messages from background thread"""
        try:
            while True:
                msg_type, msg_data = self.queue.get_nowait()

                if msg_type == 'results':
                    # Send results to parent via callback
                    self.results_callback(msg_data, self.store_id)

                elif msg_type == 'status':
                    self.status_var.set(msg_data)

                elif msg_type == 'error':
                    self.status_var.set("Error occurred")
                    print(f"Error: {msg_data}")

                elif msg_type == 'complete':
                    # Re-enable search button
                    self.search_btn.config(state='normal')
                    self.progress_bar.stop()

        except queue.Empty:
            pass

        # Schedule next check
        self.after(100, self._process_queue)

    def _clear(self):
        """Clear all fields"""
        self.url_keyword_panel.set_values('', '')
        self.category_shop_panel.main_category_var.set('')
        self.category_shop_panel.category_listbox.selection_clear(0, tk.END)
        self.category_shop_panel.shop_listbox.selection_clear(0, tk.END)

    def _schedule(self):
        """Schedule recurring search"""
        # TODO: Implement scheduling (reuse existing schedule system)
        from tkinter import messagebox
        messagebox.showinfo("Schedule", "Scheduling feature will be implemented")

    def _on_search_change(self, *args):
        """Called when search parameters change"""
        # Auto-save config if needed
        # For now, just mark as changed
        pass

    def load_config(self, config: Dict):
        """Load config into UI"""
        # Load URL and keyword
        self.url_keyword_panel.set_values(
            url=config.get('url', ''),
            keyword=config.get('keyword', '')
        )

        # Load category
        category = config.get('category', '')
        if category:
            self.category_shop_panel.set_category(category)

        # Load shop
        shop = config.get('shop', '')
        if shop:
            self.category_shop_panel.set_shop(shop)

        # Load max pages
        self.max_pages_var.set(config.get('max_pages', 5))

        # Load CSV options
        self.csv_show_in_stock_var.set(config.get('csv_show_in_stock_only', True))
        self.csv_add_secondary_var.set(config.get('csv_add_secondary_keyword', False))

        # Load store-specific options
        store_specific = config.get('store_specific', {}).get(self.store_id, {})
        if store_specific:
            self.options_panel.set_values(store_specific)

    def get_config(self) -> Dict:
        """Get current config from UI"""
        url_keyword = self.url_keyword_panel.get_values()
        category_shop = self.category_shop_panel.get_values()

        config = {
            'store': self.store_id,
            'url': url_keyword['url'],
            'keyword': url_keyword['keyword'],
            'main_category': category_shop.get('main_category', ''),
            'category': category_shop.get('category', ''),
            'shop': category_shop.get('shop', ''),
            'max_pages': self.max_pages_var.get(),
            'csv_show_in_stock_only': self.csv_show_in_stock_var.get(),
            'csv_add_secondary_keyword': self.csv_add_secondary_var.get(),
            'store_specific': {
                self.store_id: self.options_panel.get_values()
            }
        }
        return config
