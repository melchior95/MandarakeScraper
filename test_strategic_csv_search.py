#!/usr/bin/env python3
"""
Test the new strategic CSV search functionality
"""

import logging
from search_optimizer import SearchOptimizer

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

def test_strategic_csv_search():
    """Test the new strategic CSV search functionality"""

    optimizer = SearchOptimizer()

    # Test cases representing typical CSV titles
    test_cases = [
        {
            "csv_title": "Yura Kano Photobook Collection Special Edition",
            "category": "photobooks",
            "description": "Full photobook title with category"
        },
        {
            "csv_title": "Naruto Action Figure Limited Release",
            "category": "figures",
            "description": "Figure with descriptive terms"
        },
        {
            "csv_title": "Pokemon Trading Card Game Booster Pack",
            "category": None,
            "description": "Card game without explicit category"
        },
        {
            "csv_title": "Yura [Model] (2023 Release)",
            "category": None,
            "description": "Simple name with metadata brackets"
        },
        {
            "csv_title": "Super Rare Limited Edition Collectible Item",
            "category": None,
            "description": "Generic title with lots of fluff words"
        }
    ]

    print("=== Testing Strategic CSV Search ===")
    print()

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['description']}")
        print(f"CSV Title: '{test_case['csv_title']}'")
        print(f"Category: {test_case['category']}")
        print()

        strategies = optimizer.generate_strategic_csv_searches(
            test_case['csv_title'],
            test_case['category']
        )

        if strategies:
            for j, strategy in enumerate(strategies, 1):
                print(f"  Strategy {j}: '{strategy}'")
        else:
            print("  No strategies generated")

        print()
        print("-" * 50)
        print()

    # Test the strategy-based search behavior
    print("=== Strategy Usage Example ===")
    print("This shows how strategies would be used with fallback:")
    print()

    csv_title = "Yura Kano Photobook Collection"
    strategies = optimizer.generate_strategic_csv_searches(csv_title, "photobooks")

    for i, strategy in enumerate(strategies, 1):
        print(f"Strategy {i}: Search eBay for '{strategy}'")
        print(f"  -> If {5-i} or more results found, use this strategy")
        print(f"  -> If fewer results, try next strategy")
        print()

    print("This ensures we start with the most specific search and only")
    print("fall back to broader searches if needed.")

if __name__ == '__main__':
    test_strategic_csv_search()