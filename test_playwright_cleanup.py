#!/usr/bin/env python3
"""
Test Playwright cleanup to ensure no pipe errors on exit
"""

import asyncio
import logging
import os
import requests
from datetime import datetime
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_playwright_cleanup():
    """Test proper cleanup to avoid pipe errors"""

    print("=== Testing Playwright Cleanup ===")
    print()

    # Create debug directory
    debug_dir = os.path.join("debug_images", f"cleanup_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
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

    # Track matchers like the GUI does
    active_matchers = []

    try:
        # Create matcher
        print("Creating Playwright matcher...")
        matcher = SoldListingMatcher(
            headless=False,
            similarity_threshold=0.3,
            debug_output_dir=debug_dir
        )

        # Track it like GUI
        active_matchers.append(matcher)
        print("Matcher tracked successfully")

        print("Running quick image comparison...")
        result = asyncio.run(matcher.find_matching_sold_listings(
            reference_image_path=test_image_path,
            search_term="pokemon card",
            max_results=3,  # Smaller number for quick test
            days_back=90
        ))

        print(f"Comparison complete: {result.matches_found} matches found")

    except Exception as e:
        print(f"Error during test: {e}")

    finally:
        print("Starting cleanup...")

        # Cleanup like the GUI does
        for matcher in active_matchers[:]:
            try:
                print("Cleaning up Playwright matcher...")
                asyncio.run(matcher.cleanup())
                active_matchers.remove(matcher)
                print("✅ Matcher cleaned up successfully")
            except Exception as cleanup_error:
                print(f"❌ Cleanup error: {cleanup_error}")

        active_matchers.clear()
        print("✅ All matchers cleaned up")

    print("Test complete - check for pipe errors above!")

if __name__ == '__main__':
    test_playwright_cleanup()