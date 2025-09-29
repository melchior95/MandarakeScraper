#!/usr/bin/env python3
"""
Test script for eBay URL cleaning functionality
"""

import sys
import os
sys.path.insert(0, os.getcwd())

def test_url_cleaning():
    """Test URL cleaning with various eBay URL formats"""

    # Import the GUI class to access the URL cleaning method
    from gui_config import ScraperGUI
    import tkinter as tk

    # Create a minimal GUI instance to access the method
    root = tk.Tk()
    root.withdraw()
    gui = ScraperGUI()
    gui.withdraw()

    # Test URLs in various formats
    test_urls = [
        # Valid eBay URLs
        "https://www.ebay.com/itm/Pokemon-Card-Pikachu-VMAX/123456789012",
        "https://www.ebay.com/itm/123456789012",
        "/itm/Pokemon-Card-Rare/987654321098",
        "https://www.ebay.com/itm/Trading-Card-Game/555666777888?hash=item1234567890",

        # URLs with tracking parameters
        "https://www.ebay.com/itm/123456789012?_trkparms=pageci%3A123&_trksid=p2047675.c100005.m1851",
        "https://www.ebay.com/itm/987654321098?mkevt=1&mkcid=2&mkrid=123&campid=456",

        # Search URLs
        "https://www.ebay.com/sch/i.html?_nkw=pokemon+card&_sacat=0",

        # Placeholder URLs
        "https://www.ebay.com/listing/1",
        "https://www.ebay.com/listing/123",

        # Invalid URLs
        "",
        None,
        "not-a-url",
        "https://www.amazon.com/item/123",
    ]

    print("Testing eBay URL Cleaning Functionality")
    print("=" * 50)

    for i, test_url in enumerate(test_urls, 1):
        print(f"\nTest {i}: {test_url}")
        try:
            if test_url is None:
                clean_url = gui._clean_ebay_url("")
            else:
                clean_url = gui._clean_ebay_url(test_url)
            print(f"Result: {clean_url}")

            # Validate result
            if clean_url:
                if "itm/" in clean_url and clean_url.startswith("https://www.ebay.com"):
                    print("Status: GOOD - Clean eBay item URL")
                elif "sch/" in clean_url and clean_url.startswith("https://www.ebay.com"):
                    print("Status: GOOD - eBay search URL")
                elif any(x in clean_url for x in ["No URL", "Placeholder", "Invalid", "Error"]):
                    print("Status: HANDLED - Invalid URL properly flagged")
                else:
                    print("Status: OK - URL preserved")
            else:
                print("Status: ERROR - No result returned")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Clean up
    gui.destroy()
    root.destroy()

    print(f"\nURL cleaning test completed!")

def test_specific_ebay_patterns():
    """Test specific eBay URL patterns we might encounter"""

    from gui_config import ScraperGUI
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    gui = ScraperGUI()
    gui.withdraw()

    print("\nTesting Specific eBay URL Patterns")
    print("=" * 40)

    # Test patterns that might come from the sold listing matcher
    patterns = [
        "https://www.ebay.com/itm/Pokemon-Pikachu-VMAX-Card-Rare-Holo-TCG-Gaming/334567890123",
        "https://www.ebay.com/itm/334567890123?hash=item4de8f7b8c3:g:abc123def456",
        "/itm/Trading-Cards-Pokemon-Booster-Pack/445566778899",
        "https://ebay.com/itm/556677889900",  # Missing www
        "http://www.ebay.com/itm/667788990011",  # HTTP instead of HTTPS
    ]

    for pattern in patterns:
        print(f"\nPattern: {pattern}")
        clean = gui._clean_ebay_url(pattern)
        print(f"Cleaned: {clean}")

        # Verify it's a proper format
        if clean.startswith("https://www.ebay.com/itm/") and clean.split("/")[-1].isdigit():
            print("PASS: Proper clean eBay item URL format")
        else:
            print("NEEDS REVIEW: Unusual format")

    gui.destroy()
    root.destroy()

    print("\nSpecific pattern testing completed!")

if __name__ == "__main__":
    try:
        test_url_cleaning()
        test_specific_ebay_patterns()
        print("\nAll URL cleaning tests completed successfully!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)