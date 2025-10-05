#!/usr/bin/env python3
"""
Sold Listing Image Matcher

Automatically searches for sold listings, compares images using computer vision,
and extracts pricing data for matching products.
"""

import os
import logging
import asyncio
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import cv2
import numpy as np
from PIL import Image
import requests
from playwright.async_api import async_playwright, Browser, Page
from dataclasses import dataclass
from search_optimizer import SearchOptimizer


@dataclass
class SoldListing:
    """Data structure for a sold listing"""
    title: str
    price: float
    currency: str
    sold_date: str
    image_url: str
    listing_url: str
    image_similarity: float = 0.0
    confidence_score: float = 0.0


@dataclass
class ImageMatchResult:
    """Result of image matching analysis"""
    matches_found: int
    best_match: Optional[SoldListing]
    all_matches: List[SoldListing]
    average_price: float
    price_range: Tuple[float, float]
    confidence: str


class SoldListingMatcher:
    """Matches product images with sold listings for price analysis"""

    def __init__(self, headless: bool = True, similarity_threshold: float = 0.7, debug_output_dir: str = None):
        self.headless = headless
        self.similarity_threshold = similarity_threshold
        self.search_optimizer = SearchOptimizer()

        # Image comparison settings
        self.image_size = (400, 400)  # Larger size for better feature detection
        self.feature_detector = cv2.ORB_create(nfeatures=2000)  # More features for better matching

        # Browser setup
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        # Cache for downloaded images
        self.image_cache = {}

        # Track current search URL for better linking
        self.current_search_url = ""

        # Debug output directory
        self.debug_output_dir = debug_output_dir
        if self.debug_output_dir:
            import os
            os.makedirs(self.debug_output_dir, exist_ok=True)
            logging.info(f"Debug output directory: {self.debug_output_dir}")

        # Store playwright instance for proper cleanup
        self._playwright_instance = None

    async def find_matching_sold_listings(self,
                                        reference_image_path: str,
                                        search_term: str,
                                        max_results: int = 5,
                                        days_back: int = 90) -> ImageMatchResult:
        """
        Find sold listings that match the reference image

        Args:
            reference_image_path: Path to the product image to match
            search_term: Search term for finding listings
            max_results: Maximum number of results to analyze
            days_back: How many days back to search for sold items

        Returns:
            ImageMatchResult with matches and pricing data
        """
        try:
            logging.info(f"Starting image matching for: {search_term}")

            # Step 1: Load and prepare reference image
            reference_features = await self._load_and_process_image(reference_image_path)
            if reference_features is None:
                raise ValueError("Could not process reference image")

            # Step 2: Search for sold listings (use exact search term, no optimization needed)
            listings_to_analyze = await self._search_sold_listings(search_term, max_results, days_back)

            logging.info(f"Found {len(listings_to_analyze)} unique sold listings to analyze")

            # Step 3: Compare images and find matches
            matches = await self._compare_images_with_listings(
                reference_features, listings_to_analyze
            )

            # Step 4: Analyze results
            result = self._analyze_matches(matches)

            logging.info(f"Image matching complete: {result.matches_found} matches found")
            return result

        except Exception as e:
            logging.error(f"Error in image matching: {e}")
            return ImageMatchResult(
                matches_found=0,
                best_match=None,
                all_matches=[],
                average_price=0.0,
                price_range=(0.0, 0.0),
                confidence="error"
            )

    async def _search_sold_listings(self,
                                  search_term: str,
                                  max_results: int,
                                  days_back: int) -> List[SoldListing]:
        """Search for sold listings using headless browser"""
        try:
            if not self.browser:
                await self._init_browser()

            # Navigate to eBay sold listings with improved error handling
            sold_url = self._build_ebay_sold_url(search_term, days_back)
            self.current_search_url = sold_url  # Track the current search URL

            try:
                # Skip networkidle - go straight to faster option for immediate image extraction
                logging.info("Using fast page load for immediate image extraction")
                await self.page.goto(sold_url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                logging.warning(f"domcontentloaded timeout, trying basic load: {e}")
                try:
                    # Fallback to basic load
                    await self.page.goto(sold_url, wait_until="load", timeout=10000)
                except Exception as e2:
                    logging.warning(f"load timeout, proceeding anyway: {e2}")
                    # Continue anyway - we might still be able to extract prefetch images

            # Skip traditional selectors - go straight to extraction
            # This prioritizes prefetch images and avoids timeouts
            logging.info("Skipping traditional selector waits - extracting data immediately")

            # Brief wait for prefetch images to load (much faster than selector waits)
            await asyncio.sleep(2)  # 2 seconds should be enough for prefetch images

            # Extract listing data (will try prefetch images first, then fallback to selectors if needed)
            listings = await self._extract_listing_data(max_results)

            logging.info(f"Extracted {len(listings)} listings for '{search_term}'")
            return listings

        except Exception as e:
            logging.error(f"Error searching sold listings: {e}")

            # Check if this is a blocking/timeout issue and provide helpful info
            if "timeout" in str(e).lower() or "navigation" in str(e).lower():
                logging.warning("eBay may be blocking automated access. This is common and expected.")
                logging.info("Suggestions: 1) Try again in a few minutes 2) Use a different search term 3) Check internet connection")

            return []

    def _build_ebay_sold_url(self, search_term: str, days_back: int) -> str:
        """Build eBay sold listings URL with proper encoding"""
        from urllib.parse import quote_plus

        base_url = "https://www.ebay.com/sch/i.html"

        # Clean and encode search term
        clean_term = search_term.strip()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        params = {
            '_nkw': clean_term,
            '_in_kw': '1',
            '_ex_kw': '',
            '_sacat': '0',
            'LH_Sold': '1',
            'LH_Complete': '1',
            '_udlo': '',
            '_udhi': '',
            '_samilow': '',
            '_samihi': '',
            '_sadis': '15',
            '_stpos': '',
            '_sargn': '-1',
            '_salic': '1',
            '_sop': '12',  # Sort by ending soonest
            '_dmd': '1',
            '_ipg': '25'  # Fewer results per page to load faster
        }

        # Build URL with proper encoding
        param_parts = []
        for k, v in params.items():
            if v:  # Only include non-empty values
                if k == '_nkw':
                    # Special handling for search term - preserve + for spaces
                    encoded_value = clean_term.replace(' ', '+')
                else:
                    encoded_value = str(v)
                param_parts.append(f"{k}={encoded_value}")

        param_string = '&'.join(param_parts)
        url = f"{base_url}?{param_string}"

        logging.debug(f"Built eBay URL: {url}")
        return url

    async def _extract_listing_data(self, max_results: int) -> List[SoldListing]:
        """Extract sold listing data from the page - updated for modern eBay structure"""
        listings = []

        try:
            # Check for blocking and wait for automatic redirect
            page_title = await self.page.title()
            if "pardon our interruption" in page_title.lower():
                logging.info("eBay 'Pardon Our Interruption' page detected - waiting for automatic redirect...")

                # Wait for the page to automatically redirect (usually 3-10 seconds)
                max_wait_time = 15  # Maximum wait time in seconds
                wait_interval = 1   # Check every 1 second

                for i in range(max_wait_time):
                    await asyncio.sleep(wait_interval)

                    # Check if page has redirected
                    current_title = await self.page.title()
                    if "pardon our interruption" not in current_title.lower():
                        logging.info(f"Page redirected after {i+1} seconds: '{current_title}'")
                        break

                    if i == max_wait_time - 1:
                        logging.warning("eBay page did not redirect after maximum wait time")
                        return []

            # First, try to extract prefetch images (modern eBay approach) - prioritize this method
            prefetch_listings = await self._extract_from_prefetch_images_playwright(max_results)
            if prefetch_listings:
                logging.info(f"Found {len(prefetch_listings)} listings from prefetch images - stopping here!")
                return prefetch_listings

            # Only try traditional selectors if prefetch completely failed
            logging.warning("No prefetch images found, trying traditional selectors...")

            # Add short timeout to avoid long waits
            try:
                await self.page.wait_for_selector('.s-item', timeout=5000)  # 5 second timeout only
                items = await self.page.query_selector_all('.s-item')
            except Exception as e:
                logging.warning(f"Primary selector timeout, trying alternatives: {e}")
                try:
                    await self.page.wait_for_selector('.s-item__wrapper, [data-testid="item-card"]', timeout=5000)
                    items = await self.page.query_selector_all('.s-item__wrapper, [data-testid="item-card"]')
                except Exception as e2:
                    logging.warning(f"Alternative selector timeout, trying basic item selector: {e2}")
                    items = await self.page.query_selector_all('[data-view="mi:1686|iid:1"]')

            if not items:
                logging.warning("No listing items found with any selectors")
                return []

            for i, item in enumerate(items[:max_results]):
                try:
                    # Extract title with enhanced selectors
                    title = "Unknown"
                    title_selectors = [
                        '.s-item__title',
                        '.s-item__title span',
                        '.it-ttl',
                        'h3',
                        '.s-item__link'
                    ]

                    for selector in title_selectors:
                        title_elem = await item.query_selector(selector)
                        if title_elem:
                            title_text = await title_elem.inner_text()
                            if title_text and title_text.strip() and len(title_text.strip()) > 10:
                                # Clean up the title
                                import re
                                clean_title = title_text.strip()
                                clean_title = re.sub(r'^(New Listing|SPONSORED)\s*', '', clean_title, flags=re.IGNORECASE)
                                if len(clean_title) > 10:
                                    title = clean_title
                                    logging.debug(f"Extracted regular title: {clean_title[:50]}...")
                                    break

                    # Extract price
                    price_elem = await item.query_selector('.s-item__price')
                    price_text = await price_elem.inner_text() if price_elem else "$0"
                    price, currency = self._parse_price(price_text)

                    # Extract sold date
                    date_elem = await item.query_selector('.s-item__title--tag')
                    sold_date = await date_elem.inner_text() if date_elem else "Unknown"

                    # Extract image URL
                    img_elem = await item.query_selector('.s-item__image img')
                    image_url = await img_elem.get_attribute('src') if img_elem else ""

                    # Extract listing URL
                    link_elem = await item.query_selector('.s-item__link')
                    listing_url = await link_elem.get_attribute('href') if link_elem else ""

                    if price > 0 and image_url:
                        listing = SoldListing(
                            title=title.strip(),
                            price=price,
                            currency=currency,
                            sold_date=sold_date.strip(),
                            image_url=image_url,
                            listing_url=listing_url
                        )
                        listings.append(listing)

                except Exception as e:
                    logging.debug(f"Error extracting listing {i}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error extracting listings: {e}")

        return listings

    async def _extract_from_prefetch_original(self, prefetch_images, max_results: int) -> List[SoldListing]:
        """Original prefetch image extraction method that was working"""
        listings = []

        # Extract title information from page
        page_title = await self.page.title()
        search_term = ""
        if page_title:
            if " for sale" in page_title:
                search_term = page_title.split(" for sale")[0]
            elif ":" in page_title:
                search_term = page_title.split(":")[0]

        for i, img in enumerate(prefetch_images[:max_results]):
            try:
                img_src = await img.get_attribute('src')
                if not img_src:
                    continue

                # Download and save image immediately
                if self.debug_output_dir:
                    try:
                        logging.info(f"Downloading image {i+1} immediately: {img_src}")

                        import requests, os, cv2, numpy as np
                        response = requests.get(img_src, timeout=10, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        })
                        response.raise_for_status()

                        filename = f"listing_{i+1:02d}.jpg"
                        debug_path = os.path.join(self.debug_output_dir, filename)
                        os.makedirs(self.debug_output_dir, exist_ok=True)

                        image_array = np.frombuffer(response.content, np.uint8)
                        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                        if image is not None:
                            cv2.imwrite(debug_path, image)
                            logging.info(f"✅ Saved debug image immediately: {debug_path}")

                            try:
                                features = self._extract_image_features(image)
                                cache_key = f"{img_src}_{i}"
                                self.image_cache[cache_key] = features
                                logging.debug(f"Cached features for image {i+1}")
                            except Exception as cache_error:
                                logging.debug(f"Error caching features for image {i+1}: {cache_error}")
                        else:
                            logging.warning(f"Failed to decode image {i+1}")

                    except Exception as download_error:
                        logging.warning(f"Error downloading image {i+1} immediately: {download_error}")

                # Try to extract enhanced data from the page context
                title = f"eBay Item {i+1}"
                listing_url = "No URL found"
                price = 0.0
                currency = 'USD'
                sold_date = "Recent"

                # Find the parent item container for this image
                try:
                    parent_item = await img.query_selector('xpath=ancestor::div[contains(@class,"s-item")][1]')
                    if not parent_item:
                        parent_item = await img.query_selector('xpath=ancestor::div[@class][1]')

                    if parent_item:
                        # Extract URL using enhanced selectors
                        url_selectors = ['.s-item__link', 'a[href*="/itm/"]']
                        for selector in url_selectors:
                            link_elem = await parent_item.query_selector(selector)
                            if link_elem:
                                href = await link_elem.get_attribute('href')
                                if href and '/itm/' in href:
                                    import re
                                    if href.startswith('/'):
                                        href = f"https://www.ebay.com{href}"
                                    item_id_match = re.search(r'/itm/[^/]*?(\d{10,})', href)
                                    if item_id_match:
                                        item_id = item_id_match.group(1)
                                        listing_url = f"https://www.ebay.com/itm/{item_id}"
                                    else:
                                        listing_url = href.split('?')[0]
                                    break

                        # Extract title using enhanced selectors
                        title_selectors = ['.s-item__title span', '.s-item__title']
                        for selector in title_selectors:
                            title_elem = await parent_item.query_selector(selector)
                            if title_elem:
                                title_text = await title_elem.inner_text()
                                if title_text and len(title_text.strip()) > 10:
                                    import re
                                    clean_title = title_text.strip()
                                    clean_title = re.sub(r'^(New Listing|SPONSORED)\s*', '', clean_title, flags=re.IGNORECASE)
                                    if len(clean_title) > 10:
                                        title = clean_title
                                        break

                        # Extract price using enhanced selectors
                        price_selectors = ['.s-item__price .notranslate', '.s-item__price']
                        for selector in price_selectors:
                            price_elem = await parent_item.query_selector(selector)
                            if price_elem:
                                price_text = await price_elem.inner_text()
                                if price_text:
                                    try:
                                        import re
                                        price_match = re.search(r'[\$£€¥]?([\d,]+\.?\d*)', price_text)
                                        if price_match:
                                            price_str = price_match.group(1).replace(',', '')
                                            price = float(price_str)
                                            if '$' in price_text:
                                                currency = 'USD'
                                            elif '£' in price_text:
                                                currency = 'GBP'
                                            elif '€' in price_text:
                                                currency = 'EUR'
                                            elif '¥' in price_text:
                                                currency = 'JPY'
                                            break
                                    except Exception as e:
                                        logging.debug(f"Error parsing price '{price_text}': {e}")

                except Exception as e:
                    logging.debug(f"Enhanced extraction failed for image {i+1}: {e}")

                # Fallback to original search page URL if no specific URL found
                if listing_url == "No URL found":
                    listing_url = f"Search Results Page: {self.current_search_url}"

                listing = SoldListing(
                    title=title,
                    price=price,
                    currency=currency,
                    sold_date=sold_date,
                    image_url=img_src,
                    listing_url=listing_url
                )

                listings.append(listing)
                logging.info(f"✅ Extracted listing {i+1}: {title[:50]}... | {currency} {price:.2f} | {listing_url[:50]}...")

            except Exception as e:
                logging.warning(f"Error processing prefetch image {i+1}: {e}")
                continue

        logging.info(f"✅ Successfully extracted {len(listings)} listings using original prefetch method")
        return listings

    async def _extract_from_prefetch_images_playwright(self, max_results: int) -> List[SoldListing]:
        """Extract listings from eBay search results using proven Scrapy selectors and Playwright"""
        listings = []

        try:
            # First, try to find prefetch images (original working method)
            prefetch_container = await self.page.query_selector('.s-prefetch-image')
            if prefetch_container:
                prefetch_images = await prefetch_container.query_selector_all('img[src*="ebayimg.com"]')
                if prefetch_images:
                    logging.info(f"Found {len(prefetch_images)} prefetch images (using original method)")
                    return await self._extract_from_prefetch_original(prefetch_images, max_results)

            # Fallback: Try to find listing containers (enhanced method)
            try:
                await self.page.wait_for_selector('.s-item, .srp-results .s-item', timeout=5000)
                all_items = await self.page.query_selector_all('.s-item, .srp-results .s-item')
                # Filter out headers/ads (usually the first item)
                items = [item for item in all_items[1:] if item is not None] if len(all_items) > 1 else all_items
                total_found = len(items)
                logging.info(f"Found {total_found} total eBay sold listings on page (using enhanced method)")
            except Exception as e:
                logging.warning(f"Enhanced method failed: {e}")
                return []

            # Process enhanced method with listing containers
            logging.info(f"Processing first {max_results} listings from {total_found} found")

            for i, item in enumerate(items[:max_results]):
                try:
                    # Extract image URL using proven scrapy selectors
                    img_elem = await item.query_selector('img[src*="ebayimg.com"]')
                    if not img_elem:
                        logging.debug(f"No eBay image found for item {i+1}")
                        continue

                    img_src = await img_elem.get_attribute('src')
                    if not img_src:
                        continue

                    # Extract listing URL using proven scrapy selectors
                    listing_url = "No URL found"
                    url_selectors = ['.s-item__link', 'a[href*="/itm/"]']

                    for selector in url_selectors:
                        link_elem = await item.query_selector(selector)
                        if link_elem:
                            href = await link_elem.get_attribute('href')
                            if href and '/itm/' in href:
                                # Clean URL and extract item ID
                                import re
                                from urllib.parse import urljoin

                                # Convert relative to absolute
                                if href.startswith('/'):
                                    href = f"https://www.ebay.com{href}"

                                # Extract clean item ID
                                item_id_match = re.search(r'/itm/[^/]*?(\d{10,})', href)
                                if item_id_match:
                                    item_id = item_id_match.group(1)
                                    listing_url = f"https://www.ebay.com/itm/{item_id}"
                                else:
                                    # Fallback: remove query parameters
                                    listing_url = href.split('?')[0]
                                break

                    # Extract title using proven scrapy selectors
                    title = f"eBay Item {i+1}"
                    title_selectors = ['.s-item__title span', '.s-item__title']

                    for selector in title_selectors:
                        title_elem = await item.query_selector(selector)
                        if title_elem:
                            title_text = await title_elem.inner_text()
                            if title_text and len(title_text.strip()) > 10:
                                # Clean up title
                                import re
                                clean_title = title_text.strip()
                                clean_title = re.sub(r'^(New Listing|SPONSORED)\s*', '', clean_title, flags=re.IGNORECASE)
                                if len(clean_title) > 10:
                                    title = clean_title
                                    break

                    # Extract price using proven scrapy selectors
                    price = 0.0
                    currency = 'USD'
                    price_selectors = ['.s-item__price .notranslate', '.s-item__price']

                    for selector in price_selectors:
                        price_elem = await item.query_selector(selector)
                        if price_elem:
                            price_text = await price_elem.inner_text()
                            if price_text:
                                try:
                                    import re
                                    # Extract price with regex - handle various currencies
                                    price_match = re.search(r'[\$£€¥]?([\d,]+\.?\d*)', price_text)
                                    if price_match:
                                        price_str = price_match.group(1).replace(',', '')
                                        price = float(price_str)

                                        # Determine currency from symbol
                                        if '$' in price_text:
                                            currency = 'USD'
                                        elif '£' in price_text:
                                            currency = 'GBP'
                                        elif '€' in price_text:
                                            currency = 'EUR'
                                        elif '¥' in price_text:
                                            currency = 'JPY'
                                        break
                                except Exception as e:
                                    logging.debug(f"Error parsing price '{price_text}': {e}")

                    # Extract sold date from subtitle
                    sold_date = "Recent"
                    subtitle_elem = await item.query_selector('.s-item__subtitle')
                    if subtitle_elem:
                        subtitle_text = await subtitle_elem.inner_text()
                        if subtitle_text and ('sold' in subtitle_text.lower() or 'ended' in subtitle_text.lower()):
                            sold_date = subtitle_text.strip()

                    # Download and save image for debugging
                    if self.debug_output_dir:
                        try:
                            logging.info(f"Downloading image {i+1}/{max_results}: {title[:50]}...")

                            import requests, os, cv2, numpy as np
                            response = requests.get(img_src, timeout=10, headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            })
                            response.raise_for_status()

                            filename = f"listing_{i+1:02d}.jpg"
                            debug_path = os.path.join(self.debug_output_dir, filename)
                            os.makedirs(self.debug_output_dir, exist_ok=True)

                            # Convert and save image
                            image_array = np.frombuffer(response.content, np.uint8)
                            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                            if image is not None:
                                cv2.imwrite(debug_path, image)
                                logging.info(f"✅ Saved debug image: {debug_path}")

                                # Cache features for comparison
                                try:
                                    features = self._extract_image_features(image)
                                    cache_key = f"{img_src}_{i}"
                                    self.image_cache[cache_key] = features
                                    logging.debug(f"Cached features for image {i+1}")
                                except Exception as cache_error:
                                    logging.debug(f"Error caching features: {cache_error}")
                            else:
                                logging.warning(f"Failed to decode image {i+1}")

                        except Exception as download_error:
                            logging.warning(f"Error downloading image {i+1}: {download_error}")

                    # Create listing with extracted data
                    listing = SoldListing(
                        title=title,
                        price=price,
                        currency=currency,
                        sold_date=sold_date,
                        image_url=img_src,
                        listing_url=listing_url
                    )

                    listings.append(listing)
                    logging.info(f"✅ Extracted listing {i+1}: {title[:50]}... | {currency} {price:.2f} | {listing_url[:50]}...")

                except Exception as e:
                    logging.warning(f"Error processing item {i+1}: {e}")
                    continue

            logging.info(f"✅ Successfully extracted {len(listings)} listings from {total_found} total found")
            return listings

        except Exception as e:
            logging.error(f"Error extracting eBay listings: {e}")
            return []

    def _parse_price(self, price_text: str) -> Tuple[float, str]:
        """Parse price text and extract amount and currency"""
        try:
            # Remove extra text and normalize
            price_text = price_text.replace('Sold  ', '').replace('to ', '').strip()

            # Extract currency and amount using regex
            price_match = re.search(r'([£$€¥])([\d,]+\.?\d*)', price_text)
            if price_match:
                currency_symbol = price_match.group(1)
                amount_str = price_match.group(2).replace(',', '')
                amount = float(amount_str)

                # Map currency symbols
                currency_map = {'$': 'USD', '£': 'GBP', '€': 'EUR', '¥': 'JPY'}
                currency = currency_map.get(currency_symbol, 'USD')

                return amount, currency

        except Exception as e:
            logging.debug(f"Error parsing price '{price_text}': {e}")

        return 0.0, 'USD'

    async def _compare_images_with_listings(self,
                                          reference_features: dict,
                                          listings: List[SoldListing]) -> List[SoldListing]:
        """Compare reference image with listing images"""
        matches = []

        for i, listing in enumerate(listings):
            try:
                # Download and process listing image
                listing_features = await self._download_and_process_image(listing.image_url, i)

                if listing_features is not None:
                    # Calculate similarity
                    similarity = self._calculate_image_similarity(reference_features, listing_features)

                    if similarity >= self.similarity_threshold:
                        listing.image_similarity = similarity
                        listing.confidence_score = self._calculate_confidence_score(listing, similarity)
                        matches.append(listing)

                        logging.info(f"Match found: {listing.title[:50]}... (similarity: {similarity:.2f})")

            except Exception as e:
                logging.debug(f"Error comparing image for listing: {e}")
                continue

        # Sort by similarity score
        matches.sort(key=lambda x: x.image_similarity, reverse=True)
        return matches

    async def _load_and_process_image(self, image_path: str) -> Optional[dict]:
        """Load and extract features from reference image"""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Reference image not found: {image_path}")

            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            return self._extract_image_features(image)

        except Exception as e:
            logging.error(f"Error processing reference image: {e}")
            return None

    async def _download_and_process_image(self, image_url: str, listing_index: int = 0) -> Optional[dict]:
        """Download and process image from URL"""
        try:
            # Check cache first
            cache_key = f"{image_url}_{listing_index}"
            if cache_key in self.image_cache:
                return self.image_cache[cache_key]

            logging.info(f"Downloading image {listing_index + 1}: {image_url}")

            # Download image
            response = requests.get(image_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()

            logging.info(f"Downloaded image {listing_index + 1}: {len(response.content):,} bytes")

            # Convert to OpenCV format
            image_array = np.frombuffer(response.content, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                logging.warning(f"Failed to decode image {listing_index + 1}: {image_url}")
                return None

            logging.info(f"Decoded image {listing_index + 1}: {image.shape} shape")

            # Save debug image if requested
            if self.debug_output_dir:
                import os
                filename = f"listing_{listing_index + 1:02d}.jpg"
                debug_path = os.path.join(self.debug_output_dir, filename)
                cv2.imwrite(debug_path, image)
                logging.info(f"Saved debug image: {debug_path}")

            # Extract features
            features = self._extract_image_features(image)

            # Cache result
            self.image_cache[cache_key] = features

            return features

        except Exception as e:
            logging.debug(f"Error downloading/processing image {image_url}: {e}")
            return None

    def _extract_image_features(self, image: np.ndarray) -> dict:
        """Extract multiple types of features from image for robust comparison"""
        try:
            # Resize image for consistent comparison
            resized = cv2.resize(image, self.image_size)

            # Convert to grayscale
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            features = {}

            # 1. ORB features for keypoint matching
            keypoints, descriptors = self.feature_detector.detectAndCompute(gray, None)
            features['orb'] = descriptors if descriptors is not None else np.array([])

            # 2. Color histogram for overall color similarity
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [60], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [60], [0, 256])
            features['color_hist'] = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])

            # 3. Structural similarity (using template matching on smaller scale)
            small_gray = cv2.resize(gray, (64, 64))
            features['structure'] = small_gray.flatten().astype(np.float32)

            # 4. Edge features for shape comparison
            edges = cv2.Canny(gray, 50, 150)
            edge_hist = cv2.calcHist([edges], [0], None, [256], [0, 256])
            features['edges'] = edge_hist.flatten()

            return features

        except Exception as e:
            logging.debug(f"Error extracting image features: {e}")
            return {'orb': np.array([]), 'color_hist': np.array([]), 'structure': np.array([]), 'edges': np.array([])}

    def _calculate_image_similarity(self, features1: dict, features2: dict) -> float:
        """Calculate similarity between two multi-feature sets using weighted combination"""
        try:
            print(f"[DEBUG] Playwright similarity calculation called with types: {type(features1)}, {type(features2)}")
            if not features1 or not features2:
                return 0.0

            similarities = {}
            weights = {
                'orb': 0.4,      # ORB features are most important for exact matches
                'color_hist': 0.3, # Color similarity is very important for similar products
                'structure': 0.2,  # Overall structure similarity
                'edges': 0.1       # Edge patterns
            }

            # 1. ORB feature matching
            orb_sim = 0.0
            if len(features1['orb']) > 0 and len(features2['orb']) > 0:
                try:
                    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                    matches = bf.match(features1['orb'], features2['orb'])

                    if len(matches) > 0:
                        # Use more lenient distance threshold for similar but not identical images
                        good_matches = [m for m in matches if m.distance < 70]  # Increased from 50
                        # Normalize by minimum feature count for better scaling
                        min_features = min(len(features1['orb']), len(features2['orb']))
                        orb_sim = len(good_matches) / max(min_features, 1)
                        orb_sim = min(orb_sim, 1.0)
                except Exception as e:
                    logging.debug(f"ORB matching error: {e}")
                    orb_sim = 0.0
            similarities['orb'] = orb_sim

            # 2. Color histogram similarity
            if len(features1['color_hist']) > 0 and len(features2['color_hist']) > 0:
                color_sim = cv2.compareHist(features1['color_hist'], features2['color_hist'], cv2.HISTCMP_CORREL)
                color_sim = max(0.0, color_sim)  # Ensure non-negative
            else:
                color_sim = 0.0
            similarities['color_hist'] = color_sim

            # 3. Structural similarity (normalized cross-correlation)
            if len(features1['structure']) > 0 and len(features2['structure']) > 0:
                # Normalize features
                struct1 = features1['structure'] / (np.linalg.norm(features1['structure']) + 1e-8)
                struct2 = features2['structure'] / (np.linalg.norm(features2['structure']) + 1e-8)
                struct_sim = np.dot(struct1, struct2)
                struct_sim = max(0.0, struct_sim)  # Ensure non-negative
            else:
                struct_sim = 0.0
            similarities['structure'] = struct_sim

            # 4. Edge similarity
            if len(features1['edges']) > 0 and len(features2['edges']) > 0:
                edge_sim = cv2.compareHist(features1['edges'], features2['edges'], cv2.HISTCMP_CORREL)
                edge_sim = max(0.0, edge_sim)  # Ensure non-negative
            else:
                edge_sim = 0.0
            similarities['edges'] = edge_sim

            # Calculate weighted average
            total_similarity = sum(similarities[key] * weights[key] for key in weights.keys())

            # Bonus for multiple good matches
            good_feature_count = sum(1 for sim in similarities.values() if sim > 0.5)
            if good_feature_count >= 2:
                total_similarity *= 1.1  # 10% bonus for multiple good feature matches

            total_similarity = min(total_similarity, 1.0)

            # Debug logging for similar images
            if total_similarity > 0.2:
                try:
                    logging.info("Similarity breakdown: ORB=%.3f, Color=%.3f, Structure=%.3f, Edges=%.3f, Total=%.3f" % (
                        similarities['orb'], similarities['color_hist'], similarities['structure'],
                        similarities['edges'], total_similarity
                    ))
                except Exception as format_error:
                    print(f"[DEBUG] Format error in similarity logging: {format_error}")
                    print(f"[DEBUG] Similarities: {similarities}")
                    print(f"[DEBUG] Total: {total_similarity}")

            return total_similarity

        except Exception as e:
            logging.debug(f"Error calculating similarity: {e}")
            return 0.0

    def _calculate_confidence_score(self, listing: SoldListing, similarity: float) -> float:
        """Calculate overall confidence score for a match"""
        # Base confidence from image similarity
        confidence = similarity

        # Boost confidence for recent sales
        try:
            if 'day' in listing.sold_date.lower():
                if 'yesterday' in listing.sold_date.lower() or '1 day' in listing.sold_date.lower():
                    confidence += 0.1
            elif 'week' in listing.sold_date.lower():
                confidence += 0.05
        except (AttributeError, TypeError):
            pass  # sold_date is None or not a string

        # Boost confidence for reasonable prices (not too high/low)
        if 10 <= listing.price <= 1000:
            confidence += 0.05

        return min(confidence, 1.0)

    def _analyze_matches(self, matches: List[SoldListing]) -> ImageMatchResult:
        """Analyze matches and calculate statistics"""
        if not matches:
            return ImageMatchResult(
                matches_found=0,
                best_match=None,
                all_matches=[],
                average_price=0.0,
                price_range=(0.0, 0.0),
                confidence="no_matches"
            )

        # Calculate price statistics
        prices = [match.price for match in matches]
        avg_price = sum(prices) / len(prices)
        price_range = (min(prices), max(prices))

        # Determine confidence level
        confidence = "high" if len(matches) >= 3 else "medium" if len(matches) >= 2 else "low"

        return ImageMatchResult(
            matches_found=len(matches),
            best_match=matches[0],  # Already sorted by similarity
            all_matches=matches,
            average_price=avg_price,
            price_range=price_range,
            confidence=confidence
        )

    async def _init_browser(self):
        """Initialize headless browser with enhanced stealth"""
        try:
            self._playwright_instance = await async_playwright().start()

            # Enhanced args for better stealth
            browser_args = [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-dev-shm-usage',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-background-networking',
                '--disable-ipc-flooding-protection',
                '--disable-field-trial-config',
                '--disable-features=TranslateUI',
                '--disable-default-apps',
                '--disable-sync',
                '--no-first-run',
                '--no-default-browser-check',
                '--window-size=1920,1080',
            ]

            # Only add disable-images if headless to save bandwidth
            if self.headless:
                browser_args.append('--disable-images')

            self.browser = await self._playwright_instance.chromium.launch(
                headless=self.headless,
                args=browser_args
            )

            # Create page with stealth settings
            self.page = await self.browser.new_page()

            # Set realistic viewport and user agent
            await self.page.set_viewport_size({"width": 1920, "height": 1080})

            # Enhanced headers for better stealth
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })

            # Remove automation indicators
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });

                window.chrome = {
                    runtime: {},
                };
            """)

            # Add random delay before first navigation
            import random
            await asyncio.sleep(random.uniform(1, 3))

            logging.info("Browser initialized successfully with enhanced stealth")

        except Exception as e:
            logging.error(f"Error initializing browser: {e}")
            raise

    async def cleanup(self):
        """Clean up browser resources thoroughly"""
        try:
            # Close page first
            if self.page:
                try:
                    await self.page.close()
                    logging.debug("Page closed successfully")
                except Exception as e:
                    logging.debug(f"Error closing page: {e}")
                finally:
                    self.page = None

            # Close browser context and browser
            if self.browser:
                try:
                    # Close all contexts first
                    contexts = self.browser.contexts
                    for context in contexts:
                        try:
                            await context.close()
                        except Exception as e:
                            logging.debug(f"Error closing context: {e}")

                    # Close browser
                    await self.browser.close()
                    logging.debug("Browser closed successfully")
                except Exception as e:
                    logging.debug(f"Error closing browser: {e}")
                finally:
                    self.browser = None

            # Close playwright instance if we have a reference to it
            if hasattr(self, '_playwright_instance'):
                try:
                    await self._playwright_instance.stop()
                    logging.debug("Playwright instance stopped")
                except Exception as e:
                    logging.debug(f"Error stopping playwright: {e}")
                finally:
                    self._playwright_instance = None

            # Clear image cache
            self.image_cache.clear()
            logging.debug("Cleanup completed successfully")

        except Exception as e:
            logging.debug(f"Error during cleanup: {e}")

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.cleanup()


# Convenience functions
async def match_product_with_sold_listings(reference_image_path: str,
                                         search_term: str,
                                         headless: bool = True,
                                         max_results: int = 5) -> ImageMatchResult:
    """
    Convenience function to match a product image with sold listings

    Args:
        reference_image_path: Path to product image
        search_term: Search term for the product
        headless: Whether to run browser in headless mode
        max_results: Maximum results to analyze

    Returns:
        ImageMatchResult with pricing data
    """
    async with SoldListingMatcher(headless=headless) as matcher:
        return await matcher.find_matching_sold_listings(
            reference_image_path, search_term, max_results
        )


if __name__ == '__main__':
    # Example usage and testing
    import sys

    async def test_matcher():
        if len(sys.argv) < 3:
            print("Usage: python sold_listing_matcher.py <image_path> <search_term>")
            print("Example: python sold_listing_matcher.py image.jpg 'yura kano photobook'")
            return

        image_path = sys.argv[1]
        search_term = sys.argv[2]

        print(f"=== SOLD LISTING MATCHER TEST ===")
        print(f"Image: {image_path}")
        print(f"Search term: {search_term}")
        print()

        result = await match_product_with_sold_listings(
            image_path, search_term, headless=False, max_results=5
        )

        print(f"=== RESULTS ===")
        print(f"Matches found: {result.matches_found}")
        print(f"Confidence: {result.confidence}")

        if result.best_match:
            print(f"\nBest match:")
            print(f"  Title: {result.best_match.title}")
            print(f"  Price: {result.best_match.currency} {result.best_match.price}")
            print(f"  Similarity: {result.best_match.image_similarity:.2f}")
            print(f"  Sold: {result.best_match.sold_date}")

        if result.matches_found > 0:
            print(f"\nPrice analysis:")
            print(f"  Average price: ${result.average_price:.2f}")
            print(f"  Price range: ${result.price_range[0]:.2f} - ${result.price_range[1]:.2f}")

            print(f"\nAll matches:")
            for i, match in enumerate(result.all_matches, 1):
                print(f"  {i}. {match.title[:60]}... - ${match.price:.2f} (sim: {match.image_similarity:.2f})")

    if len(sys.argv) > 1:
        asyncio.run(test_matcher())
    else:
        print("Sold Listing Matcher")
        print("Usage: python sold_listing_matcher.py <image_path> <search_term>")


# Add the missing method to the SoldListingMatcher class
def add_url_extraction_method():
    """Add the URL extraction method to the SoldListingMatcher class"""

    async def _extract_listing_url_from_image(self, img_element, index: int) -> Optional[str]:
        """Try to extract actual listing URL from image element context"""
        try:
            # Method 1: Look for parent link elements
            parent_link = await img_element.query_selector('xpath=ancestor::a[@href][1]')
            if parent_link:
                href = await parent_link.get_attribute('href')
                if href and 'itm/' in href:
                    return href

            # Method 2: Look for sibling elements with URLs
            parent = await img_element.query_selector('xpath=..')
            if parent:
                sibling_links = await parent.query_selector_all('a[href*="itm/"]')
                if sibling_links:
                    href = await sibling_links[0].get_attribute('href')
                    return href

            # Method 3: Look for data attributes that might contain URLs
            data_attrs = ['data-href', 'data-url', 'data-item-id']
            for attr in data_attrs:
                value = await img_element.get_attribute(attr)
                if value:
                    if value.isdigit():
                        return f"https://www.ebay.com/itm/{value}"
                    elif 'itm/' in value:
                        return value if value.startswith('http') else f"https://www.ebay.com{value}"

            return None

        except Exception as e:
            logging.debug(f"Error extracting URL from image {index}: {e}")
            return None

    # Add the method to the class
    SoldListingMatcher._extract_listing_url_from_image = _extract_listing_url_from_image

    async def _extract_price_from_page_context(self, img_element, index: int) -> dict:
        """Try to extract actual price and title from the page context around an image"""
        try:
            # Initialize default values
            result = {
                'price': 0.0,
                'currency': 'USD',
                'title': '',
                'sold_date': 'Recent'
            }

            # Method 1: Look for price in parent containers of the image
            parent = await img_element.query_selector('xpath=ancestor::div[contains(@class,"s-item")][1]')
            if not parent:
                parent = await img_element.query_selector('xpath=ancestor::div[@class][1]')

            if parent:
                # Try to find price elements
                price_selectors = [
                    '.s-item__price .notranslate',
                    '.s-item__price',
                    '.price .notranslate',
                    '.prc',
                    '[class*="price"] .notranslate',
                    '[class*="sold"] .notranslate',
                    '.u-flL.condText .notranslate'
                ]

                for selector in price_selectors:
                    price_elem = await parent.query_selector(selector)
                    if price_elem:
                        price_text = await price_elem.text_content()
                        if price_text and ('$' in price_text or '£' in price_text or '€' in price_text):
                            # Extract price using regex
                            import re
                            price_match = re.search(r'[\$£€]?([0-9,]+\.?[0-9]*)', price_text)
                            if price_match:
                                try:
                                    price_str = price_match.group(1).replace(',', '')
                                    result['price'] = float(price_str)

                                    # Determine currency
                                    if '$' in price_text:
                                        result['currency'] = 'USD'
                                    elif '£' in price_text:
                                        result['currency'] = 'GBP'
                                    elif '€' in price_text:
                                        result['currency'] = 'EUR'

                                    logging.debug(f"Extracted price from context: {result['currency']} {result['price']}")
                                    break
                                except ValueError:
                                    continue

                # Try to find title elements with enhanced selectors
                title_selectors = [
                    '.s-item__title',
                    '.s-item__title span',
                    '.it-ttl',
                    'h3',
                    'h3 a',
                    '[class*="title"]',
                    'a[href*="itm/"]',
                    '.s-item__link',
                    '.s-item__wrapper .s-item__title',
                    '.s-item__detail .s-item__title'
                ]

                for selector in title_selectors:
                    title_elem = await parent.query_selector(selector)
                    if title_elem:
                        title_text = await title_elem.text_content()
                        if title_text and title_text.strip() and len(title_text.strip()) > 10:  # Require longer titles
                            # Clean up the title
                            clean_title = title_text.strip()
                            # Remove "New Listing" or similar prefixes
                            clean_title = re.sub(r'^(New Listing|SPONSORED)\s*', '', clean_title, flags=re.IGNORECASE)
                            if len(clean_title) > 10:  # Still long enough after cleaning
                                result['title'] = clean_title
                                logging.debug(f"Extracted title from {selector}: {clean_title[:50]}...")
                                break

                # Try to find sold date
                sold_selectors = [
                    '.s-item__title--tag',
                    '.s-item__subtitle',
                    '[class*="sold"]',
                    '.s-item__dynamic'
                ]

                for selector in sold_selectors:
                    date_elem = await parent.query_selector(selector)
                    if date_elem:
                        date_text = await date_elem.text_content()
                        if date_text and ('sold' in date_text.lower() or 'end' in date_text.lower()):
                            result['sold_date'] = date_text.strip()
                            break

            # Method 2: If no parent context found, try to extract from the broader page
            if result['price'] == 0.0:
                # Look for any price elements on the current page
                all_prices = await self.page.query_selector_all('.s-item__price .notranslate, .prc, [class*="price"] .notranslate')
                if all_prices and index < len(all_prices):
                    try:
                        price_elem = all_prices[index]
                        price_text = await price_elem.text_content()
                        if price_text:
                            import re
                            price_match = re.search(r'[\$£€]?([0-9,]+\.?[0-9]*)', price_text)
                            if price_match:
                                price_str = price_match.group(1).replace(',', '')
                                result['price'] = float(price_str)
                                if '$' in price_text:
                                    result['currency'] = 'USD'
                                logging.debug(f"Extracted price from page index {index}: {result['currency']} {result['price']}")
                    except (ValueError, IndexError):
                        pass

            # Method 3: Extract titles from all items on the page as fallback
            if not result['title']:
                # Get all titles on the page and match by index
                all_titles = await self.page.query_selector_all('.s-item__title, .it-ttl, h3 a[href*="itm/"]')
                if all_titles and index < len(all_titles):
                    try:
                        title_elem = all_titles[index]
                        title_text = await title_elem.text_content()
                        if title_text and len(title_text.strip()) > 10:
                            clean_title = title_text.strip()
                            clean_title = re.sub(r'^(New Listing|SPONSORED)\s*', '', clean_title, flags=re.IGNORECASE)
                            if len(clean_title) > 10:
                                result['title'] = clean_title
                                logging.debug(f"Extracted title from page index {index}: {clean_title[:50]}...")
                    except (IndexError, AttributeError):
                        pass

            # Method 4: Try extracting from link text
            if not result['title']:
                all_links = await self.page.query_selector_all('a[href*="itm/"]')
                if all_links and index < len(all_links):
                    try:
                        link_elem = all_links[index]
                        link_text = await link_elem.text_content()
                        if link_text and len(link_text.strip()) > 10:
                            clean_title = link_text.strip()
                            if len(clean_title) > 10:
                                result['title'] = clean_title
                                logging.debug(f"Extracted title from link {index}: {clean_title[:50]}...")
                    except (IndexError, AttributeError):
                        pass

            # Method 5: Extract from page title or meta information if available (last resort)
            if not result['title']:
                page_title = await self.page.title()
                if page_title and 'eBay' in page_title:
                    # Extract search term from title
                    if ' for sale' in page_title:
                        search_part = page_title.split(' for sale')[0]
                        if search_part and len(search_part) > 3:
                            result['title'] = f"{search_part} - Item {index + 1}"
                    elif '|' in page_title:
                        # Handle titles like "Pokemon Cards | eBay"
                        search_part = page_title.split('|')[0].strip()
                        if search_part and len(search_part) > 3:
                            result['title'] = f"{search_part} - Item {index + 1}"

            return result

        except Exception as e:
            logging.debug(f"Error extracting price from context for item {index}: {e}")
            return {
                'price': 0.0,
                'currency': 'USD',
                'title': f"eBay Item {index + 1}",
                'sold_date': 'Recent'
            }

    # Add the method to the class
    SoldListingMatcher._extract_price_from_page_context = _extract_price_from_page_context

# Apply the method addition
add_url_extraction_method()