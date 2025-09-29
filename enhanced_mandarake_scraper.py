#!/usr/bin/env python3
"""
Enhanced Mandarake Scraper with Browser Mimicking
Combines the original scraper with advanced browser simulation
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from browser_mimic import BrowserMimic
from result_limiter import MandarakeResultLimiter


class EnhancedMandarakeScraper:
    """Enhanced Mandarake scraper with browser mimicking"""

    def __init__(self, config_path: str):
        """Initialize with browser mimic"""
        self.config = self._load_config(config_path)
        self.config_path = config_path

        # Initialize browser mimic
        session_file = f"browser_session_{Path(config_path).stem}.pkl"
        self.browser = BrowserMimic(session_file)

        # Initialize result limiter
        self.result_limiter = MandarakeResultLimiter(self.browser)

        # Setup logging
        self._setup_logging()

        logging.info(f"Enhanced scraper initialized with browser: {self.browser.get_session_info()}")

    def _get_bool_config(self, key: str, default: bool = False) -> bool:
        """Helper to read boolean flags from config"""
        if key not in self.config:
            return default

        value = self.config.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {'1', 'true', 'yes', 'on'}

        return default

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.DEBUG if self.config.get('debug', False) else logging.INFO
        log_format = '%(asctime)s - %(levelname)s - %(message)s'

        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(f"enhanced_scraper_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )

    def test_connection(self) -> bool:
        """Test connection to Mandarake"""
        test_url = "https://order.mandarake.co.jp"

        try:
            logging.info("Testing connection to Mandarake...")
            response = self.browser.get(test_url)

            success = (response.status_code == 200 and
                      len(response.text) > 100)  # More lenient check

            if success:
                logging.info("✅ Successfully connected to Mandarake")
            else:
                logging.warning(f"⚠️ Connection issues: Status {response.status_code}, Length: {len(response.text)}")

            return success

        except Exception as e:
            logging.error(f"❌ Connection test failed: {e}")
            return False

    def build_search_url(self) -> str:
        """Build search URL from config"""
        base_url = "https://order.mandarake.co.jp/order/ListPage/list"

        params = []
        if self.config.get('keyword'):
            from urllib.parse import quote
            keyword = quote(self.config['keyword'], safe='')
            params.append(f"keyword={keyword}")

        if self.config.get('category'):
            params.append(f"categoryCode={self.config['category']}")

        if self.config.get('shop'):
            params.append(f"shop={self.config['shop']}")

        if self._get_bool_config('hide_sold_out', False):
            params.append('soldOut=1')

        params.append("dispCount=240")  # Max items per page

        return f"{base_url}?{'&'.join(params)}"

    def scrape_search_page(self, url: str) -> dict:
        """Scrape a search page and return results"""
        try:
            logging.info(f"Scraping URL: {url}")
            response = self.browser.get(url)

            if response.status_code != 200:
                logging.error(f"HTTP Error: {response.status_code}")
                return {'error': f"HTTP {response.status_code}", 'results': []}

            content = response.text
            if len(content) < 1000:
                logging.warning(f"Short response ({len(content)} bytes) - possible blocking")
                return {'error': 'Short response', 'results': []}

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Look for product listings with multiple selectors
            products = []

            # Try different selectors based on Mandarake's structure
            selectors = [
                '.entry .thumlarge .block',
                '.item-list .item',
                '.product-item',
                '.search-result-item',
                '.block',
                '.item'
            ]

            for selector in selectors:
                found_products = soup.select(selector)
                if found_products:
                    logging.info(f"Found {len(found_products)} products using selector: {selector}")
                    products = found_products
                    break

            if not products:
                logging.warning("No products found with any selector")
                # Debug: show some of the page structure
                titles = soup.find_all(['h1', 'h2', 'h3', 'title'])
                if titles:
                    logging.info(f"Page titles found: {[t.get_text(strip=True)[:50] for t in titles[:3]]}")

            results = []
            for i, product in enumerate(products[:10]):  # Limit to first 10 for testing
                try:
                    # Extract basic info
                    title = ""
                    price = ""
                    link = ""

                    # Try to find title
                    title_elem = (product.find('a') or
                                 product.find(['h1', 'h2', 'h3', 'h4']) or
                                 product.find(class_=['title', 'name', 'product-title']))

                    if title_elem:
                        title = title_elem.get_text(strip=True)

                    # Try to find price
                    price_elem = product.find(text=lambda x: x and ('円' in x or 'yen' in x.lower()))
                    if price_elem:
                        price = price_elem.strip()

                    # Try to find link
                    link_elem = product.find('a')
                    if link_elem and link_elem.get('href'):
                        link = link_elem.get('href')

                    if title:  # Only add if we found a title
                        results.append({
                            'title': title,
                            'price': price,
                            'link': link,
                            'scraped_at': datetime.now().isoformat()
                        })

                except Exception as e:
                    logging.warning(f"Error parsing product {i}: {e}")

            logging.info(f"Successfully parsed {len(results)} products")
            return {'results': results, 'total_found': len(products)}

        except Exception as e:
            logging.error(f"Scraping failed: {e}")
            return {'error': str(e), 'results': []}

    def run_test_scrape(self, limit_config: dict = None):
        """Run a test scrape with current config and optional limits"""
        logging.info("Starting enhanced scrape test...")

        # Test connection first
        if not self.test_connection():
            logging.error("Connection test failed - aborting scrape")
            return {'error': 'Connection test failed', 'results': []}

        # Build search URL
        search_url = self.build_search_url()
        logging.info(f"Search URL: {search_url}")

        # Use result limiter if configured
        if limit_config:
            logging.info(f"Using result limiter with config: {limit_config}")
            results = self.result_limiter.search_with_limits(search_url, limit_config)

            # Report limited results
            logging.info(f"Limited scrape completed: {results['total_found']} products found across {results['pages_scraped']} pages")

            # Show first few results
            for i, product in enumerate(results['products'][:3]):
                title = product.get('title', 'No title')[:50]
                price = product.get('price_text', 'N/A')
                page = product.get('page', '?')
                logging.info(f"Product {i+1} (Page {page}): {title}... - {price}")

            return results
        else:
            # Use original single page scrape
            results = self.scrape_search_page(search_url)

            # Report results
            if results.get('error'):
                logging.error(f"Scrape failed: {results['error']}")
            else:
                logging.info(f"Scrape completed: {len(results['results'])} products found")

                # Show first few results
                for i, product in enumerate(results['results'][:3]):
                    logging.info(f"Product {i+1}: {product['title'][:50]}... - {product['price']}")

            return results

    def close(self):
        """Clean up resources"""
        if hasattr(self, 'browser'):
            self.browser.close()


def parse_mandarake_url_enhanced(url: str) -> dict:
    """Enhanced URL parsing"""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        config = {}

        # Extract keyword
        if 'keyword' in params:
            config['keyword'] = unquote(params['keyword'][0])

        # Extract category
        if 'categoryCode' in params:
            config['category'] = params['categoryCode'][0]

        # Extract shop
        if 'shop' in params:
            shop_value = params['shop'][0]
            config['shop'] = shop_value

        if 'soldOut' in params:
            config['hide_sold_out'] = params['soldOut'][0] == '1'

        return config

    except Exception as e:
        raise ValueError(f"Invalid Mandarake URL: {e}")


def create_enhanced_config_from_url(url: str, output_name: str = None) -> str:
    """Create config from URL for enhanced scraper"""
    url_config = parse_mandarake_url_enhanced(url)

    if not output_name:
        keyword = url_config.get('keyword', 'search')
        import re
        safe_keyword = re.sub(r'[^\w\-_\.]', '_', keyword)
        output_name = safe_keyword.lower()

    config = {
        'keyword': url_config.get('keyword', ''),
        'category': url_config.get('category', ''),
        'shop': url_config.get('shop', ''),
        'hide_sold_out': url_config.get('hide_sold_out', False),
        'debug': True  # Enable debug logging for testing
    }

    config_path = f'configs/enhanced_{output_name}.json'
    os.makedirs('configs', exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return config_path


def main():
    """Enhanced main entry point"""
    parser = argparse.ArgumentParser(description='Enhanced Mandarake Scraper with Browser Mimicking')

    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument('--config', help='Configuration file path')
    config_group.add_argument('--url', help='Mandarake search URL to scrape')

    parser.add_argument('--output', help='Output name (used with --url)')
    parser.add_argument('--test', action='store_true', help='Run connection test only')

    # Result limiting options
    parser.add_argument('--max-items', type=int, help='Maximum items to return')
    parser.add_argument('--max-pages', type=int, help='Maximum pages to scrape')
    parser.add_argument('--items-per-page', type=int, default=240, help='Items per page (default: 240)')

    args = parser.parse_args()

    # Handle URL input
    if args.url:
        try:
            print(f"Parsing URL: {args.url}")
            config_path = create_enhanced_config_from_url(args.url, args.output)
            print(f"Created config: {config_path}")
            args.config = config_path

        except Exception as e:
            print(f"Error parsing URL: {e}")
            sys.exit(1)

    # Initialize scraper
    try:
        scraper = EnhancedMandarakeScraper(args.config)

        if args.test:
            # Run connection test only
            success = scraper.test_connection()
            print(f"Connection test: {'PASSED' if success else 'FAILED'}")
        else:
            # Build limit config if specified
            limit_config = None
            if args.max_items or args.max_pages:
                limit_config = {
                    'items_per_page': args.items_per_page,
                    'stop_on_empty': True
                }
                if args.max_items:
                    limit_config['max_items'] = args.max_items
                if args.max_pages:
                    limit_config['max_pages'] = args.max_pages

                print(f"Using result limits: {limit_config}")

            # Run scrape test with optional limits
            results = scraper.run_test_scrape(limit_config)

            if limit_config and results.get('products'):
                print(f"Limited scrape completed: {results['total_found']} products found across {results['pages_scraped']} pages")
            else:
                print(f"Scrape test completed: {len(results.get('results', []))} products found")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        if 'scraper' in locals():
            scraper.close()


if __name__ == '__main__':
    main()
