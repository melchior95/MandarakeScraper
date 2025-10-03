"""
Test script to check if we can scrape Yahoo Auction Japan using ScrapeOps
"""
import requests
from bs4 import BeautifulSoup

# ScrapeOps API key
SCRAPEOPS_API_KEY = 'f3106dda-ac3c-4a67-badf-e95985d50a73'

# Yahoo Auction URL to test
test_url = 'https://auctions.yahoo.co.jp/jp/auction/t1201146949'

# Test different bypass configurations
test_configs = [
    {
        'name': 'No Bypass',
        'params': {
            'api_key': SCRAPEOPS_API_KEY,
            'url': test_url,
        }
    },
    {
        'name': 'Generic Level 1',
        'params': {
            'api_key': SCRAPEOPS_API_KEY,
            'url': test_url,
            'bypass': 'generic_level_1',
        }
    },
    {
        'name': 'Generic Level 2',
        'params': {
            'api_key': SCRAPEOPS_API_KEY,
            'url': test_url,
            'bypass': 'generic_level_2',
        }
    },
    {
        'name': 'Generic Level 3',
        'params': {
            'api_key': SCRAPEOPS_API_KEY,
            'url': test_url,
            'bypass': 'generic_level_3',
        }
    },
    {
        'name': 'With JS Rendering',
        'params': {
            'api_key': SCRAPEOPS_API_KEY,
            'url': test_url,
            'render_js': 'true',
            'bypass': 'generic_level_2',
        }
    },
]

print("Testing Yahoo Auction scraping with ScrapeOps...\n")

for config in test_configs:
    print(f"Testing: {config['name']}")
    print("=" * 60)

    try:
        response = requests.get(
            'https://proxy.scrapeops.io/v1/',
            params=config['params'],
            timeout=30
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response Length: {len(response.text)} chars")

        # Parse and check for key content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for auction title
        title = soup.find('h1')
        if title:
            print(f"Title Found: {title.get_text(strip=True)[:100]}")
        else:
            print("Title: NOT FOUND")

        # Look for price
        price_indicators = ['円', '¥', 'JPY', '現在価格']
        has_price = any(indicator in response.text for indicator in price_indicators)
        print(f"Has Price Data: {has_price}")

        # Look for age gate
        has_age_gate = '18歳未満' in response.text or 'age verification' in response.text.lower()
        print(f"Age Gate Present: {has_age_gate}")

        # Check for bot detection
        bot_indicators = ['robot', 'bot detection', 'captcha', 'blocked']
        has_bot_detection = any(indicator in response.text.lower() for indicator in bot_indicators)
        print(f"Bot Detection: {has_bot_detection}")

        # Save sample HTML for inspection
        filename = f"yahoo_test_{config['name'].replace(' ', '_').lower()}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Saved to: {filename}")

    except Exception as e:
        print(f"ERROR: {e}")

    print("\n")

print("Testing complete!")
