#!/usr/bin/env python3
"""
Browser Mimic - Advanced browser simulation for web scraping
Inspired by mdrscr's requestAsBrowser functionality
"""

import json
import logging
import os
import random
import time
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BrowserMimic:
    """Advanced browser simulation for web scraping"""

    # Realistic browser fingerprints
    BROWSER_PROFILES = [
        {
            'name': 'Chrome_Windows',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept_language': 'en-US,en;q=0.9,ja;q=0.8',
            'accept_encoding': 'gzip, deflate, br',
            'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec_ch_ua_mobile': '?0',
            'sec_ch_ua_platform': '"Windows"',
            'sec_fetch_dest': 'document',
            'sec_fetch_mode': 'navigate',
            'sec_fetch_site': 'none',
            'sec_fetch_user': '?1',
            'upgrade_insecure_requests': '1'
        },
        {
            'name': 'Firefox_Windows',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'accept_language': 'en-US,en;q=0.5',
            'accept_encoding': 'gzip, deflate, br',
            'upgrade_insecure_requests': '1'
        },
        {
            'name': 'Edge_Windows',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept_language': 'en-US,en;q=0.9',
            'accept_encoding': 'gzip, deflate, br',
            'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
            'sec_ch_ua_mobile': '?0',
            'sec_ch_ua_platform': '"Windows"',
            'upgrade_insecure_requests': '1'
        }
    ]

    def __init__(self, session_file: str = 'browser_session.pkl'):
        """Initialize browser mimic with session persistence"""
        self.session_file = session_file
        self.session = requests.Session()
        self.current_profile = random.choice(self.BROWSER_PROFILES)
        self.request_history = []
        self.last_request_time = None

        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Load or create session
        self._load_session()
        self._setup_browser_headers()
        self._setup_cookies()

    def _setup_browser_headers(self):
        """Setup realistic browser headers"""
        profile = self.current_profile

        headers = {
            'User-Agent': profile['user_agent'],
            'Accept': profile['accept'],
            'Accept-Language': profile['accept_language'],
            'Accept-Encoding': profile['accept_encoding'],
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }

        # Add Chrome/Edge specific headers
        if 'Chrome' in profile['name'] or 'Edge' in profile['name']:
            headers.update({
                'sec-ch-ua': profile.get('sec_ch_ua', ''),
                'sec-ch-ua-mobile': profile.get('sec_ch_ua_mobile', '?0'),
                'sec-ch-ua-platform': profile.get('sec_ch_ua_platform', ''),
                'Sec-Fetch-Dest': profile.get('sec_fetch_dest', 'document'),
                'Sec-Fetch-Mode': profile.get('sec_fetch_mode', 'navigate'),
                'Sec-Fetch-Site': profile.get('sec_fetch_site', 'none'),
                'Sec-Fetch-User': profile.get('sec_fetch_user', '?1'),
                'Upgrade-Insecure-Requests': profile.get('upgrade_insecure_requests', '1')
            })

        # Add Firefox specific headers
        elif 'Firefox' in profile['name']:
            headers.update({
                'Upgrade-Insecure-Requests': profile.get('upgrade_insecure_requests', '1')
            })

        self.session.headers.update(headers)
        logging.info(f"Using browser profile: {profile['name']}")

    def _setup_cookies(self):
        """Setup essential cookies for Mandarake"""
        # Essential Mandarake cookie from mdrscr documentation
        self.session.cookies.set(
            'tr_mndrk_user',
            f'browser_mimic_{random.randint(100000, 999999)}',
            domain='.mandarake.co.jp',
            path='/'
        )

        # Additional realistic cookies
        self.session.cookies.set(
            'session_start',
            str(int(time.time())),
            domain='.mandarake.co.jp',
            path='/'
        )

        # Language preference
        self.session.cookies.set(
            'lang',
            'ja',
            domain='.mandarake.co.jp',
            path='/'
        )

    def _save_session(self):
        """Save session state to file"""
        try:
            # Save cookies with their full attributes to handle duplicates
            cookie_list = []
            for cookie in self.session.cookies:
                try:
                    cookie_data = {
                        'name': getattr(cookie, 'name', ''),
                        'value': getattr(cookie, 'value', ''),
                        'domain': getattr(cookie, 'domain', None),
                        'path': getattr(cookie, 'path', '/'),
                        'secure': getattr(cookie, 'secure', False),
                        'expires': getattr(cookie, 'expires', None),
                        'discard': getattr(cookie, 'discard', False),
                        'comment': getattr(cookie, 'comment', None),
                        'comment_url': getattr(cookie, 'comment_url', None),
                        'rest': getattr(cookie, 'rest', {}),
                        'version': getattr(cookie, 'version', 0)
                    }
                    cookie_list.append(cookie_data)
                except Exception as cookie_error:
                    logging.debug(f"Failed to save cookie {getattr(cookie, 'name', 'unknown')}: {cookie_error}")
                    continue

            session_data = {
                'cookies': cookie_list,
                'profile': self.current_profile,
                'request_history': self.request_history[-50:],  # Keep last 50 requests
                'last_save': datetime.now().isoformat()
            }

            with open(self.session_file, 'wb') as f:
                pickle.dump(session_data, f)

        except Exception as e:
            logging.warning(f"Failed to save session: {e}")

    def _load_session(self):
        """Load session state from file"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'rb') as f:
                    session_data = pickle.load(f)

                # Restore cookies with proper handling for new and old formats
                cookies_data = session_data.get('cookies', [])

                if isinstance(cookies_data, dict):
                    # Old format - simple dict (for backward compatibility)
                    for name, value in cookies_data.items():
                        self.session.cookies[name] = value
                elif isinstance(cookies_data, list):
                    # New format - list of cookie dictionaries with full attributes
                    for cookie_data in cookies_data:
                        try:
                            self.session.cookies.set(
                                name=cookie_data.get('name', ''),
                                value=cookie_data.get('value', ''),
                                domain=cookie_data.get('domain'),
                                path=cookie_data.get('path', '/'),
                                secure=cookie_data.get('secure', False),
                                expires=cookie_data.get('expires'),
                                discard=cookie_data.get('discard', False),
                                comment=cookie_data.get('comment'),
                                comment_url=cookie_data.get('comment_url'),
                                rest=cookie_data.get('rest', {}),
                                version=cookie_data.get('version', 0)
                            )
                        except Exception as cookie_error:
                            logging.debug(f"Failed to restore cookie {cookie_data.get('name', 'unknown')}: {cookie_error}")
                            continue

                # Restore profile if not too old
                last_save = datetime.fromisoformat(session_data.get('last_save', '2020-01-01'))
                if datetime.now() - last_save < timedelta(hours=24):
                    stored_profile = session_data.get('profile')
                    if stored_profile:
                        self.current_profile = stored_profile

                # Restore request history
                self.request_history = session_data.get('request_history', [])

                logging.info("Session loaded successfully")

        except Exception as e:
            logging.warning(f"Failed to load session: {e}")

    def _human_delay(self, base_delay: float = 2.0, url: str = ""):
        """Add human-like delay between requests with eBay-specific longer delays"""

        # Use longer delays for eBay to reduce blocking
        if "ebay.com" in url.lower():
            base_delay = max(base_delay, 4.0)  # Minimum 4 seconds for eBay
            logging.debug(f"[DELAY] Using eBay-specific delay: {base_delay}s base")

        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            min_delay = base_delay + random.uniform(-0.5, 1.5)  # More randomness for eBay

            if elapsed < min_delay:
                sleep_time = min_delay - elapsed
                # Add some randomness to make it more human-like
                sleep_time += random.uniform(0, sleep_time * 0.4)  # More variation

                if "ebay.com" in url.lower():
                    logging.info(f"[ANTI-BLOCKING] Waiting {sleep_time:.2f}s before eBay request")

                time.sleep(sleep_time)

        self.last_request_time = time.time()

    def add_ebay_search_delay(self):
        """Add extra delay specifically for eBay search requests to reduce blocking"""
        extra_delay = random.uniform(3.0, 6.0)  # 3-6 second additional delay
        logging.info(f"[EBAY ANTI-BLOCKING] Adding extra {extra_delay:.2f}s delay before eBay search")
        time.sleep(extra_delay)

    def _simulate_page_load_behavior(self, url: str):
        """Simulate realistic page load behavior"""
        # Update referrer if we have previous requests
        if self.request_history:
            last_url = self.request_history[-1].get('url')
            if last_url:
                # Ensure Referer header is ASCII-safe for HTTP headers
                try:
                    # Test if URL is ASCII-encodable
                    last_url.encode('ascii')
                    self.session.headers['Referer'] = last_url
                except UnicodeEncodeError:
                    # If URL contains non-ASCII characters, don't set Referer
                    # or use the base domain only
                    from urllib.parse import urlparse as parse_url
                    parsed = parse_url(last_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    self.session.headers['Referer'] = base_url
                    print(f"[BROWSER DEBUG] Referer contains Unicode, using base URL: {base_url}")

        # Simulate browser navigation patterns
        from urllib.parse import urlparse
        parsed_url = urlparse(url)

        # Update Sec-Fetch headers based on navigation type
        if 'Chrome' in self.current_profile['name'] or 'Edge' in self.current_profile['name']:
            if len(self.request_history) == 0:
                # First request - direct navigation
                self.session.headers['Sec-Fetch-Site'] = 'none'
                self.session.headers['Sec-Fetch-Mode'] = 'navigate'
            else:
                # Subsequent request - same-origin
                self.session.headers['Sec-Fetch-Site'] = 'same-origin'
                self.session.headers['Sec-Fetch-Mode'] = 'navigate'

    def _update_request_history(self, url: str, response):
        """Track request history for behavioral patterns"""
        self.request_history.append({
            'url': url,
            'timestamp': time.time(),
            'status_code': response.status_code,
            'response_time': response.elapsed.total_seconds()
        })

        # Keep only last 100 requests
        if len(self.request_history) > 100:
            self.request_history = self.request_history[-100:]

    def _ensure_ascii_headers(self):
        """Ensure all headers are ASCII-safe"""
        headers_to_remove = []
        for header_name, header_value in self.session.headers.items():
            try:
                header_value.encode('ascii')
            except (UnicodeEncodeError, AttributeError):
                print(f"[BROWSER DEBUG] Removing non-ASCII header: {header_name}={header_value}")
                headers_to_remove.append(header_name)

        for header_name in headers_to_remove:
            del self.session.headers[header_name]

    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request with browser simulation"""
        print(f"[BROWSER DEBUG] Original URL: {url}")
        print(f"[BROWSER DEBUG] URL type: {type(url)}")
        print(f"[BROWSER DEBUG] URL length: {len(url)}")

        # Ensure URL is properly encoded for Japanese characters
        from urllib.parse import quote, unquote, urlparse, urlunparse

        # Parse the URL to handle encoding properly
        parsed = urlparse(url)
        if parsed.query:
            print(f"[BROWSER DEBUG] Original query: {parsed.query}")
            # Re-encode the query parameters to ensure proper UTF-8 encoding
            query_parts = []
            for param in parsed.query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    print(f"[BROWSER DEBUG] Processing param: {key}={value}")
                    # Handle encoding properly - preserve + signs for spaces in query params
                    try:
                        # Check if this looks like a search query with + signs for spaces
                        if key in ['_nkw', 'q'] and '+' in value and '%' not in value:
                            # This is likely a search query with + for spaces, keep it as-is
                            query_parts.append(f"{key}={value}")
                            print(f"[BROWSER DEBUG] Preserved query param: {key}={value}")
                        else:
                            # Regular encoding for other parameters
                            decoded_value = unquote(value)
                            encoded_value = quote(decoded_value, safe='')
                            query_parts.append(f"{key}={encoded_value}")
                            print(f"[BROWSER DEBUG] Encoded param: {key}={encoded_value}")
                    except Exception as e:
                        print(f"[BROWSER DEBUG] Encoding failed for {key}={value}: {e}")
                        query_parts.append(param)
                else:
                    query_parts.append(param)

            # Rebuild URL with properly encoded query
            new_query = '&'.join(query_parts)
            new_parsed = parsed._replace(query=new_query)
            url = urlunparse(new_parsed)
            print(f"[BROWSER DEBUG] Final URL: {url}")

        # Human-like delay with eBay-specific handling
        self._human_delay(url=url)

        # Simulate page load behavior
        self._simulate_page_load_behavior(url)

        # Ensure all headers are ASCII-safe before making request
        self._ensure_ascii_headers()

        # Set timeout if not provided
        kwargs.setdefault('timeout', 30)

        try:
            response = self.session.get(url, **kwargs)

            # Update request history
            self._update_request_history(url, response)

            # Save session periodically
            if len(self.request_history) % 10 == 0:
                self._save_session()

            # Check for potential blocking
            self._check_for_blocking(response)

            return response

        except Exception as e:
            logging.error(f"Request failed: {e}")
            raise

    def _check_for_blocking(self, response: requests.Response):
        """Check if we're being blocked and adapt"""
        indicators = [
            'captcha', 'blocked', 'access denied', 'robot',
            'too many requests', 'rate limit', 'forbidden'
        ]

        content_lower = response.text.lower()

        if (response.status_code in [403, 429] or
            any(indicator in content_lower for indicator in indicators)):

            logging.warning("Potential blocking detected - adapting behavior")

            # Switch browser profile
            self.current_profile = random.choice(self.BROWSER_PROFILES)
            self._setup_browser_headers()

            # Clear some cookies (but keep essential ones)
            essential_cookies = {'tr_mndrk_user', 'session_start', 'lang'}
            cookies_to_remove = []

            for cookie_name in self.session.cookies.keys():
                if cookie_name not in essential_cookies:
                    cookies_to_remove.append(cookie_name)

            for cookie_name in cookies_to_remove:
                del self.session.cookies[cookie_name]

            # Longer delay before next request
            time.sleep(random.uniform(10, 20))

    def close(self):
        """Clean up and save session"""
        self._save_session()
        self.session.close()

    def get_session_info(self) -> Dict:
        """Get current session information"""
        return {
            'profile': self.current_profile['name'],
            'cookies_count': len(self.session.cookies),
            'requests_made': len(self.request_history),
            'last_request': self.request_history[-1] if self.request_history else None
        }

    def clear_duplicate_cookies(self):
        """Remove duplicate cookies that might cause issues"""
        try:
            # Track seen cookies by name+domain+path
            seen_cookies = set()
            cookies_to_remove = []

            for cookie in self.session.cookies:
                cookie_key = f"{cookie.name}|{cookie.domain}|{cookie.path}"
                if cookie_key in seen_cookies:
                    cookies_to_remove.append(cookie)
                    logging.debug(f"Found duplicate cookie: {cookie.name} for {cookie.domain}")
                else:
                    seen_cookies.add(cookie_key)

            # Remove duplicates
            for cookie in cookies_to_remove:
                try:
                    self.session.cookies.clear(domain=cookie.domain, path=cookie.path, name=cookie.name)
                except Exception as e:
                    logging.debug(f"Failed to remove duplicate cookie {cookie.name}: {e}")

            if cookies_to_remove:
                logging.info(f"Removed {len(cookies_to_remove)} duplicate cookies")
                self._save_session()  # Save cleaned session

        except Exception as e:
            logging.warning(f"Failed to clean duplicate cookies: {e}")


