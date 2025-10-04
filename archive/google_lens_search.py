#!/usr/bin/env python3
"""
Google Lens Image Identification Module

This module provides functionality to identify products from images using Google Lens,
then search for those products on eBay sold listings.
"""

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from search_optimizer import SearchOptimizer


class GoogleLensSearcher:
    """Class for performing Google Lens image searches and product identification"""

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def identify_product_from_image(self, image_path: str) -> Dict:
        """
        Use Google Lens to identify a product from an image and extract potential names.

        Returns:
            Dict with 'product_names', 'descriptions', 'categories', 'confidence'
        """
        async with async_playwright() as p:
            # Launch browser with anti-detection settings
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-javascript-harmony-shipping'
                ]
            )
            page = await browser.new_page()

            # Set user agent and headers
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            })

            try:
                logging.info(f"[GOOGLE LENS] Starting product identification for: {image_path}")

                # Navigate to Google Lens with better error handling
                try:
                    await page.goto("https://lens.google.com/", wait_until="networkidle", timeout=45000)
                    await page.wait_for_timeout(2000)  # Give page time to fully load
                    logging.info("Successfully navigated to Google Lens")
                except Exception as nav_error:
                    logging.error(f"Failed to navigate to Google Lens: {nav_error}")
                    return {
                        'product_names': [],
                        'descriptions': [],
                        'categories': [],
                        'confidence': 0,
                        'error': f"Cannot access Google Lens: {str(nav_error)}"
                    }

                # Try multiple approaches to find and click the upload button
                upload_clicked = False
                upload_selectors = [
                    '[data-ved] [jsaction*="upload"]',
                    '[role="button"][aria-label*="upload"]',
                    '[aria-label*="Upload"]',
                    '.Gdd5U',  # Common Google upload button class
                    '[data-ved*="upload"]',
                    'button[aria-label*="search"]',
                    '.nDcEnd',  # Another potential class
                    '[jsaction*="upload"]'
                ]

                for selector in upload_selectors:
                    try:
                        upload_button = await page.wait_for_selector(selector, timeout=3000)
                        await upload_button.click()
                        logging.info(f"Upload button clicked using selector: {selector}")
                        upload_clicked = True
                        break
                    except Exception as e:
                        logging.debug(f"Upload selector {selector} failed: {e}")
                        continue

                if not upload_clicked:
                    # Try alternative: look for any file input and trigger it directly
                    try:
                        file_inputs = await page.query_selector_all('input[type="file"]')
                        if file_inputs:
                            await file_inputs[0].set_input_files(image_path)
                            upload_clicked = True
                            logging.info("Directly uploaded file to existing input")
                    except Exception as e:
                        logging.debug(f"Direct file input failed: {e}")

                if not upload_clicked:
                    return {
                        'product_names': [],
                        'descriptions': [],
                        'categories': [],
                        'confidence': 0,
                        'error': "Google Lens failed: Could not find upload button"
                    }

                # Upload the image (if not already done above)
                file_uploaded = False
                if upload_clicked:
                    try:
                        # Give time for the page to update after button click
                        await page.wait_for_timeout(2000)

                        # Try multiple approaches for file upload
                        upload_approaches = [
                            # Approach 1: Wait for new file input and upload
                            lambda: self._try_file_input_upload(page, image_path),
                            # Approach 2: Use page.set_input_files on any file input
                            lambda: self._try_direct_file_upload(page, image_path),
                            # Approach 3: Look for specific Google Lens file input patterns
                            lambda: self._try_lens_specific_upload(page, image_path)
                        ]

                        for i, approach in enumerate(upload_approaches, 1):
                            try:
                                logging.debug(f"Trying upload approach {i}...")
                                await approach()
                                file_uploaded = True
                                logging.info(f"File uploaded successfully using approach {i}")
                                break
                            except Exception as approach_error:
                                logging.debug(f"Upload approach {i} failed: {approach_error}")
                                continue

                        if not file_uploaded:
                            raise Exception("All file upload approaches failed")

                    except Exception as e:
                        logging.error(f"File input after button click failed: {e}")
                        return {
                            'product_names': [],
                            'descriptions': [],
                            'categories': [],
                            'confidence': 0,
                            'error': f"Google Lens file upload failed: {str(e)}"
                        }

                if not file_uploaded:
                    return {
                        'product_names': [],
                        'descriptions': [],
                        'categories': [],
                        'confidence': 0,
                        'error': "Google Lens upload failed: Could not upload image file"
                    }

                logging.info("Image uploaded to Google Lens, waiting for analysis...")

                # Wait for results to load
                await page.wait_for_timeout(5000)

                # Try to wait for search results
                try:
                    await page.wait_for_selector('[data-ved*="search"]', timeout=15000)
                except:
                    # Sometimes the selector is different, try alternative approach
                    await page.wait_for_timeout(3000)

                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')

                # Parse Google Lens results
                return await self._parse_lens_results(soup, page)

            except Exception as e:
                logging.error(f"Error during Google Lens search: {e}")
                return {
                    'product_names': [],
                    'descriptions': [],
                    'categories': [],
                    'confidence': 0,
                    'error': str(e)
                }
            finally:
                await browser.close()

    async def _parse_lens_results(self, soup: BeautifulSoup, page) -> Dict:
        """Parse Google Lens results to extract product information"""
        try:
            product_names = []
            descriptions = []
            categories = []

            # Try different selectors for Google Lens results
            text_selectors = [
                '[data-ved] [role="link"]',
                '.VwiC3b',
                '.r34K7c',
                '.OSrXXb',
                '.fP1Qef',
                '.PZPZlf',
                'h3',
                '[data-attrid] span',
                '.BNeawe'
            ]

            all_text_elements = []
            for selector in text_selectors:
                elements = soup.select(selector)
                all_text_elements.extend(elements)

            # Extract meaningful text
            for element in all_text_elements:
                text = element.get_text(strip=True)
                if text and len(text) > 3:  # Filter out very short text
                    # Clean up the text
                    text = re.sub(r'\s+', ' ', text)

                    # Categorize the text
                    if self._looks_like_product_name(text):
                        product_names.append(text)
                    elif self._looks_like_description(text):
                        descriptions.append(text)
                    elif self._looks_like_category(text):
                        categories.append(text)

            # Remove duplicates while preserving order
            product_names = list(dict.fromkeys(product_names))
            descriptions = list(dict.fromkeys(descriptions))
            categories = list(dict.fromkeys(categories))

            # Calculate confidence based on results found
            confidence = min(100, len(product_names) * 20 + len(descriptions) * 10 + len(categories) * 5)

            logging.info(f"[GOOGLE LENS] Found {len(product_names)} product names, {len(descriptions)} descriptions")

            return {
                'product_names': product_names[:10],  # Top 10 results
                'descriptions': descriptions[:5],      # Top 5 descriptions
                'categories': categories[:3],          # Top 3 categories
                'confidence': confidence
            }

        except Exception as e:
            logging.error(f"Error parsing Google Lens results: {e}")
            return {
                'product_names': [],
                'descriptions': [],
                'categories': [],
                'confidence': 0,
                'error': str(e)
            }

    def _looks_like_product_name(self, text: str) -> bool:
        """Determine if text looks like a product name"""
        # Product names are usually 3-100 characters, contain alphanumeric
        if len(text) < 3 or len(text) > 100:
            return False

        # Should contain letters and possibly numbers
        if not re.search(r'[a-zA-Z]', text):
            return False

        # Exclude common non-product phrases
        exclude_patterns = [
            r'^(see|view|more|images?|photos?|search|results?|about|related)$',
            r'^(copyright|©|\d{4}|inc\.?|ltd\.?|llc)$',
            r'^(click|tap|swipe|scroll)',
            r'^(price|cost|buy|shop|store)',
        ]

        for pattern in exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        return True

    def _looks_like_description(self, text: str) -> bool:
        """Determine if text looks like a product description"""
        return (len(text) > 20 and
                len(text) < 500 and
                ' ' in text and
                not text.startswith('http'))

    def _looks_like_category(self, text: str) -> bool:
        """Determine if text looks like a category"""
        categories_keywords = [
            'figure', 'toy', 'collectible', 'anime', 'manga', 'game',
            'book', 'cd', 'dvd', 'electronics', 'clothing', 'accessories'
        ]
        return (len(text) < 50 and
                any(keyword in text.lower() for keyword in categories_keywords))

    async def search_ebay_with_lens_results(self, image_path: str, days_back: int = 90, lazy_search: bool = False) -> Dict:
        """
        Complete workflow: Use Google Lens to identify product, then search eBay sold listings
        """
        # Step 1: Get product identification from Google Lens
        lens_results = await self.identify_product_from_image(image_path)

        if lens_results.get('error') or not lens_results.get('product_names'):
            return {
                'sold_count': 0,
                'median_price': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'prices': [],
                'lens_results': lens_results,
                'error': 'No product identification results from Google Lens'
            }

        # Step 2: Search eBay sold listings using the identified product names
        from mandarake_scraper import EbayAPI

        # Use a dummy eBay API instance for web scraping
        ebay_api = EbayAPI("", "")

        best_results = None
        best_count = 0

        # If lazy search is enabled, optimize the product names first
        search_terms = lens_results['product_names'][:3]
        if lazy_search:
            optimizer = SearchOptimizer()
            optimized_terms = []
            for name in search_terms:
                optimized = optimizer.optimize_search_term(name, lazy_mode=True)
                # Add both original and optimized terms
                optimized_terms.append(name)
                optimized_terms.extend(optimized['confidence_order'][:2])  # Top 2 optimized versions
            search_terms = list(dict.fromkeys(optimized_terms))  # Remove duplicates
            logging.info(f"[GOOGLE LENS LAZY] Expanded {len(lens_results['product_names'])} terms to {len(search_terms)} optimized variations")

        # Try the search terms (original or optimized)
        for product_name in search_terms[:5]:  # Limit to prevent too many searches
            try:
                logging.info(f"[GOOGLE LENS -> EBAY] Searching eBay for: '{product_name}'")

                results = ebay_api.search_sold_listings_web(product_name, days_back=days_back)

                if results['sold_count'] > best_count:
                    best_results = results
                    best_results['search_term'] = product_name
                    best_count = results['sold_count']

                # If we found good results, no need to try more
                if best_count >= 5:
                    break

            except Exception as e:
                logging.warning(f"Error searching eBay for '{product_name}': {e}")
                continue

        if best_results:
            best_results['lens_results'] = lens_results
            logging.info(f"[GOOGLE LENS -> EBAY] Best results using term: '{best_results.get('search_term')}' - {best_count} sold items")
            return best_results
        else:
            return {
                'sold_count': 0,
                'median_price': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'prices': [],
                'lens_results': lens_results,
                'error': 'No eBay results found for any identified product names'
            }

    async def _try_file_input_upload(self, page, image_path: str):
        """Approach 1: Wait for file input to appear and upload"""
        file_input = await page.wait_for_selector('input[type="file"]', timeout=5000)
        await file_input.set_input_files(image_path)

    async def _try_direct_file_upload(self, page, image_path: str):
        """Approach 2: Use page.set_input_files directly"""
        await page.set_input_files('input[type="file"]', image_path)

    async def _try_lens_specific_upload(self, page, image_path: str):
        """Approach 3: Try Google Lens specific selectors"""
        lens_file_selectors = [
            'input[type="file"][accept*="image"]',
            'input[accept*="image/*"]',
            '[data-ved] input[type="file"]',
            '.nH input[type="file"]',
            'form input[type="file"]'
        ]

        for selector in lens_file_selectors:
            try:
                await page.wait_for_selector(selector, timeout=2000)
                await page.set_input_files(selector, image_path)
                return  # Success
            except:
                continue

        raise Exception("No Google Lens file input found")


