"""
Suruga-ya Category and Shop Code Mappings

Similar to mandarake_codes.py, this module provides mappings for
Suruga-ya's category and shop (tenpo) codes.
"""

# Main categories based on URL structure
SURUGAYA_CATEGORIES = {
    # Books & Comics (700 series)
    '7': 'Books & Photobooks (All)',
    '700': 'Books',
    '701': 'Comics',
    '702': 'Magazines',
    '703': 'Photobooks',

    # Games (200 series)
    '200': 'Games (All)',
    '201': 'Nintendo Switch',
    '202': 'PlayStation 5',
    '203': 'PlayStation 4',
    '204': 'Xbox',
    '205': 'Nintendo 3DS',
    '206': 'PS Vita',
    '207': 'Wii U',
    '208': 'Retro Games',
    '20038': 'Game Accessories',
    '20039': 'Strategy Guides',

    # Video Software (300 series)
    '300': 'Video (All)',
    '301': 'Anime DVD',
    '302': 'Anime Blu-ray',
    '303': 'Movies DVD',
    '304': 'Movies Blu-ray',
    '305': 'Drama DVD',
    '306': 'Drama Blu-ray',
    '311': 'Adult Video',

    # Music Software (400 series)
    '403': 'Music (All)',
    '404': 'J-Pop CD',
    '405': 'Anime Music',
    '406': 'Game Music',
    '416': 'Idol Music',

    # Toys & Hobby (500 series)
    '500': 'Toys & Hobby (All)',
    '501': 'Figures',
    '502': 'Scale Figures',
    '503': 'Prize Figures',
    '504': 'Nendoroid',
    '505': 'Figma',
    '50109': 'Model Kits',

    # Goods & Fashion (1000 series)
    '1000': 'Goods (All)',
    '1001': 'Keychains & Straps',
    '1002': 'Posters',
    '1003': 'Acrylic Stands',
    '1004': 'Badges & Pins',
    '1010': 'Towels',
    '1011': 'Tapestries',
    '1014': 'Cushions',
    '1015': 'Plushies',
    '1017': 'Stationery',
    '1018': 'Bags',
    '1021': 'Apparel',
    '1022': 'Cosplay',
    '1024': 'Wigs',
    '1025': 'Props',

    # Doujinshi (1100 series)
    '1100': 'Doujinshi (All)',
    '1101': 'Doujinshi Comics',
    '1102': 'Doujin Games',

    # Electronics (65000 series, 800 series)
    '65000': 'Computers & Smartphones',
    '65205': 'PC Accessories',
    '800': 'Electronics (All)',
    '812': 'Cameras & AV Equipment',
}

# Shop/Store codes (tenpo_code)
# Note: These are discovered codes. More may exist.
SURUGAYA_SHOPS = {
    'all': 'All Stores',
    '400495': 'Shop A',  # Placeholder - need actual shop names
    '400552': 'Shop B',  # Placeholder - need actual shop names
    # Add more as discovered
}

# Reverse mappings for convenience
SURUGAYA_CATEGORY_NAMES = {v: k for k, v in SURUGAYA_CATEGORIES.items()}

# Display names for main categories (for dropdown)
SURUGAYA_MAIN_CATEGORIES = {
    '7': 'Books & Photobooks',
    '200': 'Games',
    '300': 'Video Software',
    '403': 'Music',
    '500': 'Toys & Hobby',
    '1000': 'Goods & Fashion',
    '1100': 'Doujinshi',
    '65000': 'Computers & Electronics',
}


def get_surugaya_category_display_name(category_code):
    """Get display name for category code"""
    return SURUGAYA_CATEGORIES.get(str(category_code), f'Category {category_code}')


def get_surugaya_shop_display_name(shop_code):
    """Get display name for shop code"""
    if shop_code == 'all' or not shop_code:
        return 'All Stores'
    return SURUGAYA_SHOPS.get(str(shop_code), f'Store {shop_code}')


# Search URL builder
def build_surugaya_search_url(keyword, category='7', shop_code=None):
    """
    Build Suruga-ya search URL

    Args:
        keyword: Search keyword (will be URL-encoded)
        category: Category code (default: 7 = Books)
        shop_code: Optional tenpo_code for specific shop

    Returns:
        Complete search URL
    """
    from urllib.parse import quote

    base_url = "https://www.suruga-ya.jp/search"
    params = [
        f"category={category}",
        f"search_word={quote(keyword)}",
        "searchbox=1"
    ]

    if shop_code and shop_code != 'all':
        params.append(f"tenpo_code={shop_code}")

    return f"{base_url}?{'&'.join(params)}"
