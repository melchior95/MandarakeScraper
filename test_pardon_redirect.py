#!/usr/bin/env python3
"""
Test the pardon page redirect handling
"""

import asyncio
import logging
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_pardon_redirect():
    """Test handling of pardon page redirect"""

    print("=== Testing Pardon Page Redirect Handling ===")
    print()

    # Create matcher with visible browser
    matcher = SoldListingMatcher(headless=False, similarity_threshold=0.3)

    try:
        print("Testing search: 'pokemon card'")
        print("Watch the browser:")
        print("1. Should show 'Pardon Our Interruption' page first")
        print("2. Should automatically redirect to results after a few seconds")
        print("3. Should extract images from the results page")
        print()

        # Test extraction directly
        listings = await matcher._search_sold_listings("pokemon card", max_results=5, days_back=90)

        print(f"Final Results: {len(listings)} listings extracted")

        if len(listings) > 0:
            print("✅ SUCCESS: Pardon page redirect and extraction working!")
            print()
            print("Extracted listings:")
            for i, listing in enumerate(listings, 1):
                print(f"{i}. {listing.title}")
                print(f"   Image: {listing.image_url[:80]}...")
                print()
        else:
            print("❌ No listings extracted after redirect")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await matcher.cleanup()

if __name__ == '__main__':
    asyncio.run(test_pardon_redirect())