"""Utility functions for the Mandarake Scraper GUI."""

import re
import unicodedata
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple


def slugify(value: str) -> str:
    """Convert string to filesystem-safe slug."""
    if not value:
        return 'all'
    value = str(value).strip()

    # Handle Unicode characters better - create readable ASCII representation
    try:
        # Try to normalize and convert to ASCII
        normalized = unicodedata.normalize('NFKD', value)
        ascii_value = normalized.encode('ascii', 'ignore').decode('ascii')
        if ascii_value.strip():
            value = ascii_value
    except (UnicodeDecodeError, AttributeError):
        pass  # Use original value if normalization fails

    # If still contains non-ASCII, use a hash-based approach for unique identification
    if not value.isascii():
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


def fetch_exchange_rate() -> float:
    """
    Fetch current USD to JPY exchange rate.

    Falls back to last known rate if fetch fails, or 150.0 if no history exists.
    """
    import json
    from pathlib import Path

    cache_file = Path('exchange_rate_cache.json')

    try:
        import requests
        # Use exchangerate-api.com (free, no API key needed)
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=5)
        if response.status_code == 200:
            data = response.json()
            rate = data['rates']['JPY']

            # Save to cache
            try:
                with open(cache_file, 'w') as f:
                    json.dump({
                        'rate': rate,
                        'timestamp': data.get('time_last_updated', 0)
                    }, f)
            except Exception:
                pass  # Don't fail if we can't save cache

            return rate
    except Exception as e:
        print(f"[EXCHANGE RATE] Error fetching rate: {e}")

    # Try to load last known rate from cache
    try:
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cached = json.load(f)
                rate = cached.get('rate')
                if rate:
                    print(f"[EXCHANGE RATE] Using cached rate: ¥{rate:.2f}")
                    return rate
    except Exception:
        pass

    # Final fallback
    print("[EXCHANGE RATE] Using default rate: ¥150.00")
    return 150.0


def extract_price(price_text: str) -> float:
    """Extract numeric price from text."""
    if not price_text:
        return 0.0
    # Remove currency symbols and commas, extract number
    match = re.search(r'[\d,]+\.?\d*', str(price_text).replace(',', ''))
    if match:
        return float(match.group(0))
    return 0.0


def create_debug_folder(query: str) -> Path:
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


def suggest_config_filename(config: dict) -> str:
    """Generate filename for config based on search parameters."""
    keyword = slugify(str(config.get('keyword', 'search')))

    # Use category name if available, otherwise use code
    category_name = config.get('category_name', '')
    if category_name:
        category = slugify(category_name)
    else:
        category = config.get('category')
        if isinstance(category, list):
            category = category[0] if category else ''
        category = slugify(str(category or 'all'))

    # Use shop name if available, otherwise use code
    shop_name = config.get('shop_name', '')
    if shop_name:
        shop = slugify(shop_name)
    else:
        shop_value = config.get('shop', '0')
        if not shop_value or shop_value.strip() == '':
            shop_value = '0'
        shop = slugify(str(shop_value))

    return f"{keyword}_{category}_{shop}.json"


def generate_csv_filename(config: dict) -> str:
    """Generate CSV filename based on search parameters."""
    keyword = slugify(str(config.get('keyword', 'search')))

    # Use category name if available, otherwise use code
    category_name = config.get('category_name')
    if category_name:
        category = slugify(str(category_name))
    else:
        category = config.get('category')
        if isinstance(category, list):
            category = category[0] if category else ''
        category = slugify(str(category or 'all'))

    # Use shop name if available, otherwise use code
    shop_name = config.get('shop_name')
    if shop_name:
        shop = slugify(str(shop_name))
    else:
        # Handle shop with special default to '0'
        shop_value = config.get('shop', '0')
        if not shop_value or shop_value.strip() == '':
            shop_value = '0'
        shop = slugify(str(shop_value))

    return f"{keyword}_{category}_{shop}.csv"


def find_matching_csv(config: dict) -> Optional[Path]:
    """Find existing CSV files that match the search parameters."""
    results_dir = Path('results')
    if not results_dir.exists():
        return None

    # Generate the expected filename with new system
    expected_filename = generate_csv_filename(config)
    expected_path = results_dir / expected_filename

    if expected_path.exists():
        print(f"[GUI DEBUG] Found exact CSV match: {expected_path}")
        return expected_path

    # Get slugified components for searching
    keyword = slugify(str(config.get('keyword', 'search')))
    category = config.get('category')
    if isinstance(category, list):
        category = category[0] if category else ''
    category = slugify(str(category or 'all'))

    # Handle shop with special default to '0'
    shop_value = config.get('shop', '0')
    if not shop_value or shop_value.strip() == '':
        shop_value = '0'
    shop = slugify(str(shop_value))

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

    print(f"[GUI DEBUG] No matching CSV file found")
    return None


