#!/usr/bin/env python3
"""
Test the real image matching scenario with the reference image
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_real_matching():
    """Test real image matching with the reference naruto image"""

    print("=== Real Image Matching Test ===")
    print()

    # Create debug directory
    debug_dir = os.path.join("debug_images", f"real_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(debug_dir, exist_ok=True)
    print(f"Debug directory: {os.path.abspath(debug_dir)}")

    # Copy the reference image to debug directory
    reference_path = r"C:\Python Projects\mandarake_scraper\images\naruto\thumb_product_0003.jpg"
    test_reference_path = os.path.join(debug_dir, "test_reference.jpg")

    try:
        shutil.copy2(reference_path, test_reference_path)
        print(f"Reference image: {test_reference_path}")
    except Exception as e:
        print(f"Error copying reference image: {e}")
        return

    # Copy a known similar image to the debug directory to simulate a match
    similar_image_path = r"C:\Python Projects\mandarake_scraper\debug_images\comparison_20250928_202019\listing_01.jpg"
    if os.path.exists(similar_image_path):
        test_similar_path = os.path.join(debug_dir, "listing_01.jpg")
        shutil.copy2(similar_image_path, test_similar_path)
        print(f"Pre-placed similar image: {test_similar_path}")

    # Create matcher with improved algorithm and lower threshold
    matcher = SoldListingMatcher(
        headless=False,  # Show browser for demo
        similarity_threshold=0.3,  # Lower threshold to catch good matches
        debug_output_dir=debug_dir
    )

    try:
        print()
        print("Starting real image comparison...")
        print("Search term: 'naruto photobook'")
        print("This should find the similar image and detect a match!")
        print()

        result = await matcher.find_matching_sold_listings(
            reference_image_path=test_reference_path,
            search_term="naruto photobook",
            max_results=3,  # Small number for faster test
            days_back=90
        )

        print("=== RESULTS ===")
        print(f"Matches found: {result.matches_found}")
        print(f"Confidence: {result.confidence}")

        if result.matches_found > 0:
            print("SUCCESS: Found matching images!")
            print()
            print("Matches:")
            for i, match in enumerate(result.all_matches, 1):
                print(f"{i}. {match.title[:50]}...")
                print(f"   Similarity: {match.image_similarity:.3f}")
                print(f"   Price: ${match.price}")
                print()

            print(f"Price Analysis:")
            print(f"  Average: ${result.average_price:.2f}")
            print(f"  Range: ${result.price_range[0]:.2f} - ${result.price_range[1]:.2f}")
        else:
            print("No matches found - but this should now work with improved algorithm!")

        # Check what images were saved
        print()
        print("Debug images saved:")
        if os.path.exists(debug_dir):
            for f in os.listdir(debug_dir):
                if f.endswith(('.jpg', '.webp', '.png')):
                    print(f"  - {f}")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await matcher.cleanup()

if __name__ == '__main__':
    asyncio.run(test_real_matching())