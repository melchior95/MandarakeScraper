#!/usr/bin/env python3
"""
Test script to verify prefetch image extraction from saved eBay HTML
"""

import sys
import logging
from bs4 import BeautifulSoup
from sold_listing_matcher_requests import SoldListingMatcherRequests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_prefetch_extraction():
    """Test prefetch image extraction from saved eBay HTML"""

    # Read the saved eBay HTML
    try:
        with open('debug_ebay_page.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        print(f"Loaded HTML file: {len(html_content):,} characters")
    except Exception as e:
        print(f"Error reading HTML file: {e}")
        return

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    print(f"HTML parsed successfully")

    # Create matcher and test prefetch extraction
    matcher = SoldListingMatcherRequests(similarity_threshold=0.3)

    # Test the prefetch extraction method directly
    print("\n=== Testing prefetch image extraction ===")
    listings = matcher._extract_from_prefetch_images(soup, max_results=10)

    print(f"\nExtracted {len(listings)} listings from prefetch images")

    if listings:
        print("\n=== LISTINGS FOUND ===")
        for i, listing in enumerate(listings, 1):
            print(f"{i}. {listing.title}")
            print(f"   Image: {listing.image_url[:80]}...")
            print(f"   Price: ${listing.price} {listing.currency}")
            print()
    else:
        print("\nNo listings extracted. Let's debug...")

        # Check for prefetch container
        prefetch_container = soup.select_one('.s-prefetch-image')
        if prefetch_container:
            print("✓ Found prefetch image container")

            # Check for images
            prefetch_images = prefetch_container.select('img[src*="ebayimg.com"]')
            print(f"✓ Found {len(prefetch_images)} eBay images in container")

            if prefetch_images:
                print("\nFirst 3 image URLs:")
                for i, img in enumerate(prefetch_images[:3]):
                    src = img.get('src', 'No src')
                    print(f"  {i+1}. {src[:100]}...")

        else:
            print("✗ No prefetch image container found")

            # Check if there are any eBay images at all
            all_ebay_imgs = soup.select('img[src*="ebayimg.com"]')
            print(f"Found {len(all_ebay_imgs)} total eBay images on page")

            if all_ebay_imgs:
                print("First 3 eBay image URLs found anywhere:")
                for i, img in enumerate(all_ebay_imgs[:3]):
                    src = img.get('src', 'No src')
                    print(f"  {i+1}. {src[:100]}...")

if __name__ == '__main__':
    test_prefetch_extraction()