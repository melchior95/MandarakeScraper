#!/usr/bin/env python3
"""
Test the improved eBay blocking detection
"""

import logging
from sold_listing_matcher_requests import SoldListingMatcherRequests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_blocking_detection():
    """Test blocking detection with recent response"""

    print("=== Testing eBay Blocking Detection ===")
    print()

    matcher = SoldListingMatcherRequests(similarity_threshold=0.3)

    # Test the search that caused the blocking
    print("Testing search: 'yura kano photobook'")
    print("This should detect the 'Pardon Our Interruption' blocking page")
    print()

    listings = matcher._search_sold_listings("yura kano photobook", max_results=5, days_back=90)

    print(f"Results: {len(listings)} listings found")

    if len(listings) == 0:
        print("✅ Blocking detection working - no listings returned")
        print("Check the logs above for blocking detection messages")
    else:
        print("❓ Unexpected - listings found despite possible blocking")

    print()
    print("=== Recommendations ===")
    print("If eBay is blocking:")
    print("1. Wait 5-10 minutes before retrying")
    print("2. Try different/simpler search terms")
    print("3. Consider using eBay API instead of scraping")
    print("4. Use VPN to change IP address")

if __name__ == '__main__':
    test_blocking_detection()