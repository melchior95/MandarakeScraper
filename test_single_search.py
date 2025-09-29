#!/usr/bin/env python3
"""
Test to verify that eBay image comparison only searches once with the exact term
"""

import os
import sys
import logging
import requests
from datetime import datetime
from sold_listing_matcher_requests import match_product_with_sold_listings_requests

# Set up logging to capture search calls
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_single_search():
    """Test that eBay search only happens once with exact term"""

    print("=== Testing Single Search Behavior ===")
    print()

    # Create a simple test image (1x1 pixel)
    debug_dir = f"debug_images/single_search_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(debug_dir, exist_ok=True)

    # Download a small image for testing
    try:
        response = requests.get("https://i.ebayimg.com/images/g/FuYAAeSwRuVo2c6I/s-l500.webp", timeout=10)
        if response.status_code == 200:
            test_image_path = os.path.join(debug_dir, "test_image.webp")
            with open(test_image_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded test image: {test_image_path}")
        else:
            print("Could not download test image")
            return
    except Exception as e:
        print(f"Error downloading test image: {e}")
        return

    print(f"Testing search term: 'yura kano photobook'")
    print(f"Expected: Single eBay search with exact term")
    print()

    # Count the number of eBay URLs in debug output
    print("Looking for eBay search URLs in output...")

    try:
        result = match_product_with_sold_listings_requests(
            reference_image_path=test_image_path,
            search_term="yura kano photobook",
            similarity_threshold=0.3,
            max_results=3,
            debug_output_dir=debug_dir
        )

        print(f"\nSearch completed. Results: {result.matches_found} matches")
        print(f"Debug directory: {os.path.abspath(debug_dir)}")

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == '__main__':
    test_single_search()