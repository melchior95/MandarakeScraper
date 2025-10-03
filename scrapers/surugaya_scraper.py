"""
Suruga-ya Scraper

Scrapes product listings from www.suruga-ya.jp
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.base_scraper import BaseScraper


class SurugayaScraper(BaseScraper):
    """Scraper for Suruga-ya marketplace"""

    def __init__(self):
        super().__init__(
            marketplace_name='surugaya',
            base_url='https://www.suruga-ya.jp',
            rate_limit=2.0  # 2 seconds between requests
        )

    def search(self, keyword: str, category: str = '7', shop_code: str = 'all',
              max_results: int = 50, show_out_of_stock: bool = False) -> List[Dict]:
        """
        Search Suruga-ya for items

        Args:
            keyword: Search keyword (Japanese or English)
            category: Category code (default: '7' = Books & Photobooks)
            shop_code: Shop code (default: 'all')
            max_results: Maximum results to return
            show_out_of_stock: Include out of stock items

        Returns:
            List of normalized result dictionaries
        """
        self.logger.info(f"Searching Suruga-ya: keyword='{keyword}', category={category}, max={max_results}")

        results = []
        page = 1

        while len(results) < max_results:
            # Build search URL
            url = self._build_search_url(keyword, category, shop_code, page)

            # Fetch page
            soup = self.fetch_page(url)
            if not soup:
                self.logger.error(f"Failed to fetch page {page}")
                break

            # Extract items
            items = soup.select('.item_box, .item')  # Try multiple selectors
            if not items:
                self.logger.info(f"No items found on page {page}")
                break

            self.logger.info(f"Found {len(items)} items on page {page}")

            # Parse each item
            for item_elem in items:
                if len(results) >= max_results:
                    break

                item_data = self.parse_item(item_elem)
                if item_data:
                    # Filter out of stock if needed
                    if not show_out_of_stock and item_data.get('stock_status') == 'Out of Stock':
                        continue

                    # Normalize and add to results
                    normalized = self.normalize_result(item_data)
                    results.append(normalized)

            # Check for next page (pagination)
            # Suruga-ya uses URL parameter for pagination
            if len(items) == 0 or len(results) >= max_results:
                break

            page += 1

        self.logger.info(f"Scraping complete: {len(results)} items found")
        return results

    def parse_item(self, item_elem) -> Optional[Dict]:
        """
        Parse a single item from .item_box element

        Args:
            item_elem: BeautifulSoup element containing item

        Returns:
            Raw data dictionary or None if parsing fails
        """
        try:
            item_data = {}

            # Title - try multiple selectors
            title_elem = item_elem.select_one('.item_detail a, .title a, h3 a')
            if not title_elem:
                return None

            item_data['title'] = title_elem.get_text(strip=True)
            item_data['url'] = self._build_absolute_url(title_elem.get('href', ''))

            # Extract product ID from URL
            product_id_match = re.search(r'product/detail/(\d+)', item_data['url'])
            if product_id_match:
                item_data['product_id'] = product_id_match.group(1)
            else:
                item_data['product_id'] = ''

            # Price - format: "中古：￥1,234 税込" or "新品：￥5,678 税込"
            price_elem = item_elem.select_one('.price, .item_price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                item_data['price'] = price_text
            else:
                item_data['price'] = '0'

            # Condition - extract from price text or separate element
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                if '中古' in price_text:
                    item_data['condition'] = 'Used'
                elif '新品' in price_text:
                    item_data['condition'] = 'New'
                else:
                    item_data['condition'] = 'Unknown'
            else:
                item_data['condition'] = 'Unknown'

            # Stock status - look for out of stock indicators
            stock_elem = item_elem.select_one('.stock_status, .soldout, .item_status')
            if stock_elem:
                stock_text = stock_elem.get_text(strip=True)
                if '売切' in stock_text or 'sold' in stock_text.lower():
                    item_data['stock_status'] = 'Out of Stock'
                else:
                    item_data['stock_status'] = 'In Stock'
            else:
                # Default to in stock if no indicator
                item_data['stock_status'] = 'In Stock'

            # Image - Suruga-ya uses database/photo.php for thumbnails
            img_elem = item_elem.select_one('img')
            if img_elem:
                img_url = img_elem.get('src', '')
                if img_url:
                    item_data['image_url'] = self._build_absolute_url(img_url)
                    item_data['thumbnail_url'] = item_data['image_url']
                else:
                    item_data['image_url'] = ''
                    item_data['thumbnail_url'] = ''
            else:
                item_data['image_url'] = ''
                item_data['thumbnail_url'] = ''

            # Additional info that might be available
            item_data['seller'] = 'Suruga-ya'
            item_data['location'] = self._extract_location(item_elem)
            item_data['currency'] = 'JPY'

            # Extra data
            item_data['extra'] = {
                'release_date': self._extract_release_date(item_elem),
                'publisher': self._extract_publisher(item_elem)
            }

            return item_data

        except Exception as e:
            self.logger.error(f"Failed to parse item: {e}")
            return None

    def _build_search_url(self, keyword: str, category: str, shop_code: str, page: int = 1) -> str:
        """
        Build Suruga-ya search URL

        Args:
            keyword: Search keyword
            category: Category code
            shop_code: Shop code
            page: Page number (1-indexed)

        Returns:
            Complete search URL
        """
        params = [
            f"category={category}",
            f"search_word={quote(keyword)}",
            "searchbox=1"
        ]

        if shop_code and shop_code != 'all':
            params.append(f"tenpo_code={shop_code}")

        if page > 1:
            # Suruga-ya pagination (adjust if needed based on actual site behavior)
            params.append(f"page={page}")

        return f"{self.base_url}/search?{'&'.join(params)}"

    def _extract_location(self, item_elem) -> str:
        """Extract store location from item if available"""
        location_elem = item_elem.select_one('.location, .shop_name, .store')
        if location_elem:
            return location_elem.get_text(strip=True)
        return ''

    def _extract_release_date(self, item_elem) -> str:
        """Extract release date if available"""
        date_elem = item_elem.select_one('.release_date, .date')
        if date_elem:
            return date_elem.get_text(strip=True)
        return ''

    def _extract_publisher(self, item_elem) -> str:
        """Extract publisher/maker if available"""
        publisher_elem = item_elem.select_one('.publisher, .maker, .brand')
        if publisher_elem:
            return publisher_elem.get_text(strip=True)
        return ''


# CLI testing
if __name__ == "__main__":
    import sys
    import json

    # Test search
    scraper = SurugayaScraper()

    keyword = sys.argv[1] if len(sys.argv) > 1 else "杉浦則夫"
    category = sys.argv[2] if len(sys.argv) > 2 else "7"
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    print(f"Searching Suruga-ya for: '{keyword}' (category={category}, max={max_results})")
    print("=" * 80)

    results = scraper.search(keyword, category=category, max_results=max_results)

    print(f"\nFound {len(results)} results:")
    print("=" * 80)

    for i, item in enumerate(results, 1):
        print(f"\n{i}. {item['title'][:80]}")
        print(f"   Price: ¥{item['price']:.0f}")
        print(f"   Condition: {item['condition']}")
        print(f"   Stock: {item['stock_status']}")
        print(f"   URL: {item['url']}")
        if item['image_url']:
            print(f"   Image: {item['image_url'][:80]}...")

    # Save to JSON for inspection
    output_file = "surugaya_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n\nResults saved to: {output_file}")
