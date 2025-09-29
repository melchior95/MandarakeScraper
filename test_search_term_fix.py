#!/usr/bin/env python3
"""
Test to verify that search terms are not incorrectly modified with "sold"
"""

import logging
from sold_listing_matcher_requests import SoldListingMatcherRequests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_search_term_fix():
    """Test that search terms are used correctly without adding 'sold'"""

    matcher = SoldListingMatcherRequests(similarity_threshold=0.3)

    # Test the URL building method directly
    test_cases = [
        "yura kano photobook",
        "pokemon card",
        "naruto figure"
    ]

    print("=== Testing eBay URL Building ===")
    print()

    for search_term in test_cases:
        url = matcher._build_ebay_sold_url(search_term, days_back=90)
        print(f"Search term: '{search_term}'")
        print(f"Generated URL: {url}")

        # Check if 'sold' was incorrectly added to the search term
        if "+sold" in url or "sold" in url.split("_nkw=")[1].split("&")[0]:
            print("❌ ERROR: 'sold' was incorrectly added to search term!")
        else:
            print("✅ CORRECT: Search term used as-is, 'sold' filter via LH_Sold=1")

        # Check that LH_Sold=1 parameter is present
        if "LH_Sold=1" in url:
            print("✅ CORRECT: LH_Sold=1 parameter found")
        else:
            print("❌ ERROR: Missing LH_Sold=1 parameter!")

        print()

if __name__ == '__main__':
    test_search_term_fix()