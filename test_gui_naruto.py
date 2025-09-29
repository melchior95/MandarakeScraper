#!/usr/bin/env python3
"""
Test GUI-compatible naruto image matching
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_gui_naruto():
    """Test naruto image like the GUI would"""

    print("=== GUI-Compatible Naruto Test ===")
    print()

    # Create debug directory like GUI does
    debug_dir = os.path.join("debug_images", f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(debug_dir, exist_ok=True)
    print(f"Debug directory: {os.path.abspath(debug_dir)}")

    # Use the naruto image
    reference_path = r"C:\Python Projects\mandarake_scraper\images\naruto\thumb_product_0003.jpg"

    if not os.path.exists(reference_path):
        print(f"Reference image not found: {reference_path}")
        return

    # Create matcher exactly like GUI
    matcher = SoldListingMatcher(
        headless=False,  # Visible browser like GUI
        similarity_threshold=0.3,  # Default GUI threshold
        debug_output_dir=debug_dir
    )

    try:
        print()
        print("Testing GUI-style image comparison...")
        print("Search term: 'yura kano photobook'")
        print()

        result = await matcher.find_matching_sold_listings(
            reference_image_path=reference_path,
            search_term="yura kano photobook",
            max_results=5,  # Default GUI setting
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
                print(f"   Similarity: {float(match.image_similarity):.1%}")  # Test GUI formatting
                print(f"   Price: ${match.price:.2f}")
                print()

        # Check debug images
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
    asyncio.run(test_gui_naruto())