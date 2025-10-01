#!/usr/bin/env python3
"""
Test script to verify eBay scraping with Scrapy
"""
import requests
from scrapy.http import HtmlResponse

def test_ebay_access():
    """Test if we can access eBay search results"""

    url = "https://www.ebay.com/sch/i.html?_nkw=pokemon+card&_sacat=0"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    print(f"Testing eBay access...")
    print(f"URL: {url}\n")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"Response size: {len(response.content)} bytes\n")

        # Check if we hit a challenge page
        if 'challenge' in response.url or 'captcha' in response.text.lower():
            print("[FAIL] eBay is showing a CAPTCHA/challenge page")
            print("This means eBay detected automated access.\n")
            return False

        # Try to parse with Scrapy selectors
        scrapy_response = HtmlResponse(url=response.url, body=response.content)

        # Test all selectors from the spider
        selectors_to_test = [
            '.s-item',
            '.sresult',
            '[data-testid="item"]',
            '.x-item',
            '.srp-results .s-item'
        ]

        print("Testing CSS selectors:")
        for selector in selectors_to_test:
            items = scrapy_response.css(selector)
            print(f"  {selector}: {len(items)} items found")

        # Check for item links
        links = scrapy_response.css('a[href*="/itm/"]::attr(href)').getall()
        print(f"\nProduct links found: {len(links)}")

        if links:
            print("\n[OK] Successfully found eBay listings!")
            print(f"Sample links:")
            for link in links[:3]:
                print(f"  - {link[:100]}...")
            return True
        else:
            print("\n[FAIL] No product listings found")
            # Save HTML for debugging
            with open('ebay_scrapy_debug.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("Saved HTML to ebay_scrapy_debug.html for inspection")
            return False

    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    success = test_ebay_access()
    exit(0 if success else 1)