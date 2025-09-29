#!/usr/bin/env python3
"""
Browserless eBay search using requests and BeautifulSoup
This provides a more reliable alternative to the Scrapy approach
"""

import requests
import re
import json
import logging
import time
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

class BrowserlessEbaySearch:
    """Browserless eBay search engine using requests"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

        # Set up session headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        })

    def search_ebay(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search eBay for items and extract images"""
        self.logger.info(f"Starting browserless eBay search for: {query}")

        results = []

        # Build search URL
        search_params = {
            '_nkw': query,
            '_sacat': '0',
            'rt': 'nc',
            '_sop': '12',  # Best match
            '_dmd': '1',
            '_pgn': '1',
        }

        search_url = 'https://www.ebay.com/sch/i.html?' + '&'.join([f'{k}={quote(str(v))}' for k, v in search_params.items()])

        self.logger.info(f"Search URL: {search_url}")

        try:
            # Get search results page
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()

            self.logger.info(f"Search response status: {response.status_code}")
            self.logger.info(f"Response length: {len(response.content)}")

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try different item selectors
            item_containers = []
            selectors_to_try = [
                '.s-item',
                '.sresult',
                '[data-testid="item"]',
                '.x-item',
                '.srp-results .s-item',
                '.srp-river-results .s-item'
            ]

            for selector in selectors_to_try:
                containers = soup.select(selector)
                if containers:
                    self.logger.info(f"Found {len(containers)} items with selector: {selector}")
                    item_containers = containers
                    break

            if not item_containers:
                # Fallback: look for any links to item pages
                self.logger.warning("No item containers found, looking for item links")
                item_links = soup.find_all('a', href=re.compile(r'/itm/'))

                if item_links:
                    self.logger.info(f"Found {len(item_links)} item links as fallback")

                    for link in item_links[:max_results]:
                        item_url = urljoin('https://www.ebay.com', link.get('href'))

                        # Extract basic info from link context
                        title_elem = link.find(string=True) or link.find('img', alt=True)
                        title = ''
                        if title_elem:
                            if isinstance(title_elem, str):
                                title = title_elem.strip()
                            else:
                                title = title_elem.get('alt', '').strip()

                        if title and len(title) > 5:  # Basic validation
                            item_data = self.extract_item_details(item_url, title)
                            if item_data:
                                results.append(item_data)

                                if len(results) >= max_results:
                                    break

                return results

            # Process found item containers
            for container in item_containers[:max_results]:
                try:
                    item_data = self.extract_item_from_container(container)
                    if item_data:
                        # Get detailed info from item page
                        detailed_data = self.extract_item_details(item_data['item_url'], item_data.get('title', ''))
                        if detailed_data:
                            # Merge data
                            item_data.update(detailed_data)
                            results.append(item_data)

                            if len(results) >= max_results:
                                break

                except Exception as e:
                    self.logger.warning(f"Error processing item container: {e}")
                    continue

            self.logger.info(f"Found {len(results)} items total")
            return results

        except Exception as e:
            self.logger.error(f"Error during eBay search: {e}")
            return []

    def extract_item_from_container(self, container) -> Optional[Dict[str, Any]]:
        """Extract basic item data from search result container"""
        try:
            item_data = {}

            # Title
            title_selectors = [
                '.s-item__title',
                '.it-ttl',
                'h3',
                '.s-item__title span'
            ]

            for selector in title_selectors:
                title_elem = container.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    item_data['title'] = title_elem.get_text(strip=True)
                    break

            # URL
            url_selectors = [
                '.s-item__link',
                '.vip',
                'a[href*="/itm/"]'
            ]

            for selector in url_selectors:
                link_elem = container.select_one(selector)
                if link_elem and link_elem.get('href'):
                    item_data['item_url'] = urljoin('https://www.ebay.com', link_elem['href'])
                    break

            # Price
            price_selectors = [
                '.s-item__price .notranslate',
                '.s-item__price',
                '.prc'
            ]

            for selector in price_selectors:
                price_elem = container.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if '$' in price_text or '£' in price_text or '€' in price_text:
                        item_data['price'] = price_text
                        break

            # Condition
            condition_elem = container.select_one('.s-item__subtitle')
            if condition_elem:
                item_data['condition'] = condition_elem.get_text(strip=True)

            # Basic validation
            if item_data.get('title') and item_data.get('item_url'):
                return item_data
            else:
                return None

        except Exception as e:
            self.logger.warning(f"Error extracting item from container: {e}")
            return None

    def extract_item_details(self, item_url: str, fallback_title: str = '') -> Optional[Dict[str, Any]]:
        """Extract detailed item information from item page"""
        try:
            self.logger.info(f"Extracting details from: {item_url}")

            # Add delay to be respectful
            time.sleep(1)

            response = self.session.get(item_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            item_data = {'item_url': item_url}

            # Title
            title_selectors = [
                '#x-title-label-lbl',
                '.x-item-title-value',
                'h1[id*="title"]',
                '.it-ttl'
            ]

            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    item_data['title'] = title_elem.get_text(strip=True)
                    break

            if not item_data.get('title') and fallback_title:
                item_data['title'] = fallback_title

            # Price
            price_selectors = [
                '.u-flL.condText .notranslate',
                '.u-flL .notranslate',
                '#prcIsum',
                '.u-flL'
            ]

            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if any(c in price_text for c in ['$', '£', '€']):
                        item_data['price'] = price_text
                        break

            # Extract item ID
            item_id_match = re.search(r'/itm/([^/\?]+)', item_url)
            if item_id_match:
                item_data['item_id'] = item_id_match.group(1)

            # Images
            image_urls = []

            # Try different image selectors
            image_selectors = [
                '#icImg',
                '.ux-image-carousel-item img',
                '#vi_main_img_fs img',
                '.img img',
                'img[id*="img"]',
                '.vi-image img',
                '.ux-image-carousel img'
            ]

            found_images = set()  # Use set to avoid duplicates

            for selector in image_selectors:
                imgs = soup.select(selector)
                for img in imgs:
                    # Try src first, then data-src
                    img_url = img.get('src') or img.get('data-src')
                    if img_url and ('ebayimg.com' in img_url or 'i.ebayimg.com' in img_url):
                        # Convert to larger image size
                        if '$_' in img_url:
                            img_url = re.sub(r'\$_\d+\.JPG', '$_400.JPG', img_url, flags=re.IGNORECASE)
                        elif img_url.lower().endswith(('.jpg', '.jpeg')):
                            img_url = re.sub(r'\.(jpg|jpeg)$', '$_400.JPG', img_url, flags=re.IGNORECASE)

                        found_images.add(img_url)

                        if len(found_images) >= 5:  # Limit to 5 images
                            break

                if len(found_images) >= 5:
                    break

            item_data['image_urls'] = list(found_images)

            # Download and process images
            downloaded_images = []
            for i, img_url in enumerate(item_data['image_urls'][:5]):  # Max 5 images
                try:
                    img_response = self.session.get(img_url, timeout=15)
                    img_response.raise_for_status()

                    # Convert to OpenCV format for image processing
                    pil_image = Image.open(BytesIO(img_response.content))
                    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

                    downloaded_images.append({
                        'url': img_url,
                        'image': cv_image,
                        'index': i
                    })

                    time.sleep(0.5)  # Small delay between image downloads

                except Exception as e:
                    self.logger.warning(f"Failed to download image {img_url}: {e}")
                    continue

            item_data['downloaded_images'] = downloaded_images
            item_data['images_found'] = len(downloaded_images)

            self.logger.info(f"Extracted item: {item_data.get('title', 'Unknown')} with {len(downloaded_images)} images")

            return item_data

        except Exception as e:
            self.logger.error(f"Error extracting item details from {item_url}: {e}")
            return None


def test_browserless_search():
    """Test the browserless eBay search"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    searcher = BrowserlessEbaySearch()
    results = searcher.search_ebay("pokemon card pikachu", max_results=3)

    print(f"\nBrowserless eBay Search Results ({len(results)} items):")
    print("=" * 60)

    for i, result in enumerate(results, 1):
        print(f"\nItem {i}:")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Price: {result.get('price', 'N/A')}")
        print(f"Images: {result.get('images_found', 0)} downloaded")
        print(f"URL: {result.get('item_url', 'N/A')[:80]}...")

        if result.get('image_urls'):
            print("Sample Image URLs:")
            for j, img_url in enumerate(result['image_urls'][:2], 1):
                print(f"  {j}. {img_url}")


if __name__ == "__main__":
    test_browserless_search()