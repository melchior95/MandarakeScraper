#!/usr/bin/env python3
"""
Test eBay API to see what detailed data we get for listings
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mandarake_scraper import EbayAPI

def test_detailed_response():
    """Test eBay API and display full response structure"""

    # Load credentials from user_settings.json
    with open("user_settings.json", 'r') as f:
        user_settings = json.load(f)
        ebay_config = user_settings.get('ebay_api', {})
        client_id = ebay_config.get('client_id')
        client_secret = ebay_config.get('client_secret')

    api = EbayAPI(client_id, client_secret)
    token = api._get_access_token()

    # Search for Yura Kano photobook
    import requests
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {
        'q': 'Yura Kano photobook',
        'limit': 5
    }

    response = requests.get(url, headers=headers, params=params, timeout=30)
    data = response.json()

    print("Full API Response:")
    print("=" * 80)
    print(json.dumps(data, indent=2))
    print("=" * 80)

    if 'itemSummaries' in data and data['itemSummaries']:
        print("\nFirst Item Details:")
        print("=" * 80)
        item = data['itemSummaries'][0]

        print(f"Title: {item.get('title', 'N/A')}")
        print(f"Item ID: {item.get('itemId', 'N/A')}")
        print(f"Price: {item.get('price', {})}")
        print(f"Condition: {item.get('condition', 'N/A')}")
        print(f"Image: {item.get('image', {})}")
        print(f"Thumbnail Images: {item.get('thumbnailImages', [])}")
        print(f"Item Web URL: {item.get('itemWebUrl', 'N/A')}")
        print(f"Shipping: {item.get('shippingOptions', [])}")
        print(f"Seller: {item.get('seller', {})}")
        print(f"Item Location: {item.get('itemLocation', {})}")

        # Check for sold date (might be in additional fields)
        print(f"\nAll available fields:")
        for key in item.keys():
            print(f"  - {key}")

if __name__ == "__main__":
    test_detailed_response()
