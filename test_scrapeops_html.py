#!/usr/bin/env python3
"""
Fetch eBay HTML via ScrapeOps to inspect the structure
"""
import requests

API_KEY = 'f3106dda-ac3c-4a67-badf-e95985d50a73'
TARGET_URL = 'https://www.ebay.com/sch/i.html?_nkw=pokemon+card'

proxy_url = f'https://proxy.scrapeops.io/v1/?api_key={API_KEY}&url={TARGET_URL}&country=us'

print("Fetching eBay HTML via ScrapeOps...")

response = requests.get(proxy_url, timeout=30)

print(f"Status: {response.status_code}")
print(f"Size: {len(response.content)} bytes")

if response.status_code == 200:
    with open('scrapeops_ebay.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("\nSaved HTML to: scrapeops_ebay.html")

    # Check for common eBay selectors
    selectors_to_check = [
        '.s-item',
        '.srp-results',
        'li[data-viewport]',
        '.s-item__title',
        '[class*="item"]'
    ]

    print("\nChecking selectors:")
    for selector in selectors_to_check:
        count = response.text.count(selector.split('[')[0].strip('.'))
        print(f"  {selector}: ~{count} occurrences")

    # Look for item links
    itm_count = response.text.count('/itm/')
    print(f"\n'/itm/' product links: {itm_count}")

    print("\nInspect scrapeops_ebay.html to see the actual HTML structure")
else:
    print(f"Error: {response.status_code}")
    print(response.text[:500])