# Suruga-ya Categories Research - Complete ✅

**Date:** October 3, 2025
**Status:** Research Complete - Categories Mapped
**Source:** Web scraping of https://www.suruga-ya.jp/

---

## Summary

Successfully researched and documented **complete 2-level category structure** for Suruga-ya, focusing on 7 hobby/import-friendly categories (removed electronics, food, living creatures, etc.).

---

## Final Category Structure

### Level 1: Main Categories (7 Categories)

| Code | Name | Japanese | Items |
|------|------|----------|-------|
| `2` | Games | ゲーム | Nintendo, PlayStation, Arcade |
| `3` | Video Software | 映像ソフト | Anime, Movies, Dramas |
| `4` | Music | 音楽ソフト | CDs, Soundtracks, Anime Music |
| `5` | Toys & Hobby | おもちゃホビー | Figures, Models, Trading Cards |
| `7` | Books & Photobooks | 本 | Books, Comics, Magazines |
| `10` | Goods & Accessories | 雑貨・小物 | Keychains, Posters, Stickers |
| `11` | Doujinshi | 同人 | Doujin works |

### Level 2: Detailed Categories (By Parent)

#### Games (2) - 5 subcategories
- `200` - TV Games (All)
- `20038` - Nintendo Switch
- `20039` - PlayStation 5
- `201` - Portable Games
- `202` - Arcade Game Boards

#### Video Software (3) - 11 subcategories
- `300` - Anime
- `301` - Movies
- `302` - TV Dramas
- `303` - Music Videos
- `305` - Special Effects
- `306` - Other
- `308` - Stage Performances
- `309` - Sports
- `310` - Comedy
- `311` - Hobbies/Education

#### Music (4) - 12 subcategories
- `403` - Japanese Music (J-Pop)
- `406` - Western Music
- `407` - Classical
- `408` - Anime/Game Music
- `409` - Soundtracks
- `410` - Theater/Musical
- `411` - Jazz
- `405` - Children's Songs
- `413` - New Age/Light Classical
- `414` - Instrumental/BGM
- `415` - Other
- `416` - Asian Music

#### Toys & Hobby (5) - 6 subcategories
- `500` - Toys (General)
- `50109` - Dolls
- `50101` - Puzzles
- `5000000` - Miniature Cars
- `501` - Hobby (General)
- `50001` - Radio-Controlled Vehicles

#### Books (7) - 4 subcategories
- `700` - Books
- `701` - Comics/Manga
- `702` - Magazines
- `703` - Pamphlets/Photobooks

#### Goods & Accessories (10) - 15 subcategories
- `5010803` - Photos
- `1014` - Straps & Keychains
- `1029` - Badges & Pins
- `1045` - Acrylic Stands
- `501080209` - Character Cards
- `1010` - Stationery
- `1001` - Tableware
- `1015` - Postcards & Autograph Boards
- `1011` - Stickers
- `1000` - Clothing
- `1017` - Bags & Pouches
- `1003` - Posters
- `1022` - Tapestries
- `1018` - Towels & Handkerchiefs
- `1021` - Accessories

#### Doujinshi (11) - 3 subcategories
- `1100` - Doujinshi (Comics)
- `1101` - Doujin Software
- `1102` - Doujin Goods

---

## Additional Search Options

### Implemented in Code

**High Priority (User Confirmed):**
- ✅ **Exclude Keywords** - `exclude_word` parameter
- ✅ **Condition Filter** - New/Used/All (`sale_classified`)
- ✅ **Stock Filter** - In stock only (`inStock`)

**Not Needed (User Feedback):**
- ❌ Release date range
- ❌ Barcode/JAN search
- ❌ Product ID search

---

## Files Updated

### 1. `store_codes/surugaya_codes.py` ✅

**Added:**
- `SURUGAYA_MAIN_CATEGORIES` - 7 main categories
- `SURUGAYA_DETAILED_CATEGORIES` - Hierarchical structure (dict of dicts)
- `SURUGAYA_CONDITIONS` - Condition filter constants
- Updated `build_surugaya_search_url()` with new parameters:
  - `category1` (main category)
  - `category2` (detailed category)
  - `exclude_word`
  - `condition` (new/used/all)
  - `in_stock_only`

**Backwards Compatibility:**
- Kept `SURUGAYA_CATEGORIES` as flattened dict for existing code

