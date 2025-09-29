# Mandarake Category and Store Code Reference

## Store Codes

| Code | English Name | Japanese Name |
|------|-------------|---------------|
| 0 | All Stores | すべての店舗 |
| 1 | Nakano | 中野店 |
| 4 | Nagoya | 名古屋店 |
| 6 | Shibuya | 渋谷店 |
| 7 | Umeda | 梅田店 |
| 11 | Fukuoka | 福岡店 |
| 23 | Grandchaos | グランドカオス店 |
| 26 | Rarara (Ikebukuro) | らしんばん池袋店 |
| 27 | Sapporo | 札幌店 |
| 28 | Utsunomiya | 宇都宮店 |
| 29 | Kokura | 小倉店 |
| 30 | Complex | コンプレックス店 |
| 32 | Nayuta | なゆた店 |
| 33 | CoCoo | ココー店 |
| 55 | SAHRA | サーラ店 |

### Special Store Codes
| Code | English Name | Japanese Name |
|------|-------------|---------------|
| -14 | Daily Auctions | 毎日オークション |
| 14 | Great Auction Tournament | 大オークション大会 |

## Main Category Codes

| Code | English Name | Japanese Name |
|------|-------------|---------------|
| 00 | Everything | すべて |
| 01 | Books (everything) | 本（すべて） |
| 11 | Comics (everything) | コミック（すべて） |
| 02 | Toys (everything) | おもちゃ（すべて） |
| 03 | Doujinshi (everything) | 同人誌（すべて） |
| 04 | Media (everything) | メディア（すべて） |
| 05 | Idols (everything) | アイドル（すべて） |
| 06 | Cards (everything) | カード（すべて） |
| 07 | Anime Cels/Scripts (everything) | アニメセル・台本（すべて） |
| 08 | Gallery Items (everything) | ギャラリー（すべて） |
| 09 | Mandarake Publishing (everything) | まんだらけ出版（すべて） |
| 10 | Cosplay (everything) | コスプレ（すべて） |

## Popular Category Codes

### Comics
| Code | English Name | Japanese Name |
|------|-------------|---------------|
| 1101 | Comics | コミック |
| 110101 | Shonen Comics | 少年コミック |
| 110102 | Shojo Comics | 少女コミック |
| 110103 | Seinen Comics | 青年コミック |
| 110104 | Ladies Comics | レディースコミック |
| 110105 | Boys Love Comics | BLコミック |
| 110106 | Girls Love Comics | GLコミック |
| 110107 | Adult Comics | アダルトコミック |

### Figures & Toys
| Code | English Name | Japanese Name |
|------|-------------|---------------|
| 0201 | Figures | フィギュア |
| 020101 | Scale Figures | スケールフィギュア |
| 020102 | Action Figures | アクションフィギュア |
| 020103 | Prize Figures | プライズフィギュア |
| 020106 | Nendoroid | ねんどろいど |
| 020107 | Figma | figma |

### Trading Cards
| Code | English Name | Japanese Name |
|------|-------------|---------------|
| 0601 | Trading Cards | トレーディングカード |
| 060101 | Pokemon Cards | ポケモンカード |
| 060102 | Yu-Gi-Oh! Cards | 遊戯王カード |
| 060103 | Magic: The Gathering | マジック・ザ・ギャザリング |
| 060104 | One Piece Cards | ワンピースカード |

### Idols & Photos
| Code | English Name | Japanese Name |
|------|-------------|---------------|
| 0501 | Idol Photos | アイドル写真 |
| 050101 | Idol Photo Books | アイドル写真集 |
| 050102 | Gravure Photos | グラビア写真 |
| 050801 | AV Actress/Photograph Collection | AV女優・写真集 |

### Media
| Code | English Name | Japanese Name |
|------|-------------|---------------|
| 0401 | CDs | CD |
| 040101 | Anime/Game Music | アニメ・ゲーム音楽 |
| 0402 | DVDs | DVD |
| 040201 | Anime DVDs | アニメDVD |
| 0403 | Blu-rays | Blu-ray |
| 040301 | Anime Blu-rays | アニメBlu-ray |

## Usage Examples

### URL Building
```bash
# Search all stores for AV actress photos
https://order.mandarake.co.jp/order/listPage/list?shop=0&categoryCode=050801&keyword=search_term

# Search Nakano store for Pokemon cards
https://order.mandarake.co.jp/order/listPage/list?shop=1&categoryCode=060101&keyword=pokemon

# Search all categories in Shibuya store
https://order.mandarake.co.jp/order/listPage/list?shop=6&categoryCode=00&keyword=search_term
```

### Scraper Usage
```bash
# Using URL directly
python mandarake_scraper.py --url "https://order.mandarake.co.jp/order/listPage/list?shop=0&categoryCode=050801&keyword=search_term"

# Using config file with these codes
python mandarake_scraper.py --config configs/my_config.json
```

---
*Reference compiled from msikma/mdrscr GitHub repository*