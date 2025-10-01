#!/usr/bin/env python3
"""
Mandarake Scraper - Web scraper for Mandarake listings with eBay price comparison
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

from browser_mimic import BrowserMimic
import gspread
from bs4 import BeautifulSoup
from google.auth.exceptions import RefreshError
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
from tqdm import tqdm
from mandarake_codes import get_store_display_name


class MandarakeScraper:
    """Main scraper class for Mandarake listings with enhanced mdrscr features"""

    # Enhanced parsing constants from mdrscr
    IN_STOCK = {'ja': '在庫あります', 'en': 'In stock'}
    IN_STOREFRONT = {'ja': '在庫確認します', 'en': 'Store Front Item'}
    PRICE_REGEX = {'ja': re.compile(r'([0-9,]+)円(\+税)?'), 'en': re.compile(r'([0-9,]+) yen')}
    ITEM_NO_REGEX = re.compile(r'(.+?)(\(([0-9-]+)\))?$')

    def __init__(self, config_path: str, use_mimic: Optional[bool] = None):
        """Initialize scraper with configuration"""
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        self.state_file = f"state_{Path(config_path).stem}.pkl"
        self.state = self._load_state()
        self.language = self.config.get('language', 'ja')  # Language support from mdrscr
        self.use_mimic = self._get_bool_config('mimic', False) if use_mimic is None else use_mimic
        self.browser_mimic = None
        if self.use_mimic:
            session_file = f"browser_session_{Path(config_path).stem}.pkl"
            try:
                self.browser_mimic = BrowserMimic(session_file)
                print(f"[SCRAPER DEBUG] Browser mimic initialized successfully from config")
                logging.info("Browser mimic enabled")
            except Exception as exc:
                print(f"[SCRAPER DEBUG] Browser mimic initialization failed: {exc}")
                logging.warning(f"Failed to initialize browser mimic: {exc}. Falling back to requests session.")
                self.use_mimic = False

        # Setup logging
        self._setup_logging()

        # Enhanced session headers with required cookie from mdrscr
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
            'mandarake_scraper_2025',
            domain='.mandarake.co.jp',
            path='/'
        )

        # Initialize APIs with fallback handling
        self.ebay_api = self._initialize_ebay_api()
        self.sheets_api = self._initialize_sheets_api()
        self.drive_api = self._initialize_drive_api()

        # Results storage
        self.results = []

        self.max_pages_limit = self._get_int_config('max_pages')
        if self.max_pages_limit is not None and self.max_pages_limit <= 0:
            self.max_pages_limit = None
        recent_hours = self._get_int_config('recent_hours')
        self.recent_minutes = recent_hours * 60 if recent_hours else None
        if self.recent_minutes is not None and self.recent_minutes <= 0:
            self.recent_minutes = None

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

    def _get_int_config(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """Helper to read integer settings from config"""
        value = self.config.get(key)
        if value is None or value == '':
            return default
        if isinstance(value, int):
            return value
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    def _initialize_ebay_api(self) -> Optional['EbayAPI']:
        """Initialize eBay API with fallback handling"""
        try:
            client_id = self.config.get('client_id')
            client_secret = self.config.get('client_secret')

            if not client_id or not client_secret or client_id == "YOUR_EBAY_CLIENT_ID":
                logging.warning("eBay API credentials not configured, price comparison will be skipped")
                return None

            api = EbayAPI(client_id, client_secret)
            if api.is_configured():
                logging.info("eBay API initialized successfully")
                return api
            else:
                logging.warning("eBay API configuration invalid, price comparison will be skipped")
                return None

        except Exception as e:
            logging.warning(f"eBay API initialization failed: {e}. Price comparison will be skipped")
            return None

    def _initialize_sheets_api(self) -> Optional['GoogleSheetsAPI']:
        """Initialize Google Sheets API with fallback handling"""
        try:
            # Check if Google Sheets is configured
            sheets_config = self.config.get('google_sheets')
            legacy_sheet = self.config.get('sheet')

            if not sheets_config and not legacy_sheet:
                logging.info("Google Sheets not configured, will save to CSV only")
                return None

            sheet_name = None
            if sheets_config:
                sheet_name = sheets_config.get('sheet_name')
            elif legacy_sheet:
                sheet_name = legacy_sheet

            if not sheet_name:
                logging.warning("Google Sheets name not specified, will save to CSV only")
                return None

            api = GoogleSheetsAPI(sheet_name)
            if api.client:
                logging.info("Google Sheets API initialized successfully")
                return api
            else:
                logging.warning("Google Sheets API initialization failed, will save to CSV only")
                return None

        except Exception as e:
            logging.warning(f"Google Sheets API initialization failed: {e}. Will save to CSV only")
            return None

    def _initialize_drive_api(self) -> Optional['GoogleDriveAPI']:
        """Initialize Google Drive API with fallback handling"""
        try:
            if not self.config.get('upload_drive', False):
                logging.info("Google Drive upload disabled")
                return None

            drive_folder = self.config.get('drive_folder')
            if not drive_folder or drive_folder == "YOUR_DRIVE_FOLDER_ID":
                logging.warning("Google Drive folder not configured, images will be saved locally only")
                return None

            api = GoogleDriveAPI(drive_folder)
            if api.service:
                logging.info("Google Drive API initialized successfully")
                return api
            else:
                logging.warning("Google Drive API initialization failed, images will be saved locally only")
                return None

        except Exception as e:
            logging.warning(f"Google Drive API initialization failed: {e}. Images will be saved locally only")
            return None

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
                logging.FileHandler(f"mandarake_scraper_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def _load_state(self) -> Dict:
        """Load scraper state for resume functionality"""
        if self.config.get('resume', True) and os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'rb') as f:
                    state = pickle.load(f)
                    logging.info(f"Resumed from page {state.get('current_page', 1)}")
                    return state
            except Exception as e:
                logging.warning(f"Could not load state file: {e}")

        return {
            'current_page': 1,
            'total_pages': None,
            'scraped_urls': set(),
            'results': []
        }

    def _save_state(self):
        """Save current scraper state"""
        if self.config.get('resume', True):
            try:
                with open(self.state_file, 'wb') as f:
                    pickle.dump(self.state, f)
            except Exception as e:
                logging.error(f"Could not save state: {e}")

    def _build_search_url(self, page: int = 1, category: str = None, shop: str = None) -> str:
        """Build Mandarake search URL with parameters"""
        base_url = "https://order.mandarake.co.jp/order/ListPage/list"

        # Use specific parameters if provided, otherwise use config defaults
        category_code = category or self.config.get('category', '')
        shop_code = shop or self.config.get('shop', '')

        # Get results per page from config, default to 240 (max)
        results_per_page = self.config.get('results_per_page', 240)

        params = {
            'keyword': self.config.get('keyword', ''),  # Make keyword optional
            'categoryCode': category_code,
            'shop': shop_code,
            'dispCount': results_per_page,  # Configurable items per page
            'page': page
        }

        if self.language == 'en':
            params['lang'] = 'en'

        if self._get_bool_config('hide_sold_out', False):
            params['soldOut'] = '1'

        if getattr(self, 'recent_minutes', None):
            params['upToMinutes'] = str(self.recent_minutes)

        # Filter out empty parameters
        params = {k: v for k, v in params.items() if v}

        # Build URL manually to ensure proper encoding
        from urllib.parse import quote
        encoded_params = []
        for k, v in params.items():
            if k == 'keyword':
                # Properly encode Japanese characters in URL
                encoded_value = quote(str(v), safe='')
                encoded_params.append(f"{k}={encoded_value}")
            else:
                encoded_params.append(f"{k}={v}")

        param_string = '&'.join(encoded_params)
        final_url = f"{base_url}?{param_string}"

        # Log detailed URL information
        logging.info(f"Building request URL for page {page}:")
        logging.info(f"   Base URL: {base_url}")
        keyword = self.config.get('keyword', '')
        logging.info(f"   Keyword: '{keyword}'" if keyword else "   Keyword: (none - browsing category)")
        if category_code:
            logging.info(f"   Category: {category_code}")
        if shop_code:
            logging.info(f"   Shop: {shop_code}")
        logging.info(f"   Page: {page}")
        logging.info(f"   Items per page: 240")

        if self._get_bool_config('hide_sold_out', False):
            logging.info(f"   Hide sold out: Yes")

        if getattr(self, 'recent_minutes', None):
            logging.info(f"   Recent only: Last {self.recent_minutes} minutes")

        logging.info(f"   Full URL: {final_url}")
        logging.info(f"   URL length: {len(final_url)} characters")

        return final_url

    def _make_request(self, url: str, timeout: int = 30) -> requests.Response:
        """Make HTTP request using browser mimic if enabled, otherwise regular session"""
        if self.use_mimic and self.browser_mimic:
            print(f"[SCRAPER DEBUG] Using browser mimic for URL: {url}")
            return self.browser_mimic.get(url, timeout=timeout)
        else:
            print(f"[SCRAPER DEBUG] Using regular session for URL: {url}")
            return self.session.get(url, timeout=timeout)

    def _fetch_page(self, url: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page with retry logic"""
        if self.use_mimic and self.browser_mimic:
            print(f"[SCRAPER DEBUG] Using browser mimic path for URL: {url}")
            return self._fetch_page_with_mimic(url, max_retries)
        else:
            print(f"[SCRAPER DEBUG] Using regular session path for URL: {url} (use_mimic={self.use_mimic}, browser_mimic={self.browser_mimic})")

        for attempt in range(max_retries):
            try:
                time.sleep(1)  # Rate limiting
                response = self._make_request(url, timeout=30)
                response.raise_for_status()

                # Only check for explicit blocking indicators, not general keywords
                content_lower = response.text.lower()
                explicit_blocking = (
                    response.status_code == 403 or
                    'access denied' in content_lower or
                    'you have been blocked' in content_lower or
                    'captcha verification' in content_lower or
                    'please verify you are human' in content_lower
                )

                if explicit_blocking:
                    logging.warning(f"Access blocking detected on attempt {attempt + 1}")
                    time.sleep(10 * (attempt + 1))  # Longer backoff
                    continue

                return BeautifulSoup(response.content, 'html.parser')

            except requests.RequestException as e:
                logging.warning(f"Request failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))

        logging.error(f"Failed to fetch page after {max_retries} attempts: {url}")
        return None

    def _fetch_page_with_mimic(self, url: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
        for attempt in range(max_retries):
            try:
                print(f"[SCRAPER DEBUG] Browser mimic fetching URL: {url}")
                response = self.browser_mimic.get(url, timeout=30)
                response.raise_for_status()

                # Only check for explicit blocking indicators, not general keywords
                content_lower = response.text.lower()
                explicit_blocking = (
                    response.status_code == 403 or
                    'access denied' in content_lower or
                    'you have been blocked' in content_lower or
                    'captcha verification' in content_lower or
                    'please verify you are human' in content_lower
                )

                if explicit_blocking:
                    logging.warning(f"Access blocking detected (mimic) on attempt {attempt + 1}")
                    time.sleep(10 * (attempt + 1))
                    continue

                return BeautifulSoup(response.content, 'html.parser')

            except requests.RequestException as e:
                logging.warning(f"Mimic request failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))

        logging.warning(f"Failed to fetch page with mimic after {max_retries} attempts: {url}. Falling back to requests session.")
        if self.browser_mimic:
            try:
                self.browser_mimic.close()
            except Exception:
                pass
        self.browser_mimic = None
        self.use_mimic = False
        return self._fetch_page(url, max_retries)

    def parse_price_enhanced(self, price_text: str) -> int:
        """Enhanced price parsing using mdrscr regex patterns"""
        if not price_text:
            return 0

        match = self.PRICE_REGEX[self.language].search(price_text)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0

    def extract_keyword_from_title(self, title: str, search_keyword: str = None) -> str:
        """
        Extract the main keyword/subject from a title.
        Uses the search keyword as reference to find the proper form in the title.

        Args:
            title: Product title
            search_keyword: The keyword used in the search (from config)

        Returns:
            Extracted keyword with proper capitalization
        """
        if not title:
            return ""

        # If no search keyword provided, try to extract from config
        if not search_keyword:
            search_keyword = self.config.get('keyword', '')

        if not search_keyword:
            # Fallback: extract first 2-3 capitalized words
            words = title.split()
            capitalized = [w for w in words[:5] if w and (w[0].isupper() or not w[0].isalpha())]
            return ' '.join(capitalized[:3]) if capitalized else words[0] if words else ""

        # Normalize for comparison
        search_lower = search_keyword.lower()
        title_lower = title.lower()

        # Split search keyword into parts
        search_parts = search_lower.split()

        # Try to find exact match (case-insensitive)
        if search_lower in title_lower:
            # Find the position and extract with original capitalization
            start_idx = title_lower.index(search_lower)
            return title[start_idx:start_idx + len(search_keyword)]

        # Try to find reversed name (e.g., "Kano Yura" when searching "Yura Kano")
        if len(search_parts) == 2:
            reversed_keyword = f"{search_parts[1]} {search_parts[0]}"
            if reversed_keyword in title_lower:
                start_idx = title_lower.index(reversed_keyword)
                # Return in original search order
                return search_keyword.title()

        # Try to find all parts present (possibly non-contiguous)
        all_parts_present = all(part in title_lower for part in search_parts)
        if all_parts_present and len(search_parts) >= 2:
            # Find the span containing all parts
            words = title.split()
            words_lower = [w.lower() for w in words]

            # Find first and last occurrence of search parts
            first_idx = None
            last_idx = None

            for i, word in enumerate(words_lower):
                if any(part in word for part in search_parts):
                    if first_idx is None:
                        first_idx = i
                    last_idx = i

            if first_idx is not None and last_idx is not None:
                # Extract the span, but limit to reasonable length
                span_length = last_idx - first_idx + 1
                if span_length <= 5:  # Reasonable span
                    extracted = ' '.join(words[first_idx:last_idx + 1])
                    # Remove common publisher prefixes if present
                    publishers = ['Takeshobo', 'S-Digital', 'G-WALK', 'Cosplay', 'Fetish', 'Book']
                    for pub in publishers:
                        if extracted.startswith(pub + ' '):
                            extracted = extracted[len(pub) + 1:]
                            break
                    return extracted

        # Fallback: return search keyword with title case
        return search_keyword.title()

    def parse_item_number(self, item_no_text: str) -> List[str]:
        """Parse item number from mdrscr format"""
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
        """Parse stock status with mdrscr logic"""
        if not stock_text:
            return False, False

        stock_text = stock_text.strip()
        in_stock = stock_text in [self.IN_STOCK[self.language], self.IN_STOREFRONT[self.language]]
        in_storefront = stock_text == self.IN_STOREFRONT[self.language]

        return in_stock, in_storefront

    def _extract_product_info(self, product_element) -> Optional[Dict]:
        """Enhanced product extraction using mdrscr techniques"""
        try:
            # Check if this is an adult item (mdrscr feature)
            is_adult = product_element.find(class_='r18item') is not None

            # Enhanced title extraction with multiple fallbacks
            title_elem = None
            # Try div.title > p > a (current Mandarake structure)
            title_div = product_element.find('div', class_='title')
            if title_div:
                title_link = title_div.find('a')
                if title_link:
                    title_elem = title_link

            # Fallback to other structures
            if not title_elem:
                title_elem = (product_element.find('a', class_='title') or
                             product_element.find('h3') or
                             product_element.find(class_='title'))

            if not title_elem:
                logging.debug(f"No title element found in product")
                return None

            title = title_elem.get_text(strip=True)
            if not title:
                logging.debug(f"Empty title text")
                return None

            # Enhanced price extraction
            price_elem = product_element.find(class_=re.compile('price|cost'))
            price_text = price_elem.get_text(strip=True) if price_elem else ''
            price = self.parse_price_enhanced(price_text)

            # Enhanced image handling for adult content
            if is_adult:
                r18_container = product_element.find(class_='r18item')
                image_elem = r18_container.find('img') if r18_container else None
            else:
                image_elem = product_element.find('img')

            image_url = None
            if image_elem:
                image_url = image_elem.get('src') or image_elem.get('data-src')
                if image_url and not image_url.startswith('http'):
                    image_url = urljoin('https://order.mandarake.co.jp', image_url)

            # Enhanced link extraction for adult content
            if is_adult:
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

            # Enhanced shop parsing
            shop_elem = product_element.find(class_=re.compile('shop'))
            shop_text = shop_elem.get_text(strip=True) if shop_elem else ''
            shop_parts = shop_text.split(' ') if shop_text else []

            # Enhanced stock status
            stock_elem = product_element.find(class_=re.compile('stock'))
            stock_text = stock_elem.get_text(strip=True) if stock_elem else ''
            in_stock, in_storefront = self.parse_stock_status(stock_text)

            # Item number parsing
            item_no_elem = product_element.find(class_=re.compile('itemno'))
            item_no_text = item_no_elem.get_text(strip=True) if item_no_elem else ''
            item_numbers = self.parse_item_number(item_no_text)

            # Extract keyword from title
            keyword = self.extract_keyword_from_title(title)

            return {
                'title': title,
                'keyword': keyword,
                'price': price,
                'price_text': price_text,
                'image_url': image_url,
                'product_url': product_url,
                'shop': shop_parts,
                'shop_text': shop_text,
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

    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """Extract total number of pages from pagination"""
        try:
            # Look for pagination elements - adjust selectors as needed
            pagination = soup.find('div', class_=re.compile('paging|pagination'))
            if pagination:
                page_links = pagination.find_all('a')
                if page_links:
                    # Extract page numbers and find the maximum
                    pages = []
                    for link in page_links:
                        text = link.get_text(strip=True)
                        if text.isdigit():
                            pages.append(int(text))
                    if pages:
                        return max(pages)

            # Fallback: look for "page X of Y" text
            page_text = soup.find(text=re.compile(r'(\d+)\s*of\s*(\d+)'))
            if page_text:
                match = re.search(r'(\d+)\s*of\s*(\d+)', page_text)
                if match:
                    return int(match.group(2))

            return 1  # Default to 1 page if can't determine

        except Exception as e:
            logging.warning(f"Error determining total pages: {e}")
            return 1

    def scrape_page(self, page_num: int, category: str = None, shop: str = None) -> List[Dict]:
        """Scrape a single page of results"""
        url = self._build_search_url(page_num, category, shop)
        info_parts = []
        if category:
            info_parts.append(f"category: {category}")
        if shop:
            info_parts.append(f"shop: {shop}")
        info_str = f" ({', '.join(info_parts)})" if info_parts else ""

        logging.info("=" * 50)
        logging.info(f"SCRAPING PAGE {page_num}")
        logging.info("=" * 50)
        logging.info(f"Target: {info_str[2:-1] if info_str else 'All categories, all shops'}")  # Remove parentheses
        logging.info(f"Making HTTP GET request to Mandarake...")

        soup = self._fetch_page(url)
        if not soup:
            logging.error("FAILED to fetch page - no content received")
            return []

        logging.info("Successfully received page content")

        # Update total pages if not set for this combination
        combo_key = f'combo_{category or "default"}_{shop or "default"}'
        if combo_key not in self.state:
            self.state[combo_key] = {'current_page': 1, 'total_pages': None}

        combo_state = self.state[combo_key]
        if combo_state['total_pages'] is None:
            combo_state['total_pages'] = self._get_total_pages(soup)
            combo_desc = self._get_combination_description(category, shop)
            logging.info(f"Detected {combo_state['total_pages']} total pages for {combo_desc}")

        # Find product listings using successful selectors from result_limiter
        products = []
        selectors = [
            '.entry .thumlarge .block',
            '.thumlarge .block',
            '.block',
            '.item-container',
            '.product-item',
            '[class*="item"]'
        ]

        logging.info("Parsing page content for products...")

        for selector in selectors:
            found_products = soup.select(selector)
            if found_products and len(found_products) > 3:  # Reasonable number of products
                products = found_products
                logging.info(f"Found {len(products)} product elements using CSS selector: {selector}")
                break

        if not products:
            logging.warning("No products found with primary selectors, trying fallback...")
            # Fallback to original selectors
            products = soup.find_all('div', class_=re.compile('item|product|listing'))
            if not products:
                products = soup.find_all('li', class_=re.compile('item|product'))
            if products:
                logging.info(f"Found {len(products)} products using fallback selectors")

        page_results = []
        none_count = 0
        duplicate_count = 0
        for product in products:
            product_info = self._extract_product_info(product)
            if not product_info:
                none_count += 1
                continue
            if 'product_url' not in product_info or not product_info['product_url']:
                none_count += 1
                continue
            if product_info['product_url'] in self.state['scraped_urls']:
                duplicate_count += 1
                continue
            # Add category and shop information to the product
            if category:
                product_info['category'] = category
            if shop:
                product_info['shop'] = shop
            page_results.append(product_info)
            self.state['scraped_urls'].add(product_info['product_url'])

        if none_count > 0:
            logging.warning(f"Failed to extract info from {none_count} products")
        if duplicate_count > 0:
            logging.info(f"Skipped {duplicate_count} duplicate products")

        info_parts = []
        if category:
            info_parts.append(f"category {category}")
        if shop:
            info_parts.append(f"shop {shop}")
        info_str = f" in {', '.join(info_parts)}" if info_parts else ""

        logging.info("-" * 50)
        logging.info(f"EXTRACTION RESULTS")
        logging.info("-" * 50)
        logging.info(f"Total elements found: {len(products)}")
        logging.info(f"New products extracted: {len(page_results)}")
        logging.info(f"Duplicate products skipped: {len(products) - len(page_results)}")

        if page_results:
            logging.info(f"Sample products:")
            for i, product in enumerate(page_results[:3]):  # Show first 3
                title = product.get('title', 'No title')[:50]
                price = product.get('price_text', 'No price')
                logging.info(f"   {i+1}. {title}{'...' if len(product.get('title', '')) > 50 else ''} - {price}")

        logging.info("=" * 50)
        return page_results, duplicate_count

    def scrape_all_pages(self):
        """Scrape all pages with progress tracking"""
        # Support multiple categories and shops
        categories = self._get_categories_to_scrape()
        shops = self._get_shops_to_scrape()

        total_combinations = len(categories) * len(shops)
        logging.info(f"Starting scrape: {len(categories)} categories × {len(shops)} shops = {total_combinations} combinations")

        for category in categories:
            for shop in shops:
                combo_desc = self._get_combination_description(category, shop)
                logging.info(f"Starting scrape for {combo_desc}")
                self._scrape_combination(category, shop)

        logging.info(f"All combinations completed. Total products found: {len(self.results)}")

    def _get_categories_to_scrape(self) -> List[str]:
        """Get list of categories to scrape from config"""
        category_config = self.config.get('category')

        if isinstance(category_config, list):
            # Multiple categories specified
            return category_config
        elif category_config:
            # Single category specified
            return [category_config]
        else:
            # No category specified
            return [None]

    def _get_shops_to_scrape(self) -> List[str]:
        """Get list of shops to scrape from config"""
        shop_config = self.config.get('shop')

        if isinstance(shop_config, list):
            # Multiple shops specified
            return shop_config
        elif shop_config:
            # Single shop specified
            return [shop_config]
        else:
            # No shop specified - scrape all shops
            return [None, 'nakano', 'shibuya', 'umeda', 'fukuoka', 'ekoda', 'akihabara', 'grandchaos', 'complex', 'sahra', 'cosmos']

    def _get_combination_description(self, category: str = None, shop: str = None) -> str:
        """Get description for category/shop combination"""
        parts = []
        if category:
            parts.append(f"category {category}")
        else:
            parts.append("all categories")

        if shop:
            parts.append(f"shop {shop}")
        else:
            parts.append("all shops")

        return ' + '.join(parts)

    def _scrape_combination(self, category: str = None, shop: str = None):
        """Scrape all pages for a specific category/shop combination"""
        combo_key = f'combo_{category or "default"}_{shop or "default"}'

        if combo_key not in self.state:
            self.state[combo_key] = {
                'current_page': 1,
                'total_pages': None
            }

        combo_state = self.state[combo_key]
        start_page = combo_state['current_page']
        combo_desc = self._get_combination_description(category, shop)

        # Initial page fetch to determine total pages
        if combo_state['total_pages'] is None:
            initial_results, _ = self.scrape_page(start_page, category, shop)
            self.results.extend(initial_results)
            combo_state['current_page'] = start_page + 1
            self._save_state()

        total_pages = combo_state['total_pages'] or 1
        effective_total = total_pages
        if self.max_pages_limit:
            effective_total = min(total_pages, self.max_pages_limit)

        next_page = combo_state['current_page']
        max_limit = self.max_pages_limit
        if max_limit and next_page > max_limit:
            logging.info(f"Max page limit ({max_limit}) reached for {combo_desc}, skipping remaining pages")
            return

        if next_page > effective_total:
            logging.info(f"Max page limit reached for {combo_desc}, skipping remaining pages")
            return

        # Track new vs duplicate items for smart stopping
        consecutive_high_duplicate_pages = 0
        DUPLICATE_THRESHOLD = 0.8  # Stop if 80% duplicates
        CONSECUTIVE_PAGES_TO_STOP = 2  # Stop after 2 consecutive high-duplicate pages

        with tqdm(total=effective_total,
                 desc=f"Scraping {combo_desc}",
                 initial=min(next_page - 1, effective_total)) as pbar:

            for page in range(next_page, effective_total + 1):
                # Check for cancellation request
                if getattr(self, '_cancel_requested', False):
                    logging.info(f"Cancellation requested, stopping scrape at page {page}")
                    break

                # Track items before this page
                items_before = len(self.results)

                page_results, duplicates_on_page = self.scrape_page(page, category, shop)

                # Only stop on page > 1 if no results (pagination end)
                # Page 1 with no results is legitimate (no matching items)
                if not page_results and page > 1:
                    logging.warning(f"No results found on page {page} for {combo_desc}, stopping pagination")
                    break

                self.results.extend(page_results)

                # Calculate new items on this page
                items_after = len(self.results)
                new_items_this_page = items_after - items_before

                # Smart stopping: if no max_pages set and we hit many duplicates
                if not self.max_pages_limit and page > 1:
                    # If 10 or more duplicates on this page, stop
                    if duplicates_on_page >= 10:
                        logging.info(f"Page {page}: Found {duplicates_on_page} duplicates - stopping early")
                        logging.info(f"Total items collected: {len(self.results)}")
                        break

                    # Also track consecutive low-yield pages as backup
                    if items_before > 50 and new_items_this_page < 5:
                        consecutive_high_duplicate_pages += 1
                        logging.info(f"Page {page}: Only {new_items_this_page} new items")

                        if consecutive_high_duplicate_pages >= CONSECUTIVE_PAGES_TO_STOP:
                            logging.info(f"Stopping early: {CONSECUTIVE_PAGES_TO_STOP} consecutive pages with <5 new items")
                            logging.info(f"Total items collected: {len(self.results)}")
                            break
                    else:
                        consecutive_high_duplicate_pages = 0  # Reset counter

                combo_state['current_page'] = page + 1
                self.state['results'] = self.results

                # Save checkpoint after each page
                self._save_state()
                pbar.update(1)

                # Rate limiting
                time.sleep(2)

        found_products = len([r for r in self.results if r.get('category') == category and r.get('shop') == shop])
        logging.info(f"{combo_desc} completed. Found {found_products} products")

    def enhance_with_ebay_data(self):
        """Add eBay price comparison data"""
        if not self.ebay_api:
            logging.info("eBay API not available, skipping price comparison")
            return

        if not self.ebay_api.is_configured():
            logging.warning("eBay API not properly configured, skipping price comparison")
            return

        logging.info("Enhancing results with eBay data...")

        for i, product in enumerate(tqdm(self.results, desc="eBay lookup")):
            try:
                ebay_data = self.ebay_api.search_product(product['title'])
                product.update(ebay_data)
                time.sleep(0.1)  # API rate limiting

            except Exception as e:
                logging.warning(f"eBay lookup failed for '{product['title']}': {e}")
                product.update({
                    'ebay_avg_price': 0,
                    'ebay_sold_count': 0,
                    'ebay_listings': 0,
                    'ebay_error': str(e)
                })

    def download_images(self):
        """Download product images"""
        if not self.config.get('download_images'):
            print("[IMAGE DOWNLOAD] No download_images path configured, skipping")
            return

        image_dir = Path(self.config['download_images'])
        image_dir.mkdir(parents=True, exist_ok=True)

        logging.info(f"Downloading images to {image_dir}")
        print(f"[IMAGE DOWNLOAD] Saving images to: {image_dir}")

        for i, product in enumerate(tqdm(self.results, desc="Downloading images")):
            if not product.get('image_url'):
                continue

            try:
                image_path = self._download_image(product['image_url'], image_dir, i)
                if image_path:
                    product['local_image'] = str(image_path)

                    # Upload to Google Drive if configured
                    if self.drive_api:
                        try:
                            drive_url = self.drive_api.upload_image(image_path)
                            if drive_url:
                                product['drive_image'] = drive_url
                            else:
                                logging.warning(f"Failed to upload image {image_path} to Google Drive")
                        except Exception as e:
                            logging.warning(f"Google Drive upload failed for {image_path}: {e}")
                    else:
                        logging.debug("Google Drive not configured, image saved locally only")

            except Exception as e:
                logging.warning(f"Image download failed: {e}")

    def _download_image(self, url: str, image_dir: Path, index: int) -> Optional[Path]:
        """Download a single image"""
        try:
            # Use regular session directly for images (CDN doesn't need anti-blocking delays)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Extract original filename from URL
            from urllib.parse import urlparse, unquote
            parsed_url = urlparse(url)
            original_filename = Path(unquote(parsed_url.path)).name

            # Use original filename if available, otherwise fall back to indexed name
            if original_filename and '.' in original_filename:
                filename = original_filename
            else:
                # Determine file extension from content type
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                else:
                    ext = '.jpg'  # Default
                filename = f"product_{index:04d}{ext}"

            image_path = image_dir / filename

            with open(image_path, 'wb') as f:
                f.write(response.content)

            # Resize if thumbnails are requested
            if self.config.get('thumbnails'):
                self._create_thumbnail(image_path, self.config['thumbnails'])

            return image_path

        except Exception as e:
            logging.warning(f"Failed to download image {url}: {e}")
            return None

    def _create_thumbnail(self, image_path: Path, max_size: int):
        """Create thumbnail version of image"""
        try:
            with Image.open(image_path) as img:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                thumb_path = image_path.parent / f"thumb_{image_path.name}"
                img.save(thumb_path, optimize=True, quality=85)
        except Exception as e:
            logging.warning(f"Thumbnail creation failed: {e}")

    def save_results(self):
        """Save results to configured outputs"""
        print(f"[SAVE DEBUG] save_results called, results count: {len(self.results)}")
        if not self.results:
            logging.warning("No results to save")
            print(f"[SAVE DEBUG] No results to save, returning early")
            return

        saved_to_any = False

        # Save to CSV (always try this first as fallback)
        csv_path = self.config.get('csv')
        print(f"[SAVE DEBUG] CSV path from config: {csv_path}")
        if csv_path:
            try:
                print(f"[SAVE DEBUG] Calling _save_to_csv()")
                self._save_to_csv()
                saved_to_any = True
                print(f"[SAVE DEBUG] CSV save successful")
            except Exception as e:
                logging.error(f"Failed to save to CSV: {e}")
                print(f"[SAVE DEBUG] CSV save failed: {e}")

        # Save to Google Sheets
        sheets_config = self.config.get('google_sheets') or self.config.get('sheet')
        upload_sheets = self.config.get('upload_sheets', True)
        if upload_sheets and sheets_config and self.sheets_api:
            try:
                self._save_to_sheets()
                saved_to_any = True
            except Exception as e:
                logging.error(f"Failed to save to Google Sheets: {e}")
                if not self.config.get('csv'):
                    logging.info("Creating emergency CSV backup...")
                    self.config['csv'] = f"emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    try:
                        self._save_to_csv()
                        saved_to_any = True
                    except Exception as csv_e:
                        logging.error(f"Emergency CSV backup also failed: {csv_e}")
        elif sheets_config and upload_sheets:
            logging.warning("Google Sheets configured but API not available, data saved to CSV only")

        # Ensure data is saved somewhere
        if not saved_to_any:
            logging.warning("No output method succeeded, creating emergency CSV...")
            self.config['csv'] = f"emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            try:
                self._save_to_csv()
                saved_to_any = True
            except Exception as e:
                logging.error(f"All save methods failed, data may be lost: {e}")

        if saved_to_any:
            logging.info(f"Results saved: {len(self.results)} products")
        else:
            logging.error("Failed to save results to any output method")

    def _save_to_csv(self):
        """Save results to CSV file, appending new items and tracking timestamps"""
        csv_path = self.config['csv']
        logging.info(f"Saving to CSV: {csv_path}")
        print(f"[CSV SAVE DEBUG] Starting CSV save, path: {csv_path}")
        print(f"[CSV SAVE DEBUG] Results count: {len(self.results)}")

        if not self.results:
            print(f"[CSV SAVE DEBUG] No results, returning early")
            return

        # Add timestamp fields to all results
        current_time = datetime.now()
        for result in self.results:
            if 'first_seen' not in result:
                result['first_seen'] = current_time.isoformat()
            if 'last_seen' not in result:
                result['last_seen'] = current_time.isoformat()

        print(f"[CSV SAVE DEBUG] Timestamps added to {len(self.results)} results")

        # Check if CSV exists
        existing_items = {}
        csv_exists = os.path.exists(csv_path)

        if csv_exists:
            # Load existing items (keyed by product_url for deduplication)
            try:
                with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get('product_url', '')
                        if url:
                            existing_items[url] = row
                logging.info(f"Found {len(existing_items)} existing items in CSV")
                print(f"[CSV SAVE DEBUG] Loaded {len(existing_items)} existing items from CSV")
            except Exception as e:
                logging.warning(f"Could not read existing CSV: {e}")
                print(f"[CSV SAVE DEBUG] Failed to load existing CSV: {e}")
                existing_items = {}

        # Merge new results with existing items
        new_count = 0
        updated_count = 0
        merged_items = {}

        # First, add all existing items
        for url, item in existing_items.items():
            merged_items[url] = item

        # Then add/update with new results
        for result in self.results:
            url = result.get('product_url', '')
            if not url:
                print(f"[CSV SAVE DEBUG] Skipping result with no product_url: {result.get('title', 'No title')[:50]}")
                continue

            if url in existing_items:
                # Update last_seen but keep first_seen from existing
                result['first_seen'] = existing_items[url].get('first_seen', result['first_seen'])
                result['last_seen'] = current_time.isoformat()
                updated_count += 1
            else:
                # New item
                new_count += 1

            merged_items[url] = result

        # Ensure fieldnames include timestamp fields at the beginning
        print(f"[CSV SAVE DEBUG] Merged items count: {len(merged_items)}")
        if merged_items:
            sample_item = next(iter(merged_items.values()))
            fieldnames = ['first_seen', 'last_seen'] + [k for k in sample_item.keys() if k not in ['first_seen', 'last_seen']]
            print(f"[CSV SAVE DEBUG] Fieldnames: {len(fieldnames)} fields")
        else:
            fieldnames = list(self.results[0].keys()) if self.results else []
            print(f"[CSV SAVE DEBUG] No merged items, using fallback fieldnames")

        # Write merged results
        print(f"[CSV SAVE DEBUG] Opening CSV file for writing: {csv_path}")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            print(f"[CSV SAVE DEBUG] Header written")
            # Sort by first_seen (newest first)
            sorted_items = sorted(merged_items.values(),
                                key=lambda x: x.get('first_seen', ''),
                                reverse=True)
            print(f"[CSV SAVE DEBUG] Sorted {len(sorted_items)} items, writing to CSV")
            writer.writerows(sorted_items)
            print(f"[CSV SAVE DEBUG] Rows written to CSV")

        logging.info(f"CSV saved: {len(merged_items)} total items ({new_count} new, {updated_count} updated)")
        print(f"[CSV SAVE DEBUG] CSV save completed: {len(merged_items)} total items")
        if new_count > 0:
            logging.info(f"⭐ {new_count} NEW items added!")

    def _save_to_sheets(self):
        """Save results to Google Sheets with local image upload"""
        if not self.sheets_api:
            logging.warning("Google Sheets API not available")
            return

        logging.info("Saving to Google Sheets")
        try:
            # Pass drive_api to enable local image upload
            self.sheets_api.save_results(self.results, drive_api=self.drive_api)
        except Exception as e:
            logging.error(f"Google Sheets save failed: {e}")
            raise

    def cleanup_state(self):
        """Clean up state file after successful completion"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
            logging.info("State file cleaned up")

    def run(self):
        """Main scraping workflow"""
        try:
            logging.info("=" * 60)
            logging.info("MANDARAKE SCRAPER STARTED")
            logging.info("=" * 60)
            keyword = self.config.get('keyword', '')
            logging.info(f"Search keyword: '{keyword}'" if keyword else "Search keyword: (none - browsing by category/shop)")
            logging.info(f"Category: {self.config.get('category', 'All categories')}")
            logging.info(f"Shop: {self.config.get('shop', 'All shops')}")
            logging.info(f"Browser mimic: {'Enabled' if self.use_mimic else 'Disabled'}")
            logging.info(f"Fast mode: {'Enabled (skip eBay)' if self.config.get('fast', False) else 'Disabled'}")
            logging.info(f"Resume mode: {'Enabled' if self.config.get('resume', True) else 'Disabled'}")
            logging.info(f"Max pages limit: {self.max_pages_limit or 'Unlimited'}")

            if self.recent_minutes:
                logging.info(f"Recent items only: Last {self.recent_minutes//60} hours")

            logging.info("-" * 60)

            # Scrape all pages
            self.scrape_all_pages()

            if not self.results:
                logging.info("=" * 60)
                logging.info("SCRAPING COMPLETED - NO MATCHING PRODUCTS")
                logging.info("=" * 60)
                logging.info("The search completed successfully, but no products matched your criteria.")
                logging.info("This is normal if:")
                logging.info("  - Your search keyword has no matching items")
                logging.info("  - The category/shop combination has no products")
                logging.info("  - All matching items are sold out (with hide_sold_out enabled)")
                logging.info("=" * 60)
                return

            # Enhance with eBay data
            if not self.config.get('fast', False):
                self.enhance_with_ebay_data()

            # Download images
            self.download_images()

            # Save results
            self.save_results()

            # Cleanup
            self.cleanup_state()

            # Final summary
            logging.info("=" * 60)
            logging.info("SCRAPING COMPLETED SUCCESSFULLY!")
            logging.info("=" * 60)
            logging.info(f"FINAL RESULTS SUMMARY:")
            keyword = self.config.get('keyword', '')
            logging.info(f"   Search term: '{keyword}'" if keyword else "   Search term: (none - category/shop browse)")
            logging.info(f"   Total products found: {len(self.results)}")
            logging.info(f"   Pages scraped: Multiple")
            logging.info(f"   Fast mode: {'Yes' if self.config.get('fast', False) else 'No'}")

            if self.results:
                # Show price range
                prices = [p.get('price', 0) for p in self.results if p.get('price', 0) > 0]
                if prices:
                    logging.info(f"   Price range: ¥{min(prices):,} - ¥{max(prices):,}")

                # Show sample titles
                logging.info(f"   Sample products:")
                for i, product in enumerate(self.results[:3]):
                    title = product.get('title', 'No title')[:50]
                    price = product.get('price_text', 'No price')
                    logging.info(f"      {i+1}. {title}{'...' if len(product.get('title', '')) > 50 else ''} - {price}")

            logging.info("=" * 60)

        except KeyboardInterrupt:
            logging.info("Scraping interrupted by user")
            self._save_state()
        except Exception as e:
            logging.error(f"Scraping failed: {e}", exc_info=True)
            self._save_state()
            raise
        finally:
            self._close_mimic()


    def _close_mimic(self):
        if getattr(self, 'browser_mimic', None):
            try:
                self.browser_mimic.close()
            except Exception:
                pass
            self.browser_mimic = None


class EbayAPI:
    """eBay API integration for price comparison"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires = None

    def is_configured(self) -> bool:
        """Check if eBay API is properly configured"""
        return bool(self.client_id and self.client_secret and
                   self.client_id != "YOUR_EBAY_CLIENT_ID")

    def _get_access_token(self):
        """Get OAuth access token"""
        if not self.is_configured():
            raise ValueError("eBay API credentials not configured")

        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token

        # Use sandbox URL for SBX credentials
        if self.client_id.startswith('WaiTsui-') and 'SBX' in self.client_id:
            url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
        else:
            url = "https://api.ebay.com/identity/v1/oauth2/token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {self._encode_credentials()}'
        }
        # For sandbox, try without scope first, then fallback to basic scope
        data = {
            'grant_type': 'client_credentials',
            'scope': 'https://api.ebay.com/oauth/api_scope'
        }

        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()

        if response.status_code != 200:
            raise Exception(f"eBay token request failed with status {response.status_code}")

        token_data = response.json()
        self.access_token = token_data['access_token']
        self.token_expires = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)

        return self.access_token

    def _encode_credentials(self) -> str:
        """Encode client credentials for Basic auth"""
        import base64
        credentials = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(credentials.encode()).decode()

    def search_product(self, title: str) -> Dict:
        """Search for product on eBay and return price data"""
        if not self.is_configured():
            return {
                'ebay_avg_price': 0,
                'ebay_sold_count': 0,
                'ebay_listings': 0,
                'ebay_error': 'API not configured'
            }

        try:
            token = self._get_access_token()

            # Use sandbox URL for SBX credentials
            if self.client_id.startswith('WaiTsui-') and 'SBX' in self.client_id:
                url = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
            else:
                url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            params = {
                'q': title[:80],  # Limit query length
                'limit': 50,
                'filter': 'deliveryCountry:US'
            }

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            if response.status_code == 403:
                # Access denied - likely scope issue with sandbox
                raise Exception("eBay Browse API access denied. Sandbox apps may need additional scope permissions from eBay Developer Support.")
            elif response.status_code != 200:
                raise Exception(f"eBay search request failed with status {response.status_code}")

            data = response.json()
            items = data.get('itemSummaries', [])

            if not items:
                return {
                    'ebay_avg_price': 0,
                    'ebay_sold_count': 0,
                    'ebay_listings': 0
                }

            # Calculate average price
            prices = []
            for item in items:
                price_info = item.get('price', {})
                if price_info.get('value'):
                    prices.append(float(price_info['value']))

            avg_price = sum(prices) / len(prices) if prices else 0

            sold_count = sum(
                1 for i in items
                if isinstance(i.get('buyingOptions'), list) and 'FIXED_PRICE' in i['buyingOptions']
            )

            return {
                'ebay_avg_price': round(avg_price, 2),
                'ebay_sold_count': sold_count,
                'ebay_listings': len(items)
            }

        except Exception as e:
            logging.warning(f"eBay API error: {e}")
            return {
                'ebay_avg_price': 0,
                'ebay_sold_count': 0,
                'ebay_listings': 0,
                'ebay_error': str(e)
            }

    def search_sold_listings(self, title: str, days_back: int = 90) -> Dict:
        """Search for sold listings on eBay and return price analysis data"""
        if not self.is_configured():
            return {
                'sold_count': 0,
                'median_price': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'prices': [],
                'error': 'API not configured'
            }

        try:
            token = self._get_access_token()

            # eBay's Browse API doesn't directly support sold listings search
            # We'll use the item_summary/search endpoint with condition filters
            # Note: For real sold listings data, you might need the Trading API or
            # a different approach like the Finding API (which is deprecated)

            # Use sandbox URL for SBX credentials
            if self.client_id.startswith('WaiTsui-') and 'SBX' in self.client_id:
                url = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
            else:
                url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            # Clean up the search title
            search_query = self._clean_search_query(title)

            params = {
                'q': search_query[:80],  # Limit query length
                'limit': 200,  # Max results to analyze
                'filter': 'deliveryCountry:US',
                'sort': 'endTimeNewest'  # Try to get recently ended items
            }

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            if response.status_code == 403:
                raise Exception("eBay Browse API access denied. Sandbox apps may need additional scope permissions.")
            elif response.status_code != 200:
                raise Exception(f"eBay sold listings search failed with status {response.status_code}")

            data = response.json()
            items = data.get('itemSummaries', [])

            if not items:
                return {
                    'sold_count': 0,
                    'median_price': 0,
                    'avg_price': 0,
                    'min_price': 0,
                    'max_price': 0,
                    'prices': []
                }

            # Extract prices from items (these are current listings, not sold)
            # Note: For actual sold data, you'd need the Trading API or a different approach
            prices = []
            for item in items:
                price_info = item.get('price', {})
                if price_info.get('value'):
                    prices.append(float(price_info['value']))

            if not prices:
                return {
                    'sold_count': 0,
                    'median_price': 0,
                    'avg_price': 0,
                    'min_price': 0,
                    'max_price': 0,
                    'prices': []
                }

            # Calculate statistics
            import statistics
            prices.sort()

            return {
                'sold_count': len(prices),
                'median_price': round(statistics.median(prices), 2),
                'avg_price': round(sum(prices) / len(prices), 2),
                'min_price': round(min(prices), 2),
                'max_price': round(max(prices), 2),
                'prices': prices
            }

        except Exception as e:
            logging.warning(f"eBay sold listings search error: {e}")
            return {
                'sold_count': 0,
                'median_price': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'prices': [],
                'error': str(e)
            }

    def _clean_search_query(self, title: str) -> str:
        """Clean up search query for better eBay matching"""
        import re

        # Remove common Japanese particles and improve search
        title = title.replace('　', ' ')  # Replace full-width space
        title = re.sub(r'[【】『』「」〈〉《》]', '', title)  # Remove Japanese brackets
        title = re.sub(r'[（）()]', ' ', title)  # Replace parentheses with spaces
        title = re.sub(r'\s+', ' ', title)  # Normalize spaces
        title = title.strip()

        # Remove common words that might hurt search
        remove_words = ['新品', '中古', '未開封', '限定', 'セット', 'フィギュア']
        for word in remove_words:
            title = title.replace(word, ' ')

        title = re.sub(r'\s+', ' ', title).strip()
        return title

    def search_by_image_api(self, image_path: str) -> Optional[str]:
        """Search for an image on eBay using the search_by_image API."""
        if not self.is_configured():
            logging.warning("eBay API not configured for image search.")
            return None

        try:
            token = self._get_access_token()
            url = "https://api.ebay.com/buy/browse/v1/item_summary/search_by_image"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            with open(image_path, "rb") as image_file:
                import base64
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            data = {
                "image": encoded_string
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            results = response.json()
            
            if results.get("itemSummaries"):
                return results["itemSummaries"][0].get("itemWebUrl")
            else:
                return None

        except Exception as e:
            logging.error(f"eBay search by image API failed: {e}")
            if "invalid_scope" in str(e).lower():
                logging.error("This might be due to missing 'https://api.ebay.com/oauth/api_scope/buy.item.feed' scope in your application's OAuth settings.")
            return None

    def search_sold_listings_web(self, title: str, days_back: int = 90) -> Dict:
        """Search for sold listings on eBay by scraping the website and return price analysis data"""
        import re
        import statistics
        from urllib.parse import quote_plus
        from browser_mimic import BrowserMimic # Make sure this is imported
        from bs4 import BeautifulSoup

        logging.info(f"[EBAY WEB SCRAPE] Searching for: '{title}'")

        # Use a dedicated browser mimic session for eBay
        ebay_browser = BrowserMimic(session_file='ebay_session.pkl')

        try:
            # Construct the URL for sold listings
            query = quote_plus(title)
            url = f"https://www.ebay.com/sch/i.html?_nkw={query}&LH_Sold=1&_ipg=240"

            # Make the request using BrowserMimic
            response = ebay_browser.get(url)
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find price elements
            price_selectors = [
                '.s-item__price',
                '.vi-price',
                '.item__price',
                '.new-item-price'
            ]
            prices = []
            item_container_selector = 'ul.srp-results > li.s-item'
            items = soup.select(item_container_selector)

            for item in items:
                price_text = ''
                for selector in price_selectors:
                    price_element = item.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text(strip=True)
                        break

                if price_text:
                    price_text = price_text.split(' to ')[0]
                    price_value = re.sub(r'[$,]', '', price_text)
                    try:
                        prices.append(float(price_value))
                    except ValueError:
                        continue

            if not prices:
                return {
                    'sold_count': 0,
                    'median_price': 0,
                    'avg_price': 0,
                    'min_price': 0,
                    'max_price': 0,
                    'prices': []
                }

            prices.sort()

            return {
                'sold_count': len(prices),
                'median_price': round(statistics.median(prices), 2),
                'avg_price': round(sum(prices) / len(prices), 2),
                'min_price': round(min(prices), 2),
                'max_price': round(max(prices), 2),
                'prices': prices
            }

        except Exception as e:
            logging.warning(f"[EBAY WEB SCRAPE] Error: {e}")
            return {
                'sold_count': 0,
                'median_price': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'prices': [],
                'error': str(e)
            }
        finally:
            ebay_browser.close()


class GoogleSheetsAPI:
    """Google Sheets integration"""

    def __init__(self, sheet_name: str):
        self.sheet_name = sheet_name
        self.client = None
        self._initialize()

    def _initialize(self):
        """Initialize Google Sheets client"""
        try:
            # Look for credentials file
            creds_files = ['credentials.json', 'service_account.json', 'google_credentials.json']
            creds_path = None

            for filename in creds_files:
                if os.path.exists(filename):
                    creds_path = filename
                    break

            if not creds_path:
                logging.warning("Google Sheets credentials not found. Expected one of: credentials.json, service_account.json, google_credentials.json")
                return

            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            self.client = gspread.authorize(creds)

        except Exception as e:
            logging.warning(f"Google Sheets initialization failed: {e}")

    def save_results(self, results: List[Dict], drive_api=None):
        """Save results to Google Sheets with local image upload support"""
        if not self.client or not results:
            return

        try:
            # Open or create spreadsheet
            try:
                sheet = self.client.open(self.sheet_name).sheet1
            except gspread.SpreadsheetNotFound:
                spreadsheet = self.client.create(self.sheet_name)
                sheet = spreadsheet.sheet1
                spreadsheet.share('', perm_type='anyone', role='reader')  # Make readable

            # Clear existing data
            sheet.clear()

            # Prepare data with local image upload
            if results:
                headers = list(results[0].keys())
                data = [headers]

                for result in results:
                    row = []
                    for header in headers:
                        value = result.get(header, '')

                        # Handle image columns - upload local images to Drive if available
                        if header in {'local_image', 'drive_image', 'image_url'}:
                            if header == 'local_image' and drive_api and isinstance(value, str) and os.path.exists(value):
                                # Upload local image to Google Drive
                                try:
                                    drive_url = drive_api.upload_image(Path(value))
                                    if drive_url:
                                        # Use the uploaded Drive image
                                        row.append(f'=IMAGE("{drive_url.replace("/view", "/uc")}")')  # Convert to direct image URL
                                        logging.info(f"Uploaded local image to Drive: {value}")
                                    else:
                                        # Fallback to web image URL if available
                                        web_url = result.get('image_url', '')
                                        if web_url and web_url.startswith('http'):
                                            row.append(f'=IMAGE("{web_url}")')
                                        else:
                                            row.append('Image upload failed')
                                except Exception as e:
                                    logging.warning(f"Failed to upload local image {value}: {e}")
                                    # Fallback to web image URL
                                    web_url = result.get('image_url', '')
                                    if web_url and web_url.startswith('http'):
                                        row.append(f'=IMAGE("{web_url}")')
                                    else:
                                        row.append('Image unavailable')
                            elif isinstance(value, str) and value.startswith('http'):
                                # Direct web image URL
                                row.append(f'=IMAGE("{value}")')
                            elif header == 'drive_image' and isinstance(value, str) and value.startswith('http'):
                                # Google Drive image - convert to direct access URL
                                if 'drive.google.com' in value:
                                    row.append(f'=IMAGE("{value.replace("/view", "/uc")}")')
                                else:
                                    row.append(f'=IMAGE("{value}")')
                            else:
                                row.append(str(value))
                        elif header == 'shop':
                            row.append(get_store_display_name(value))
                        else:
                            row.append(str(value))
                    data.append(row)

                # Update sheet with image formulas
                sheet.update(range_name='A1', values=data, value_input_option='USER_ENTERED')

                # Auto-resize rows to fit images (if any image columns exist)
                image_columns = [i for i, header in enumerate(headers) if header in {'local_image', 'drive_image', 'image_url'}]
                if image_columns and len(data) > 1:  # Has image columns and data rows
                    try:
                        # Use Google Sheets API to set row heights
                        from googleapiclient.discovery import build
                        from google.oauth2.service_account import Credentials

                        # Get spreadsheet ID from the sheet
                        spreadsheet_id = sheet.spreadsheet.id

                        # Build the Sheets API service
                        creds_files = ['credentials.json', 'service_account.json', 'google_credentials.json']
                        creds_path = None
                        for filename in creds_files:
                            if os.path.exists(filename):
                                creds_path = filename
                                break

                        if creds_path:
                            scope = ['https://www.googleapis.com/auth/spreadsheets']
                            creds = Credentials.from_service_account_file(creds_path, scopes=scope)
                            service = build('sheets', 'v4', credentials=creds)

                            # Prepare batch update request to set row heights
                            requests = []
                            for row_idx in range(1, len(data)):  # Skip header row (start from 1)
                                requests.append({
                                    'updateDimensionProperties': {
                                        'range': {
                                            'sheetId': 0,  # First sheet
                                            'dimension': 'ROWS',
                                            'startIndex': row_idx,
                                            'endIndex': row_idx + 1
                                        },
                                        'properties': {
                                            'pixelSize': 120  # Good height for thumbnails
                                        },
                                        'fields': 'pixelSize'
                                    }
                                })

                            # Execute batch update
                            if requests:
                                batch_update_request = {'requests': requests}
                                service.spreadsheets().batchUpdate(
                                    spreadsheetId=spreadsheet_id,
                                    body=batch_update_request
                                ).execute()

                                logging.info(f"Set row heights for {len(requests)} rows with images")

                    except Exception as e:
                        logging.info(f"Row height auto-resize not available: {e}. Use manual resize in Google Sheets.")

                logging.info(f"Data saved to Google Sheets: {len(results)} rows with image integration")

        except Exception as e:
            logging.error(f"Google Sheets save failed: {e}")


class GoogleDriveAPI:
    """Google Drive integration for image uploads"""

    def __init__(self, folder_id: str):
        self.folder_id = folder_id
        self.service = None
        self._initialize()

    def _initialize(self):
        """Initialize Google Drive client"""
        try:
            creds_files = ['credentials.json', 'service_account.json', 'google_credentials.json']
            creds_path = None

            for filename in creds_files:
                if os.path.exists(filename):
                    creds_path = filename
                    break

            if not creds_path:
                logging.warning("Google Drive credentials not found. Expected one of: credentials.json, service_account.json, google_credentials.json")
                return

            creds = Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )

            self.service = build('drive', 'v3', credentials=creds)

        except Exception as e:
            logging.warning(f"Google Drive initialization failed: {e}")

    def upload_image(self, image_path: Path) -> Optional[str]:
        """Upload image to Google Drive and return shareable URL"""
        if not self.service:
            return None

        try:
            file_metadata = {
                'name': image_path.name,
                'parents': [self.folder_id] if self.folder_id != "YOUR_DRIVE_FOLDER_ID" else []
            }

            media = MediaFileUpload(str(image_path), resumable=True)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            file_id = file.get('id')

            # Make file publicly viewable
            self.service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()

            return f"https://drive.google.com/file/d/{file_id}/view"

        except Exception as e:
            logging.warning(f"Drive upload failed: {e}")
            return None


def schedule_scraper(config_path: str, schedule_time: str, use_mimic: Optional[bool] = None):
    """Schedule scraper to run daily at specified time"""
    def run_scraper():
        scraper = MandarakeScraper(config_path, use_mimic=use_mimic)
        scraper.run()

    schedule.every().day.at(schedule_time).do(run_scraper)

    logging.info(f"Scraper scheduled to run daily at {schedule_time}")

    while True:
        schedule.run_pending()
        time.sleep(60)


def parse_mandarake_url(url: str) -> Dict:
    """Parse Mandarake search URL to extract parameters"""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Extract parameters and handle URL decoding
        config = {}

        # Keyword
        if 'keyword' in params:
            config['keyword'] = unquote(params['keyword'][0])

        # Category
        if 'categoryCode' in params:
            config['category'] = params['categoryCode'][0]

        # Shop
        if 'shop' in params:
            shop_value = params['shop'][0]
            # Handle special case: shop=0 means all stores (use the number directly)
            if shop_value == '0':
                config['shop'] = '0'  # Mandarake uses 0 for all stores
            else:
                # Map shop numbers to names for individual stores
                shop_mapping = {
                    '1': '1',  # Keep as numbers since Mandarake expects them
                    '2': '2',
                    '3': '3',
                    '4': '4',
                    '5': '5',
                    '6': '6',
                    '7': '7',
                    '8': '8',
                    '9': '9',
                    '10': '10'
                }
                config['shop'] = shop_mapping.get(shop_value, shop_value)

        if 'soldOut' in params:
            config['hide_sold_out'] = params['soldOut'][0] == '1'

        if 'upToMinutes' in params:
            try:
                minutes = int(params['upToMinutes'][0])
                config['recent_hours'] = max(1, minutes // 60)
            except (ValueError, TypeError):
                pass

        # Language
        if 'lang' in params:
            lang = params['lang'][0].lower()
            if lang in ('en', 'ja'):
                config['language'] = lang

        return config

    except Exception as e:
        raise ValueError(f"Invalid Mandarake URL: {e}")

def create_config_from_url(url: str, output_name: str = None) -> str:
    """Create a temporary config file from URL parameters"""
    url_config = parse_mandarake_url(url)

    # Generate output name based on keyword if not provided
    if not output_name:
        keyword = url_config.get('keyword', 'search')
        # Clean keyword for filename
        safe_keyword = re.sub(r'[^\w\-_\.]', '_', keyword)
        output_name = safe_keyword.lower()

    # Create complete config with defaults
    config = {
        'keyword': url_config.get('keyword', ''),
        'category': url_config.get('category', ''),
        'shop': url_config.get('shop', ''),
        'hide_sold_out': url_config.get('hide_sold_out', False),
        'client_id': 'YOUR_EBAY_CLIENT_ID_HERE',  # Use existing credentials
        'client_secret': 'YOUR_EBAY_CLIENT_SECRET_HERE',
        'google_sheets': {
            'sheet_name': f'Mandarake {output_name.title()} Results',
            'worksheet_name': 'Sheet1'
        },
        'csv': f'{output_name}_results.csv',
        'download_images': f'images/{output_name}/',
        'upload_drive': True,
        'drive_folder': '1xBVwaTFGdD5HkQtq8WOILSrc9mr0AQb0',  # Use existing folder
        'thumbnails': 400,
        'fast': False,  # Enable eBay comparison by default
        'resume': True
    }

    recent_hours = url_config.get('recent_hours')
    if recent_hours:
        config['recent_hours'] = recent_hours

    # Create temporary config file
    config_path = f'configs/temp_{output_name}.json'
    os.makedirs('configs', exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return config_path

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Mandarake Scraper')

    # Create mutually exclusive group for config vs URL
    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument('--config', help='Configuration file path')
    config_group.add_argument('--url', help='Mandarake search URL to scrape')

    parser.add_argument('--output', help='Output name (used with --url)')
    parser.add_argument('--schedule', help='Schedule time (HH:MM format) for daily runs')
    parser.add_argument('--interval', type=int, help='Run every N minutes')
    parser.add_argument('--mimic', action='store_true', help='Use browser mimic session for scraping')

    args = parser.parse_args()

    # Handle URL input
    if args.url:
        try:
            print(f"Parsing URL: {args.url}")
            url_config = parse_mandarake_url(args.url)
            print(f"Extracted parameters: {url_config}")

            config_path = create_config_from_url(args.url, args.output)
            print(f"Created temporary config: {config_path}")
            args.config = config_path

        except Exception as e:
            print(f"Error parsing URL: {e}")
            print("Example URL format: https://order.mandarake.co.jp/order/listPage/list?shop=1&categoryCode=050801&keyword=search_term")
            sys.exit(1)

    try:
        if args.schedule:
            schedule_scraper(args.config, args.schedule, use_mimic=args.mimic)
        elif args.interval:
            while True:
                scraper = MandarakeScraper(args.config, use_mimic=args.mimic)
                scraper.run()
                logging.info(f"Waiting {args.interval} minutes until next run...")
                time.sleep(args.interval * 60)
        else:
            scraper = MandarakeScraper(args.config, use_mimic=args.mimic)
            scraper.run()
    finally:
        # Clean up temporary config file if created from URL
        if args.url and args.config and args.config.startswith('configs/temp_'):
            try:
                os.remove(args.config)
                print(f"Cleaned up temporary config: {args.config}")
            except Exception:
                pass  # Ignore cleanup errors


if __name__ == '__main__':
    main()