class EnhancedMandarakeScraper:
    """Enhanced scraper using browser mimicking"""

    def __init__(self, config_path: str):
        """Initialize with browser mimic"""
        self.config = self._load_config(config_path)
        self.browser = BrowserMimic(f"session_{Path(config_path).stem}.pkl")

        # Setup logging
        self._setup_logging()

        logging.info(f"Browser initialized: {self.browser.get_session_info()}")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in configuration file: {e}")
            raise

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

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch page using browser mimicking"""
        try:
            response = self.browser.get(url)
            response.raise_for_status()
            return response.text

        except Exception as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    def test_connection(self, url: str = "https://order.mandarake.co.jp") -> bool:
        """Test connection to Mandarake"""
        try:
            response = self.browser.get(url)
            success = response.status_code == 200 and 'mandarake' in response.text.lower()

            if success:
                logging.info("✅ Successfully connected to Mandarake")
            else:
                logging.warning(f"⚠️ Connection issues: Status {response.status_code}")

            return success

        except Exception as e:
            logging.error(f"❌ Connection test failed: {e}")
            return False

    def close(self):
        """Clean up resources"""
        self.browser.close()


def main():
    """Test the browser mimic functionality"""
    print("Testing Browser Mimic System...")

    # Test basic functionality
    browser = BrowserMimic('test_session.pkl')

    print(f"Browser Profile: {browser.current_profile['name']}")
    print(f"Session Info: {browser.get_session_info()}")

    # Test Mandarake connection
    try:
        response = browser.get("https://order.mandarake.co.jp")
        print(f"Mandarake Response: {response.status_code}")
        print(f"Content Length: {len(response.text)}")

        if response.status_code == 200:
            print("✅ Successfully bypassed initial blocking!")
        else:
            print("⚠️ May be blocked or rate limited")

    except Exception as e:
        print(f"❌ Test failed: {e}")

    finally:
        browser.close()


if __name__ == '__main__':
    main()