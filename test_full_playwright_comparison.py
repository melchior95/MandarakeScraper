#!/usr/bin/env python3
"""
Test full image comparison with Playwright version
"""

import asyncio
import logging
import os
import requests
from datetime import datetime
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_full_playwright_comparison():
    """Test full image comparison pipeline with Playwright"""

    print("=== Full Playwright Image Comparison Test ===")
    print()

    # Create debug directory
    debug_dir = f"debug_images/playwright_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(debug_dir, exist_ok=True)
    print(f"Debug directory: {os.path.abspath(debug_dir)}")

    # Download a test image
    print("Downloading test image...")
    try:
        response = requests.get("https://i.ebayimg.com/images/g/FuYAAeSwRuVo2c6I/s-l500.webp", timeout=10)
        if response.status_code == 200:
            test_image_path = os.path.join(debug_dir, "test_reference.webp")
            with open(test_image_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded test image: {test_image_path}")
        else:
            print("Could not download test image")
            return
    except Exception as e:
        print(f"Error downloading test image: {e}")
        return

    # Create matcher with visible browser and debug directory
    matcher = SoldListingMatcher(headless=False, similarity_threshold=0.3, debug_output_dir=debug_dir)

    try:
        print()
        print("Starting full image comparison...")
        print("Search term: 'pokemon card'")
        print("Watch the browser window for the process!")
        print()

        result = await matcher.find_matching_sold_listings(
            reference_image_path=test_image_path,
            search_term="pokemon card",
            max_results=3,  # Test with just 3 images for faster completion
            days_back=90
        )

        print("=== RESULTS ===")
        print(f"Matches found: {result.matches_found}")
        print(f"Confidence: {result.confidence}")

        if result.matches_found > 0:
            print("SUCCESS: Full image comparison working!")
            print()
            print("Matches:")
            for i, match in enumerate(result.all_matches, 1):
                print(f"{i}. {match.title[:50]}...")
                print(f"   Price: ${match.price}")
                print(f"   Similarity: {match.image_similarity:.3f}")
                print()

            print(f"Price Analysis:")
            print(f"  Average: ${result.average_price:.2f}")
            print(f"  Range: ${result.price_range[0]:.2f} - ${result.price_range[1]:.2f}")
        else:
            print("No matches found above threshold")
            print("But listings were extracted - try lowering similarity threshold")

        print(f"Test completed successfully!")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await matcher.cleanup()

if __name__ == '__main__':
    asyncio.run(test_full_playwright_comparison())