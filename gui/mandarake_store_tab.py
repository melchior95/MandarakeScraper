"""Mandarake store subtab"""

from typing import Dict, List
from gui.base_store_tab import BaseStoreTab
from store_codes.mandarake_codes import (
    MANDARAKE_MAIN_CATEGORIES,
    MANDARAKE_ALL_CATEGORIES,
    MANDARAKE_STORES
)


class MandarakeStoreTab(BaseStoreTab):
    """Mandarake subtab for unified Stores tab"""

    def __init__(self, parent, settings_manager, results_callback):
        super().__init__(parent, settings_manager, results_callback, "Mandarake")

    def _get_main_categories(self) -> Dict[str, str]:
        """Return main categories for Mandarake"""
        # Convert from dict format {code: {'en': name, 'jp': name}}
        return {
            code: data['en']
            for code, data in MANDARAKE_MAIN_CATEGORIES.items()
        }

    def _get_detailed_categories(self) -> Dict[str, str]:
        """Return detailed categories for Mandarake"""
        # Convert from dict format
        return {
            code: data['en']
            for code, data in MANDARAKE_ALL_CATEGORIES.items()
        }

    def _get_shops(self) -> Dict[str, str]:
        """Return shops for Mandarake"""
        # Convert from dict format
        shops = {}
        for code, data in MANDARAKE_STORES.items():
            # Skip auction categories
            if code in ['-14', '14']:
                continue
            shops[code] = data['en']

        return shops

    def _add_store_options(self):
        """Add Mandarake-specific options"""
        # Hide sold out items
        self.hide_sold_var = self.options_panel.add_checkbox(
            'hide_sold_out',
            'Hide Sold Out Items',
            default=False
        )

        # Show adult content
        self.show_adult_var = self.options_panel.add_checkbox(
            'show_adult',
            'Show Adult Content (18+)',
            default=False
        )

        # Sort order
        self.sort_var = self.options_panel.add_combobox(
            'sort_order',
            'Sort by:',
            values=['Newest', 'Price: Low to High', 'Price: High to Low', 'Title A-Z'],
            default='Newest'
        )

    def _run_scraper(self, config: Dict) -> List[Dict]:
        """Execute Mandarake scraper"""
        # Import the existing mandarake_scraper
        from mandarake_scraper import MandarakeScraper

        # Create scraper with config
        scraper = MandarakeScraper(config)

        # Run scrape
        results = scraper.scrape()

        return results
