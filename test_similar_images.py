#!/usr/bin/env python3
"""
Test the improved image matching on the specific similar images
"""

import cv2
import numpy as np
import logging
from sold_listing_matcher import SoldListingMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_similar_images():
    """Test the specific similar images that should match"""

    print("=== Testing Similar Image Matching ===")
    print()

    # Image paths
    reference_path = r"C:\Python Projects\mandarake_scraper\images\naruto\thumb_product_0003.jpg"
    comparison_path = r"C:\Python Projects\mandarake_scraper\debug_images\comparison_20250928_202019\listing_01.jpg"

    print(f"Reference image: {reference_path}")
    print(f"Comparison image: {comparison_path}")
    print()

    # Create matcher with improved algorithm
    matcher = SoldListingMatcher(similarity_threshold=0.3)  # Lower threshold for testing

    try:
        print("Loading reference image...")
        ref_image = cv2.imread(reference_path)
        if ref_image is None:
            print("❌ Could not load reference image")
            return

        print("Loading comparison image...")
        comp_image = cv2.imread(comparison_path)
        if comp_image is None:
            print("❌ Could not load comparison image")
            return

        print("Extracting features from reference image...")
        ref_features = matcher._extract_image_features(ref_image)

        print("Extracting features from comparison image...")
        comp_features = matcher._extract_image_features(comp_image)

        print()
        print("Feature extraction results:")
        print(f"Reference ORB features: {len(ref_features['orb'])}")
        print(f"Comparison ORB features: {len(comp_features['orb'])}")
        print(f"Reference color histogram: {len(ref_features['color_hist'])}")
        print(f"Comparison color histogram: {len(comp_features['color_hist'])}")
        print()

        print("Calculating similarity...")
        similarity = matcher._calculate_image_similarity(ref_features, comp_features)

        print(f"Final similarity score: {similarity:.4f}")
        print(f"Threshold: {matcher.similarity_threshold}")

        if similarity >= matcher.similarity_threshold:
            print("SUCCESS: MATCH FOUND! Images are considered similar.")
        else:
            print("FAIL: NO MATCH. Images below threshold.")
            print(f"   Need at least {matcher.similarity_threshold:.3f}, got {similarity:.3f}")
            print(f"   Difference: {(matcher.similarity_threshold - similarity):.3f}")

        # Test with different thresholds
        print()
        print("Testing with different thresholds:")
        for threshold in [0.1, 0.2, 0.3, 0.4, 0.5]:
            match = "MATCH" if similarity >= threshold else "NO MATCH"
            print(f"  Threshold {threshold:.1f}: {match} (score: {similarity:.3f})")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_similar_images()