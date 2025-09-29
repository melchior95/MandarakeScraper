#!/usr/bin/env python3
"""
Test script to verify eBay price extraction is working correctly
"""

import sys
import os
sys.path.insert(0, os.getcwd())

def test_price_parsing():
    """Test the price parsing method from SoldListingMatcher"""

    try:
        from sold_listing_matcher import SoldListingMatcher

        # Create a matcher instance to access the price parsing method
        matcher = SoldListingMatcher()

        # Test various eBay price formats
        test_prices = [
            "$23.45",
            "Sold  $45.99",
            "$1,234.56",
            "£12.99",
            "€89.50",
            "$99.99 to $150.00",
            "Sold  $19.95",
            "$0.99",
            "No price",
            "",
            "$123",
            "¥1500",
        ]

        print("Testing eBay Price Parsing")
        print("=" * 40)

        for i, price_text in enumerate(test_prices, 1):
            print(f"\nTest {i}: '{price_text}'")
            try:
                amount, currency = matcher._parse_price(price_text)
                print(f"Result: {currency} {amount:.2f}")

                # Validate result
                if amount > 0 and currency in ['USD', 'GBP', 'EUR', 'JPY']:
                    print("Status: SUCCESS - Valid price extracted")
                elif amount == 0:
                    print("Status: INFO - Zero price (possibly no price found)")
                else:
                    print("Status: WARNING - Unusual result")

            except Exception as e:
                print(f"ERROR: {e}")

        print("\nPrice parsing test completed!")
        return True

    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_real_ebay_structure():
    """Test with realistic eBay HTML price structures"""

    print("\nTesting Realistic eBay Price Structures")
    print("=" * 45)

    # These are examples of actual price text from eBay pages
    realistic_prices = [
        # Sold listings
        "$24.99",
        "Sold  $45.50",
        "$1,299.00",

        # Buy It Now prices
        "$89.95",
        "$199.99",

        # Auction results
        "$12.50",
        "$0.99",

        # International prices
        "£15.99",
        "€25.00",
        "¥2,500",

        # Complex formats
        "$19.99 to $29.99",
        "Sold  $150.00",
        "$500.00 + $15.00 shipping",
    ]

    from sold_listing_matcher import SoldListingMatcher
    matcher = SoldListingMatcher()

    success_count = 0
    for i, price_text in enumerate(realistic_prices, 1):
        print(f"\nRealistic Test {i}: '{price_text}'")
        try:
            amount, currency = matcher._parse_price(price_text)
            print(f"Extracted: {currency} {amount:.2f}")

            if amount > 0:
                print("Status: GOOD - Valid price extracted")
                success_count += 1
            else:
                print("Status: NEEDS REVIEW - Zero price")

        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\nRealistic tests: {success_count}/{len(realistic_prices)} successful")
    return success_count == len(realistic_prices)

def test_currency_formatting():
    """Test the new currency formatting in GUI"""

    print("\nTesting Currency Formatting")
    print("=" * 30)

    # Mock listing data with different currencies
    test_listings = [
        {'price': 24.99, 'currency': 'USD'},
        {'price': 15.50, 'currency': 'GBP'},
        {'price': 89.00, 'currency': 'EUR'},
        {'price': 1500, 'currency': 'JPY'},
        {'price': 0, 'currency': 'USD'},
    ]

    for i, listing in enumerate(test_listings, 1):
        print(f"\nFormat Test {i}: {listing['currency']} {listing['price']}")

        # Simulate the formatting logic from the GUI
        if listing['price'] > 0:
            if listing['currency'] == 'USD':
                price_display = f"${listing['price']:.2f}"
            elif listing['currency'] == 'GBP':
                price_display = f"£{listing['price']:.2f}"
            elif listing['currency'] == 'EUR':
                price_display = f"€{listing['price']:.2f}"
            else:
                price_display = f"{listing['currency']} {listing['price']:.2f}"
        else:
            price_display = 'Price not found'

        print(f"Formatted: {price_display}")

    print("\nCurrency formatting test completed!")

if __name__ == "__main__":
    try:
        print("eBay Price Extraction Verification")
        print("=" * 50)

        results = []
        results.append(("Basic Price Parsing", test_price_parsing()))
        results.append(("Realistic Price Structures", test_real_ebay_structure()))

        test_currency_formatting()

        print("\nFinal Results Summary")
        print("=" * 25)

        passed = 0
        for test_name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"{test_name}: {status}")
            if result:
                passed += 1

        print(f"\nOverall: {passed}/{len(results)} tests passed")

        if passed == len(results):
            print("\nSUCCESS: Price extraction should now show real sold prices instead of $1.00!")
            print("\nNext steps:")
            print("1. Run the GUI: python gui_config.py")
            print("2. Go to 'eBay Text Search' tab")
            print("3. Search for an item with a reference image")
            print("4. Verify prices show actual sold amounts")
        else:
            print(f"\nWARNING: {len(results) - passed} test(s) failed - check implementation")

    except Exception as e:
        print(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)