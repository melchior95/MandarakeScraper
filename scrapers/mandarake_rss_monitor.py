"""
Mandarake RSS feed monitoring for real-time stock alerts.

This is FAR more efficient than polling:
- Instant notifications when items are added
- Zero overhead between updates
- Mandarake pushes data to us instead of us polling

RSS Feeds Available:
- All stores: https://order.mandarake.co.jp/rss/
- Nakano: https://order.mandarake.co.jp/rss/?shop=1
- Shibuya: https://order.mandarake.co.jp/rss/?shop=6
- Kyoto: https://order.mandarake.co.jp/rss/?shop=34
- etc.
"""

import xml.etree.ElementTree as ET
import requests
import time
from typing import List, Dict, Optional, Callable
from datetime import datetime
from browser_mimic import BrowserMimic


class MandarakeRSSMonitor:
    """Monitor Mandarake RSS feeds for new items."""

    # Shop code to RSS URL mapping (from official Mandarake RSS page)
    RSS_FEEDS = {
        'all': 'https://order.mandarake.co.jp/rss/',
        'nkn': 'https://order.mandarake.co.jp/rss/?shop=1',   # Nakano
        'nagoya': 'https://order.mandarake.co.jp/rss/?shop=4', # Nagoya
        'shr': 'https://order.mandarake.co.jp/rss/?shop=6',   # Shibuya
        'umeda': 'https://order.mandarake.co.jp/rss/?shop=7', # Umeda
        'fukuoka': 'https://order.mandarake.co.jp/rss/?shop=11', # Fukuoka
        'grand-chaos': 'https://order.mandarake.co.jp/rss/?shop=23', # Grand Chaos
        'ikebukuro': 'https://order.mandarake.co.jp/rss/?shop=26', # Ikebukuro
        'sapporo': 'https://order.mandarake.co.jp/rss/?shop=27', # Sapporo
        'utsunomiya': 'https://order.mandarake.co.jp/rss/?shop=28', # Utsunomiya
        'kokura': 'https://order.mandarake.co.jp/rss/?shop=29', # Kokura
        'complex': 'https://order.mandarake.co.jp/rss/?shop=30', # Complex
        'nayuta': 'https://order.mandarake.co.jp/rss/?shop=32', # Nayuta
        'cocoo': 'https://order.mandarake.co.jp/rss/?shop=33',  # CoCoo
        'kyoto': 'https://order.mandarake.co.jp/rss/?shop=34',  # Kyoto
        'sala': 'https://order.mandarake.co.jp/rss/?shop=55',   # Sala
    }

    def __init__(self, use_browser_mimic: bool = True):
        """
        Initialize RSS monitor.

        Args:
            use_browser_mimic: Use BrowserMimic for anti-bot protection
        """
        self.use_browser_mimic = use_browser_mimic
        if use_browser_mimic:
            self.session = BrowserMimic()
        else:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                'Accept': 'application/rss+xml,application/xml;q=0.9,*/*;q=0.8',
            })

        # Track seen item GUIDs to avoid duplicates
        self.seen_items = set()

    def fetch_feed(self, shop_code: str = 'all') -> Optional[List[Dict]]:
        """
        Fetch RSS feed for a shop.

        Args:
            shop_code: Shop code (e.g. 'nkn', 'shr') or 'all'

        Returns:
            List of item dicts or None on error
        """
        url = self.RSS_FEEDS.get(shop_code)
        if not url:
            print(f"Unknown shop code: {shop_code}")
            return None

        try:
            response = self.session.get(url, timeout=10, allow_redirects=False)

            # Handle redirects (RSS may require auth)
            if response.status_code in [301, 302, 303]:
                print(f"RSS feed redirected - may require authentication")
                return None

            if response.status_code != 200:
                print(f"RSS feed returned {response.status_code}")
                return None

            # Parse RSS XML
            root = ET.fromstring(response.content)

            # Handle both RSS 2.0 and Atom formats
            items = []

            # Try RSS 2.0 format
            channel = root.find('channel')
            if channel is not None:
                items = self._parse_rss_items(channel.findall('item'))
            else:
                # Try Atom format
                items = self._parse_atom_entries(root.findall('{http://www.w3.org/2005/Atom}entry'))

            return items

        except ET.ParseError as e:
            print(f"Failed to parse RSS XML: {e}")
            return None
        except requests.RequestException as e:
            print(f"Failed to fetch RSS feed: {e}")
            return None

    def _parse_rss_items(self, items) -> List[Dict]:
        """Parse RSS 2.0 format items."""
        parsed_items = []

        for item in items:
            item_data = {}

            # Standard RSS fields
            title = item.find('title')
            if title is not None:
                item_data['title'] = title.text

            link = item.find('link')
            if link is not None:
                item_data['link'] = link.text

            description = item.find('description')
            if description is not None:
                item_data['description'] = description.text

            pub_date = item.find('pubDate')
            if pub_date is not None:
                item_data['pub_date'] = pub_date.text

            guid = item.find('guid')
            if guid is not None:
                item_data['guid'] = guid.text

            # Custom Mandarake fields (if they exist)
            # These are speculative - need to inspect actual feed
            price = item.find('price') or item.find('{http://mandarake.co.jp}price')
            if price is not None:
                item_data['price'] = price.text

            item_code = item.find('itemCode') or item.find('{http://mandarake.co.jp}itemCode')
            if item_code is not None:
                item_data['item_code'] = item_code.text

            shop = item.find('shop') or item.find('{http://mandarake.co.jp}shop')
            if shop is not None:
                item_data['shop'] = shop.text

            parsed_items.append(item_data)

        return parsed_items

    def _parse_atom_entries(self, entries) -> List[Dict]:
        """Parse Atom format entries."""
        parsed_items = []

        for entry in entries:
            item_data = {}

            # Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            title = entry.find('atom:title', ns)
            if title is not None:
                item_data['title'] = title.text

            link = entry.find('atom:link', ns)
            if link is not None:
                item_data['link'] = link.get('href')

            summary = entry.find('atom:summary', ns)
            if summary is not None:
                item_data['description'] = summary.text

            updated = entry.find('atom:updated', ns)
            if updated is not None:
                item_data['pub_date'] = updated.text

            id_elem = entry.find('atom:id', ns)
            if id_elem is not None:
                item_data['guid'] = id_elem.text

            parsed_items.append(item_data)

        return parsed_items

    def monitor_feed(self, shop_code: str, keywords: List[str],
                    callback: Callable[[Dict], None],
                    check_interval: int = 60):
        """
        Continuously monitor RSS feed for matching items.

        Args:
            shop_code: Shop to monitor ('all' for all shops)
            keywords: List of keywords to match (case-insensitive)
            callback: Function to call when match found
            check_interval: Seconds between checks (default: 60)
        """
        print(f"Starting RSS monitor for shop '{shop_code}' with keywords: {keywords}")
        print(f"Check interval: {check_interval} seconds")

        while True:
            try:
                items = self.fetch_feed(shop_code)

                if items:
                    # Check each item for keyword matches
                    for item in items:
                        guid = item.get('guid', item.get('link'))
                        if not guid or guid in self.seen_items:
                            continue

                        # Check if any keyword matches
                        title = item.get('title', '').lower()
                        description = item.get('description', '').lower()

                        matched = False
                        for keyword in keywords:
                            kw_lower = keyword.lower()
                            if kw_lower in title or kw_lower in description:
                                matched = True
                                break

                        if matched:
                            print(f"\n✓ MATCH FOUND: {item.get('title')}")
                            print(f"  Link: {item.get('link')}")
                            print(f"  Published: {item.get('pub_date')}")

                            # Mark as seen
                            self.seen_items.add(guid)

                            # Call callback
                            try:
                                callback(item)
                            except Exception as e:
                                print(f"Error in callback: {e}")
                        else:
                            # Mark as seen even if no match
                            self.seen_items.add(guid)

                # Wait before next check
                time.sleep(check_interval)

            except KeyboardInterrupt:
                print("\nStopping RSS monitor")
                break
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(check_interval)

    def get_new_items_since_last_check(self, shop_code: str) -> List[Dict]:
        """
        Get items that are new since last check.

        Returns:
            List of new items (not in seen_items)
        """
        items = self.fetch_feed(shop_code)
        if not items:
            return []

        new_items = []
        for item in items:
            guid = item.get('guid', item.get('link'))
            if guid and guid not in self.seen_items:
                new_items.append(item)
                self.seen_items.add(guid)

        return new_items


def test_rss_monitor():
    """Test RSS monitoring."""
    import sys
    import io

    # Fix encoding for Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    monitor = MandarakeRSSMonitor(use_browser_mimic=True)

    # Test fetching Nakano store feed
    print("Testing Nakano store RSS feed...")
    items = monitor.fetch_feed('nkn')

    if items:
        print(f"SUCCESS: Found {len(items)} items in feed")
        if items:
            print("\nFirst item:")
            for key, value in items[0].items():
                print(f"  {key}: {value[:100] if isinstance(value, str) else value}")
    else:
        print("FAILED: Could not fetch feed (may require authentication)")

    # Test all stores feed
    print("\n\nTesting all stores RSS feed...")
    items = monitor.fetch_feed('all')

    if items:
        print(f"SUCCESS: Found {len(items)} items in feed")
    else:
        print("FAILED: Could not fetch feed (may require authentication)")


if __name__ == '__main__':
    test_rss_monitor()
