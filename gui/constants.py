"""Constants and configuration for the Mandarake Scraper GUI."""

from pathlib import Path
from mandarake_codes import MANDARAKE_STORES, MANDARAKE_MAIN_CATEGORIES

# Store options for dropdown
STORE_OPTIONS = [
    (code, info['en'])
    for code, info in sorted(
        MANDARAKE_STORES.items(),
        key=lambda item: int(item[0]) if item[0].lstrip('-').isdigit() else item[0],
    )
]

# Main category options for dropdown
MAIN_CATEGORY_OPTIONS = [
    (code, data['en']) for code, data in sorted(MANDARAKE_MAIN_CATEGORIES.items())
]

# Recent time filter options
RECENT_OPTIONS = [
    ("All (default)", None),
    ("Last 6 hours", 6),
    ("Last 12 hours", 12),
    ("Last 24 hours", 24),
    ("Last 72 hours", 72),
]

# Settings file path (separate from search configs)
SETTINGS_PATH = Path('.mandarake/gui_settings.json')

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
