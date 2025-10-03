"""Suruga-ya store subtab"""

from typing import Dict, List
from gui.base_store_tab import BaseStoreTab
from store_codes.surugaya_codes import (
    SURUGAYA_MAIN_CATEGORIES,
    SURUGAYA_CATEGORIES,
    SURUGAYA_SHOPS
)


class SurugayaStoreTab(BaseStoreTab):
    """Suruga-ya subtab for unified Stores tab"""

    def __init__(self, parent, settings_manager, results_callback):
        super().__init__(parent, settings_manager, results_callback, "Suruga-ya")

    def _get_main_categories(self) -> Dict[str, str]:
        """Return main categories for Suruga-ya"""
        return SURUGAYA_MAIN_CATEGORIES

    def _get_detailed_categories(self) -> Dict[str, str]:
        """Return detailed categories for Suruga-ya"""
        return SURUGAYA_CATEGORIES

    def _get_shops(self) -> Dict[str, str]:
        """Return shops for Suruga-ya"""
        return SURUGAYA_SHOPS

    def _add_store_options(self):
        """Add Suruga-ya-specific options"""
        # Show out of stock items
        self.show_out_of_stock_var = self.options_panel.add_checkbox(
            'show_out_of_stock',
            'Show Out of Stock Items',
            default=False
        )

        # Sort order (Suruga-ya specific)
        self.sort_var = self.options_panel.add_combobox(
            'sort_order',
            'Sort by:',
            values=['Newest', 'Price: Low to High', 'Price: High to Low'],
            default='Newest'
        )

    def _run_scraper(self, config: Dict) -> List[Dict]:
        """Execute Suruga-ya scraper"""
        from scrapers.surugaya_scraper import SurugayaScraper

        scraper = SurugayaScraper()

        # Determine search parameters
        keyword = config.get('keyword', '')
        url = config.get('url', '')
        category = config.get('category', '7')
        shop_code = config.get('shop', 'all')
        max_pages = config.get('max_pages', 5)
        show_out_of_stock = config.get('store_specific', {}).get('surugaya', {}).get('show_out_of_stock', False)

        # If URL is provided, extract parameters from it
        if url:
            # TODO: Parse URL to extract search parameters
            pass

        # Calculate max results (Suruga-ya returns ~50 items per page)
        max_results = max_pages * 50

        # Run search
        results = scraper.search(
            keyword=keyword,
            category=category,
            shop_code=shop_code,
            max_results=max_results,
            show_out_of_stock=show_out_of_stock
        )

        return results