# Sync wrapper functions
def identify_product_sync(image_path: str, headless: bool = True) -> Dict:
    """Synchronous wrapper for Google Lens product identification"""
    searcher = GoogleLensSearcher(headless=headless)
    return asyncio.run(searcher.identify_product_from_image(image_path))

def search_ebay_with_lens_sync(image_path: str, days_back: int = 90, headless: bool = True, lazy_search: bool = False) -> Dict:
    """Synchronous wrapper for complete Google Lens -> eBay workflow"""
    searcher = GoogleLensSearcher(headless=headless)
    return asyncio.run(searcher.search_ebay_with_lens_results(image_path, days_back, lazy_search))


if __name__ == '__main__':
    # Example usage:
    # python google_lens_search.py "path/to/image.jpg" [--identify-only]
    import sys

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        identify_only = "--identify-only" in sys.argv

        if identify_only:
            print(f"Identifying product from image: {image_path}")
            result = identify_product_sync(image_path, headless=False)
            print(f"Google Lens Results:")
            print(f"  Confidence: {result['confidence']}%")
            print(f"  Product names: {result['product_names']}")
            print(f"  Descriptions: {result['descriptions']}")
            print(f"  Categories: {result['categories']}")
        else:
            print(f"Complete workflow - Image identification + eBay search: {image_path}")
            result = search_ebay_with_lens_sync(image_path, headless=False)
            print(f"Final Results:")
            print(f"  Search term used: {result.get('search_term', 'N/A')}")
            print(f"  Sold items found: {result['sold_count']}")
            if result['sold_count'] > 0:
                print(f"  Price range: ${result['min_price']:.2f} - ${result['max_price']:.2f}")
                print(f"  Median price: ${result['median_price']:.2f}")
            print(f"  Google Lens confidence: {result.get('lens_results', {}).get('confidence', 0)}%")
    else:
        print("Usage:")
        print("  python google_lens_search.py <image_path>                  # Full workflow")
        print("  python google_lens_search.py <image_path> --identify-only  # Google Lens only")