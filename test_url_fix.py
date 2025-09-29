#!/usr/bin/env python3
"""
Quick test to verify the eBay URL fixing is working
"""

import sys
import os
sys.path.insert(0, os.getcwd())

def test_url_fix():
    """Test the URL cleaning on common problematic URLs"""

    from gui_config import ScraperGUI
    import tkinter as tk

    # Create GUI instance to access the URL cleaning method
    root = tk.Tk()
    root.withdraw()
    gui = ScraperGUI()
    gui.withdraw()

    # Test various problematic URLs
    test_cases = [
        # Placeholder URLs that should be caught
        "https://www.ebay.com/listing/1",
        "https://www.ebay.com/listing/123",

        # Relative URLs that should be fixed
        "/itm/Pokemon-Card-Rare/987654321098",

        # URLs with tracking that should be cleaned
        "https://www.ebay.com/itm/123456789012?_trkparms=abc&_trksid=def&mkevt=1",

        # Valid URLs that should be preserved
        "https://www.ebay.com/itm/Pokemon-Pikachu-Card/445566778899",

        # Search results page (should be descriptive)
        "Search Results Page: https://www.ebay.com/sch/i.html?_nkw=pokemon+card&LH_Sold=1",

        # Empty/None URLs
        "",
        None
    ]

    print("Testing eBay URL Fixing")
    print("=" * 40)

    for i, url in enumerate(test_cases, 1):
        print(f"\nTest {i}: {repr(url)}")

        try:
            if url is None:
                result = gui._clean_ebay_url("")
            else:
                result = gui._clean_ebay_url(url)

            print(f"Result: {result}")

            # Analyze the result
            if "Placeholder URL" in result:
                print("Status: GOOD - Placeholder correctly identified")
            elif "No URL available" in result:
                print("Status: GOOD - Empty URL handled")
            elif result.startswith("https://www.ebay.com/itm/") and result.split("/")[-1].replace("?", "").split("?")[0].isdigit():
                print("Status: EXCELLENT - Clean eBay item URL")
            elif "Search Results Page:" in result:
                print("Status: GOOD - Search page properly labeled")
            elif result.startswith("https://www.ebay.com"):
                print("Status: OK - Valid eBay URL maintained")
            else:
                print("Status: REVIEW - Unusual result")

        except Exception as e:
            print(f"ERROR: {e}")

    # Clean up
    gui.destroy()
    root.destroy()

    print("\nURL fixing test completed!")

if __name__ == "__main__":
    test_url_fix()