#!/usr/bin/env python3
"""
Example of how to use the strategic CSV search in practice
"""

from search_optimizer import generate_csv_search_strategies

def example_csv_search_workflow(csv_title: str, category: str = None, min_results_threshold: int = 3):
    """
    Example workflow showing how to use strategic search with fallback

    Args:
        csv_title: Title from CSV file
        category: Optional category for the item
        min_results_threshold: Minimum results needed before trying next strategy

    Returns:
        The search term that found sufficient results, or the last one tried
    """

    print(f"=== Strategic Search for: '{csv_title}' ===")
    if category:
        print(f"Category: {category}")
    print()

    # Get all strategies in order
    strategies = generate_csv_search_strategies(csv_title, category)

    if not strategies:
        print("No search strategies generated!")
        return None

    # Try each strategy until we find enough results
    for i, strategy in enumerate(strategies, 1):
        print(f"Strategy {i}: Searching for '{strategy}'")

        # Simulate eBay search (in real implementation, this would be actual eBay API call)
        simulated_results = simulate_ebay_search(strategy)
        print(f"  -> Found {simulated_results} results")

        if simulated_results >= min_results_threshold:
            print(f"  ✅ SUCCESS: Using Strategy {i} (found {simulated_results} results)")
            return strategy
        else:
            print(f"  ❌ Not enough results, trying next strategy...")

        print()

    # If we get here, no strategy found enough results
    final_strategy = strategies[-1]
    print(f"⚠️  Using final strategy '{final_strategy}' (best available)")
    return final_strategy

def simulate_ebay_search(search_term: str) -> int:
    """Simulate eBay search results (for demo purposes)"""
    # This simulates different search terms finding different numbers of results
    search_lower = search_term.lower()

    if len(search_term.split()) >= 4:  # Long/specific searches
        return 2  # Usually fewer results
    elif len(search_term.split()) == 3:  # Medium searches
        return 5  # Good results
    elif len(search_term.split()) == 2:  # Core name + keyword
        return 8  # More results
    else:  # Single words or very short
        return 15  # Many results (might be too generic)

if __name__ == '__main__':
    # Test examples
    test_cases = [
        ("Yura Kano Photobook Collection Special Edition", "photobooks"),
        ("Naruto Action Figure Limited Release", "figures"),
        ("Pokemon Trading Card Game Booster Pack", None),
        ("Yura [Model] (2023 Release)", None),
    ]

    for csv_title, category in test_cases:
        best_strategy = example_csv_search_workflow(csv_title, category)
        print(f"Final choice: '{best_strategy}'")
        print()
        print("=" * 60)
        print()