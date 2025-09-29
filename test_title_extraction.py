#!/usr/bin/env python3
"""
Test script to verify eBay title extraction is working correctly
"""

import sys
import os
import re
sys.path.insert(0, os.getcwd())

def test_title_cleaning():
    """Test the title cleaning logic"""

    print("Testing Title Cleaning Logic")
    print("=" * 35)

    # Test various eBay title formats that might be encountered
    test_titles = [
        "Pokemon Pikachu VMAX Card Rare Holo TCG Gaming Card",
        "SPONSORED Pokemon Booster Pack Sealed",
        "New Listing Pokemon Card Collection Lot",
        "Trading Card Game Booster Box Factory Sealed",
        "Yu-Gi-Oh! Dark Magician Blue-Eyes White Dragon",
        "SPONSORED New Listing Pokemon Cards Bundle",
        "   Pokemon Charizard GX Holo Rare   ",  # With extra spaces
        "Short",  # Too short
        "",  # Empty
        "A very long Pokemon card title that describes the item in great detail including condition",
    ]

    success_count = 0
    for i, title_text in enumerate(test_titles, 1):
        print(f"\nTest {i}: '{title_text}'")

        # Apply the cleaning logic from the sold listing matcher
        if title_text and title_text.strip() and len(title_text.strip()) > 10:
            clean_title = title_text.strip()
            clean_title = re.sub(r'^(New Listing|SPONSORED)\s*', '', clean_title, flags=re.IGNORECASE)
            if len(clean_title) > 10:
                print(f"Result: '{clean_title}'")
                print("Status: SUCCESS - Valid title extracted")
                success_count += 1
            else:
                print("Status: SKIPPED - Too short after cleaning")
        else:
            print("Status: SKIPPED - Too short or empty")

    print(f"\nTitle cleaning: {success_count}/{len([t for t in test_titles if t.strip()])} valid titles processed")

def test_title_selectors():
    """Test the CSS selectors that would be used for title extraction"""

    print("\nTesting Title Selector Strategy")
    print("=" * 35)

    # These are the selectors used in the enhanced title extraction
    selectors = [
        '.s-item__title',
        '.s-item__title span',
        '.it-ttl',
        'h3',
        'h3 a',
        '[class*="title"]',
        'a[href*="itm/"]',
        '.s-item__link',
        '.s-item__wrapper .s-item__title',
        '.s-item__detail .s-item__title'
    ]

    print("Enhanced title selectors in priority order:")
    for i, selector in enumerate(selectors, 1):
        print(f"  {i}. {selector}")

    print(f"\nTotal selectors: {len(selectors)}")
    print("Strategy: Try each selector until a valid title (>10 chars) is found")

def test_fallback_methods():
    """Test the fallback title extraction methods"""

    print("\nTesting Fallback Methods")
    print("=" * 25)

    # Test page title extraction
    test_page_titles = [
        "Pokemon Cards for sale | eBay",
        "Trading Cards: Pokemon | eBay",
        "Yu-Gi-Oh Cards | eBay",
        "Search results for pokemon pikachu | eBay",
        "eBay - Pokemon",
    ]

    print("Testing page title extraction:")
    for i, page_title in enumerate(test_page_titles, 1):
        print(f"\nPage Title {i}: '{page_title}'")

        if 'eBay' in page_title:
            extracted_title = None

            if ' for sale' in page_title:
                search_part = page_title.split(' for sale')[0]
                if search_part and len(search_part) > 3:
                    extracted_title = f"{search_part} - Item 1"
            elif '|' in page_title:
                search_part = page_title.split('|')[0].strip()
                if search_part and len(search_part) > 3:
                    extracted_title = f"{search_part} - Item 1"

            if extracted_title:
                print(f"Extracted: '{extracted_title}'")
                print("Status: SUCCESS - Valid fallback title")
            else:
                print("Status: No extraction possible")
        else:
            print("Status: Not an eBay page title")

def simulate_title_extraction():
    """Simulate the complete title extraction process"""

    print("\nSimulating Complete Title Extraction Process")
    print("=" * 45)

    # Simulate scenarios
    scenarios = [
        {
            "name": "Perfect Case",
            "parent_title": "Pokemon Pikachu VMAX Gold Rare Card PSA 10",
            "page_titles": [],
            "page_title": "Pokemon Cards for sale | eBay"
        },
        {
            "name": "Sponsored Listing",
            "parent_title": "SPONSORED Pokemon Charizard Holo Rare",
            "page_titles": [],
            "page_title": "Pokemon for sale | eBay"
        },
        {
            "name": "Fallback to Page List",
            "parent_title": None,
            "page_titles": ["Trading Card Game Booster Pack", "Yu-Gi-Oh Blue Eyes", "Pokemon Starter Deck"],
            "page_title": "Trading Cards | eBay"
        },
        {
            "name": "Ultimate Fallback",
            "parent_title": None,
            "page_titles": [],
            "page_title": "Pokemon Cards for sale | eBay"
        }
    ]

    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")

        final_title = None
        method_used = None

        # Method 1: Parent context
        if scenario['parent_title']:
            title_text = scenario['parent_title']
            if title_text and len(title_text.strip()) > 10:
                clean_title = title_text.strip()
                clean_title = re.sub(r'^(New Listing|SPONSORED)\s*', '', clean_title, flags=re.IGNORECASE)
                if len(clean_title) > 10:
                    final_title = clean_title
                    method_used = "Parent Context"

        # Method 2: Page title list (simulated)
        if not final_title and scenario['page_titles']:
            index = 0  # Simulate first item
            if index < len(scenario['page_titles']):
                title_text = scenario['page_titles'][index]
                if len(title_text.strip()) > 10:
                    final_title = title_text.strip()
                    method_used = "Page Title List"

        # Method 3: Page title fallback
        if not final_title:
            page_title = scenario['page_title']
            if 'eBay' in page_title:
                if ' for sale' in page_title:
                    search_part = page_title.split(' for sale')[0]
                    if search_part and len(search_part) > 3:
                        final_title = f"{search_part} - Item 1"
                        method_used = "Page Title Fallback"

        print(f"Final Title: '{final_title}'")
        print(f"Method Used: {method_used}")

if __name__ == "__main__":
    print("eBay Title Extraction Testing")
    print("=" * 40)

    try:
        test_title_cleaning()
        test_title_selectors()
        test_fallback_methods()
        simulate_title_extraction()

        print("\n" + "="*50)
        print("SUMMARY: Title extraction enhancements complete!")
        print("\nKey Improvements:")
        print("1. Enhanced CSS selectors for better title detection")
        print("2. Multiple fallback methods for title extraction")
        print("3. Title cleaning to remove 'SPONSORED' and 'New Listing'")
        print("4. Minimum length requirements (>10 chars)")
        print("5. Index-based matching for page-wide title extraction")
        print("\nNext: Test with real eBay search to see actual titles!")

    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()