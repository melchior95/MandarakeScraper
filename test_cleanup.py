#!/usr/bin/env python3
"""
Test Playwright cleanup to verify pipe errors are minimized
"""

import asyncio
import logging
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

async def test_cleanup():
    """Test the improved cleanup process"""

    print("=== Testing Improved Playwright Cleanup ===")
    print()

    matchers = []

    try:
        # Create multiple matchers like GUI might
        for i in range(2):
            print(f"Creating matcher {i+1}...")
            matcher = SoldListingMatcher(
                headless=True,  # Headless for faster test
                similarity_threshold=0.3
            )
            matchers.append(matcher)

            # Initialize browser
            await matcher._init_browser()
            print(f"Matcher {i+1} initialized")

        print()
        print("Testing cleanup of all matchers...")

        # Clean up all matchers
        for i, matcher in enumerate(matchers):
            print(f"Cleaning up matcher {i+1}...")
            await matcher.cleanup()
            print(f"Matcher {i+1} cleaned up")

        print()
        print("All matchers cleaned up successfully!")
        print("Check for reduced pipe errors above...")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("Test completed.")

if __name__ == '__main__':
    asyncio.run(test_cleanup())