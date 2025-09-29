#!/usr/bin/env python3
"""
Test script to verify lazy search is working with text-only eBay searches
"""

import sys
import os

# Add current directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_lazy_search_text_only():
    """Test lazy search with text-only search (no image processing)"""

    try:
        # Import the search optimizer
        from search_optimizer import SearchOptimizer

        # Test optimization
        optimizer = SearchOptimizer()

        # Test with a typical Japanese product title
        test_title = "Yura Kano Magical Girlfriend photo book collection"

        print("=== LAZY SEARCH TEXT-ONLY TEST ===")
        print(f"Original title: '{test_title}'")
        print()

        # Get optimized search terms
        optimization = optimizer.optimize_search_term(test_title, lazy_mode=True)

        print("Optimization results:")
        print(f"Core terms: {optimization['core_terms']}")
        print(f"Generated variations: {optimization['variations']}")
        print(f"Search strategies (confidence order): {optimization['confidence_order']}")
        print()

        # Test the manual eBay search function
        print("=== TESTING EBAY SEARCH INTEGRATION ===")

        # Import eBay API
        from mandarake_scraper import EbayAPI

        # Create dummy eBay API instance
        ebay_api = EbayAPI("", "")

        print(f"Testing original search: '{test_title}'")
        result_original = ebay_api.search_sold_listings_web(test_title, days_back=90)

        if result_original:
            print(f"Original search results: {result_original.get('sold_count', 0)} items found")
            if result_original.get('error'):
                print(f"Original search error: {result_original['error']}")
        else:
            print("Original search returned None")

        print()

        # Test optimized terms
        optimized_terms = optimization['confidence_order'][:3]  # Test top 3

        print(f"Testing optimized terms: {optimized_terms}")

        best_result = result_original
        best_count = result_original.get('sold_count', 0) if result_original else 0

        for optimized_term in optimized_terms:
            if optimized_term != test_title:  # Skip if same as original
                print(f"  Testing: '{optimized_term}'")

                opt_result = ebay_api.search_sold_listings_web(optimized_term, days_back=90)

                if opt_result:
                    opt_count = opt_result.get('sold_count', 0)
                    print(f"    Results: {opt_count} items")

                    if opt_result.get('error'):
                        print(f"    Error: {opt_result['error']}")

                    if opt_count > best_count:
                        print(f"    *** BETTER RESULT! {opt_count} vs {best_count}")
                        best_result = opt_result
                        best_count = opt_count
                else:
                    print(f"    No result returned")

        print()
        print("=== FINAL RESULTS ===")
        if best_result and best_result != result_original:
            print(f"LAZY SEARCH SUCCESS: Found better result with {best_count} items")
            print(f"Best search term: '{best_result.get('search_term_used', 'unknown')}'")
        elif best_result:
            print(f"Original search was best: {best_count} items")
            if best_result.get('error'):
                print(f"Note: eBay access issues: {best_result['error']}")
        else:
            print("No results found with any search terms")

        print()
        print("=== CATEGORY DETECTION TEST ===")

        # Test category detection
        detected_categories = optimizer._detect_categories(test_title.lower())
        print(f"Detected categories: {detected_categories}")

        if detected_categories:
            print("Category variations that would be tried:")
            for i, category_variants in enumerate(detected_categories, 1):
                print(f"  Category {i}: {category_variants}")

        return True

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_optimization_only():
    """Test just the search optimization without eBay calls"""

    try:
        from search_optimizer import SearchOptimizer

        optimizer = SearchOptimizer()

        test_cases = [
            "Yura Kano photo book collection",
            "Rei Ayanami figure limited edition",
            "Pokemon trading card holographic rare",
            "Japanese gravure idol magazine 2024"
        ]

        print("=== SEARCH OPTIMIZATION TEST (No eBay calls) ===")

        for test_title in test_cases:
            print(f"\nTesting: '{test_title}'")

            optimization = optimizer.optimize_search_term(test_title, lazy_mode=True)

            print(f"  Core terms: {optimization['core_terms']}")
            print(f"  Top 3 optimized: {optimization['confidence_order'][:3]}")

            # Test category detection
            detected_categories = optimizer._detect_categories(test_title.lower())
            if detected_categories:
                print(f"  Detected categories: {[cat[:2] for cat in detected_categories]}")  # Show first 2 variants

        return True

    except Exception as e:
        print(f"Optimization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "optimize-only":
        print("Running optimization-only test (no eBay calls)...")
        success = test_search_optimization_only()
    else:
        print("Running full lazy search test (includes eBay calls)...")
        print("Note: eBay may block these requests with CAPTCHAs")
        print()
        success = test_lazy_search_text_only()

    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")

    print("\nUsage:")
    print("  python test_lazy_search.py                 # Full test with eBay calls")
    print("  python test_lazy_search.py optimize-only   # Test optimization only")