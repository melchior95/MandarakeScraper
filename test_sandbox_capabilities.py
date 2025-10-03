#!/usr/bin/env python3
"""
Test what the eBay Sandbox API can actually do
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mandarake_scraper import EbayAPI

def test_sandbox():
    """Test sandbox capabilities"""

    # Load credentials from user_settings.json
    with open("user_settings.json", 'r') as f:
        user_settings = json.load(f)
        ebay_config = user_settings.get('ebay_api', {})
        client_id = ebay_config.get('client_id')
        client_secret = ebay_config.get('client_secret')

    print(f"Client ID: {client_id}")
    print(f"Is Sandbox: {'SBX' in client_id}")
    print()

    # Initialize API
    api = EbayAPI(client_id, client_secret)

    # Get access token
    try:
        token = api._get_access_token()
        print(f"[SUCCESS] Got access token: {token[:50]}...")
        print()
    except Exception as e:
        print(f"[ERROR] Failed to get token: {e}")
        return

    # Try a simple search
    import requests

    url = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
    }
    params = {
        'q': 'iPhone',
        'limit': 5
    }

    print("Testing Browse API search...")
    response = requests.get(url, headers=headers, params=params, timeout=30)

    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    print(f"Response Body:")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_sandbox()