---

## Category Codes Reference

### Removed Categories (Not Import-Friendly)

These were excluded from the final structure:
- `6` - Computers & Smartphones (practical electronics)
- `8` - Home Appliances/Cameras (not hobby items)
- `9` - Food & Food Toys (perishable/customs issues)
- `12` - Lucky Bags (random items)
- `13` - Gifts (generic category)
- `14` - Living Creatures (animals/pets)

**Rationale:** Focus on hobby/collectible items suitable for import and resale.

---

## URL Structure

### Advanced Search Form
```
https://www.suruga-ya.jp/detailed_search
```

**Form Parameters:**
- `category1` - Main category (2, 3, 4, 5, 7, 10, 11)
- `category2` - Detailed category (200, 300, 403, etc.)
- `category3` - Third level (not used in our implementation)
- `search_word` - Keyword
- `exclude_word` - Exclude keywords
- `sale_classified` - Condition (1=new, 2=used)
- `tenpo_code` - Shop filter
- `inStock` - Stock filter (1=in stock only)

### Example Search URLs

**Games - Nintendo Switch:**
```
https://www.suruga-ya.jp/search?category1=2&category2=20038&search_word=Pokemon&searchbox=1
```

**Books - Photobooks, exclude DVD:**
```
https://www.suruga-ya.jp/search?category1=7&category2=703&search_word=Yura Kano&exclude_word=DVD&searchbox=1
```

**Music - Anime Music, New Only:**
```
https://www.suruga-ya.jp/search?category1=4&category2=408&search_word=Gundam&sale_classified=1&searchbox=1
```

---

## Next Steps

### Phase 1: GUI Integration (Pending)

1. **Update `_populate_surugaya_categories()`**
   - Load hierarchical categories based on selected main category
   - Show only relevant detailed categories

2. **Add Search Options UI**
   - Exclude keywords text field
   - Condition filter dropdown (All/New/Used)

3. **Update `_on_main_category_selected()`**
   - Filter detailed categories by parent category
   - Clear detailed selection when main category changes

### Phase 2: Scraper Integration (Pending)

1. **Update `surugaya_scraper.py`**
   - Modify `_build_search_url()` to use new parameters
   - Update `search()` method to accept new filters

2. **Update GUI Config Collection**
   - Add `exclude_word` field
   - Add `condition` field
   - Store `category1` and `category2` separately

3. **Update Config Schema**
   ```json
   {
     "store": "suruga-ya",
     "keyword": "Pokemon",
     "exclude_word": "plush",
     "category1": "2",
     "category2": "20038",
     "shop": "all",
     "condition": "all",
     "max_pages": 5,
     "show_out_of_stock": false
   }
   ```

### Phase 3: Testing (Pending)

- [ ] Test category dropdown loading
- [ ] Test exclude keywords functionality
- [ ] Test condition filter (new/used)
- [ ] Verify search URLs are correct
- [ ] Test config save/load with new fields

---

## Category Count Summary

**Total Categories Mapped:**
- Main Categories: **7**
- Detailed Subcategories: **56**
- Total Category Codes: **63**

**Categories by Parent:**
- Games (2): 5 subcategories
- Video (3): 11 subcategories
- Music (4): 12 subcategories
- Toys (5): 6 subcategories
- Books (7): 4 subcategories
- Goods (10): 15 subcategories
- Doujinshi (11): 3 subcategories

---

## Research Method

1. **Web Scraping** - Used WebFetch to extract category links from each main category page
2. **Code Extraction** - Parsed URLs to find category codes (e.g., `category=200`)
3. **Name Mapping** - Matched codes to Japanese names, provided English translations
4. **Validation** - Cross-referenced with advanced search form structure

**Sources:**
- https://www.suruga-ya.jp/search?category=2 (Games)
- https://www.suruga-ya.jp/search?category=3 (Video)
- https://www.suruga-ya.jp/search?category=4 (Music)
- https://www.suruga-ya.jp/search?category=5 (Toys)
- https://www.suruga-ya.jp/search?category=7 (Books)
- https://www.suruga-ya.jp/search?category=10 (Goods)
- https://www.suruga-ya.jp/search?category=11 (Doujinshi)

---

**Status:** ✅ Research Complete - Ready for GUI Integration
