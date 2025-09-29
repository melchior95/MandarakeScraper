#!/usr/bin/env python3
"""
Result Limiter for Mandarake Scraper
Provides flexible options for limiting search results by pages or items
"""

import argparse
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from browser_mimic import BrowserMimic


class MandarakeResultLimiter:
    """Handles result limiting for Mandarake searches"""

    def __init__(self, browser: BrowserMimic):
        self.browser = browser

    def parse_pagination_info(self, soup: BeautifulSoup) -> Dict:
        """Extract pagination information from search results"""
        pagination_info = {
            'current_page': 1,
            'total_pages': 1,
            'total_items': 0,
            'items_per_page': 240
        }

        try:
            # Look for pagination elements with various patterns
            pagination_patterns = [
                # Look for "Page X of Y" or "ページ X / Y"
                lambda: soup.find(string=lambda x: x and ('page' in x.lower() or 'ページ' in x)),
                # Look for navigation elements
                lambda: soup.find_all(class_=['pagination', 'pager', 'page-nav']),
                # Look for numbered page links
                lambda: soup.find_all('a', string=lambda x: x and x.isdigit()),
            ]

            # Try to find total items count
            for text_node in soup.find_all(string=True):
                if text_node and ('件' in text_node or 'items' in text_node.lower()):
                    # Extract numbers from text like "123件見つかりました"
                    import re
                    numbers = re.findall(r'\d+', text_node)
                    if numbers:
                        pagination_info['total_items'] = int(numbers[0])
                        break

            # Try to find page navigation
            page_links = soup.find_all('a', href=True)
            page_numbers = []

            for link in page_links:
                href = link.get('href', '')
                if 'page=' in href:
                    # Extract page number from URL
                    import re
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        page_numbers.append(int(page_match.group(1)))

            if page_numbers:
                pagination_info['total_pages'] = max(page_numbers)

            # Estimate items per page based on dispCount in URL
            current_url = getattr(self.browser, 'last_url', '')
            if 'dispCount=' in current_url:
                import re
                count_match = re.search(r'dispCount=(\d+)', current_url)
                if count_match:
                    pagination_info['items_per_page'] = int(count_match.group(1))

        except Exception as e:
            logging.warning(f"Error parsing pagination: {e}")

        return pagination_info

    def extract_products(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract product information from a search page"""
        products = []

        # Try multiple selectors to find products
        selectors = [
            '.entry .thumlarge .block',
            '.thumlarge .block',
            '.block',
            '.item-container',
            '.product-item',
            '[class*="item"]',
            'tr[onclick]',  # Sometimes items are in table rows
            '.searchresult .item'
        ]

        found_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements and len(elements) > 3:  # Reasonable number of products
                found_elements = elements
                logging.info(f"Found {len(elements)} products using selector: {selector}")
                break

        for i, element in enumerate(found_elements):
            try:
                product = self.parse_single_product(element, i)
                if product:
                    products.append(product)
            except Exception as e:
                logging.warning(f"Error parsing product {i}: {e}")

        return products

    def parse_single_product(self, element, index: int) -> Optional[Dict]:
        """Parse a single product element"""
        try:
            product = {
                'index': index,
                'scraped_at': datetime.now().isoformat()
            }

            # Extract title
            title_selectors = ['a', 'h1', 'h2', 'h3', 'h4', '.title', '.name', '.product-title']
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 3:  # Valid title
                        product['title'] = title
                        break

            # Extract price
            price_text = ""
            price_patterns = [r'[\d,]+円', r'[\d,]+\s*yen']

            for pattern in price_patterns:
                import re
                price_match = re.search(pattern, element.get_text(), re.IGNORECASE)
                if price_match:
                    price_text = price_match.group()
                    # Extract numeric value
                    numeric_price = re.sub(r'[^\d]', '', price_text)
                    if numeric_price:
                        product['price'] = int(numeric_price)
                        product['price_text'] = price_text
                    break

            # Extract image URL
            img_elem = element.find('img')
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src')
                if img_src:
                    from urllib.parse import urljoin
                    product['image_url'] = urljoin('https://order.mandarake.co.jp', img_src)

            # Extract product URL
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem.get('href')
                if href:
                    from urllib.parse import urljoin
                    product['product_url'] = urljoin('https://order.mandarake.co.jp', href)

            # Extract item number if available
            item_no_patterns = [r'[a-zA-Z]+-[a-zA-Z0-9-]+', r'\d{10,}']
            for pattern in item_no_patterns:
                import re
                item_match = re.search(pattern, element.get_text())
                if item_match:
                    product['item_number'] = item_match.group()
                    break

            # Only return if we found at least a title
            if product.get('title'):
                return product

        except Exception as e:
            logging.warning(f"Error parsing product element: {e}")

        return None

    def search_with_limits(self, base_url: str, limit_config: Dict) -> Dict:
        """
        Search with configurable limits

        limit_config options:
        - max_items: Maximum number of items to return (default: unlimited)
        - max_pages: Maximum number of pages to scrape (default: unlimited)
        - items_per_page: Items per page (default: 240)
        - stop_on_empty: Stop if page has no results (default: True)
        """

        max_items = limit_config.get('max_items', float('inf'))
        max_pages = limit_config.get('max_pages', float('inf'))
        items_per_page = limit_config.get('items_per_page', 240)
        stop_on_empty = limit_config.get('stop_on_empty', True)

        all_products = []
        current_page = 1
        total_scraped = 0

        logging.info(f"Starting search with limits: max_items={max_items}, max_pages={max_pages}")

        while current_page <= max_pages and total_scraped < max_items:
            # Build URL for current page
            separator = '&' if '?' in base_url else '?'
            page_url = f"{base_url}{separator}page={current_page}&dispCount={items_per_page}"

            logging.info(f"Scraping page {current_page}: {page_url}")

            try:
                response = self.browser.get(page_url)

                if response.status_code != 200:
                    logging.error(f"HTTP {response.status_code} on page {current_page}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Parse pagination info
                pagination_info = self.parse_pagination_info(soup)

                # Extract products from this page
                page_products = self.extract_products(soup)

                if not page_products and stop_on_empty:
                    logging.info(f"No products found on page {current_page}, stopping")
                    break

                # Apply item limit
                remaining_items = max_items - total_scraped
                if remaining_items < len(page_products):
                    page_products = page_products[:int(remaining_items)]

                # Add products with page info
                for product in page_products:
                    product['page'] = current_page
                    product['position_on_page'] = product['index']
                    product['global_index'] = total_scraped
                    all_products.append(product)
                    total_scraped += 1

                logging.info(f"Page {current_page}: found {len(page_products)} products (total: {total_scraped})")

                # Check if we've reached limits
                if total_scraped >= max_items:
                    logging.info(f"Reached item limit ({max_items})")
                    break

                current_page += 1

                # Add delay between pages
                import time, random
                time.sleep(random.uniform(2, 4))

            except Exception as e:
                logging.error(f"Error scraping page {current_page}: {e}")
                break

        return {
            'products': all_products,
            'total_found': total_scraped,
            'pages_scraped': current_page - 1,
            'pagination_info': pagination_info if 'pagination_info' in locals() else {},
            'limit_config': limit_config,
            'completed': total_scraped < max_items or current_page > max_pages
        }


def main():
    """Test the result limiter"""
    parser = argparse.ArgumentParser(description='Test Mandarake Result Limiter')
    parser.add_argument('--url', required=True, help='Search URL')
    parser.add_argument('--max-items', type=int, help='Maximum items to return')
    parser.add_argument('--max-pages', type=int, help='Maximum pages to scrape')
    parser.add_argument('--items-per-page', type=int, default=50, help='Items per page')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    browser = BrowserMimic('result_limiter_test.pkl')
    limiter = MandarakeResultLimiter(browser)

    try:
        limit_config = {
            'items_per_page': args.items_per_page,
            'stop_on_empty': True
        }

        if args.max_items:
            limit_config['max_items'] = args.max_items
        if args.max_pages:
            limit_config['max_pages'] = args.max_pages

        print(f"Testing with config: {limit_config}")

        results = limiter.search_with_limits(args.url, limit_config)

        print(f"\n=== RESULTS ===")
        print(f"Total products found: {results['total_found']}")
        print(f"Pages scraped: {results['pages_scraped']}")
        print(f"Search completed: {results['completed']}")

        print(f"\nFirst 3 products:")
        for i, product in enumerate(results['products'][:3]):
            print(f"  {i+1}. {product.get('title', 'No title')[:50]}...")
            print(f"      Price: {product.get('price_text', 'N/A')}")
            print(f"      Page: {product.get('page')}, Position: {product.get('position_on_page')}")
            print()

    except Exception as e:
        print(f"Error: {e}")

    finally:
        browser.close()


if __name__ == '__main__':
    main()