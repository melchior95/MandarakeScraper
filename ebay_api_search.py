"""
eBay API Search - Production API wrapper for searching active listings
Maps eBay Browse API response to Scrapy-compatible format
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from mandarake_scraper import EbayAPI


def run_ebay_api_search(query: str, max_results: int = 50) -> List[Dict]:
    """
    Search eBay using official Browse API and return results

    NOTE: This searches ACTIVE listings only (not sold listings).
    For sold listings, use the Scrapy method instead.

    Args:
        query: Search query
        max_results: Maximum number of results to fetch (up to 200)

    Returns:
        List of dictionaries containing eBay data in Scrapy-compatible format
    """

    # Load credentials from user_settings.json
    try:
        user_settings_path = Path(__file__).parent / "user_settings.json"
        if not user_settings_path.exists():
            print("[eBay API ERROR] user_settings.json not found")
            return []

        with open(user_settings_path, 'r') as f:
            user_settings = json.load(f)
            ebay_config = user_settings.get('ebay_api', {})
            client_id = ebay_config.get('client_id')
            client_secret = ebay_config.get('client_secret')

        if not client_id or not client_secret:
            print("[eBay API ERROR] No credentials in user_settings.json")
            return []

    except Exception as e:
        print(f"[eBay API ERROR] Failed to load credentials: {e}")
        return []

    # Initialize API
    api = EbayAPI(client_id, client_secret)

    if not api.is_configured():
        print("[eBay API ERROR] API not properly configured")
        return []

    try:
        # Get access token
        token = api._get_access_token()

        # Determine API URL based on credentials
        if 'SBX' in client_id:
            base_url = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
        else:
            base_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

        import requests

        results = []
        offset = 0
        limit_per_request = min(50, max_results)  # API max is 200, but fetch in batches

        print(f"[eBay API] Searching for: '{query}' (max {max_results} results)")

        while len(results) < max_results:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            params = {
                'q': query[:80],  # Limit query length
                'limit': min(limit_per_request, max_results - len(results)),
                'offset': offset
            }

            response = requests.get(base_url, headers=headers, params=params, timeout=30)

            if response.status_code != 200:
                print(f"[eBay API ERROR] Request failed with status {response.status_code}")
                if response.status_code == 403:
                    print("[eBay API ERROR] Access denied - check your credentials")
                break

            data = response.json()
            items = data.get('itemSummaries', [])

            if not items:
                print(f"[eBay API] No more results (fetched {len(results)} total)")
                break

            # Convert each item to Scrapy-compatible format
            for item in items:
                converted = _convert_api_item_to_scrapy_format(item, query)
                if converted:
                    results.append(converted)

            print(f"[eBay API] Fetched {len(items)} items (total: {len(results)})")

            # Check if there are more results
            if 'next' not in data or len(results) >= max_results:
                break

            offset += limit_per_request

        print(f"[eBay API] Successfully fetched {len(results)} items")
        return results

    except Exception as e:
        print(f"[eBay API ERROR] {e}")
        import traceback
        traceback.print_exc()
        return []


def _convert_api_item_to_scrapy_format(item: Dict, query: str) -> Optional[Dict]:
    """
    Convert eBay Browse API item format to Scrapy-compatible format

    Args:
        item: Raw item from eBay Browse API
        query: Original search query

    Returns:
        Dictionary in Scrapy format, or None if conversion fails
    """
    try:
        result = {}

        # Basic info
        result['product_title'] = item.get('title', '')
        result['product_url'] = item.get('itemWebUrl', '')
        result['product_id'] = item.get('legacyItemId', '')
        result['listing_id'] = result['product_id']

        # Price
        price_obj = item.get('price', {})
        price_value = price_obj.get('value', '0')
        currency = price_obj.get('currency', 'USD')
        result['current_price'] = f"${price_value}" if currency == 'USD' else f"{price_value} {currency}"

        # Shipping
        shipping_options = item.get('shippingOptions', [])
        if shipping_options:
            shipping_cost_obj = shipping_options[0].get('shippingCost', {})
            shipping_value = shipping_cost_obj.get('value', '0')
            if float(shipping_value) == 0:
                result['shipping_cost'] = 'Free delivery'
            else:
                result['shipping_cost'] = f"${shipping_value}"
        else:
            result['shipping_cost'] = ''

        # IMPORTANT: This is an ACTIVE listing, not sold
        result['sold_date'] = 'Active listing'  # Mark as active to distinguish from sold

        # Seller info
        seller = item.get('seller', {})
        result['seller_name'] = seller.get('username', '')
        result['seller_feedback_score'] = seller.get('feedbackScore', '')
        result['seller_feedback_percentage'] = seller.get('feedbackPercentage', '')

        # Location
        location = item.get('itemLocation', {})
        result['seller_location'] = location.get('country', '')

        # Condition
        result['condition'] = item.get('condition', '')

        # Images - prefer thumbnailImages (higher res), fallback to image
        thumbnail_images = item.get('thumbnailImages', [])
        if thumbnail_images:
            # Get s-l1600 size (1600px) for better quality
            image_url = thumbnail_images[0].get('imageUrl', '')
        else:
            image_obj = item.get('image', {})
            image_url = image_obj.get('imageUrl', '')

        result['main_image'] = image_url
        result['thumbnail_image'] = image_url

        # Additional images for image comparison
        additional_images = item.get('additionalImages', [])
        result['additional_images'] = [img.get('imageUrl', '') for img in additional_images]

        # Price type
        buying_options = item.get('buyingOptions', [])
        if 'AUCTION' in buying_options:
            result['price_type'] = 'auction'
        else:
            result['price_type'] = 'buy_it_now'

        # Search metadata
        result['search_query'] = query

        # Fields for compatibility with Scrapy format
        result['bid_count'] = ''
        result['time_left'] = ''
        result['buy_it_now_price'] = ''
        result['watchers'] = ''
        result['items_sold'] = ''
        result['fast_n_free'] = False
        result['top_rated_seller'] = item.get('topRatedBuyingExperience', False)
        result['returns_accepted'] = False
        result['authenticity_guarantee'] = False
        result['search_position'] = 0
        result['search_page'] = 1
        result['search_sort'] = 'BestMatch'
        result['original_price'] = ''
        result['discount_percentage'] = ''
        result['brand'] = ''
        result['model'] = ''
        result['category'] = ''
        result['subcategory'] = ''
        result['seller_id'] = ''
        result['seller_verified'] = False
        result['quantity_available'] = ''
        result['listing_type'] = result['price_type']
        result['listing_format'] = ''
        result['ebay_plus'] = False
        result['sponsored'] = item.get('priorityListing', False)
        result['reserve_met'] = ''
        result['end_time'] = ''
        result['ships_from'] = ''
        result['ships_to'] = ''
        result['handling_time'] = ''
        result['shipping_type'] = ''
        result['return_period'] = ''
        result['image_count'] = 1 + len(result.get('additional_images', []))

        # API-specific metadata
        result['data_source'] = 'ebay_api'  # Tag to distinguish from Scrapy results
        result['item_creation_date'] = item.get('itemCreationDate', '')

        return result

    except Exception as e:
        print(f"[eBay API ERROR] Failed to convert item: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Test the API search
    print("Testing eBay API search...")
    results = run_ebay_api_search("Yura Kano photobook", max_results=5)

    if results:
        print(f"\nFound {len(results)} results:")
        for i, item in enumerate(results, 1):
            print(f"\n{i}. {item['product_title'][:60]}...")
            print(f"   Price: {item['current_price']}")
            print(f"   Shipping: {item.get('shipping_cost', 'N/A')}")
            print(f"   Status: {item.get('sold_date', 'N/A')}")
            print(f"   Image: {item.get('thumbnail_image', 'N/A')[:80]}...")
    else:
        print("No results found")
