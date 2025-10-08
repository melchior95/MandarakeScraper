"""
Mandarake Cart API

Handles cart operations including:
- Session management (cookie-based authentication)
- Adding items to cart
- Fetching cart contents
- Removing items from cart
- Cart state analysis (per-shop breakdown)
"""

import logging
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


class MandarakeCartAPI:
    """API wrapper for Mandarake cart operations"""

    def __init__(self, session_id: str = None, session_cookies: dict = None):
        """
        Initialize cart API

        Args:
            session_id: JSESSIONID from Mandarake cart URL
            session_cookies: Full cookie dict (alternative to session_id)
        """
        self.base_url = "https://order.mandarake.co.jp"
        self.cart_url = "https://cart.mandarake.co.jp"
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # Set up session
        if session_id:
            self.session.cookies.set('JSESSIONID', session_id, domain='.mandarake.co.jp')
        elif session_cookies:
            self.session.cookies.update(session_cookies)

        # Browser headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def extract_session_from_url(self, cart_url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract session information from cart URL

        Supports multiple formats:
        - jsessionid in path: ;jsessionid=ABC123
        - jsessionid as query param: ?jsessionid=ABC123
        - te-uniquekey as query param: ?te-uniquekey=ABC123

        Args:
            cart_url: Full cart URL with session info

        Returns:
            Tuple of (session_id, unique_key)
        """
        session_id = None
        unique_key = None

        # Try jsessionid in path (old format)
        # Example: https://cart.mandarake.co.jp/cart/view/order/inputOrderEn.html;jsessionid=ABC123
        match = re.search(r';jsessionid=([A-Fa-f0-9]+)', cart_url)
        if match:
            session_id = match.group(1)

        # Try jsessionid as query parameter
        # Example: ?jsessionid=ABC123
        if not session_id:
            match = re.search(r'[?&]jsessionid=([A-Fa-f0-9]+)', cart_url)
            if match:
                session_id = match.group(1)

        # Try te-uniquekey (new format)
        # Example: ?te-uniquekey=199c1ff6120
        match = re.search(r'[?&]te-uniquekey=([A-Fa-f0-9]+)', cart_url)
        if match:
            unique_key = match.group(1)

        return session_id, unique_key

    def verify_session(self) -> bool:
        """
        Verify session is valid by attempting to access cart

        Returns:
            bool: True if session is valid
        """
        try:
            response = self.session.get(f"{self.cart_url}/cart/view/order/inputOrderEn.html")
            # If redirected to login, session is invalid
            if 'login' in response.url.lower():
                self.logger.warning("Session invalid - redirected to login")
                return False
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Session verification failed: {e}")
            return False

    def get_cart(self) -> Dict[str, List[Dict]]:
        """
        Fetch current cart contents from Mandarake

        Returns:
            dict: Cart data grouped by shop
            {
                'Nakano': [
                    {
                        'product_id': '1126279062',
                        'title': 'Product Title',
                        'price_jpy': 3000,
                        'image_url': 'https://...',
                        'product_url': 'https://...',
                        'view_id': 'winkid-00IMK2HI',
                        'status': 'Store Front Item',
                        'quantity': 1,
                        'cart_item_id': '...'
                    }
                ],
                'SAHRA': [...]
            }
        """
        try:
            url = f"{self.cart_url}/cart/view/order/inputOrderEn.html"
            response = self.session.get(url)

            if response.status_code != 200:
                self.logger.error(f"Failed to fetch cart: {response.status_code}")
                return {}

            soup = BeautifulSoup(response.content, 'html.parser')

            cart_by_shop = {}

            # Find all shop sections (div.section)
            shop_sections = soup.find_all('div', class_='section')

            for section in shop_sections:
                # Get shop name from h3 > span
                shop_name = self._extract_shop_name(section)
                if not shop_name:
                    continue

                # Get all items in this shop (div.block)
                items = []
                item_blocks = section.find_all('div', class_='block')

                for block in item_blocks:
                    item = self._parse_cart_item(block)
                    if item:
                        item['shop_name'] = shop_name
                        items.append(item)

                if items:
                    cart_by_shop[shop_name] = items

            self.logger.info(f"Fetched cart: {len(cart_by_shop)} shops, {sum(len(items) for items in cart_by_shop.values())} items")
            return cart_by_shop

        except Exception as e:
            self.logger.error(f"Error fetching cart: {e}")
            return {}

    def _extract_shop_name(self, shop_section) -> Optional[str]:
        """Extract shop name from section"""
        try:
            h3 = shop_section.find('h3')
            if h3:
                shop_span = h3.find('span', id=re.compile('shopName'))
                if shop_span:
                    return shop_span.text.strip()
        except Exception as e:
            self.logger.error(f"Error extracting shop name: {e}")
        return None

    def _parse_cart_item(self, item_block) -> Optional[Dict]:
        """Parse individual cart item from HTML"""
        try:
            item_data = {}

            # Title (h4 > span with id="name-x1")
            title_elem = item_block.find('h4')
            if title_elem:
                title_span = title_elem.find('span', id=re.compile('name'))
                if title_span:
                    item_data['title'] = title_span.text.strip()

            # Price (span with id="price-x")
            price_elem = item_block.find('span', id=re.compile('price'))
            if price_elem:
                price_text = price_elem.text.strip().replace(',', '')
                try:
                    item_data['price_jpy'] = int(price_text)
                except ValueError:
                    item_data['price_jpy'] = 0

            # Image (div.pic > a > img)
            pic_div = item_block.find('div', class_='pic')
            if pic_div:
                img = pic_div.find('img')
                if img:
                    item_data['image_url'] = img.get('src', '')

            # Product URL (a with id="inCartDetailUrl")
            detail_link = item_block.find('a', id=re.compile('inCartDetailUrl'))
            if detail_link:
                item_data['product_url'] = detail_link.get('href', '')
                # Extract product ID from URL
                match = re.search(r'itemCode=(\d+)', item_data['product_url'])
                if match:
                    item_data['product_id'] = match.group(1)

            # Cart item ID (hidden input id="id-x")
            id_input = item_block.find_next_sibling('input', id=re.compile('id-x'))
            if id_input:
                item_data['cart_item_id'] = id_input.get('value', '')

            # Parse table for additional details
            table = item_block.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        header = th.get_text(strip=True)

                        if 'Status' in header:
                            item_data['status'] = td.get_text(strip=True)

                        elif 'Item ID' in header:
                            view_id_span = td.find('span', id=re.compile('viewId'))
                            if view_id_span:
                                item_data['view_id'] = view_id_span.text.strip()

                        elif 'Quantity' in header:
                            # Try to find input first
                            qty_input = td.find('input', id=re.compile('itemCount'))
                            if qty_input:
                                try:
                                    item_data['quantity'] = int(qty_input.get('value', 1))
                                except:
                                    item_data['quantity'] = 1
                            else:
                                # Sold out items have text only
                                try:
                                    qty_text = td.get_text(strip=True)
                                    item_data['quantity'] = int(qty_text)
                                except:
                                    item_data['quantity'] = 1

            return item_data if item_data.get('title') else None

        except Exception as e:
            self.logger.error(f"Error parsing cart item: {e}")
            return None

    def add_to_cart(self, product_id: str, shop_code: str = None, quantity: int = 1,
                   referer: str = None) -> bool:
        """
        Add item to cart

        Args:
            product_id: Mandarake product ID (itemCode from product page)
            shop_code: Optional shop code (not used in actual API)
            quantity: Quantity to add (default: 1)
            referer: Referer URL (defaults to search page)

        Returns:
            bool: True if added successfully
        """
        try:
            # Real add-to-cart endpoint
            url = "https://tools.mandarake.co.jp/basket/add/"

            # Default referer if not provided
            if not referer:
                referer = "https://order.mandarake.co.jp/order/listPage/list?keyword=&lang=en"

            # Payload from captured request
            data = {
                'request[id]': product_id,
                'request[count]': str(quantity),
                'request[shopType]': 'webshop',
                'request[langage]': 'en',
                'request[countryId]': 'EN',
                'request[location]': referer.replace('https://order.mandarake.co.jp', ''),
                'request[referer]': referer
            }

            # Headers for add-to-cart request
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'https://order.mandarake.co.jp',
                'Referer': referer,
                'Accept': 'text/html, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest'  # Important: indicates AJAX request
            }

            response = self.session.post(url, data=data, headers=headers)

            if response.status_code == 200:
                self.logger.info(f"Added item {product_id} to cart (qty: {quantity})")
                return True
            else:
                self.logger.error(f"Failed to add {product_id}: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Error adding to cart: {e}")
            return False

    def remove_from_cart(self, cart_item_id: str) -> bool:
        """
        Remove item from cart

        Args:
            cart_item_id: Cart item ID (from get_cart)

        Returns:
            bool: True if removed successfully
        """
        try:
            url = f"{self.cart_url}/cart/view/order/deleteItem"
            data = {'itemId': cart_item_id}

            response = self.session.post(url, data=data)

            if response.status_code == 200:
                self.logger.info(f"Removed item {cart_item_id} from cart")
                return True
            else:
                self.logger.error(f"Failed to remove {cart_item_id}: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Error removing from cart: {e}")
            return False

    def get_cart_summary(self) -> Dict:
        """
        Get summary statistics for current cart

        Returns:
            dict: {
                'total_items': int,
                'total_value_jpy': int,
                'shop_count': int,
                'by_shop': {
                    'shop_code': {
                        'items': int,
                        'total_jpy': int
                    }
                }
            }
        """
        cart = self.get_cart()

        by_shop = {}
        total_items = 0
        total_value = 0

        for shop_code, items in cart.items():
            shop_total = sum(item['price_jpy'] * item.get('quantity', 1) for item in items)
            by_shop[shop_code] = {
                'items': len(items),
                'total_jpy': shop_total
            }
            total_items += len(items)
            total_value += shop_total

        return {
            'total_items': total_items,
            'total_value_jpy': total_value,
            'shop_count': len(cart),
            'by_shop': by_shop
        }

    def open_cart_in_browser(self):
        """Open cart page in default browser"""
        import webbrowser
        cart_url = f"{self.cart_url}/cart/view/order/inputOrderEn.html"
        webbrowser.open(cart_url)
        self.logger.info(f"Opened cart in browser: {cart_url}")


class MandarakeCartSession:
    """
    Helper class to manage Mandarake cart sessions with cookie persistence
    """

    def __init__(self, session_file: str = 'mandarake_session.json'):
        """
        Initialize session manager

        Args:
            session_file: Path to save/load session cookies
        """
        self.session_file = session_file
        self.cart_api = None
        self.logger = logging.getLogger(__name__)

    def login_with_url(self, cart_url: str) -> MandarakeCartAPI:
        """
        Create cart API from cart URL (extracts session and establishes connection)

        Args:
            cart_url: Full cart URL with session info (jsessionid or te-uniquekey)

        Returns:
            MandarakeCartAPI instance
        """
        api = MandarakeCartAPI()
        session_id, unique_key = api.extract_session_from_url(cart_url)

        # If we have a jsessionid, use it directly
        if session_id:
            self.cart_api = MandarakeCartAPI(session_id=session_id)
            if self.cart_api.verify_session():
                self.save_session()
                return self.cart_api

        # If we have a te-uniquekey, visit the URL to get session cookies
        if unique_key:
            try:
                # Create a session and visit the URL
                temp_api = MandarakeCartAPI()
                response = temp_api.session.get(cart_url, allow_redirects=True)

                # Check if we got cookies from the response
                if response.cookies:
                    cookies = dict(response.cookies)
                    self.cart_api = MandarakeCartAPI(session_cookies=cookies)

                    if self.cart_api.verify_session():
                        self.save_session()
                        return self.cart_api

                self.logger.error(f"No session cookies received from URL")
            except Exception as e:
                self.logger.error(f"Failed to connect with URL: {e}")
                raise ValueError(f"Failed to establish session: {e}")

        raise ValueError("Invalid cart URL - no session info found (need jsessionid or te-uniquekey)")

    def login_with_cookies(self, cookies: dict) -> MandarakeCartAPI:
        """
        Create cart API from cookie dict

        Args:
            cookies: Cookie dictionary

        Returns:
            MandarakeCartAPI instance
        """
        self.cart_api = MandarakeCartAPI(session_cookies=cookies)

        if self.cart_api.verify_session():
            self.save_session()
            return self.cart_api

        raise ValueError("Invalid session cookies")

    def save_session(self):
        """Save current session to file"""
        if self.cart_api:
            import json
            cookies = dict(self.cart_api.session.cookies)
            with open(self.session_file, 'w') as f:
                json.dump(cookies, f)

    def load_session(self) -> Optional[MandarakeCartAPI]:
        """
        Load saved session from file

        Tries multiple filenames:
        - mandarake_cookies.json (browser export)
        - mandarake_session.json (saved session)
        - self.session_file (custom filename)

        Supports two formats:
        - Dict format: {"cookie_name": "value", ...}
        - Browser extension format: [{"name": "cookie_name", "value": "...", "domain": "...", ...}, ...]

        Returns:
            MandarakeCartAPI instance if session valid, None otherwise
        """
        import json
        from pathlib import Path

        # Try multiple filenames in order
        filenames_to_try = [
            'mandarake_cookies.json',  # Browser export
            self.session_file,          # Default or custom
        ]

        for filename in filenames_to_try:
            if not Path(filename).exists():
                continue

            try:
                with open(filename, 'r') as f:
                    cookies_data = json.load(f)

                # Convert browser extension format (array) to dict format
                if isinstance(cookies_data, list):
                    cookies = {}
                    for cookie in cookies_data:
                        cookies[cookie['name']] = cookie['value']
                else:
                    cookies = cookies_data

                self.cart_api = MandarakeCartAPI(session_cookies=cookies)

                if self.cart_api.verify_session():
                    self.logger.info(f"Loaded session from {filename}")
                    return self.cart_api
                else:
                    self.logger.warning(f"Session from {filename} is invalid")

            except Exception as e:
                self.logger.error(f"Error loading session from {filename}: {e}")
                continue

        return None
