"""
Analyze all existing comparison results from debug folders.
"""
import cv2
import numpy as np
from pathlib import Path
import sys

# Import the compare_images function from workers
sys.path.insert(0, str(Path(__file__).parent / "gui"))
from workers import compare_images

# Expected matches based on user input
EXPECTED_MATCHES = [
    "Magical_Girlfriend",
    "Paragraph",
    "Ill_do_it_properly",  # Matches "Ill_do_it_properly_from_tomorrow"
]

def load_image(path):
    """Load image from path."""
    img = cv2.imread(str(path))
    return img

def extract_item_name(csv_path):
    """Extract item name from CSV filename."""
    name = csv_path.stem
    # Remove prefix
    name = name.replace("CSV_01_REF_", "").replace("Yura_Kano_", "")
    return name

def main():
    debug_base = Path("debug_comparison")

    # Find all Yura Kano comparison folders
    folders = sorted([f for f in debug_base.glob("Yura_Kano_Photobook_*")], reverse=True)

    print(f"Found {len(folders)} comparison folders\n")

    results = []

    for folder in folders:
        # Find CSV ref image
        csv_images = list(folder.glob("CSV_*_REF_*.jpg"))
        if not csv_images:
            continue

        csv_path = csv_images[0]
        csv_img = load_image(csv_path)
        if csv_img is None:
            continue

        item_name = extract_item_name(csv_path)

        # Find all eBay images
        ebay_images = sorted(folder.glob("ebay_*.jpg"))
        if not ebay_images:
            continue

        print(f"{item_name}:")

        best_score = 0.0
        best_match_idx = None

        for ebay_path in ebay_images:
            ebay_img = load_image(ebay_path)
            if ebay_img is None:
                continue

            score = compare_images(csv_img, ebay_img)

            if score > best_score:
                best_score = score
                best_match_idx = ebay_path.stem

        # Check if expected match
        is_expected = any(exp in item_name for exp in EXPECTED_MATCHES)

        symbol = "[MATCH]" if is_expected else "[NO-MATCH]"
        print(f"  Best: {best_score:.1f}% {symbol}\n")

        results.append({
            'name': item_name,
            'score': best_score,
            'is_match': is_expected
        })

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)

    match_results = [r for r in results if r['is_match']]
    non_match_results = [r for r in results if not r['is_match']]

    print(f"\nExpected MATCHES ({len(match_results)} items) - should be HIGH:")
    for r in sorted(match_results, key=lambda x: x['score'], reverse=True):
        print(f"  {r['score']:5.1f}% - {r['name']}")

    print(f"\nExpected NON-MATCHES ({len(non_match_results)} items) - should be LOW:")
    for r in sorted(non_match_results, key=lambda x: x['score'], reverse=True):
        print(f"  {r['score']:5.1f}% - {r['name']}")

    if match_results and non_match_results:
        match_scores = [r['score'] for r in match_results]
        non_match_scores = [r['score'] for r in non_match_results]

        avg_match = sum(match_scores) / len(match_scores)
        avg_non_match = sum(non_match_scores) / len(non_match_scores)
        min_match = min(match_scores)
        max_non_match = max(non_match_scores)

        print(f"\n" + "="*80)
        print(f"Average MATCH: {avg_match:.1f}%   |   Average NON-MATCH: {avg_non_match:.1f}%")
        print(f"Worst MATCH: {min_match:.1f}%   |   Best NON-MATCH: {max_non_match:.1f}%")
        print(f"\nSeparation gap: {min_match - max_non_match:.1f}%")

        if min_match > max_non_match + 10:
            print("STATUS: EXCELLENT - Clear separation with buffer")
        elif min_match > max_non_match:
            print("STATUS: GOOD - Matches higher than non-matches")
        else:
            print("STATUS: POOR - Overlap detected, needs adjustment")

if __name__ == "__main__":
    main()
