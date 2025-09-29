#!/usr/bin/env python3
"""
Mandarake Auction Scraper - Based on mdrscr ekizo functionality
Scrapes auction listings from ekizo.mandarake.co.jp
"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin


class MandarakeAuctionScraper:
    """Scraper for Mandarake auction site (ekizo)"""

    # Auction categories from mdrscr
    AUCTION_CATEGORIES = {
        'anime_cels': 'アニメセル',
        'original_art': 'ギャラリー',
        'shikishi': '色紙',
        'comics': 'コミック',
        'figures': 'フィギュア',
        'cards': 'カード',
        'doujinshi': '同人誌',
        'books': '本',
        'goods': 'グッズ'
    }

    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://ekizo.mandarake.co.jp"

        # Setup session
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

    def parse_time_left(self, time_str: str) -> Dict:
        """Parse Japanese time duration from auction listings"""
        if time_str == '入札開始前':
            return {'type': 'pre-bidding'}

        # Regex for parsing Japanese time: 13日18時間3分
        time_regex = re.compile(r'(([0-9]+)日)?(([0-9]+)時間)?(([0-9]+)分)?')
        matches = time_regex.match(time_str)

        if not matches:
            return {'type': 'unknown', 'raw': time_str}

        days = int(matches.group(2)) if matches.group(2) else 0
        hours = int(matches.group(4)) if matches.group(4) else 0
        minutes = int(matches.group(6)) if matches.group(6) else 0

        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'formatted_time': f"{hours:02d}:{minutes:02d}"
        }

    def parse_price(self, price_str: str) -> int:
        """Parse price string, removing commas and converting to int"""
        if not price_str:
            return 0
        return int(price_str.replace(',', '').replace('円', ''))

    def parse_auction_item(self, item_element) -> Optional[Dict]:
        """Parse a single auction item from HTML"""
        try:
            # Extract basic information
            title_elem = item_element.find(id='itemName')
            title = title_elem.get_text(strip=True) if title_elem else ''

            item_no_elem = item_element.find(id='itemNo')
            item_no = item_no_elem.get_text(strip=True) if item_no_elem else ''

            # Image and link
            link_elem = item_element.find(id='goItemInfo')
            link = urljoin(self.base_url, link_elem.get('href')) if link_elem else ''

            image_elem = item_element.find(id='thumbnail')
            image = image_elem.get('src') if image_elem else ''

            # Auction type and shop
            auction_type_elem = item_element.find(id='auctionName')
            auction_type = auction_type_elem.get_text(strip=True) if auction_type_elem else ''

            shop_elem = item_element.find('#isNotAucFesta .shop')
            shop = shop_elem.get_text(strip=True) if shop_elem else ''

            # Categories
            categories = []
            category_elems = item_element.find_all('#aucItemCategoryItems a')
            for cat_elem in category_elems:
                name_elem = cat_elem.find(id='name')
                if name_elem:
                    category_name = name_elem.get_text(strip=True)
                    href = cat_elem.get('href', '')
                    # Extract category slug from URL
                    category_match = re.search(r'category=(.+?)$', href)
                    category_slug = category_match.group(1) if category_match else ''
                    categories.append({
                        'name': category_name,
                        'slug': category_slug
                    })

            # Prices
            current_price_elem = item_element.find(id='nowPrice')
            current_price = self.parse_price(current_price_elem.get_text(strip=True)) if current_price_elem else 0

            starting_price_elem = item_element.find(id='startPrice')
            starting_price = self.parse_price(starting_price_elem.get_text(strip=True)) if starting_price_elem else 0

            # Bid and watch counts
            bid_count_elem = item_element.find(id='bidCount')
            bids = int(bid_count_elem.get_text(strip=True)) if bid_count_elem else 0

            watch_count_elem = item_element.find(id='watchCount')
            watchers = int(watch_count_elem.get_text(strip=True)) if watch_count_elem else 0

            # Time left
            time_left_elem = item_element.find(id='strTimeLeft')
            time_left_str = time_left_elem.get_text(strip=True) if time_left_elem else ''
            time_left = self.parse_time_left(time_left_str)

            return {
                'title': title,
                'item_no': item_no,
                'link': link,
                'image': image,
                'auction_type': auction_type,
                'shop': shop if shop else None,
                'categories': categories,
                'current_price': current_price,
                'starting_price': starting_price,
                'bids': bids,
                'watchers': watchers,
                'time_left': time_left,
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            logging.warning(f"Error parsing auction item: {e}")
            return None

    def search_auctions(self, query: str = '', category: str = '') -> Dict:
        """Search auction listings"""
        # Build search URL
        search_url = f"{self.base_url}/auction/item/itemsListJa.html"
        params = {}

        if query:
            params['q'] = query
        if category:
            params['category'] = category

        try:
            response = self.session.get(search_url, params=params, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find auction items
            items = soup.find_all(id='itemListLayout')
            if not items:
                items = soup.find_all(class_='block')

            results = []
            for item in items:
                parsed_item = self.parse_auction_item(item)
                if parsed_item:
                    results.append(parsed_item)

            # Filter by category if both query and category are provided
            if query and category:
                results = [item for item in results
                          if any(cat['slug'] == category for cat in item['categories'])]

            return {
                'search_details': {'query': query, 'category': category},
                'url': response.url,
                'entries': results,
                'entry_count': len(results),
                'language': 'ja'
            }

        except Exception as e:
            logging.error(f"Auction search failed: {e}")
            return {
                'search_details': {'query': query, 'category': category},
                'url': search_url,
                'entries': [],
                'entry_count': 0,
                'error': str(e)
            }

    def get_auction_categories(self) -> Dict[str, str]:
        """Get available auction categories"""
        return self.AUCTION_CATEGORIES


def main():
    """Test the auction scraper"""
    scraper = MandarakeAuctionScraper()

    # Test search
    results = scraper.search_auctions(query='ルパン三世', category='anime_cels')

    print(f"Found {results['entry_count']} auction items")
    for item in results['entries'][:3]:  # Show first 3 items
        print(f"- {item['title']}")
        print(f"  Current Price: {item['current_price']}円")
        print(f"  Bids: {item['bids']}")
        print(f"  Time Left: {item['time_left']}")
        print()


if __name__ == '__main__':
    main()