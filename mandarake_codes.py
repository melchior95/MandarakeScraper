"""
Mandarake Category and Store Code Mappings
Based on research from msikma/mdrscr GitHub repository
"""

# Store/Shop Codes
STORE_SLUG_TO_NAME = {
    'all': 'All Stores',
    'all stores': 'All Stores',
    'nakano': 'Nakano',
    'shibuya': 'Shibuya',
    'umeda': 'Umeda',
    'fukuoka': 'Fukuoka',
    'ekoda': 'Ekoda',
    'akihabara': 'Akihabara',
    'grandchaos': 'Grandchaos',
    'grand chaos': 'Grandchaos',
    'complex': 'Complex',
    'sahra': 'SAHRA',
    'cosmos': 'Cosmos',
    'nagoya': 'Nagoya',
    'rarara': 'Rarara (Ikebukuro)',
    'rarara (ikebukuro)': 'Rarara (Ikebukuro)',
}

MANDARAKE_STORES = {
    '0': {'en': 'All Stores', 'jp': 'すべての店舗'},
    '1': {'en': 'Nakano', 'jp': '中野店'},
    '4': {'en': 'Nagoya', 'jp': '名古屋店'},
    '6': {'en': 'Shibuya', 'jp': '渋谷店'},
    '7': {'en': 'Umeda', 'jp': '梅田店'},
    '11': {'en': 'Fukuoka', 'jp': '福岡店'},
    '23': {'en': 'Grandchaos', 'jp': 'グランドカオス店'},
    '26': {'en': 'Rarara (Ikebukuro)', 'jp': 'らしんばん池袋店'},
    '27': {'en': 'Sapporo', 'jp': '札幌店'},
    '28': {'en': 'Utsunomiya', 'jp': '宇都宮店'},
    '29': {'en': 'Kokura', 'jp': '小倉店'},
    '30': {'en': 'Complex', 'jp': 'コンプレックス店'},
    '32': {'en': 'Nayuta', 'jp': 'なゆた店'},
    '33': {'en': 'CoCoo', 'jp': 'ココー店'},
    '55': {'en': 'SAHRA', 'jp': 'サーラ店'},
    # Auction categories
    '-14': {'en': 'Daily Auctions', 'jp': '毎日オークション'},
    '14': {'en': 'Great Auction Tournament', 'jp': '大オークション大会'},
}

# Main Category Codes (Major Categories)
MANDARAKE_MAIN_CATEGORIES = {
    '00': {'en': 'Everything', 'jp': 'すべて'},
    '01': {'en': 'Books (everything)', 'jp': '本（すべて）'},
    '11': {'en': 'Comics (everything)', 'jp': 'コミック（すべて）'},
    '02': {'en': 'Toys (everything)', 'jp': 'おもちゃ（すべて）'},
    '03': {'en': 'Doujinshi (everything)', 'jp': '同人誌（すべて）'},
    '04': {'en': 'Media (everything)', 'jp': 'メディア（すべて）'},
    '05': {'en': 'Idols (everything)', 'jp': 'アイドル（すべて）'},
    '06': {'en': 'Cards (everything)', 'jp': 'カード（すべて）'},
    '07': {'en': 'Anime Cels/Scripts (everything)', 'jp': 'アニメセル・台本（すべて）'},
    '08': {'en': 'Gallery Items (everything)', 'jp': 'ギャラリー（すべて）'},
    '09': {'en': 'Mandarake Publishing (everything)', 'jp': 'まんだらけ出版（すべて）'},
    '10': {'en': 'Cosplay (everything)', 'jp': 'コスプレ（すべて）'},
}

