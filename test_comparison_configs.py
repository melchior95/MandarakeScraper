"""
Compare results with:
1. Current (multiplier, no RANSAC) - use_ransac=False
2. Multiplier + RANSAC - use_ransac=True

For "old" version (no multiplier), you'll need to manually edit workers.py
to disable consistency bonus, then run analyze_all_comparisons.py
"""
import cv2
import numpy as np
from pathlib import Path
import sys
import time

# Import the compare_images function from workers
sys.path.insert(0, str(Path(__file__).parent / "gui"))
from workers import compare_images

# Expected matches based on user input
EXPECTED_MATCHES = [
    "Magical_Girlfriend",
    "Paragraph",
    "Ill_do_it_properly",
]

def load_image(path):
    """Load image from path."""
    img = cv2.imread(str(path))
    return img

def extract_item_name(csv_path):
    """Extract item name from CSV filename."""
    name = csv_path.stem.replace("CSV_01_REF_", "").replace("Yura_Kano_", "")
    return name

def run_test(use_ransac, config_name):
    """Run comparison test."""
    debug_base = Path("debug_comparison")
    folders = sorted([f for f in debug_base.glob("Yura_Kano_Photobook_*")], reverse=True)

    print(f"\n{'='*80}")
    print(f"Testing: {config_name}")
    print(f"{'='*80}\n")

    results = []
    start_time = time.time()

    for folder in folders:
        csv_images = list(folder.glob("CSV_*_REF_*.jpg"))
        if not csv_images:
            continue

        csv_path = csv_images[0]
        csv_img = load_image(csv_path)
        if csv_img is None:
            continue

        item_name = extract_item_name(csv_path)
        ebay_images = sorted(folder.glob("ebay_*.jpg"))
        if not ebay_images:
            continue

        best_score = 0.0

        for ebay_path in ebay_images:
            ebay_img = load_image(ebay_path)
            if ebay_img is None:
                continue

            score = compare_images(csv_img, ebay_img, use_ransac=use_ransac)

            if score > best_score:
                best_score = score

        is_expected = any(exp in item_name for exp in EXPECTED_MATCHES)

        symbol = "[MATCH]" if is_expected else "[NO-MATCH]"
        print(f"{item_name}: {best_score:.1f}% {symbol}")

        results.append({
            'name': item_name,
            'score': best_score,
            'is_match': is_expected
        })

    elapsed = time.time() - start_time

    # Calculate statistics
    match_results = [r for r in results if r['is_match']]
    non_match_results = [r for r in results if not r['is_match']]

    match_scores = [r['score'] for r in match_results]
    non_match_scores = [r['score'] for r in non_match_results]

    print(f"\n{'='*80}")
    print(f"SUMMARY - {config_name}")
    print(f"{'='*80}\n")

    print(f"Expected MATCHES ({len(match_results)} items):")
    for r in sorted(match_results, key=lambda x: x['score'], reverse=True):
        print(f"  {r['score']:5.1f}% - {r['name']}")

    print(f"\nExpected NON-MATCHES ({len(non_match_results)} items):")
    for r in sorted(non_match_results, key=lambda x: x['score'], reverse=True):
        print(f"  {r['score']:5.1f}% - {r['name']}")

    if match_scores and non_match_scores:
        avg_match = sum(match_scores) / len(match_scores)
        avg_non_match = sum(non_match_scores) / len(non_match_scores)
        min_match = min(match_scores)
        max_non_match = max(non_match_scores)
        gap = min_match - max_non_match

        print(f"\n{'='*80}")
        print(f"Average MATCH: {avg_match:.1f}%   |   Average NON-MATCH: {avg_non_match:.1f}%")
        print(f"Worst MATCH: {min_match:.1f}%   |   Best NON-MATCH: {max_non_match:.1f}%")
        print(f"Separation gap: {gap:.1f}%")
        print(f"Processing time: {elapsed:.2f}s")

        return {
            'config': config_name,
            'avg_match': avg_match,
            'avg_non_match': avg_non_match,
            'min_match': min_match,
            'max_non_match': max_non_match,
            'gap': gap,
            'time': elapsed
        }

    return None

def main():
    print("="*80)
    print("IMAGE COMPARISON ALGORITHM TEST")
    print("="*80)

    results = []

    # Test without RANSAC (current multiplier version)
    result1 = run_test(False, "Multiplier (no RANSAC)")
    if result1:
        results.append(result1)

    # Test with RANSAC
    result2 = run_test(True, "Multiplier + RANSAC")
    if result2:
        results.append(result2)

    # Final comparison
    if len(results) >= 2:
        print(f"\n\n{'='*80}")
        print("FINAL COMPARISON")
        print(f"{'='*80}\n")

        print(f"{'Configuration':<30} {'Avg Match':>10} {'Gap':>10} {'Time':>10}")
        print("-"*80)
        for r in results:
            print(f"{r['config']:<30} {r['avg_match']:>9.1f}% {r['gap']:>9.1f}% {r['time']:>9.2f}s")

        print(f"\n\nTo test 'Old' versions (without consistency bonus):")
        print(f"1. Edit gui/workers.py")
        print(f"2. Find the lines with 'consistency_multiplier = 1.25' and '= 1.15'")
        print(f"3. Comment them out or set multiplier to always be 1.0")
        print(f"4. Run this script again")

if __name__ == "__main__":
    main()
