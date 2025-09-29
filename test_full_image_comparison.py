#!/usr/bin/env python3
"""
Test full end-to-end image comparison by downloading a reference image and testing against eBay
"""

import os
import sys
import logging
import requests
from datetime import datetime
from sold_listing_matcher_requests import match_product_with_sold_listings_requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_full_image_comparison():
    """Test full image comparison flow"""

    print("=== Full eBay Image Comparison Test ===")
    print()

    # Create debug directory
    debug_dir = f"debug_images/full_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(debug_dir, exist_ok=True)
    print(f"Debug directory: {os.path.abspath(debug_dir)}")

    # Download a reference Pokemon card image from the prefetch URLs we found
    reference_urls = [
        "https://i.ebayimg.com/images/g/FuYAAeSwRuVo2c6I/s-l500.webp",
        "https://i.ebayimg.com/images/g/b0kAAeSw1SNow6Ix/s-l500.webp"
    ]

    reference_path = None
    for i, url in enumerate(reference_urls):
        try:
            print(f"Downloading reference image {i+1}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Convert webp to jpg for better compatibility
                reference_path = os.path.join(debug_dir, f"reference_image_{i+1}.webp")
                with open(reference_path, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded reference image: {reference_path}")
                break
        except Exception as e:
            print(f"Failed to download image {i+1}: {e}")

    if not reference_path:
        print("❌ Could not download any reference image")
        return

    # Now test the full image comparison
    print(f"\n=== Testing Image Comparison ===")
    print(f"Reference image: {reference_path}")
    print(f"Search term: pokemon card")
    print()

    try:
        result = match_product_with_sold_listings_requests(
            reference_image_path=reference_path,
            search_term="pokemon card",
            similarity_threshold=0.3,  # Lower threshold to see more comparisons
            max_results=5,
            debug_output_dir=debug_dir
        )

        print(f"=== RESULTS ===")
        print(f"Matches found: {result.matches_found}")
        print(f"Confidence: {result.confidence}")

        if result.matches_found > 0:
            print(f"\n=== MATCHES ===")
            for i, match in enumerate(result.all_matches, 1):
                print(f"{i}. {match.title[:50]}...")
                print(f"   Price: ${match.price}")
                print(f"   Similarity: {match.image_similarity:.3f}")
                print(f"   Confidence: {match.confidence_score:.3f}")
                print()

            print(f"Price Analysis:")
            print(f"  Average: ${result.average_price:.2f}")
            print(f"  Range: ${result.price_range[0]:.2f} - ${result.price_range[1]:.2f}")
        else:
            print("No matches found above threshold")

        # Check what images were saved
        if os.path.exists(debug_dir):
            saved_images = [f for f in os.listdir(debug_dir) if f.endswith(('.jpg', '.png', '.webp'))]
            print(f"\n=== SAVED IMAGES ===")
            print(f"Total images saved: {len(saved_images)}")

            for img in sorted(saved_images):
                img_path = os.path.join(debug_dir, img)
                size = os.path.getsize(img_path)
                print(f"  {img} ({size:,} bytes)")

            print(f"\nYou can inspect the images in:")
            print(f"  {os.path.abspath(debug_dir)}")

        print(f"\n✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_full_image_comparison()