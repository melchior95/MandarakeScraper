#!/usr/bin/env python3
"""
Debug eBay selectors to find the current HTML structure
"""

import sys
import logging
from browser_mimic import BrowserMimic
from bs4 import BeautifulSoup

def debug_ebay_selectors(search_term="pokemon card"):
    """Debug what selectors work on current eBay"""

    browser = BrowserMimic("test_ebay.pkl")

    url = f"https://www.ebay.com/sch/i.html?_nkw={search_term.replace(' ', '+')}&_sacat=0&LH_Sold=1&LH_Complete=1&_ipg=25"

    print(f"Testing eBay selectors for: {search_term}")
    print(f"URL: {url}")
    print()

    try:
        response = browser.get(url)

        if response.status_code != 200:
            print(f"HTTP Error: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        print(f"Response size: {len(response.text):,} characters")

        # Save the HTML for manual inspection
        with open('debug_ebay_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Saved full HTML to: debug_ebay_page.html")

        # Test various selectors that might contain listings
        test_selectors = [
            # Current eBay selectors (2024)
            '.s-item',
            '.srp-result',
            '.s-item__wrapper',
            '[data-view]',

            # Alternative selectors
            '.it-ttl',
            '.lvtitle',
            '.vip',
            '.item',

            # Container selectors
            '.srp-results',
            '.srp-river-results',
            '#ResultSetItems',

            # Image selectors
            '.s-item img',
            '.srp-result img',
            'img[src*="ebayimg"]',

            # Title selectors
            '.s-item__title',
            '.it-ttl a',
            'h3.s-item__title',

            # Price selectors
            '.s-item__price',
            '.notranslate',
            '.u-flL.condText'
        ]

        print("\n=== SELECTOR TEST RESULTS ===")

        for selector in test_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    print(f"✓ {selector:30} -> {len(elements):3d} elements")

                    # For the first few, show sample content
                    if len(elements) > 0 and selector in ['.s-item', '.srp-result', '.s-item__title', '.s-item__price']:
                        sample = elements[0].get_text().strip()[:60] if elements[0].get_text() else elements[0].get('src', '')[:60]
                        print(f"   Sample: {sample}...")

                else:
                    print(f"✗ {selector:30} -> 0 elements")
            except Exception as e:
                print(f"! {selector:30} -> Error: {e}")

        # Try to extract first few items manually
        print(f"\n=== MANUAL EXTRACTION TEST ===")

        # Find the most promising selector
        main_items = soup.select('.s-item')
        if not main_items:
            main_items = soup.select('.srp-result')

        if main_items:
            print(f"Found {len(main_items)} main items to analyze")

            for i, item in enumerate(main_items[:3]):
                print(f"\n--- Item {i+1} ---")

                # Try to extract title
                title_selectors = ['.s-item__title', '.it-ttl', 'h3', '.s-item__title span']
                title = "Not found"
                for ts in title_selectors:
                    title_elem = item.select_one(ts)
                    if title_elem:
                        title = title_elem.get_text().strip()[:80]
                        break

                print(f"Title: {title}")

                # Try to extract price
                price_selectors = ['.s-item__price', '.notranslate', '.u-flL']
                price = "Not found"
                for ps in price_selectors:
                    price_elem = item.select_one(ps)
                    if price_elem:
                        price = price_elem.get_text().strip()[:30]
                        break

                print(f"Price: {price}")

                # Try to extract image
                img_elem = item.select_one('img')
                if img_elem:
                    img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-original')
                    print(f"Image: {img_src[:80] if img_src else 'No src'}...")
                else:
                    print("Image: Not found")

        else:
            print("No main items found!")

            # Check what IS on the page
            print("\n=== PAGE CONTENT ANALYSIS ===")

            # Check for common elements
            common_checks = [
                ('body', 'Body tag'),
                ('.srp-results', 'Search results container'),
                ('.globalheader', 'eBay header'),
                ('.srp-controls', 'Search controls'),
                ('.srp-river-results', 'River results'),
                ('#srp-river-results', 'River results by ID')
            ]

            for selector, description in common_checks:
                elements = soup.select(selector)
                print(f"{description:25}: {'Found' if elements else 'Not found'}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        browser.cleanup()

    print(f"\nCheck debug_ebay_page.html to manually inspect the eBay page structure.")

if __name__ == '__main__':
    search_term = sys.argv[1] if len(sys.argv) > 1 else "pokemon card"
    debug_ebay_selectors(search_term)