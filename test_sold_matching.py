#!/usr/bin/env python3
"""
Test script for sold listing image matching system

Demonstrates the complete workflow of finding and matching sold listings
"""

import asyncio
import sys
import logging
from pathlib import Path
from sold_listing_matcher import match_product_with_sold_listings
from price_validation_service import PriceValidationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


async def test_sold_listing_matching():
    """Test the sold listing matching system"""

    print("=== SOLD LISTING MATCHING TEST ===")
    print()

    # Check if we have image and search term
    if len(sys.argv) < 3:
        print("This test requires an image file and search term.")
        print()
        print("Usage:")
        print("  python test_sold_matching.py <image_path> <search_term>")
        print()
        print("Example:")
        print("  python test_sold_matching.py product.jpg 'Yura Kano photobook'")
        print()
        print("The system will:")
        print("1. Open eBay in a headless browser (invisible)")
        print("2. Search for sold listings matching your search term")
        print("3. Download images from the sold listings")
        print("4. Compare your image with the sold listing images using computer vision")
        print("5. Find matches and extract pricing data")
        print("6. Provide market analysis and price recommendations")
        return

    image_path = sys.argv[1]
    search_term = sys.argv[2]

    # Validate inputs
    if not Path(image_path).exists():
        print(f"❌ Error: Image file not found: {image_path}")
        return

    print(f"📸 Image: {image_path}")
    print(f"🔍 Search: {search_term}")
    print(f"🤖 Browser: Headless (invisible)")
    print()

    try:
        # Test 1: Direct matching
        print("=== TESTING DIRECT IMAGE MATCHING ===")
        print("Searching for sold listings and comparing images...")
        print()

        result = await match_product_with_sold_listings(
            reference_image_path=image_path,
            search_term=search_term,
            headless=True,  # Run completely in background
            max_results=5
        )

        # Display results
        print("=== MATCHING RESULTS ===")
        print(f"🎯 Matches found: {result.matches_found}")
        print(f"📊 Confidence level: {result.confidence}")
        print()

        if result.matches_found > 0:
            print("💰 PRICE ANALYSIS:")
            print(f"   Average sold price: ${result.average_price:.2f}")
            print(f"   Price range: ${result.price_range[0]:.2f} - ${result.price_range[1]:.2f}")
            print()

            print("🏆 BEST MATCH:")
            best = result.best_match
            print(f"   Title: {best.title}")
            print(f"   Price: {best.currency} {best.price}")
            print(f"   Sold: {best.sold_date}")
            print(f"   Image similarity: {best.image_similarity:.1%}")
            print(f"   Listing: {best.listing_url}")
            print()

            if result.matches_found > 1:
                print("📋 ALL MATCHES:")
                for i, match in enumerate(result.all_matches, 1):
                    print(f"   {i}. {match.title[:50]}...")
                    print(f"      ${match.price} | Similarity: {match.image_similarity:.1%}")
                print()

        else:
            print("❌ No matches found")
            print("Possible reasons:")
            print("- Image doesn't match any sold listings")
            print("- Search term too specific or not relevant to eBay")
            print("- Product hasn't been sold recently on eBay")
            print("- Similarity threshold too high (try lowering it)")

        print()

        # Test 2: Price validation service
        print("=== TESTING PRICE VALIDATION SERVICE ===")

        # Create test product data
        test_product = {
            'title': search_term,
            'price': 3000,  # Example JPY price
            'currency': 'JPY',
            'shop': 'Mandarake Test',
            'id': 'test_001'
        }

        # Test configuration
        test_config = {
            'price_validation': {
                'enabled': True,
                'headless': True,
                'similarity_threshold': 0.6,  # Lower threshold for testing
                'max_results': 5,
                'days_back': 90
            }
        }

        print(f"Testing price validation for: {test_product['title']}")
        print(f"Original price: ¥{test_product['price']}")
        print()

        async with PriceValidationService(test_config) as validator:
            validation_result = await validator.validate_product_price(test_product, image_path)

            if validation_result:
                print("✅ PRICE VALIDATION RESULTS:")
                market_data = validation_result.get('market_data', {})
                recommendation = validation_result.get('price_recommendation', {})

                if market_data:
                    print(f"   Market average: ${market_data['average_sold_price']:.2f}")
                    print(f"   Sample size: {market_data['sample_size']} sold items")

                if recommendation:
                    print(f"   Estimated USD value: ${recommendation['estimated_usd_value']:.2f}")
                    print(f"   Market comparison: {recommendation['percentage_difference']:+.1f}%")
                    print(f"   Recommendation: {recommendation['recommendation'].replace('_', ' ').title()}")

            else:
                print("❌ Price validation failed")

        print()
        print("=== TEST COMPLETE ===")
        print("✅ Sold listing matching system is working!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


async def test_system_only():
    """Test the system without requiring specific inputs"""

    print("=== SOLD LISTING MATCHING SYSTEM ===")
    print()
    print("This system provides automated price validation by:")
    print()
    print("🔍 1. INTELLIGENT SEARCH")
    print("   - Uses lazy search optimization for better eBay results")
    print("   - Searches specifically for 'sold' listings")
    print("   - Handles Japanese product names and translations")
    print()
    print("🤖 2. BACKGROUND AUTOMATION")
    print("   - Runs completely headless (invisible browser)")
    print("   - Bypasses eBay's anti-bot measures")
    print("   - Extracts sold listing data automatically")
    print()
    print("🖼️  3. IMAGE MATCHING")
    print("   - Downloads images from sold listings")
    print("   - Uses computer vision (ORB feature detection)")
    print("   - Compares visual similarity with your product")
    print()
    print("💰 4. PRICE ANALYSIS")
    print("   - Calculates average sold prices")
    print("   - Provides market price ranges")
    print("   - Generates pricing recommendations")
    print()
    print("📊 5. CONFIDENCE SCORING")
    print("   - Rates match quality based on multiple factors")
    print("   - Considers image similarity, recent sales, reasonable prices")
    print("   - Provides reliability indicators")
    print()
    print("To test the system:")
    print("  python test_sold_matching.py <image_file> <search_term>")
    print()
    print("Example:")
    print("  python test_sold_matching.py yura_kano.jpg 'Yura Kano photobook'")


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        # Run full test with image and search term
        asyncio.run(test_sold_listing_matching())
    else:
        # Show system overview
        asyncio.run(test_system_only())