def clean_ebay_url(url: str) -> str:
    """
    Clean and validate eBay URLs, removing tracking parameters.

    Args:
        url: Raw eBay URL

    Returns:
        Cleaned URL or None if invalid
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    # Handle relative URLs
    if url.startswith('/itm/'):
        url = 'https://www.ebay.com' + url
    elif url.startswith('//'):
        url = 'https:' + url

    # Extract item ID from various eBay URL formats
    patterns = [
        r'ebay\.com/itm/([^/?]+)',
        r'ebay\.com/.*/(\d+)',
        r'/(\d{12,})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            item_id = match.group(1)
            # Return clean URL without tracking parameters
            return f"https://www.ebay.com/itm/{item_id}"

    # If no pattern matches, return original URL if it contains ebay.com
    if 'ebay.com' in url.lower():
        return url

    return None


def extract_code(text: str) -> Optional[str]:
    """Extract category code from dropdown text.

    Handles formats:
    - "01 - Comics" -> "01"
    - "Name (code)" -> "code"
    - "code" -> "code"
    """
    if not text:
        return None

    text = text.strip()

    # Try to extract from parentheses at end: "Name (code)"
    if '(' in text and text.endswith(')'):
        code = text.split('(')[-1].rstrip(')')
        return code.strip() or None

    # Try to extract from beginning: "01 - Comics"
    match = re.match(r'^(\d+)', text)
    if match:
        return match.group(1)

    # Return as-is if it looks like a code
    return text or None


def match_main_code(code: str) -> Optional[str]:
    """Match a detail category code to its main category."""
    if not code:
        return None
    # Try progressively shorter prefixes
    for length in range(len(code), 0, -1):
        prefix = code[:length]
        from .constants import MAIN_CATEGORY_OPTIONS
        for main_code, _ in MAIN_CATEGORY_OPTIONS:
            if main_code == prefix:
                return main_code
    return None


def load_publisher_list() -> set:
    """Load publisher list from file."""
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


def save_publisher_list(publisher_list: set):
    """Save publisher list to file."""
    try:
        publisher_file = Path('publishers.txt')
        with open(publisher_file, 'w', encoding='utf-8') as f:
            for pub in sorted(publisher_list):
                f.write(f"{pub}\n")
        print(f"[PUBLISHERS] Saved {len(publisher_list)} publishers to file")
    except Exception as e:
        print(f"[PUBLISHERS] Error saving file: {e}")


def get_proxy_settings(store: str = 'mandarake') -> Tuple[bool, Optional[str]]:
    """
    Get proxy settings for a specific store from user settings.

    Args:
        store: Store name ('ebay', 'mandarake', or 'surugaya')

    Returns:
        Tuple of (use_proxy: bool, api_key: str or None)

    Example:
        >>> use_proxy, api_key = get_proxy_settings('mandarake')
        >>> if use_proxy and api_key:
        >>>     browser = BrowserMimic(use_scrapeops=True, scrapeops_api_key=api_key)
    """
    try:
        from gui.settings_manager import SettingsManager
        settings = SettingsManager()

        # Check if proxy is globally enabled
        proxy_enabled = settings.get_setting('proxy.enabled', False)
        if not proxy_enabled:
            return False, None

        # Check if proxy is enabled for this specific store
        store_setting_key = f'proxy.{store}_enabled'
        store_enabled = settings.get_setting(store_setting_key, True)  # Default to True
        if not store_enabled:
            return False, None

        # Get API key
        api_key = settings.get_setting('proxy.api_key', '')
        if not api_key:
            return False, None

        return True, api_key

    except Exception as e:
        logging.error(f"Error getting proxy settings: {e}")
        return False, None


def get_browser_with_proxy(store: str = 'mandarake'):
    """
    Get BrowserMimic instance with proxy enabled if configured for the store.

    Args:
        store: Store name ('mandarake' or 'surugaya')

    Returns:
        BrowserMimic instance with or without proxy

    Example:
        >>> browser = get_browser_with_proxy('mandarake')
        >>> response = browser.get('https://order.mandarake.co.jp/...')
    """
    from browser_mimic import BrowserMimic

    use_proxy, api_key = get_proxy_settings(store)

    if use_proxy and api_key:
        logging.info(f"[PROXY] Using ScrapeOps proxy for {store}")
        return BrowserMimic(use_scrapeops=True, scrapeops_api_key=api_key)
    else:
        return BrowserMimic()
