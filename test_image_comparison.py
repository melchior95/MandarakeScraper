"""
Test script to evaluate image comparison algorithm on Yura Kano dataset.
This will compare all CSV items against all eBay items and report scores.
"""
import cv2
import numpy as np
from pathlib import Path
import sys

# Import the compare_images function from workers
sys.path.insert(0, str(Path(__file__).parent / "gui"))
from workers import compare_images

def load_image(path):
    """Load image from path."""
    img = cv2.imread(str(path))
    if img is None:
        print(f"Failed to load: {path}")
        return None
    return img

def main():
    # Find the most recent Yura Kano debug folder
    debug_base = Path("debug_comparison")
    yura_folders = sorted([f for f in debug_base.glob("Yura_Kano*")], reverse=True)

    if not yura_folders:
        print("No Yura Kano debug folders found!")
        return

    folder = yura_folders[0]
    print(f"Testing with folder: {folder.name}\n")

    # Load all CSV reference images
    csv_images = sorted(folder.glob("CSV_*_REF_*.jpg"))
    ebay_images = sorted(folder.glob("ebay_*.jpg"))

    print(f"Found {len(csv_images)} CSV images and {len(ebay_images)} eBay images\n")

    # Expected matches (based on user input)
    expected_matches = {
        "Magical_Girlfriend": True,
        "Paragraph": True,
        "I'll_do_it_properly_tomorrow": True,
    }

    results = []

    # Compare each CSV image against all eBay images
    for csv_path in csv_images:
        csv_img = load_image(csv_path)
        if csv_img is None:
            continue

        # Extract item name from filename
        csv_name = csv_path.stem.replace("CSV_01_REF_", "").replace("Yura_Kano_", "")

        print(f"\n{'='*80}")
        print(f"CSV Item: {csv_name}")
        print(f"{'='*80}")

        best_score = 0.0
        best_match = None

        for ebay_path in ebay_images:
            ebay_img = load_image(ebay_path)
            if ebay_img is None:
                continue

            ebay_name = ebay_path.stem

            # Compare images
            score = compare_images(csv_img, ebay_img)

            print(f"  vs {ebay_name}: {score:.1f}%")

            if score > best_score:
                best_score = score
                best_match = ebay_name

        # Check if this should be a match
        is_expected_match = any(key in csv_name for key in expected_matches.keys())

        results.append({
            'name': csv_name,
            'best_score': best_score,
            'best_match': best_match,
            'expected_match': is_expected_match
        })

        status = "✓ MATCH" if is_expected_match else "✗ NON-MATCH"
        print(f"\n  Best: {best_match} ({best_score:.1f}%) [{status}]")

    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    print("Expected MATCHES (should have HIGH scores):")
    for r in results:
        if r['expected_match']:
            print(f"  {r['name']}: {r['best_score']:.1f}%")

    print("\nExpected NON-MATCHES (should have LOW scores):")
    for r in results:
        if not r['expected_match']:
            print(f"  {r['name']}: {r['best_score']:.1f}%")

    # Calculate separation
    match_scores = [r['best_score'] for r in results if r['expected_match']]
    non_match_scores = [r['best_score'] for r in results if not r['expected_match']]

    if match_scores and non_match_scores:
        avg_match = sum(match_scores) / len(match_scores)
        avg_non_match = sum(non_match_scores) / len(non_match_scores)
        min_match = min(match_scores)
        max_non_match = max(non_match_scores)

        print(f"\n{'='*80}")
        print(f"Average MATCH score: {avg_match:.1f}%")
        print(f"Average NON-MATCH score: {avg_non_match:.1f}%")
        print(f"Separation: {avg_match - avg_non_match:.1f}%")
        print(f"\nWorst match: {min_match:.1f}%")
        print(f"Best non-match: {max_non_match:.1f}%")
        print(f"Gap: {min_match - max_non_match:.1f}%")

        if min_match > max_non_match:
            print(f"\n✓ GOOD SEPARATION - Clear distinction between matches and non-matches")
        else:
            print(f"\n✗ POOR SEPARATION - Overlap between matches and non-matches")

if __name__ == "__main__":
    main()
