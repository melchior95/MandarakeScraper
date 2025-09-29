#!/usr/bin/env python3
"""
Direct test of eBay access to see what's being returned
"""

import logging
from browser_mimic import BrowserMimic
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_ebay_direct():
    """Test direct eBay access and see what we get"""

    browser = BrowserMimic("test_ebay.pkl")

    # Test a simple search that should have results
    test_urls = [
        "https://www.ebay.com/sch/i.html?_nkw=pokemon+card&_sacat=0&LH_Sold=1&LH_Complete=1&_ipg=25",
        "https://www.ebay.com/sch/i.html?_nkw=nintendo+switch&_sacat=0&LH_Sold=1&LH_Complete=1&_ipg=25",
        "https://www.ebay.com/sch/i.html?_nkw=iphone&_sacat=0&LH_Sold=1&LH_Complete=1&_ipg=25"
    ]

    for i, test_url in enumerate(test_urls, 1):
        print(f"\n=== TEST {i}: {test_url.split('_nkw=')[1].split('&')[0]} ===")

        try:
            response = browser.get(test_url)

            print(f"Status code: {response.status_code}")
            print(f"Response size: {len(response.text):,} characters")

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Check page title
                title = soup.find('title')
                if title:
                    print(f"Page title: {title.get_text()[:100]}...")

                # Check for blocking indicators
                page_text = response.text.lower()
                blocking_indicators = ['blocked', 'captcha', 'robot', 'automation', 'verify you are human']
                found_indicators = [indicator for indicator in blocking_indicators if indicator in page_text]

                if found_indicators:
                    print(f"⚠️  Blocking indicators found: {found_indicators}")
                else:
                    print("✅ No obvious blocking indicators")

                # Try to find listings
                item_selectors = ['.s-item', '.srp-result', '.it-ttl', '.lvtitle']

                for selector in item_selectors:
                    items = soup.select(selector)
                    if items:
                        print(f"✅ Found {len(items)} items with selector: {selector}")

                        # Check first item for image
                        first_item = items[0]
                        img = first_item.select_one('img')
                        if img:
                            img_src = img.get('src') or img.get('data-src')
                            print(f"   First item image: {img_src[:80] if img_src else 'No src'}...")

                        # Check first item for title
                        title_selectors = ['.s-item__title', '.it-ttl', 'h3', 'a']
                        for title_sel in title_selectors:
                            title_elem = first_item.select_one(title_sel)
                            if title_elem:
                                print(f"   First item title: {title_elem.get_text()[:60]}...")
                                break

                        break
                else:
                    print("❌ No items found with any selector")

                    # Check for results container
                    results_containers = soup.select('.srp-results, .listingscnt, .srp-river-results, #ResultSetItems')
                    if results_containers:
                        print(f"   Found results containers: {len(results_containers)}")
                    else:
                        print("   No results containers found")

                # Save the HTML for manual inspection
                with open(f'debug_ebay_response_{i}.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"   Saved HTML to: debug_ebay_response_{i}.html")

            else:
                print(f"❌ HTTP error: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {e}")

        # Stop after first successful test to avoid too many requests
        if response.status_code == 200:
            break

    browser.cleanup()

    print(f"\n=== SUMMARY ===")
    print("Check the saved HTML files to see what eBay is actually returning.")
    print("Look for:")
    print("- Blocking messages or CAPTCHAs")
    print("- Different HTML structure than expected")
    print("- Empty search results")

if __name__ == '__main__':
    test_ebay_direct()