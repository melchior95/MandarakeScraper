"""
Suruga-ya Tab

GUI tab for searching Suruga-ya marketplace
"""

import sys
from pathlib import Path
from tkinter import ttk
import tkinter as tk
from typing import Dict

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.base_marketplace_tab import BaseMarketplaceTab
from scrapers.surugaya_scraper import SurugayaScraper
from surugaya_codes import SURUGAYA_MAIN_CATEGORIES, SURUGAYA_SHOPS


class SurugayaTab(BaseMarketplaceTab):
    """Tab for Suruga-ya marketplace searches"""

    def __init__(self, parent, settings_manager, alert_manager):
        """Initialize Suruga-ya tab"""
        # Initialize scraper
        self.scraper = SurugayaScraper()

        # Call parent init (creates UI)
        super().__init__(parent, settings_manager, alert_manager, "Suruga-ya")

        # Load saved settings
        surugaya_settings = self.settings.get_surugaya_settings()
        self.category_var.set(surugaya_settings.get('default_category', '7'))
        self.shop_var.set(surugaya_settings.get('default_shop', 'all'))
        self.show_out_of_stock_var.set(surugaya_settings.get('show_out_of_stock', False))

    def _create_marketplace_specific_controls(self, parent, start_row: int):
        """Create Suruga-ya specific controls (category, shop, filters)"""
        pad = {'padx': 5, 'pady': 3}

        # Category dropdown
        ttk.Label(parent, text="Category:").grid(row=start_row, column=0, sticky=tk.W, **pad)
        self.category_var = tk.StringVar(value='7')

        # Create category dropdown
        category_options = [(code, name) for code, name in SURUGAYA_MAIN_CATEGORIES.items()]
        category_options.sort(key=lambda x: x[1])  # Sort by name

        category_combo = ttk.Combobox(
            parent,
            textvariable=self.category_var,
            values=[f"{code} - {name}" for code, name in category_options],
            width=40,
            state='readonly'
        )
        category_combo.grid(row=start_row, column=1, columnspan=2, sticky=tk.EW, **pad)

        # Extract code when selection changes
        def on_category_change(*args):
            value = self.category_var.get()
            if ' - ' in value:
                code = value.split(' - ')[0]
                self.category_code = code
            else:
                self.category_code = value

        self.category_var.trace_add('write', on_category_change)
        self.category_code = '7'  # Default

        start_row += 1

        # Shop dropdown
        ttk.Label(parent, text="Shop:").grid(row=start_row, column=0, sticky=tk.W, **pad)
        self.shop_var = tk.StringVar(value='all')

        shop_options = [('all', 'All Stores')]
        shop_options.extend([(code, name) for code, name in SURUGAYA_SHOPS.items() if code != 'all'])

        shop_combo = ttk.Combobox(
            parent,
            textvariable=self.shop_var,
            values=[name for code, name in shop_options],
            width=30,
            state='readonly'
        )
        shop_combo.grid(row=start_row, column=1, sticky=tk.W, **pad)

        # Extract shop code when selection changes
        self.shop_code_map = {name: code for code, name in shop_options}

        def on_shop_change(*args):
            shop_name = self.shop_var.get()
            self.shop_code = self.shop_code_map.get(shop_name, 'all')

        self.shop_var.trace_add('write', on_shop_change)
        self.shop_code = 'all'  # Default

        start_row += 1

        # Filters
        filter_frame = ttk.LabelFrame(parent, text="Filters", padding=5)
        filter_frame.grid(row=start_row, column=0, columnspan=4, sticky=tk.EW, **pad)
        start_row += 1

        # Show out of stock checkbox
        self.show_out_of_stock_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            filter_frame,
            text="Show out of stock items",
            variable=self.show_out_of_stock_var
        ).grid(row=0, column=0, sticky=tk.W, **pad)

    def _get_tree_columns(self) -> tuple:
        """Define columns for results tree"""
        return ('title', 'price', 'condition', 'stock_status', 'publisher')

    def _get_column_widths(self) -> Dict[str, int]:
        """Define column widths"""
        return {
            'title': 350,
            'price': 80,
            'condition': 80,
            'stock_status': 100,
            'publisher': 150
        }

    def _format_tree_values(self, item: Dict) -> tuple:
        """Format item data for tree display"""
        price_str = f"¥{item['price']:.0f}" if item['price'] > 0 else "N/A"

        publisher = item.get('extra', {}).get('publisher', '')
        if publisher:
            # Remove brackets
            publisher = publisher.replace('[', '').replace(']', '')

        return (
            item['title'],
            price_str,
            item['condition'],
            item['stock_status'],
            publisher
        )

    def _search_worker(self):
        """Background worker for Suruga-ya search"""
        try:
            # Get search parameters
            keyword = self.keyword_var.get().strip()
            max_results = int(self.max_results_var.get())
            category = getattr(self, 'category_code', '7')
            shop_code = getattr(self, 'shop_code', 'all')
            show_out_of_stock = self.show_out_of_stock_var.get()

            # Update status
            self.queue.put(('status', f"Searching Suruga-ya for '{keyword}'..."))

            # Perform search
            results = self.scraper.search(
                keyword=keyword,
                category=category,
                shop_code=shop_code,
                max_results=max_results,
                show_out_of_stock=show_out_of_stock
            )

            # Post results to queue
            if results:
                self.queue.put(('results', results))
                self.queue.put(('status', f"Found {len(results)} items on Suruga-ya"))
            else:
                self.queue.put(('status', "No results found on Suruga-ya"))
                self.queue.put(('error', "No items found. Try different keywords or category."))

            # Signal completion
            self.queue.put(('complete', None))

        except Exception as e:
            import traceback
            error_msg = f"Search failed: {e}\n{traceback.format_exc()}"
            self.queue.put(('error', error_msg))
            self.queue.put(('complete', None))

    def _convert_to_alert_format(self, item: Dict) -> Dict:
        """Convert Suruga-ya item to alert format"""
        return {
            'title': item.get('title', ''),
            'price': item.get('price', 0),
            'url': item.get('url', ''),
            'image_url': item.get('image_url', ''),
            'marketplace': 'Suruga-ya',
            'condition': item.get('condition', ''),
            'stock_status': item.get('stock_status', ''),
            'status': 'Pending',
            'extra': item.get('extra', {})
        }

    def on_closing(self):
        """Save settings when tab is closed"""
        # Save current settings
        self.settings.save_surugaya_settings(
            default_category=getattr(self, 'category_code', '7'),
            default_shop=getattr(self, 'shop_code', 'all'),
            show_out_of_stock=self.show_out_of_stock_var.get()
        )

        # Close scraper
        if hasattr(self, 'scraper'):
            self.scraper.close()
