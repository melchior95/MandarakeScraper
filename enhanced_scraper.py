#!/usr/bin/env python3
"""
Enhanced Mandarake Scraper - Combining features from both projects
Based on original mandarake_scraper.py + mdrscr features
"""

import argparse
import csv
import json
import logging
import os
import pickle
import re
import requests
import schedule
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import gspread
from bs4 import BeautifulSoup
from google.auth.exceptions import RefreshError
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
from tqdm import tqdm

# Import our enhanced code mappings
from mandarake_codes import (
    MANDARAKE_STORES, MANDARAKE_ALL_CATEGORIES,
    get_store_name, get_category_name
)

class EnhancedMandarakeScraper:
    """Enhanced Mandarake scraper with mdrscr features"""

    # Constants from mdrscr for better parsing
    IN_STOCK = {'ja': '在庫あります', 'en': 'In stock'}
    IN_STOREFRONT = {'ja': '在庫確認します', 'en': 'Store Front Item'}
    PRICE_REGEX = {'ja': re.compile(r'([0-9,]+)円(\+税)?'), 'en': re.compile(r'([0-9,]+) yen')}
    ITEM_NO_REGEX = re.compile(r'(.+?)(\(([0-9-]+)\))?$')

    def __init__(self, config_path: str):
        """Initialize enhanced scraper with configuration"""
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        self.state_file = f"state_{Path(config_path).stem}.pkl"
        self.state = self._load_state()
        self.language = self.config.get('language', 'ja')  # Support for language selection

        # Setup logging
        self._setup_logging()

        # Enhanced session headers with cookie support
        self._setup_session()

        # Initialize APIs with fallback handling
        self.ebay_api = self._initialize_ebay_api()
        self.sheets_api = self._initialize_sheets_api()
        self.drive_api = self._initialize_drive_api()

        # Results storage
        self.results = []

    def _setup_session(self):
        """Setup enhanced session with better headers and cookie support"""
        # Enhanced headers based on mdrscr
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })

        # Add required cookie from mdrscr documentation
        self.session.cookies.set(
            'tr_mndrk_user',
            'enhanced_scraper_2025',
            domain='.mandarake.co.jp',
            path='/'
        )

    def _load_config(self, config_path: str) -> Dict:
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
                logging.StreamHandler(sys.stdout)
            ]
        )

    def parse_price(self, price_text: str) -> int:
        """Enhanced price parsing using regex from mdrscr"""
        if not price_text:
            return 0

        match = self.PRICE_REGEX[self.language].search(price_text)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0

    def parse_item_number(self, item_no_text: str) -> List[str]:
        """Enhanced item number parsing from mdrscr"""
        if not item_no_text:
            return []

        match = self.ITEM_NO_REGEX.match(item_no_text.strip())
        if match and match.group(3):
            # Both Mandarake ID and product ID
            return [match.group(1).strip(), match.group(3).strip()]
        elif match and match.group(1):
            # Only Mandarake ID
            return [match.group(1).strip()]
        else:
            return [item_no_text.strip()]

    def parse_stock_status(self, stock_text: str) -> Tuple[bool, bool]:
        """Parse stock status to determine availability"""
        if not stock_text:
            return False, False

        stock_text = stock_text.strip()
        in_stock = stock_text in [self.IN_STOCK[self.language], self.IN_STOREFRONT[self.language]]
        in_storefront = stock_text == self.IN_STOREFRONT[self.language]

        return in_stock, in_storefront

    def parse_shop_info(self, shop_text: str) -> Tuple[List[str], str]:
        """Enhanced shop parsing"""
        if not shop_text:
            return [], None

        shop_parts = shop_text.strip().split(' ')
        shop_name = shop_parts[0] if shop_parts else None

        # Find shop code by name
        shop_code = None
        for code, info in MANDARAKE_STORES.items():
            if shop_name in [info['en'], info['jp']]:
                shop_code = code
                break

        return shop_parts, shop_code

    def _extract_product_info_enhanced(self, product_element) -> Optional[Dict]:
        """Enhanced product extraction using mdrscr techniques"""
        try:
            # Check if this is an adult item
            is_adult = product_element.find(class_='r18item') is not None

            # Get title with multiple fallbacks
            title_elem = (product_element.find('a', class_='title') or
                         product_element.find('h3') or
                         product_element.find(class_='title'))

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)

            # Enhanced price extraction
            price_elem = product_element.find(class_=re.compile('price|cost'))
            price_text = price_elem.get_text(strip=True) if price_elem else ''
            price = self.parse_price(price_text)

            # Enhanced image handling for adult content
            if is_adult:
                image_elem = product_element.find(class_='r18item').find('img') if product_element.find(class_='r18item') else None
            else:
                image_elem = product_element.find('img')

            image_url = None
            if image_elem:
                image_url = image_elem.get('src') or image_elem.get('data-src')
                if image_url and not image_url.startswith('http'):
                    image_url = urljoin('https://order.mandarake.co.jp', image_url)

            # Enhanced link extraction
            if is_adult:
                # For adult items, construct link from item code
                adult_link_elem = product_element.find(class_='adult_link')
                if adult_link_elem and adult_link_elem.get('id'):
                    item_id = adult_link_elem.get('id').strip()
                    product_url = f"https://order.mandarake.co.jp/order/detailPage/item?itemCode={item_id}"
                else:
                    product_url = None
            else:
                link_elem = product_element.find('a')
                product_url = None
                if link_elem:
                    product_url = link_elem.get('href')
                    if product_url and not product_url.startswith('http'):
                        product_url = urljoin('https://order.mandarake.co.jp', product_url)

            # Enhanced shop and stock parsing
            shop_elem = product_element.find(class_=re.compile('shop'))
            shop_text = shop_elem.get_text(strip=True) if shop_elem else ''
            shop_parts, shop_code = self.parse_shop_info(shop_text)

            stock_elem = product_element.find(class_=re.compile('stock'))
            stock_text = stock_elem.get_text(strip=True) if stock_elem else ''
            in_stock, in_storefront = self.parse_stock_status(stock_text)

            # Item number parsing
            item_no_elem = product_element.find(class_=re.compile('itemno'))
            item_no_text = item_no_elem.get_text(strip=True) if item_no_elem else ''
            item_numbers = self.parse_item_number(item_no_text)

            return {
                'title': title,
                'price': price,
                'price_text': price_text,
                'image_url': image_url,
                'product_url': product_url,
                'shop': shop_parts,
                'shop_code': shop_code,
                'item_numbers': item_numbers,
                'is_adult': is_adult,
                'in_stock': in_stock,
                'in_storefront': in_storefront,
                'stock_status': stock_text,
                'scraped_at': datetime.now().isoformat(),
                'language': self.language
            }

        except Exception as e:
            logging.warning(f"Error extracting product info: {e}")
            return None

    def _fetch_page_enhanced(self, url: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
        """Enhanced page fetching with better error handling"""
        for attempt in range(max_retries):
            try:
                # Add delay based on attempt number
                time.sleep(1 + attempt)

                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Enhanced blocking detection
                if (response.status_code == 403 or
                    'captcha' in response.text.lower() or
                    'access denied' in response.text.lower() or
                    'robot' in response.text.lower()):
                    logging.warning(f"Access blocked detected on attempt {attempt + 1}")
                    time.sleep(10 * (attempt + 1))  # Longer backoff
                    continue

                return BeautifulSoup(response.content, 'html.parser')

            except requests.RequestException as e:
                logging.warning(f"Request failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))

        logging.error(f"Failed to fetch page after {max_retries} attempts: {url}")
        return None

    # Include all the other methods from the original scraper but enhanced
    # ... (keeping the original API initialization methods and other functionality)

    def _initialize_ebay_api(self):
        """Initialize eBay API (from original)"""
        # ... (keeping original implementation)
        pass

    def _initialize_sheets_api(self):
        """Initialize Google Sheets API (from original)"""
        # ... (keeping original implementation)
        pass

    def _initialize_drive_api(self):
        """Initialize Google Drive API (from original)"""
        # ... (keeping original implementation)
        pass

# Include enhanced URL parsing and main function
def create_enhanced_config_from_url(url: str, output_name: str = None) -> str:
    """Enhanced config creation with better language support"""
    # ... (enhanced version of the original function)
    pass

def main():
    """Enhanced main entry point"""
    parser = argparse.ArgumentParser(description='Enhanced Mandarake Scraper')

    # Enhanced argument parsing
    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument('--config', help='Configuration file path')
    config_group.add_argument('--url', help='Mandarake search URL to scrape')

    parser.add_argument('--output', help='Output name (used with --url)')
    parser.add_argument('--language', choices=['ja', 'en'], default='ja', help='Language preference')
    parser.add_argument('--schedule', help='Schedule time (HH:MM format) for daily runs')
    parser.add_argument('--interval', type=int, help='Run every N minutes')

    args = parser.parse_args()

    # Enhanced URL handling with language support
    # ... (implementation)

if __name__ == '__main__':
    main()