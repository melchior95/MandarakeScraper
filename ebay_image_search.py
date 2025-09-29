import asyncio
from playwright.async_api import async_playwright
import logging
import statistics
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from search_optimizer import SearchOptimizer
import os
from pathlib import Path

async def search_by_image_web(image_path: str) -> str:
    """
    Performs a reverse image search on eBay using Playwright.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            logging.info("Navigating to eBay for image search...")
            await page.goto("https://www.ebay.com/vis/imgUpload")

            # Upload the image
            logging.info(f"Uploading image: {image_path}")
            await page.set_input_files('input[type="file"]', image_path)

            # Wait for the results to load
            logging.info("Waiting for search results...")
            await page.wait_for_url("**/sch/**", timeout=30000)

            results_url = page.url
            logging.info(f"Found results URL: {results_url}")
            return results_url

        except Exception as e:
            logging.error(f"Error during eBay image search: {e}")
            return f"https://www.ebay.com/sch/i.html?_nkw=Error+searching+for+image"
        finally:
            await browser.close()

async def search_sold_listings_by_image(image_path: str, days_back: int = 90, lazy_search: bool = False) -> Dict:
    """
    Search for sold listings on eBay by uploading an image and return price analysis data.
    """
    async with async_playwright() as p:
        # Launch browser with anti-detection settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Speed up loading
                '--disable-javascript-harmony-shipping',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows'
            ]
        )
        page = await browser.new_page()

        # Set user agent and other headers to look more like a real browser
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        try:
            logging.info(f"[EBAY IMAGE SEARCH] Starting image search for sold listings: {image_path}")

            # Navigate to eBay image search with better error handling
            try:
                logging.info("Attempting to navigate to eBay image upload page...")
                await page.goto("https://www.ebay.com/vis/imgUpload", wait_until="networkidle", timeout=45000)
                logging.info("Successfully navigated to eBay image upload page")

                # Debug: Check what page we actually landed on
                current_url = page.url
                page_title = await page.title()
                logging.info(f"Current URL: {current_url}")
                logging.info(f"Page title: {page_title}")

                # Check if we're being redirected or blocked
                if "blocked" in page_title.lower() or "error" in page_title.lower():
                    logging.warning(f"Possible blocking detected - Page title: {page_title}")

            except Exception as nav_error:
                logging.error(f"Failed to navigate to eBay image upload page: {nav_error}")
                return {
                    'sold_count': 0,
                    'median_price': 0,
                    'avg_price': 0,
                    'min_price': 0,
                    'max_price': 0,
                    'price_range': '$0.00 - $0.00',
                    'items': [],
                    'search_method': 'navigation_failed',
                    'error': f"eBay is blocking automated access or is unavailable. Error: {str(nav_error)}"
                }

            # Upload the image with better error handling and multiple selector attempts
            try:
                # Try multiple selectors for the file input
                file_input_selectors = [
                    'input[type="file"]',
                    'input[accept*="image"]',
                    '#fileInput',
                    '.fileInput',
                    '[data-testid="file-input"]'
                ]

                # Debug: Log what elements are actually on the page
                all_inputs = await page.query_selector_all('input')
                logging.info(f"Found {len(all_inputs)} input elements on page")

                for i, input_elem in enumerate(all_inputs[:5]):  # Check first 5
                    input_type = await input_elem.get_attribute('type')
                    input_id = await input_elem.get_attribute('id')
                    input_class = await input_elem.get_attribute('class')
                    logging.debug(f"Input {i}: type='{input_type}', id='{input_id}', class='{input_class}'")

                file_input_found = False
                for selector in file_input_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        await page.set_input_files(selector, image_path, timeout=30000)
                        logging.info(f"Image uploaded successfully using selector: {selector}")
                        file_input_found = True
                        break
                    except Exception as selector_error:
                        logging.debug(f"Selector {selector} failed: {selector_error}")
                        continue

                if not file_input_found:
                    # Final debug: Save page content for analysis
                    page_content = await page.content()
                    logging.debug(f"Page HTML length: {len(page_content)} characters")
                    if "captcha" in page_content.lower():
                        raise Exception("eBay is showing CAPTCHA - automated access blocked")
                    elif "robot" in page_content.lower() or "bot" in page_content.lower():
                        raise Exception("eBay has detected automated access")
                    else:
                        raise Exception("No file input found - eBay may have changed their interface")

                # Give time for upload processing
                await page.wait_for_timeout(3000)

            except Exception as upload_error:
                error_msg = str(upload_error)
                logging.error(f"Image upload failed: {error_msg}")

                # Provide helpful guidance based on the error
                if "captcha" in error_msg.lower():
                    helpful_msg = "eBay is requiring CAPTCHA verification. Try using the regular eBay analysis with search terms instead."
                elif "robot" in error_msg.lower() or "bot" in error_msg.lower():
                    helpful_msg = "eBay has detected automated access. Consider using manual image search on eBay.com or try the text-based analysis."
                elif "timeout" in error_msg.lower():
                    helpful_msg = "eBay is not responding. Check your internet connection or try again later."
                elif "no file input" in error_msg.lower():
                    helpful_msg = "eBay has changed their image upload interface. Use text-based search or manual eBay analysis instead."
                else:
                    helpful_msg = "Try using the regular eBay analysis with product titles instead of image search."

                return {
                    'sold_count': 0,
                    'median_price': 0,
                    'avg_price': 0,
                    'min_price': 0,
                    'max_price': 0,
                    'price_range': '$0.00 - $0.00',
                    'items': [],
                    'search_method': 'failed_upload',
                    'error': f"eBay image search unavailable: {error_msg}",
                    'suggestion': helpful_msg
                }

            # Wait for the search results to load with longer timeout
            try:
                await page.wait_for_url("**/sch/**", timeout=45000)
            except Exception as url_wait_error:
                logging.warning(f"URL change timeout: {url_wait_error}, checking current page...")
                # Sometimes eBay doesn't change URL but shows results on same page
                await page.wait_for_timeout(5000)  # Give extra time
            current_url = page.url
            logging.info(f"Search results loaded: {current_url}")

            # Modify URL to show sold listings only
            if "&LH_Sold=1" not in current_url:
                sold_url = current_url + "&LH_Sold=1&_ipg=240"  # Add sold filter and max items per page
                await page.goto(sold_url, wait_until="networkidle")
                logging.info(f"Navigated to sold listings: {sold_url}")

            # Wait for sold listings to load
            await page.wait_for_timeout(3000)

            # Get page content for parsing
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Parse sold listings data
            initial_results = await _parse_sold_listings_data(soup, page)

            # If lazy search is enabled and we got poor results, try optimized text searches
            if lazy_search and initial_results['sold_count'] < 3:
                logging.info("[LAZY SEARCH] Initial image search yielded few results, trying optimized text searches...")
                text_results = await _try_lazy_text_searches(page, image_path)
                if text_results['sold_count'] > initial_results['sold_count']:
                    logging.info(f"[LAZY SEARCH] Text search found better results: {text_results['sold_count']} vs {initial_results['sold_count']}")
                    text_results['search_method'] = 'lazy_text_search'
                    return text_results
                else:
                    initial_results['search_method'] = 'image_search'
                    return initial_results
            else:
                initial_results['search_method'] = 'image_search'
                return initial_results

        except Exception as e:
            logging.error(f"Error during eBay image search for sold listings: {e}")
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
            await browser.close()

async def _parse_sold_listings_data(soup: BeautifulSoup, page) -> Dict:
    """Parse sold listings data from eBay search results"""
    try:
        # eBay sold listings selectors (updated for 2025)
        item_selectors = [
            'div.s-item',
            '.s-item',
            '.srp-results .s-item',
            'li.s-item'
        ]

        items = []
        for selector in item_selectors:
            items = soup.select(selector)
            if len(items) > 5:  # Found reasonable number of items
                break

        if not items:
            logging.warning("No sold listings found in search results")
            return {
                'sold_count': 0,
                'median_price': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'prices': []
            }

        prices = []
        listings_data = []

        for item in items:
            try:
                # Extract price
                price_selectors = [
                    '.s-item__price',
                    '.notranslate',
                    '.item__price',
                    '.price'
                ]

                price_element = None
                for price_sel in price_selectors:
                    price_element = item.select_one(price_sel)
                    if price_element:
                        break

                if not price_element:
                    continue

                price_text = price_element.get_text(strip=True)

                # Extract numeric price
                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))
                    prices.append(price)

                    # Extract additional data
                    title_elem = item.select_one('.s-item__title') or item.select_one('.it-ttl')
                    title = title_elem.get_text(strip=True) if title_elem else "Unknown"

                    # Extract sold date if available
                    date_elem = item.select_one('.s-item__ended-date') or item.select_one('.sold-date')
                    sold_date = date_elem.get_text(strip=True) if date_elem else ""

                    # Extract condition if available
                    condition_elem = item.select_one('.s-item__subtitle') or item.select_one('.condition')
                    condition = condition_elem.get_text(strip=True) if condition_elem else ""

                    listings_data.append({
                        'title': title[:100],  # Truncate for readability
                        'price': price,
                        'sold_date': sold_date,
                        'condition': condition
                    })

            except Exception as e:
                logging.debug(f"Error parsing individual item: {e}")
                continue

        if not prices:
            return {
                'sold_count': 0,
                'median_price': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'prices': [],
                'listings': []
            }

        # Calculate statistics
        prices.sort()

        result = {
            'sold_count': len(prices),
            'median_price': round(statistics.median(prices), 2),
            'avg_price': round(sum(prices) / len(prices), 2),
            'min_price': round(min(prices), 2),
            'max_price': round(max(prices), 2),
            'prices': prices,
            'listings': listings_data[:10]  # Return top 10 for reference
        }

        logging.info(f"[EBAY IMAGE SEARCH] Found {len(prices)} sold listings, median price: ${result['median_price']}")
        return result

    except Exception as e:
        logging.error(f"Error parsing sold listings data: {e}")
        return {
            'sold_count': 0,
            'median_price': 0,
            'avg_price': 0,
            'min_price': 0,
            'max_price': 0,
            'prices': [],
            'error': str(e)
        }

async def _try_lazy_text_searches(page, image_path: str) -> Dict:
    """
    Try text-based searches using optimized terms when image search yields poor results
    """
    try:
        # First, try to extract any visible text from the current page results
        # This could give us clues about what the image represents
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # Look for product titles or descriptions that might give us search terms
        title_elements = soup.select('.s-item__title, .it-ttl, h3')
        search_terms = []

        for elem in title_elements[:5]:  # Only check first few
            text = elem.get_text(strip=True)
            if text and len(text) > 10:  # Skip very short titles
                search_terms.append(text)

        if not search_terms:
            # Fallback: extract terms from the URL or use generic terms
            current_url = page.url
            url_terms = re.findall(r'_nkw=([^&]+)', current_url)
            if url_terms:
                search_terms = [url_terms[0].replace('+', ' ')]
            else:
                # Last resort: use very generic terms
                search_terms = ["japanese collectible", "figure model", "photo book"]

        # Use SearchOptimizer to create better search terms
        optimizer = SearchOptimizer()
        best_results = None
        best_count = 0

        for original_term in search_terms[:3]:  # Try top 3 terms
            try:
                # Get optimized search variations
                optimized = optimizer.optimize_search_term(original_term, lazy_mode=True)
                progressive_terms = optimized['confidence_order'][:3]  # Try top 3 optimized versions

                for search_term in progressive_terms:
                    logging.info(f"[LAZY SEARCH] Trying optimized term: '{search_term}'")

                    # Navigate to text-based search with sold filter
                    search_url = f"https://www.ebay.com/sch/i.html?_nkw={search_term.replace(' ', '+')}&LH_Sold=1&_ipg=240"
                    await page.goto(search_url, wait_until="networkidle")
                    await page.wait_for_timeout(2000)

                    # Parse results
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    results = await _parse_sold_listings_data(soup, page)

                    if results['sold_count'] > best_count:
                        best_results = results
                        best_results['search_term_used'] = search_term
                        best_count = results['sold_count']

                        # If we found good results (5+ items), stop searching
                        if best_count >= 5:
                            break

                # If we found good results, stop trying other original terms
                if best_count >= 5:
                    break

            except Exception as e:
                logging.warning(f"Error trying lazy search with term '{original_term}': {e}")
                continue

        if best_results:
            logging.info(f"[LAZY SEARCH] Best text search results: {best_count} items using term '{best_results.get('search_term_used')}'")
            return best_results
        else:
            return {
                'sold_count': 0,
                'median_price': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'prices': [],
                'error': 'No results found with lazy text search'
            }

    except Exception as e:
        logging.error(f"Error during lazy text search: {e}")
        return {
            'sold_count': 0,
            'median_price': 0,
            'avg_price': 0,
            'min_price': 0,
            'max_price': 0,
            'prices': [],
            'error': str(e)
        }


def run_ebay_image_search(image_path: str) -> str:
    """
    Sync wrapper for the async search_by_image_web function.
    """
    return asyncio.run(search_by_image_web(image_path))

def run_sold_listings_image_search(image_path: str, days_back: int = 90, lazy_search: bool = False) -> Dict:
    """
    Sync wrapper for the async search_sold_listings_by_image function.
    """
    return asyncio.run(search_sold_listings_by_image(image_path, days_back, lazy_search))

if __name__ == '__main__':
    # Example usage:
    # python ebay_image_search.py "path/to/your/image.jpg" [--sold]
    import sys

    if len(sys.argv) > 1:
        image_to_search = sys.argv[1]
        use_sold_search = "--sold" in sys.argv

        if use_sold_search:
            print(f"Searching for sold listings by image: {image_to_search}")
            result = run_sold_listings_image_search(image_to_search)
            print(f"Sold listings analysis:")
            print(f"  Found: {result['sold_count']} sold items")
            print(f"  Price range: ${result['min_price']:.2f} - ${result['max_price']:.2f}")
            print(f"  Median price: ${result['median_price']:.2f}")
            print(f"  Average price: ${result['avg_price']:.2f}")
            if result.get('listings'):
                print("\nSample listings:")
                for i, listing in enumerate(result['listings'][:3], 1):
                    print(f"  {i}. {listing['title']} - ${listing['price']:.2f}")
        else:
            print(f"Searching for image: {image_to_search}")
            url = run_ebay_image_search(image_to_search)
            print(f"Results URL: {url}")
    else:
        print("Usage:")
        print("  python ebay_image_search.py <image_path>          # Regular image search")
        print("  python ebay_image_search.py <image_path> --sold   # Sold listings analysis")
