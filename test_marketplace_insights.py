#!/usr/bin/env python3
"""
Test if we have access to eBay Marketplace Insights API for sold listings
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mandarake_scraper import EbayAPI

def test_marketplace_insights():
    """Test Marketplace Insights API access"""

    # Load credentials from user_settings.json
    with open("user_settings.json", 'r') as f:
        user_settings = json.load(f)
        ebay_config = user_settings.get('ebay_api', {})
        client_id = ebay_config.get('client_id')
        client_secret = ebay_config.get('client_secret')

    api = EbayAPI(client_id, client_secret)
    token = api._get_access_token()

    # Try Marketplace Insights API
    import requests

    url = "https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search"

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    params = {
        'q': 'iPhone',
        'limit': 5
    }

    print("Testing Marketplace Insights API...")
    print(f"URL: {url}")
    print(f"Query: {params['q']}")
    print()

    response = requests.get(url, headers=headers, params=params, timeout=30)

    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))

    if response.status_code == 403:
        print("\n[ERROR] Access denied - This API requires special approval from eBay")
        print("The Marketplace Insights API is restricted to eBay Business partners only.")
        print("\nYou will need to continue using Scrapy for sold listings.")
        return False
    elif response.status_code == 200:
        print("\n[SUCCESS] You have access to Marketplace Insights API!")
        return True
    else:
        print(f"\n[ERROR] Unexpected response code: {response.status_code}")
        return False

if __name__ == "__main__":
    test_marketplace_insights()
