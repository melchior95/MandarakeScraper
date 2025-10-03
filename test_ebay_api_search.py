#!/usr/bin/env python3
"""
Test eBay API search with a basic query for "Yura Kano photobook"
"""

import json
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mandarake_scraper import EbayAPI

def test_ebay_search():
    """Test eBay API search functionality"""

    client_id = None
    client_secret = None

    # Try to load credentials from user_settings.json first
    try:
        user_settings_path = Path("user_settings.json")
        if user_settings_path.exists():
            with open(user_settings_path, 'r') as f:
                user_settings = json.load(f)
                ebay_config = user_settings.get('ebay_api', {})
                client_id = ebay_config.get('client_id')
                client_secret = ebay_config.get('client_secret')
                if client_id and client_secret:
                    print(f"Found eBay credentials in: user_settings.json")
    except Exception as e:
        print(f"Could not load user_settings.json: {e}")

    # Fallback to config files
    if not client_id or not client_secret:
        config_files = list(Path("configs").glob("*.json"))
        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    if config.get('client_id') and config.get('client_secret'):
                        if config['client_id'] != "YOUR_EBAY_CLIENT_ID":
                            client_id = config['client_id']
                            client_secret = config['client_secret']
                            print(f"Found eBay credentials in: {config_file.name}")
                            break
            except:
                continue

    if not client_id or not client_secret:
        print("ERROR: No eBay API credentials found in user_settings.json or config files")
        print("Please add 'client_id' and 'client_secret' to user_settings.json under 'ebay_api'")
        return

    # Initialize eBay API
    print(f"\nInitializing eBay API...")
    api = EbayAPI(client_id, client_secret)

    # Test query
    query = "Yura Kano photobook"
    print(f"\nSearching eBay for: '{query}'")
    print("-" * 60)

    try:
        result = api.search_product(query)

        print(f"\nResults:")
        print(f"  Listings found: {result.get('ebay_listings', 0)}")
        print(f"  Average price: ${result.get('ebay_avg_price', 0):.2f}")
        print(f"  Sold count: {result.get('ebay_sold_count', 0)}")

        if 'ebay_error' in result:
            print(f"  Error: {result['ebay_error']}")
        else:
            print("\n[SUCCESS] eBay API search successful!")

    except Exception as e:
        print(f"\n[ERROR] eBay API search failed: {e}")

if __name__ == "__main__":
    test_ebay_search()
