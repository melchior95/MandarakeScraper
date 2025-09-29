#!/usr/bin/env python3
"""
Test the updated Playwright version image extraction
"""

import asyncio
import logging
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_playwright_extraction():
    """Test Playwright version image extraction"""

    print("=== Testing Playwright Image Extraction ===")
    print()

    # Create matcher with visible browser to see what's happening
    matcher = SoldListingMatcher(headless=False, similarity_threshold=0.3)

    try:
        print("Testing search: 'pokemon card'")
        print("Browser window should open and show eBay page...")
        print()

        # Test the search that should work
        listings = await matcher._search_sold_listings("pokemon card", max_results=5, days_back=90)

        print(f"Results: {len(listings)} listings found")

        if len(listings) > 0:
            print("✅ SUCCESS: Playwright extraction working!")
            print()
            print("Found listings:")
            for i, listing in enumerate(listings, 1):
                print(f"{i}. {listing.title}")
                print(f"   Image: {listing.image_url[:80]}...")
                print(f"   Price: ${listing.price} {listing.currency}")
                print()
        else:
            print("❌ No listings extracted")
            print("Check the browser window to see what eBay returned")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await matcher.cleanup()

if __name__ == '__main__':
    asyncio.run(test_playwright_extraction())