#!/usr/bin/env python3
"""
Debug what selectors are actually available in the Playwright browser
"""

import asyncio
import logging
from playwright.async_api import async_playwright

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def debug_playwright_selectors():
    """Debug what selectors work in Playwright browser"""

    async with async_playwright() as p:
        # Launch visible browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            url = "https://www.ebay.com/sch/i.html?_nkw=pokemon+card&_sacat=0&LH_Sold=1&LH_Complete=1&_ipg=25"
            print(f"Navigating to: {url}")

            # Navigate with longer timeout
            await page.goto(url, timeout=60000, wait_until='domcontentloaded')

            print("Page loaded! Analyzing selectors...")

            # Test various selectors
            test_selectors = [
                '.s-item',
                '.srp-result',
                '.s-item__wrapper',
                '.s-prefetch-image',
                '[data-view]',
                'img[src*="ebayimg"]',
                '.srp-results',
                '.srp-river-results'
            ]

            print("\n=== SELECTOR TEST RESULTS ===")

            for selector in test_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"✓ {selector:25} -> {len(elements):3d} elements")

                        # For image selectors, show first few URLs
                        if 'img' in selector and len(elements) > 0:
                            for i, img in enumerate(elements[:3]):
                                src = await img.get_attribute('src')
                                if src:
                                    print(f"   Image {i+1}: {src[:80]}...")
                    else:
                        print(f"✗ {selector:25} -> 0 elements")
                except Exception as e:
                    print(f"! {selector:25} -> Error: {e}")

            print(f"\n=== PAGE ANALYSIS ===")

            # Check page title
            title = await page.title()
            print(f"Page title: {title}")

            # Check if there are any eBay images at all
            all_images = await page.query_selector_all('img')
            ebay_images = []
            for img in all_images:
                src = await img.get_attribute('src')
                if src and 'ebayimg.com' in src:
                    ebay_images.append(src)

            print(f"Total images on page: {len(all_images)}")
            print(f"eBay images found: {len(ebay_images)}")

            if ebay_images:
                print("First 5 eBay image URLs:")
                for i, url in enumerate(ebay_images[:5]):
                    print(f"  {i+1}. {url[:80]}...")

            # Wait for user to inspect the page
            print(f"\n=== MANUAL INSPECTION ===")
            print("Check the browser window - can you see listing results?")
            input("Press Enter when ready to continue...")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_playwright_selectors())