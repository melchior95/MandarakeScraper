#!/usr/bin/env python3
"""
Demo script for eBay Image Comparison (no actual eBay access required)

This creates a demonstration of what the results would look like without
actually accessing eBay, useful for testing the GUI integration.
"""

import logging
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List
import random


@dataclass
class MockSoldListing:
    """Mock data structure for demonstration"""
    title: str
    price: float
    currency: str
    sold_date: str
    image_url: str
    listing_url: str
    image_similarity: float = 0.0
    confidence_score: float = 0.0


@dataclass
class MockImageMatchResult:
    """Mock result for demonstration"""
    matches_found: int
    best_match: MockSoldListing
    all_matches: List[MockSoldListing]
    average_price: float
    price_range: tuple
    confidence: str


def create_mock_image_comparison_result(search_term: str) -> MockImageMatchResult:
    """Create realistic mock results for demonstration"""

    # Create mock sold listings based on search term
    mock_listings = []

    if "photobook" in search_term.lower():
        mock_listings = [
            MockSoldListing(
                title="Yura Kano Magical Girlfriend Photo Book Collection Japanese Gravure",
                price=42.50,
                currency="USD",
                sold_date="3 days ago",
                image_url="https://example.com/image1.jpg",
                listing_url="https://ebay.com/itm/123456",
                image_similarity=0.87,
                confidence_score=0.92
            ),
            MockSoldListing(
                title="Yura Kano Photo Book Japanese Idol Gravure Collection Rare",
                price=38.99,
                currency="USD",
                sold_date="1 week ago",
                image_url="https://example.com/image2.jpg",
                listing_url="https://ebay.com/itm/234567",
                image_similarity=0.74,
                confidence_score=0.81
            ),
            MockSoldListing(
                title="Japanese Gravure Photo Book Yura Kano Idol Collection",
                price=45.00,
                currency="USD",
                sold_date="2 weeks ago",
                image_url="https://example.com/image3.jpg",
                listing_url="https://ebay.com/itm/345678",
                image_similarity=0.71,
                confidence_score=0.79
            )
        ]
    elif "figure" in search_term.lower():
        mock_listings = [
            MockSoldListing(
                title="Anime Figure Collection Rare Japanese Import",
                price=89.99,
                currency="USD",
                sold_date="5 days ago",
                image_url="https://example.com/figure1.jpg",
                listing_url="https://ebay.com/itm/456789",
                image_similarity=0.82,
                confidence_score=0.88
            ),
            MockSoldListing(
                title="Japanese Collectible Figure Anime Character Limited Edition",
                price=76.50,
                currency="USD",
                sold_date="1 week ago",
                image_url="https://example.com/figure2.jpg",
                listing_url="https://ebay.com/itm/567890",
                image_similarity=0.75,
                confidence_score=0.83
            )
        ]
    else:
        # Generic results for any other search term
        base_price = random.uniform(25, 75)
        mock_listings = [
            MockSoldListing(
                title=f"{search_term} - Japanese Import Collectible Item",
                price=base_price + random.uniform(-10, 10),
                currency="USD",
                sold_date="4 days ago",
                image_url="https://example.com/generic1.jpg",
                listing_url="https://ebay.com/itm/generic1",
                image_similarity=0.78,
                confidence_score=0.85
            ),
            MockSoldListing(
                title=f"{search_term} Rare Collection Japanese",
                price=base_price + random.uniform(-5, 15),
                currency="USD",
                sold_date="1 week ago",
                image_url="https://example.com/generic2.jpg",
                listing_url="https://ebay.com/itm/generic2",
                image_similarity=0.72,
                confidence_score=0.80
            )
        ]

    if not mock_listings:
        # No matches scenario
        return MockImageMatchResult(
            matches_found=0,
            best_match=None,
            all_matches=[],
            average_price=0.0,
            price_range=(0.0, 0.0),
            confidence="no_matches"
        )

    # Calculate statistics
    prices = [listing.price for listing in mock_listings]
    avg_price = sum(prices) / len(prices)
    price_range = (min(prices), max(prices))

    # Sort by similarity
    mock_listings.sort(key=lambda x: x.image_similarity, reverse=True)

    # Determine confidence
    confidence = "high" if len(mock_listings) >= 3 else "medium" if len(mock_listings) >= 2 else "low"

    return MockImageMatchResult(
        matches_found=len(mock_listings),
        best_match=mock_listings[0],
        all_matches=mock_listings,
        average_price=avg_price,
        price_range=price_range,
        confidence=confidence
    )


async def mock_match_product_with_sold_listings(reference_image_path: str,
                                               search_term: str,
                                               headless: bool = True,
                                               max_results: int = 5):
    """
    Mock version of match_product_with_sold_listings for demonstration
    """
    print(f"[MOCK] Analyzing image: {reference_image_path}")
    print(f"[MOCK] Search term: {search_term}")
    print(f"[MOCK] Headless mode: {headless}")
    print(f"[MOCK] Creating demonstration results...")

    # Simulate some processing time
    import asyncio
    await asyncio.sleep(2)

    return create_mock_image_comparison_result(search_term)


if __name__ == '__main__':
    import asyncio

    if len(sys.argv) > 1:
        search_term = ' '.join(sys.argv[1:])
    else:
        search_term = "Yura Kano photobook"

    async def demo():
        print("=== eBay Image Comparison Demo ===")
        print("This demonstrates what the results would look like")
        print("without actually accessing eBay.")
        print()

        result = await mock_match_product_with_sold_listings(
            "demo_image.jpg",
            search_term,
            headless=True
        )

        print(f"Search term: {search_term}")
        print(f"Matches found: {result.matches_found}")
        print(f"Confidence: {result.confidence}")

        if result.matches_found > 0:
            print(f"\nPrice Analysis:")
            print(f"  Average: ${result.average_price:.2f}")
            print(f"  Range: ${result.price_range[0]:.2f} - ${result.price_range[1]:.2f}")

            print(f"\nBest Match:")
            best = result.best_match
            print(f"  Title: {best.title}")
            print(f"  Price: ${best.price}")
            print(f"  Similarity: {best.image_similarity:.1%}")
            print(f"  Sold: {best.sold_date}")

            if len(result.all_matches) > 1:
                print(f"\nAll Matches:")
                for i, match in enumerate(result.all_matches, 1):
                    print(f"  {i}. {match.title[:50]}...")
                    print(f"     ${match.price} | {match.image_similarity:.1%} similar | {match.sold_date}")
        else:
            print("No matches found in this demo")

    asyncio.run(demo())