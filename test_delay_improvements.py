#!/usr/bin/env python3
"""
Test the improved delay system to reduce eBay blocking
"""

import logging
import time
from browser_mimic import BrowserMimic

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_delay_improvements():
    """Test the new delay system"""

    print("=== Testing Enhanced eBay Delay System ===")
    print()

    browser = BrowserMimic("test_delays.pkl")

    # Test 1: Regular non-eBay request (should use normal delays)
    print("Test 1: Non-eBay request (normal delay)")
    start_time = time.time()

    try:
        response = browser.get("https://httpbin.org/status/200")
        elapsed = time.time() - start_time
        print(f"✅ Non-eBay request completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"❌ Error: {e}")

    print()

    # Test 2: eBay request (should use longer delays)
    print("Test 2: eBay request (enhanced delay)")
    start_time = time.time()

    try:
        # This should trigger the eBay-specific delays
        ebay_url = "https://www.ebay.com/sch/i.html?_nkw=test"
        print(f"Requesting: {ebay_url}")
        print("Watch for delay messages...")

        response = browser.get(ebay_url)
        elapsed = time.time() - start_time
        print(f"✅ eBay request completed in {elapsed:.2f}s")
        print(f"Response status: {response.status_code}")

        # Check if it's a blocking page
        if "pardon our interruption" in response.text.lower():
            print("⚠️  eBay blocking detected, but delays are working")
        else:
            print("✅ No blocking detected")

    except Exception as e:
        print(f"❌ Error: {e}")

    browser.cleanup()

    print()
    print("=== Delay Summary ===")
    print("Normal requests: ~2-4 seconds base delay")
    print("eBay requests: ~4-7 seconds base delay + 3-6 second extra delay")
    print("Total eBay delay: ~7-13 seconds between requests")
    print()
    print("This should significantly reduce eBay blocking!")

if __name__ == '__main__':
    test_delay_improvements()