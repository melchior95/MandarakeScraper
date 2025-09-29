#!/usr/bin/env python3
"""
Test script that mimics the GUI's calling pattern exactly
"""

import asyncio
import logging
import os
import requests
from datetime import datetime
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_gui_compatibility():
    """Test the exact same calling pattern as the GUI uses"""

    print("=== GUI Compatibility Test ===")
    print()

    # Create debug directory (same as GUI)
    debug_dir = os.path.join("debug_images", f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(debug_dir, exist_ok=True)
    print(f"Debug directory: {os.path.abspath(debug_dir)}")

    # Download a test image (same as test script)
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

    # Create matcher exactly like the GUI does
    print("Creating matcher like GUI...")
    show_browser = True  # Using visible browser like GUI choice
    similarity_threshold = 0.3  # Same as test

    if show_browser:
        # Use Playwright version with visible browser (same as GUI)
        matcher = SoldListingMatcher(
            headless=False,  # Show browser window
            similarity_threshold=similarity_threshold,
            debug_output_dir=debug_dir
        )
        print("Using Playwright version with visible browser")

    try:
        if show_browser:
            # Playwright version needs async handling (same as GUI)
            result = asyncio.run(matcher.find_matching_sold_listings(
                reference_image_path=test_image_path,
                search_term="pokemon card",
                max_results=5,
                days_back=90
            ))

        print("=== RESULTS ===")
        print(f"Matches found: {result.matches_found}")
        print(f"Confidence: {result.confidence}")

        # Check if images were saved (same as GUI)
        if os.path.exists(debug_dir):
            image_count = len([f for f in os.listdir(debug_dir) if f.endswith('.jpg')])
            print(f"Downloaded {image_count} images to: {debug_dir}")

            # List all files in debug directory
            print("Files in debug directory:")
            for f in os.listdir(debug_dir):
                print(f"  - {f}")

        print("SUCCESS: GUI pattern test completed!")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Handle cleanup exactly like GUI
        if show_browser:
            # Playwright version has async cleanup
            try:
                asyncio.run(matcher.cleanup())
            except Exception as cleanup_error:
                print(f"Error during Playwright cleanup: {cleanup_error}")

if __name__ == '__main__':
    test_gui_compatibility()