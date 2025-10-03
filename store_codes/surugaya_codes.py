"""
Suruga-ya Category and Shop Code Mappings

Complete 2-level category structure for hobby/import-friendly items.
Based on advanced search form at: https://www.suruga-ya.jp/detailed_search
"""

# ==============================================================================
# LEVEL 1: MAIN CATEGORIES (7 hobby categories - excludes electronics, food, etc.)
# ==============================================================================

SURUGAYA_MAIN_CATEGORIES = {
    '2': 'Games',
    '3': 'Video Software (Anime/Movies)',
    '4': 'Music (CDs/Soundtracks)',
    '5': 'Toys & Hobby',
    '7': 'Books & Photobooks',
    '10': 'Goods & Accessories',
    '11': 'Doujinshi',
}

# ==============================================================================
# LEVEL 2: DETAILED CATEGORIES (organized by parent)
# ==============================================================================

SURUGAYA_DETAILED_CATEGORIES = {
    # Games (2)
    '2': {
        '200': 'TV Games (All)',
        '20038': 'Nintendo Switch',
        '20039': 'PlayStation 5',
        '201': 'Portable Games',
        '202': 'Arcade Game Boards',
    },

    # Video Software (3)
    '3': {
        '300': 'Anime',
        '301': 'Movies',
        '302': 'TV Dramas',
        '303': 'Music Videos',
        '305': 'Special Effects',
        '306': 'Other',
        '308': 'Stage Performances',
        '309': 'Sports',
        '310': 'Comedy',
        '311': 'Hobbies/Education',
    },

    # Music (4)
    '4': {
        '403': 'Japanese Music (J-Pop)',
        '406': 'Western Music',
        '407': 'Classical',
        '408': 'Anime/Game Music',
        '409': 'Soundtracks',
        '410': 'Theater/Musical',
        '411': 'Jazz',
        '405': 'Children\'s Songs',
        '413': 'New Age/Light Classical',
        '414': 'Instrumental/BGM',
        '415': 'Other',
        '416': 'Asian Music',
    },

    # Toys & Hobby (5)
    '5': {
        '500': 'Toys (General)',
        '50109': 'Dolls',
        '50101': 'Puzzles',
        '5000000': 'Miniature Cars',
        '501': 'Hobby (General)',
        '50001': 'Radio-Controlled Vehicles',
    },

    # Books (7)
    '7': {
        '700': 'Books (書籍)',
        '701': 'Comics/Manga (コミック)',
        '702': 'Magazines (雑誌)',
        '703': 'Pamphlets (パンフレット)',
    },

    # Goods & Accessories (10)
    '10': {
        '5010803': 'Photos',
        '1014': 'Straps & Keychains',
        '1029': 'Badges & Pins',
        '1045': 'Acrylic Stands',
        '501080209': 'Character Cards',
        '1010': 'Stationery',
        '1001': 'Tableware',
        '1015': 'Postcards & Autograph Boards',
        '1011': 'Stickers',
        '1000': 'Clothing',
        '1017': 'Bags & Pouches',
        '1003': 'Posters',
        '1022': 'Tapestries',
        '1018': 'Towels & Handkerchiefs',
        '1021': 'Accessories',
    },

    # Doujinshi (11)
    '11': {
        '1100': 'Doujinshi (Comics)',
        '1101': 'Doujin Software',
        '1102': 'Doujin Goods',
    },
}

# Flattened categories for backwards compatibility
SURUGAYA_CATEGORIES = {
    # Games
    '200': 'TV Games (All)',
    '20038': 'Nintendo Switch',
    '20039': 'PlayStation 5',
    '201': 'Portable Games',
    '202': 'Arcade Game Boards',

    # Video
    '300': 'Anime',
    '301': 'Movies',
    '302': 'TV Dramas',
    '303': 'Music Videos',
    '305': 'Special Effects',
    '306': 'Other Video',
    '308': 'Stage Performances',
    '309': 'Sports',
    '310': 'Comedy',
    '311': 'Hobbies/Education',

    # Music
    '403': 'Japanese Music',
    '406': 'Western Music',
    '407': 'Classical',
    '408': 'Anime/Game Music',
    '409': 'Soundtracks',
    '410': 'Theater/Musical',
    '411': 'Jazz',
    '415': 'Other Music',
    '416': 'Asian Music',

    # Toys & Hobby
    '500': 'Toys',
    '501': 'Hobby',
    '50109': 'Dolls',
    '50101': 'Puzzles',

    # Books
    '700': 'Books',
    '701': 'Comics/Manga',
    '702': 'Magazines',
    '703': 'Pamphlets',

    # Goods
    '1000': 'Goods (All)',
    '1003': 'Posters',
    '1010': 'Stationery',
    '1014': 'Straps & Keychains',
    '1018': 'Towels',
    '1022': 'Tapestries',

    # Doujinshi
    '1100': 'Doujinshi',
    '1101': 'Doujin Software',
    '1102': 'Doujin Goods',
}

# Shop/Store codes (tenpo_code)
# Note: These are discovered codes. More may exist.
SURUGAYA_SHOPS = {
    'all': 'All Stores',
    '400495': 'Shop A',  # Placeholder - need actual shop names
    '400552': 'Shop B',  # Placeholder - need actual shop names
    # Add more as discovered
}

# ==============================================================================
# CONDITION FILTERS
# ==============================================================================

SURUGAYA_CONDITIONS = {
    'all': 'All Conditions',
    '1': 'New Only',
    '2': 'Used Only',
}

# Reverse mappings for convenience
SURUGAYA_CATEGORY_NAMES = {v: k for k, v in SURUGAYA_CATEGORIES.items()}


def get_surugaya_category_display_name(category_code):
    """Get display name for category code"""
    return SURUGAYA_CATEGORIES.get(str(category_code), f'Category {category_code}')


def get_surugaya_shop_display_name(shop_code):
    """Get display name for shop code"""
    if shop_code == 'all' or not shop_code:
        return 'All Stores'
    return SURUGAYA_SHOPS.get(str(shop_code), f'Store {shop_code}')


# Search URL builder
def build_surugaya_search_url(keyword, category1='7', category2=None, shop_code=None,
                               exclude_word=None, condition='all', in_stock_only=False,
                               adult_only=False):
    """
    Build Suruga-ya search URL with 2-level categories and filters

    Args:
        keyword: Search keyword (will be URL-encoded)
        category1: Main category code (2, 3, 4, 5, 7, 10, 11)
        category2: Detailed category code (optional)
        shop_code: Optional tenpo_code for specific shop
        exclude_word: Keywords to exclude from search (optional)
        condition: 'all', '1' (new), or '2' (used)
        in_stock_only: Show only in-stock items
        adult_only: Show only adult content (R18+)

    Returns:
        Complete search URL
    """
    from urllib.parse import quote

    base_url = "https://www.suruga-ya.jp/search"
    params = [
        f"search_word={quote(keyword) if keyword else ''}",
        "searchbox=1"
    ]

    # Category filters (use 2-level structure)
    if category1:
        params.append(f"category1={category1}")
    if category2:
        params.append(f"category2={category2}")

    # Exclude keywords
    if exclude_word:
        params.append(f"exclude_word={quote(exclude_word)}")

    # Condition filter (new/used)
    if condition and condition != 'all':
        params.append(f"sale_classified={condition}")

    # Shop filter
    if shop_code and shop_code != 'all':
        params.append(f"tenpo_code={shop_code}")

    # Stock filter
    if in_stock_only:
        params.append("inStock=1")

    # Adult content filter
    if adult_only:
        params.append("adult_s=1")

    return f"{base_url}?{'&'.join(params)}"