# Detailed Category Codes (All Categories)
MANDARAKE_ALL_CATEGORIES = {
    # Everything
    '00': {'en': 'Everything', 'jp': 'すべて'},

    # Books
    '01': {'en': 'Books (everything)', 'jp': '本（すべて）'},
    '0101': {'en': 'Art Books', 'jp': '画集'},
    '0102': {'en': 'Photography Books', 'jp': '写真集'},
    '0103': {'en': 'Novels', 'jp': '小説'},
    '0104': {'en': 'Essay/Biography', 'jp': 'エッセイ・伝記'},
    '0105': {'en': 'How-to Books', 'jp': 'ハウツー本'},
    '0106': {'en': 'Reference Books', 'jp': '資料・設定'},
    '0107': {'en': 'Magazines', 'jp': '雑誌'},

    # Comics
    '11': {'en': 'Comics (everything)', 'jp': 'コミック（すべて）'},
    '1101': {'en': 'Comics', 'jp': 'コミック'},
    '110101': {'en': 'Shonen Comics', 'jp': '少年コミック'},
    '110102': {'en': 'Shojo Comics', 'jp': '少女コミック'},
    '110103': {'en': 'Seinen Comics', 'jp': '青年コミック'},
    '110104': {'en': 'Ladies Comics', 'jp': 'レディースコミック'},
    '110105': {'en': 'Boys Love Comics', 'jp': 'BLコミック'},
    '110106': {'en': 'Girls Love Comics', 'jp': 'GLコミック'},
    '110107': {'en': 'Adult Comics', 'jp': 'アダルトコミック'},
    '110108': {'en': 'Foreign Comics', 'jp': '海外コミック'},
    '1102': {'en': 'Complete Sets', 'jp': '全巻セット'},
    '1103': {'en': 'Limited Editions', 'jp': '限定版'},

    # Toys
    '02': {'en': 'Toys (everything)', 'jp': 'おもちゃ（すべて）'},
    '0201': {'en': 'Figures', 'jp': 'フィギュア'},
    '020101': {'en': 'Scale Figures', 'jp': 'スケールフィギュア'},
    '020102': {'en': 'Action Figures', 'jp': 'アクションフィギュア'},
    '020103': {'en': 'Prize Figures', 'jp': 'プライズフィギュア'},
    '020104': {'en': 'Garage Kits', 'jp': 'ガレージキット'},
    '020105': {'en': 'Dolls', 'jp': 'ドール'},
    '020106': {'en': 'Nendoroid', 'jp': 'ねんどろいど'},
    '020107': {'en': 'Figma', 'jp': 'figma'},
    '020108': {'en': 'Super Deformed', 'jp': 'デフォルメフィギュア'},
    '020109': {'en': 'Robot Figures', 'jp': 'ロボットフィギュア'},
    '020110': {'en': 'Trading Figures', 'jp': 'トレーディングフィギュア'},
    '020111': {'en': 'Food Toys', 'jp': '食玩'},
    '020112': {'en': 'Character Goods', 'jp': 'キャラクターグッズ'},
    '020113': {'en': 'Models/Kits', 'jp': 'プラモデル・模型'},
    '020114': {'en': 'Miniature Models', 'jp': 'ミニチュア'},
    '020115': {'en': 'Vehicles', 'jp': '乗り物'},
    '020116': {'en': 'Transformers', 'jp': 'トランスフォーマー'},
    '020117': {'en': 'Vintage Toys', 'jp': 'ビンテージトイ'},
    '020118': {'en': 'Other Toys', 'jp': 'その他おもちゃ'},

    # Doujinshi
    '03': {'en': 'Doujinshi (everything)', 'jp': '同人誌（すべて）'},
    '0301': {'en': 'Doujinshi', 'jp': '同人誌'},
    '0302': {'en': 'Doujin Games', 'jp': '同人ゲーム'},
    '0303': {'en': 'Doujin Music', 'jp': '同人音楽'},
    '0304': {'en': 'Doujin Videos', 'jp': '同人映像'},
    '0305': {'en': 'Doujin Goods', 'jp': '同人グッズ'},

    # Media
    '04': {'en': 'Media (everything)', 'jp': 'メディア（すべて）'},
    '0401': {'en': 'CDs', 'jp': 'CD'},
    '040101': {'en': 'Anime/Game Music', 'jp': 'アニメ・ゲーム音楽'},
    '040102': {'en': 'Character Songs', 'jp': 'キャラクターソング'},
    '040103': {'en': 'Drama CDs', 'jp': 'ドラマCD'},
    '040104': {'en': 'Pop/Rock Music', 'jp': 'ポップス・ロック'},
    '040105': {'en': 'Classical Music', 'jp': 'クラシック'},
    '040106': {'en': 'Soundtracks', 'jp': 'サウンドトラック'},
    '0402': {'en': 'DVDs', 'jp': 'DVD'},
    '040201': {'en': 'Anime DVDs', 'jp': 'アニメDVD'},
    '040202': {'en': 'Live Action DVDs', 'jp': '実写DVD'},
    '040203': {'en': 'Special Interest DVDs', 'jp': '特撮DVD'},
    '0403': {'en': 'Blu-rays', 'jp': 'Blu-ray'},
    '040301': {'en': 'Anime Blu-rays', 'jp': 'アニメBlu-ray'},
    '040302': {'en': 'Live Action Blu-rays', 'jp': '実写Blu-ray'},
    '0404': {'en': 'Games', 'jp': 'ゲーム'},
    '040401': {'en': 'Console Games', 'jp': 'コンシューマーゲーム'},
    '040402': {'en': 'PC Games', 'jp': 'PCゲーム'},
    '040403': {'en': 'Mobile Games', 'jp': 'モバイルゲーム'},
    '040404': {'en': 'Arcade Games', 'jp': 'アーケードゲーム'},
    '040405': {'en': 'Game Accessories', 'jp': 'ゲーム周辺機器'},

    # Idols
    '05': {'en': 'Idols (everything)', 'jp': 'アイドル（すべて）'},
    '0501': {'en': 'Idol Photos', 'jp': 'アイドル写真'},
    '050101': {'en': 'Idol Photo Books', 'jp': 'アイドル写真集'},
    '050102': {'en': 'Gravure Photos', 'jp': 'グラビア写真'},
    '050103': {'en': 'Bromide Photos', 'jp': 'ブロマイド'},
    '0502': {'en': 'Idol Goods', 'jp': 'アイドルグッズ'},
    '0503': {'en': 'Idol Videos', 'jp': 'アイドル映像'},
    '0504': {'en': 'Idol Music', 'jp': 'アイドル音楽'},

    # Adult Categories
    '050801': {'en': 'AV Actress/Photograph Collection', 'jp': 'AV女優・写真集'},

    # Cards
    '06': {'en': 'Cards (everything)', 'jp': 'カード（すべて）'},
    '0601': {'en': 'Trading Cards', 'jp': 'トレーディングカード'},
    '060101': {'en': 'Pokemon Cards', 'jp': 'ポケモンカード'},
    '060102': {'en': 'Yu-Gi-Oh! Cards', 'jp': '遊戯王カード'},
    '060103': {'en': 'Magic: The Gathering', 'jp': 'マジック・ザ・ギャザリング'},
    '060104': {'en': 'One Piece Cards', 'jp': 'ワンピースカード'},
    '060105': {'en': 'Dragon Ball Cards', 'jp': 'ドラゴンボールカード'},
    '0602': {'en': 'Sports Cards', 'jp': 'スポーツカード'},
    '0603': {'en': 'Idol Cards', 'jp': 'アイドルカード'},

    # Anime Cels/Scripts
    '07': {'en': 'Anime Cels/Scripts (everything)', 'jp': 'アニメセル・台本（すべて）'},
    '0701': {'en': 'Animation Cels', 'jp': 'アニメセル'},
    '0702': {'en': 'Scripts', 'jp': '台本'},
    '0703': {'en': 'Storyboards', 'jp': '絵コンテ'},
    '0704': {'en': 'Animation Materials', 'jp': 'アニメ資料'},

    # Gallery Items
    '08': {'en': 'Gallery Items (everything)', 'jp': 'ギャラリー（すべて）'},
    '0801': {'en': 'Original Artwork', 'jp': '原画'},
    '0802': {'en': 'Illustrations', 'jp': 'イラスト'},
    '0803': {'en': 'Manuscripts', 'jp': '原稿'},

    # Mandarake Publishing
    '09': {'en': 'Mandarake Publishing (everything)', 'jp': 'まんだらけ出版（すべて）'},
    '0901': {'en': 'Mandarake Books', 'jp': 'まんだらけ本'},

    # Cosplay
    '10': {'en': 'Cosplay (everything)', 'jp': 'コスプレ（すべて）'},
    '1001': {'en': 'Cosplay Costumes', 'jp': 'コスプレ衣装'},
    '1002': {'en': 'Cosplay Accessories', 'jp': 'コスプレ小物'},
    '1003': {'en': 'Cosplay Wigs', 'jp': 'コスプレウィッグ'},
}

