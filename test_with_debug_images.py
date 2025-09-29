#!/usr/bin/env python3
"""
Test script for debugging image comparison with saved images
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def test_with_debug_images():
    """Test image comparison and save all images for inspection"""

    if len(sys.argv) < 3:
        print("Usage: python test_with_debug_images.py <image_path> <search_term>")
        print("Example: python test_with_debug_images.py naruto.jpg 'naruto figure'")
        print()
        print("This will:")
        print("1. Search eBay for sold listings")
        print("2. Download all listing images")
        print("3. Save images to debug_images/ folder")
        print("4. Show comparison results")
        return

    image_path = sys.argv[1]
    search_term = sys.argv[2]

    # Check if image exists
    if not Path(image_path).exists():
        print(f"❌ Image not found: {image_path}")
        return

    print("=== eBay Image Comparison Debug Test ===")
    print(f"Reference image: {image_path}")
    print(f"Search term: {search_term}")
    print()

    # Create debug directory
    debug_dir = f"debug_images/test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(debug_dir, exist_ok=True)

    print(f"Debug images will be saved to: {os.path.abspath(debug_dir)}")
    print()

    try:
        from sold_listing_matcher_requests import match_product_with_sold_listings_requests

        print("Starting eBay search and image comparison...")

        # Use a lower threshold to see more potential matches
        result = match_product_with_sold_listings_requests(
            reference_image_path=image_path,
            search_term=search_term,
            similarity_threshold=0.3,  # Lower threshold to see more comparisons
            max_results=5,
            debug_output_dir=debug_dir
        )

        print("\n=== RESULTS ===")
        print(f"Matches found: {result.matches_found}")
        print(f"Confidence: {result.confidence}")

        # Show what images were saved
        if os.path.exists(debug_dir):
            saved_images = [f for f in os.listdir(debug_dir) if f.endswith('.jpg')]
            print(f"\n=== SAVED IMAGES ===")
            print(f"Total images saved: {len(saved_images)}")

            for img in sorted(saved_images):
                img_path = os.path.join(debug_dir, img)
                size = os.path.getsize(img_path)
                print(f"  {img} ({size:,} bytes)")

            print(f"\nYou can now manually inspect the images in:")
            print(f"  {os.path.abspath(debug_dir)}")

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
            print("\nNo matches found above threshold.")
            print("Check the saved images to see what was downloaded and compared.")

        print(f"\n=== TROUBLESHOOTING ===")

        # Check if any images were actually downloaded
        if os.path.exists(debug_dir):
            image_files = [f for f in os.listdir(debug_dir) if f.endswith('.jpg')]

            if 'reference_image.jpg' in image_files:
                print("✅ Reference image was processed")
            else:
                print("❌ Reference image was not saved - check if input image is valid")

            listing_images = [f for f in image_files if f.startswith('listing_')]
            if listing_images:
                print(f"✅ Downloaded {len(listing_images)} listing images from eBay")
                print("   This means eBay search worked and images were found")
            else:
                print("❌ No listing images downloaded")
                print("   This could mean:")
                print("   - eBay blocked the request")
                print("   - No search results found")
                print("   - Images could not be downloaded")

            if not result.matches_found and listing_images:
                print(f"❓ Images downloaded but no matches found")
                print(f"   Try lowering the similarity threshold (currently 0.3)")
                print(f"   Or check if reference image is similar to listings")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_with_debug_images()