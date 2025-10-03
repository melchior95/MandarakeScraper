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
    '050230': {'en': 'Female Idol Photobooks', 'jp': '女性アイドル写真集'},
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

    # Goods
    '12': {'en': 'Goods', 'jp': 'グッズ'},
    '1201': {'en': 'Shonen Comics', 'jp': '少年マンガ作品'},
    '1202': {'en': 'Shonen Comic magazine goods', 'jp': '少年誌付録'},
    '1203': {'en': 'Movie Theater original goods', 'jp': '劇場特典'},
    '1204': {'en': 'Shojo Comics', 'jp': '少女マンガ作品'},
    '1205': {'en': 'Girl retro', 'jp': '少女レトロ'},
    '1206': {'en': 'Otome Goods', 'jp': '乙女グッズ'},
    '1207': {'en': 'BL Goods', 'jp': 'BLグッズ'},
    '1208': {'en': 'Tapestry', 'jp': 'タペストリー'},
    '1209': {'en': 'Shop bonus', 'jp': '店舗特典'},
    '1299': {'en': 'Others', 'jp': 'その他'},

    # Sticker Yokocho
    '31': {'en': 'Sticker yokocho', 'jp': 'シール横丁'},

    # Others
    '99': {'en': 'Others (everything)', 'jp': 'その他（すべて）'},
    '9901': {'en': 'Cosplay', 'jp': 'コスプレ'},
    '9902': {'en': 'Pro Sports', 'jp': 'プロスポーツ'},
    '9903': {'en': 'Movies', 'jp': '映画'},
    '9904': {'en': 'Posters', 'jp': 'ポスター'},
    '9905': {'en': 'Martial arts and pro wrestling', 'jp': '格闘技･プロレス'},
    '9999': {'en': 'Others', 'jp': 'その他'},

    # Additional Books subcategories
    '0108': {'en': 'Sexual & Adult Interests', 'jp': '性風俗・成年向け'},
    '010801': {'en': 'S&M', 'jp': 'SM'},
    '010802': {'en': 'Fetishes', 'jp': 'フェチ'},
    '010803': {'en': 'Vinyl Books', 'jp': 'ビニ本・自販機本'},
    '010804': {'en': 'Nude Photography', 'jp': 'ヌード写真'},
    '010805': {'en': 'Light Novels', 'jp': '小説・読み物'},
    '010806': {'en': 'Adult Magazines', 'jp': '成年雑誌'},
    '010807': {'en': 'Erotic Arts', 'jp': '春画・艶本'},
    '010808': {'en': 'LGBT', 'jp': 'LGBT'},
    '010899': {'en': 'Others', 'jp': 'その他'},
    '0111': {'en': 'TV Picture Books', 'jp': 'テレビ絵本'},
    '0130': {'en': 'Pamphlets', 'jp': 'パンフレット'},
    '0131': {'en': 'Art books', 'jp': '画集'},
    '0132': {'en': 'Mooks (Bishojo)', 'jp': 'ムック(美少女)'},
    '0133': {'en': 'Mooks (Tokusatsu/Anime)', 'jp': 'ムック(特撮・アニメ)'},
    '0134': {'en': 'Other Related books', 'jp': 'その他関連書籍'},
    '010203': {'en': 'Illustration', 'jp': '画集・イラスト集'},
    '010205': {'en': 'TV Picture Book', 'jp': 'テレビ絵本'},
    '010207': {'en': 'Pamphlet', 'jp': 'パンフレット'},
    '010208': {'en': 'Novel', 'jp': '小説'},
    '010209': {'en': 'Game Book', 'jp': 'ゲームブック'},
    '010299': {'en': 'Others', 'jp': 'その他'},
    '010301': {'en': 'Picture books', 'jp': '絵本・童話'},
    '010302': {'en': 'Photographs', 'jp': '写真集'},
    '010304': {'en': 'Art, Design', 'jp': 'アート・デザイン'},
    '010307': {'en': 'Subculture, Sex culture', 'jp': '趣味・娯楽・カルチャー'},
    '010308': {'en': 'Music', 'jp': '音楽'},
    '010310': {'en': 'Fashion', 'jp': 'ファッション'},
    '010311': {'en': 'Performing arts', 'jp': '舞台芸術'},
    '010314': {'en': 'Movies, TV series', 'jp': '映画・ドラマ'},
    '010315': {'en': 'Nature', 'jp': 'ネイチャー'},
    '010316': {'en': 'Architecture, Interior', 'jp': '建築・インテリア'},
    '010318': {'en': 'Lifestyle', 'jp': 'くらし'},
    '010399': {'en': 'Others', 'jp': 'その他'},
    '010401': {'en': 'Paranormal', 'jp': '超常現象・陰謀論'},
    '010402': {'en': 'Spiritual', 'jp': 'スピリチュアリティ'},
    '010403': {'en': 'Oriental', 'jp': '東洋'},
    '010404': {'en': 'Health, Body work', 'jp': '健康・からだ'},
    '010405': {'en': 'Martial arts', 'jp': '武'},
    '010406': {'en': 'Japan', 'jp': '日本'},
    '010407': {'en': 'New religious movement', 'jp': '新宗教'},
    '010408': {'en': 'Big three religions', 'jp': '三大宗教・オリエント'},
    '010409': {'en': 'Occultism', 'jp': 'オカルティズム'},
    '010410': {'en': 'Fortune telling', 'jp': '占い・呪術'},
    '010499': {'en': 'Others', 'jp': 'その他'},
    '010601': {'en': 'Literature', 'jp': '文芸一般'},
    '010602': {'en': 'Poetry', 'jp': '詩・短歌'},
    '010603': {'en': 'Sci-Fi, Mystery', 'jp': 'SF・ミステリ･幻想'},
    '010604': {'en': 'Fiction', 'jp': 'ジュブナイル'},
    '010605': {'en': 'Kashihon novels', 'jp': '貸本小説'},
    '010699': {'en': 'Others', 'jp': 'その他'},
    '010701': {'en': 'Humanities & Sociology', 'jp': '人文・社会'},
    '010702': {'en': 'Natural Science & Engineering', 'jp': '自然科学・理工'},
    '010703': {'en': 'Military', 'jp': 'ミリタリ'},
    '010704': {'en': 'Dictionaries & Encyclopedias', 'jp': '図鑑・事典'},
    '010799': {'en': 'Others', 'jp': 'その他'},

    # Additional Toys subcategories
    '020119': {'en': 'Disney', 'jp': 'ディズニー'},
    '020199': {'en': 'Others', 'jp': 'その他'},
    '020201': {'en': 'Tokusatsu', 'jp': '特撮'},
    '020202': {'en': 'Anime/Comics', 'jp': 'マンガ・アニメ・ゲーム'},
    '020204': {'en': 'American Comics', 'jp': '洋画・アメコミヒーロー'},
    '200104': {'en': 'Soft Vinyl', 'jp': 'ソフビ'},

    # Additional Doujin subcategories
    '030101': {'en': 'Doujinshi (Male Audience)', 'jp': '同人誌'},
    '030102': {'en': 'Sound Horizon', 'jp': 'Sound Horizon'},
    '030103': {'en': 'Dakimakura', 'jp': '抱き枕・シーツ類'},
    '030104': {'en': 'Cosplay ROMs', 'jp': 'コスプレROM'},
    '030105': {'en': 'Vocaloid ROMs', 'jp': 'ボーカロイドROM'},
    '030106': {'en': 'Toho project', 'jp': '東方Project'},
    '030107': {'en': 'Adult ROMs', 'jp': '成年DVD'},
    '030108': {'en': 'Doujin Music', 'jp': '同人音楽'},
    '030110': {'en': 'Anime Picture Collection', 'jp': 'アニメ原画集'},
    '030111': {'en': 'Posters', 'jp': 'ポスター'},
    '030114': {'en': 'PC Game', 'jp': 'PCゲーム'},
    '030197': {'en': 'Doujin Softs', 'jp': 'その他同人ソフト'},
    '030198': {'en': 'Doujin Goods', 'jp': 'その他グッズ'},
    '030199': {'en': 'Others', 'jp': 'その他'},
    '030301': {'en': 'Doujinshi (Female Audience)', 'jp': '同人誌'},
    '030303': {'en': 'Games', 'jp': 'ゲーム'},
    '030304': {'en': 'Goods', 'jp': 'グッズ'},
    '030399': {'en': 'Others', 'jp': 'その他'},
    '030601': {'en': 'Manga', 'jp': 'マンガ'},
    '030602': {'en': 'Anime', 'jp': 'アニメ'},
    '030603': {'en': 'Tokusatsu', 'jp': '特撮(実写ドラマ含む)'},
    '030604': {'en': 'Collection', 'jp': 'コレクション(TOYなど)'},
    '030605': {'en': 'Military', 'jp': 'ミリタリー'},
    '030606': {'en': 'Foods/Drinks', 'jp': '食べ物・飲み物'},
    '030699': {'en': 'Others', 'jp': 'その他'},

    # Additional Disk/Game subcategories
    '0406': {'en': 'VHS', 'jp': 'VHS'},
    '0450': {'en': 'PC game', 'jp': 'PCゲーム'},
    '0451': {'en': 'Consumer game', 'jp': '家庭用ゲーム'},
    '0498': {'en': 'Other media', 'jp': 'その他メディア'},
    '040107': {'en': 'Voice Actor', 'jp': '声優'},
    '040108': {'en': 'Anime Song', 'jp': 'アニソン歌手'},
    '040109': {'en': 'Vocaloid / Utaite', 'jp': 'ボーカロイド/歌い手'},
    '040112': {'en': 'Otome game', 'jp': '乙女ゲーム'},
    '040113': {'en': 'Situation', 'jp': 'シチュエーション/企画系'},
    '040114': {'en': 'Female light novel', 'jp': '女性ライトノベル原作'},
    '040199': {'en': 'Others', 'jp': 'その他'},
    '040204': {'en': 'Dorama', 'jp': 'ドラマ'},
    '040205': {'en': 'Movie', 'jp': '洋画'},
    '040206': {'en': 'Japanese Movie', 'jp': '邦画'},
    '040207': {'en': 'Live', 'jp': 'ライブ'},
    '040208': {'en': 'Musical', 'jp': '舞台'},
    '040209': {'en': 'Voice Actor', 'jp': '声優'},
    '040210': {'en': 'Game', 'jp': 'ゲーム'},
    '040211': {'en': 'Variety', 'jp': 'バラエティ'},
    '040212': {'en': 'Otome game', 'jp': '乙女ゲーム'},
    '040213': {'en': 'Situation', 'jp': 'シチュエーション/企画系'},
    '040214': {'en': 'Female light novel', 'jp': '女性ライトノベル原作'},
    '040299': {'en': 'Others', 'jp': 'その他'},
    '040303': {'en': 'BL', 'jp': 'BL'},
    '040304': {'en': 'Dorama', 'jp': 'ドラマ'},
    '040305': {'en': 'Movie', 'jp': '洋画'},
    '040306': {'en': 'Japanese movie', 'jp': '邦画'},
    '040307': {'en': 'Live', 'jp': 'ライブ'},
    '040308': {'en': 'Musical', 'jp': '舞台'},
    '040309': {'en': 'Voice Actor', 'jp': '声優'},
    '0403010': {'en': 'Game', 'jp': 'ゲーム'},
    '0403011': {'en': 'Variety', 'jp': 'バラエティ'},
    '0403012': {'en': 'Otome game', 'jp': '乙女ゲーム'},
    '0403013': {'en': 'Situation', 'jp': 'シチュエーション/企画系'},
    '0403099': {'en': 'Others', 'jp': 'その他'},

    # Additional Idol subcategories
    '0505': {'en': 'Takarazuka', 'jp': '宝塚'},
    '0507': {'en': 'Male Celebrities', 'jp': '芸能タレント一般(男性)'},
    '0508': {'en': 'Female Celebrities', 'jp': '芸能タレント一般(女性)'},
    '050104': {'en': 'Tenimyu', 'jp': 'テニミュ'},
    '050105': {'en': 'Visual Kei', 'jp': 'ヴィジュアル系'},
    '050199': {'en': 'Others', 'jp': 'その他'},
    '050401': {'en': 'Photo', 'jp': '写真集'},
    '050402': {'en': 'Magazine', 'jp': '雑誌・書類'},
    '050403': {'en': 'Pamphlet', 'jp': 'パンフレット'},
    '050404': {'en': 'Bulletin', 'jp': '会報'},
    '050411': {'en': 'Clothing / T-shirt', 'jp': '衣類・Tシャツ'},
    '050412': {'en': 'Bromide', 'jp': 'ブロマイド'},
    '050429': {'en': 'Other goods', 'jp': 'その他グッズ'},
    '050430': {'en': 'Posters', 'jp': 'ポスター'},
    '050701': {'en': 'Photograph books', 'jp': '写真集'},
    '050702': {'en': 'Written Works', 'jp': '読み物'},
    '050703': {'en': 'Audio Visual (male celebrities)', 'jp': '音楽・映像ソフト'},
    '050704': {'en': 'Goods', 'jp': 'グッズ'},
    '050799': {'en': 'Others', 'jp': 'その他'},
    '050802': {'en': 'Written Works', 'jp': '読み物'},
    '050803': {'en': 'Audio visual', 'jp': '音楽・映像ソフト'},
    '050804': {'en': 'Goods', 'jp': 'グッズ'},
    '050899': {'en': 'Others', 'jp': 'その他'},

    # Additional Card subcategories
    '0604': {'en': 'TCG', 'jp': 'トレーディングカードゲーム'},
    '0605': {'en': 'Old Kamen Rider Cards', 'jp': 'カルビー旧仮面ライダーカード'},
    '0606': {'en': 'Baseball Card', 'jp': '70～80年代プロ野球カード'},
    '0607': {'en': 'Carddass', 'jp': 'カードダス'},
    '0608': {'en': 'Trading Cards', 'jp': 'トレカ'},
    '0609': {'en': 'Telephone Cards', 'jp': 'テレホンカード'},
    '0610': {'en': 'Shitajiki', 'jp': '下敷き'},
    '0611': {'en': 'Laminated Cards', 'jp': 'ラミカ'},
    '0613': {'en': 'Bromide', 'jp': '5円引きブロマイド'},
    '0614': {'en': 'Bikkuriman Stickers', 'jp': 'ビックリマンシール'},
    '0615': {'en': 'Shinrabansho choco', 'jp': '神羅万象'},
    '0616': {'en': 'Shokugan', 'jp': '食玩カード'},
    '0617': {'en': 'Mini cards', 'jp': 'ミニカード'},
    '0618': {'en': 'Clear files', 'jp': 'クリアファイル'},
    '0619': {'en': 'MTG', 'jp': 'MTG マジック・ザ・ギャザリング'},
    '0698': {'en': 'Minor cards', 'jp': 'マイナーシール'},
    '0699': {'en': 'Others', 'jp': 'その他'},

    # Additional Anime Cels/Scripts subcategories
    '0705': {'en': 'Scripts', 'jp': '台本'},

    # Additional Gallery subcategories
    '0804': {'en': 'Autograph Boards(Shikishi)', 'jp': '色紙'},
    '0899': {'en': 'Others', 'jp': 'その他'},

    # Additional Mandarake Publishing subcategories
    '0902': {'en': 'Laza comics', 'jp': 'ラザコミックス'},
    '0903': {'en': 'Silk screen', 'jp': 'シルクスクリーン'},
    '0904': {'en': 'Comics / Books', 'jp': 'まんが・書籍'},
    '0905': {'en': 'Sofvi toys', 'jp': 'ソフビTOY'},
    '0906': {'en': 'Card / Stickers', 'jp': 'カード・シール'},
    '0907': {'en': 'Zakka', 'jp': '雑貨'},
    '0908': {'en': 'BL / Yaoi', 'jp': 'BL関連'},
    '0909': {'en': 'Doujin', 'jp': '同人関連'},
    '0910': {'en': 'Goods', 'jp': 'アニメグッズ'},
    '0911': {'en': 'Cosplay', 'jp': 'コスプレ'},
    '0912': {'en': 'T-shirt', 'jp': 'Tシャツ'},
    '0913': {'en': 'Spiritual', 'jp': '精神世界'},
    '0999': {'en': 'Others', 'jp': 'その他'},

    # Magazines subcategories
    '1004': {'en': 'Comic & light novel information magazines', 'jp': 'マンガ情報誌'},
    '1005': {'en': 'Tokusatsu information magazines', 'jp': '特撮情報誌'},
    '1006': {'en': 'Hobby information magazines', 'jp': '模型&ホビー誌'},
    '1007': {'en': 'Voice actor & Anime song information magazines', 'jp': '声優＆アニソン情報誌'},
    '1008': {'en': 'Cosplay magazines', 'jp': 'コスプレ雑誌'},
    '1009': {'en': 'Ladies game magazines', 'jp': '乙女ゲーム雑誌'},
    '1097': {'en': 'Infomation magazine supplements', 'jp': '情報誌付録'},
    '1098': {'en': 'Adult contents infomation magazines', 'jp': '成年メディア情報誌'},
    '1099': {'en': 'Others', 'jp': 'その他雑誌'},
    '100101': {'en': 'Entertainments, Idol', 'jp': '芸能・アイドル'},
    '100102': {'en': 'Subculture', 'jp': 'サブカルチャー'},
    '100103': {'en': 'Art, Design', 'jp': 'アート・デザイン'},
    '100104': {'en': 'Fashion, Culture', 'jp': 'ファッション・カルチャー'},
    '100105': {'en': 'SF, Mystery, Fantasy', 'jp': 'SF・ミステリ･幻想'},
    '100106': {'en': 'Music', 'jp': '音楽'},
    '100107': {'en': 'Boys, Girls Magazine', 'jp': '少年誌・少女雑誌'},
    '100108': {'en': 'Literature', 'jp': '文芸・人文系'},
    '100109': {'en': 'Architecture, Interior', 'jp': '建築・インテリア'},
    '100110': {'en': 'Inner world', 'jp': '精神世界系'},
    '100111': {'en': 'Photo', 'jp': '写真'},
    '100199': {'en': 'Others', 'jp': 'その他'},
    '100202': {'en': 'Woman comic magazines', 'jp': '女性マンガ誌'},
    '100205': {'en': 'For young comic magazines', 'jp': '青年マンガ誌'},
    '100206': {'en': 'Gekiga magazines', 'jp': '劇画雑誌'},
    '100281': {'en': 'GARO', 'jp': 'ガロ'},
    '100282': {'en': 'COM', 'jp': 'COM'},
    '100296': {'en': 'Horor manga magazines', 'jp': 'ホラーマンガ誌'},
    '100297': {'en': 'Boyslove comic magazines', 'jp': 'BLマンガ雑誌'},
    '100298': {'en': 'Adult comic magazines', 'jp': '成年マンガ誌'},
    '100299': {'en': 'Others', 'jp': 'その他'},
    '101002': {'en': 'Boys love novel magazines', 'jp': 'BL小説誌'},

    # Comics subcategories
    '110109': {'en': 'Translate Comics', 'jp': '翻訳コミック'},
    '110110': {'en': 'Convenience store Comics', 'jp': 'コンビニコミック'},
    '110111': {'en': 'Little press', 'jp': 'リトルプレス'},
    '110199': {'en': 'Others', 'jp': 'その他'},
    '110201': {'en': 'Comics(before 1945)', 'jp': '戦前漫画単行本(昭和20年以前)'},
    '110202': {'en': 'Comics(1956-1964)', 'jp': '戦後漫画単行本(昭和20から30年代)'},
    '110203': {'en': 'Akahon / Senkashihon (comics)', 'jp': '赤本/仙花紙本'},
    '110204': {'en': 'Kashihon', 'jp': '貸本'},
    '110205': {'en': 'Furoku Comics', 'jp': '付録本'},
    '110206': {'en': 'Limited distribution Comics', 'jp': '限定流通コミックス'},
    '110207': {'en': 'Vintage Comics (after 1965)', 'jp': 'コミックス(昭和40年以降)'},
    '110301': {'en': 'Light Novels', 'jp': 'ライトノベル'},
    '110302': {'en': 'BL Novels', 'jp': 'BL小説'},
    '110303': {'en': 'TL Novels', 'jp': 'TL小説'},
    '110305': {'en': 'Novels', 'jp': '小説'},
    '110307': {'en': 'Adult Novels', 'jp': '成年小説'},
    '110309': {'en': 'Game Books', 'jp': 'ゲームブック'},
    '110310': {'en': 'TRPG', 'jp': 'TRPG'},
    '110399': {'en': 'Others', 'jp': 'その他'},
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