def get_store_name(store_code: str, language: str = 'en') -> str:
    """Get store name by code and language"""
    if store_code in MANDARAKE_STORES:
        return MANDARAKE_STORES[store_code][language]
    return f"Unknown Store ({store_code})"

def get_category_name(category_code: str, language: str = 'en') -> str:
    """Get category name by code and language"""
    if category_code in MANDARAKE_ALL_CATEGORIES:
        return MANDARAKE_ALL_CATEGORIES[category_code][language]
    return f"Unknown Category ({category_code})"

def get_all_stores() -> dict:
    """Get all store codes and names"""
    return MANDARAKE_STORES

def get_all_categories() -> dict:
    """Get all category codes and names"""
    return MANDARAKE_ALL_CATEGORIES

def get_main_categories() -> dict:
    """Get main category codes and names"""
    return MANDARAKE_MAIN_CATEGORIES

# For backwards compatibility with existing scraper
SHOP_MAPPING = {
    '0': '0',   # All stores
    '1': '1',   # Nakano
    '2': '6',   # Shibuya (corrected mapping)
    '3': '7',   # Umeda
    '4': '4',   # Nagoya
    '5': '11',  # Fukuoka
    '6': '23',  # Grandchaos
    '7': '30',  # Complex
    '8': '55',  # SAHRA
    '9': '32',  # Nayuta
    '10': '33', # CoCoo
}


def get_store_display_name(store_value) -> str:
    """Return human-readable English store name from various representations."""
    if not store_value:
        return ''

    if isinstance(store_value, (list, tuple)):
        for item in store_value:
            name = get_store_display_name(item)
            if name:
                return name
        return ''

    store_str = str(store_value).strip()
    if not store_str:
        return ''

    if store_str in MANDARAKE_STORES:
        return MANDARAKE_STORES[store_str]['en']

    lower = store_str.lower()
    if lower in STORE_SLUG_TO_NAME:
        return STORE_SLUG_TO_NAME[lower]

    if store_str.isdigit() and store_str in MANDARAKE_STORES:
        return MANDARAKE_STORES[store_str]['en']

    for slug, name in STORE_SLUG_TO_NAME.items():
        if slug in lower:
            return name

    return store_str.title()

