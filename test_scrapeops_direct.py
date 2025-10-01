#!/usr/bin/env python3
"""
Test ScrapeOps API directly to see what response we get
"""
import requests

API_KEY = '2672f764-7b8b-4f8a-a120-1409fa0d527b'
TARGET_URL = 'https://www.ebay.com/sch/i.html?_nkw=pokemon+card'

# Build ScrapeOps proxy URL
proxy_url = f'https://proxy.scrapeops.io/v1/?api_key={API_KEY}&url={TARGET_URL}'

print("=" * 70)
print("Testing ScrapeOps Proxy API")
print("=" * 70)
print(f"\nTarget URL: {TARGET_URL}")
print(f"API Key: {API_KEY}")
print(f"\nFull Proxy URL: {proxy_url[:100]}...")
print("\nMaking request...\n")

try:
    response = requests.get(
        proxy_url,
        timeout=30,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

    print(f"\nResponse Size: {len(response.content)} bytes")

    if response.status_code == 403:
        print("\n[FAIL] Got 403 Forbidden from ScrapeOps")
        print("\nResponse content:")
        print(response.text[:500])
        print("\n\nPossible reasons:")
        print("1. API key doesn't have access to eBay (check ScrapeOps dashboard)")
        print("2. Free tier doesn't support eBay scraping")
        print("3. Need to upgrade to paid plan")
        print("4. API key might be invalid or expired")
        print("\nCheck your account at: https://scrapeops.io/app/")

    elif response.status_code == 200:
        print("\n[OK] ScrapeOps proxy worked!")

        # Check if we got actual eBay content
        if 'ebay' in response.text.lower():
            print("[OK] Response contains eBay content")

            # Check for listings
            if 's-item' in response.text:
                print("[OK] Found eBay listing elements in HTML")
            else:
                print("[WARN] No eBay listing elements found - might be challenge page")
        else:
            print("[WARN] Response doesn't contain eBay content")

        # Save for inspection
        with open('scrapeops_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\nSaved response to: scrapeops_response.html")
    else:
        print(f"\n[WARN] Unexpected status code: {response.status_code}")
        print(response.text[:500])

except requests.exceptions.Timeout:
    print("[ERROR] Request timed out")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 70)