"""
Test all 4 configurations of the image comparison algorithm:
1. Old (no consistency bonus, no RANSAC)
2. Multiplier (consistency bonus, no RANSAC)
3. Old + RANSAC (no consistency bonus, RANSAC enabled)
4. Multiplier + RANSAC (consistency bonus + RANSAC)
"""
import cv2
import numpy as np
from pathlib import Path
import sys
import importlib

# Import the compare_images function from workers
sys.path.insert(0, str(Path(__file__).parent / "gui"))

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

def run_test(config_name, use_consistency, use_ransac):
    """Run comparison test with specified configuration."""
    # Reload workers to get the current version
    import workers
    importlib.reload(workers)

    # Temporarily disable consistency bonus if needed
    original_code = None
    if not use_consistency:
        # Read the workers.py file and modify consistency_multiplier to always be 1.0
        workers_path = Path(__file__).parent / "gui" / "workers.py"
        with open(workers_path, 'r', encoding='utf-8') as f:
            original_code = f.read()

        # Modify to disable consistency bonus
        modified_code = original_code.replace(
            "if high_count >= 3:\n            consistency_multiplier = 1.25",
            "if False:  # DISABLED\n            consistency_multiplier = 1.25"
        ).replace(
            "elif high_count >= 2:\n            consistency_multiplier = 1.15",
            "elif False:  # DISABLED\n            consistency_multiplier = 1.15"
        )

        with open(workers_path, 'w', encoding='utf-8') as f:
            f.write(modified_code)

        # Reload with modified code
        importlib.reload(workers)

    from workers import compare_images

    debug_base = Path("debug_comparison")
    folders = sorted([f for f in debug_base.glob("Yura_Kano_Photobook_*")], reverse=True)

    results = []

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

        results.append({
            'name': item_name,
            'score': best_score,
            'is_match': is_expected
        })

    # Restore original code if we modified it
    if original_code:
        with open(workers_path, 'w', encoding='utf-8') as f:
            f.write(original_code)
        importlib.reload(workers)

    # Calculate statistics
    match_results = [r for r in results if r['is_match']]
    non_match_results = [r for r in results if not r['is_match']]

    match_scores = [r['score'] for r in match_results]
    non_match_scores = [r for r in non_match_results]

    if match_scores and non_match_scores:
        avg_match = sum(match_scores) / len(match_scores)
        avg_non_match = sum(non_match_scores) / len(non_match_scores)
        min_match = min(match_scores)
        max_non_match = max(non_match_scores)
        gap = min_match - max_non_match

        return {
            'config': config_name,
            'avg_match': avg_match,
            'avg_non_match': avg_non_match,
            'min_match': min_match,
            'max_non_match': max_non_match,
            'gap': gap,
            'match_results': match_results,
            'non_match_results': non_match_results
        }

    return None

def main():
    print("="*80)
    print("COMPREHENSIVE ALGORITHM COMPARISON TEST")
    print("="*80)
    print()

    configs = [
        ("1. Old (no bonus, no RANSAC)", False, False),
        ("2. Multiplier (bonus, no RANSAC)", True, False),
        ("3. Old + RANSAC (no bonus, RANSAC)", False, True),
        ("4. Multiplier + RANSAC (bonus + RANSAC)", True, True),
    ]

    all_results = []

    for config_name, use_consistency, use_ransac in configs:
        print(f"\n{'='*80}")
        print(f"Testing: {config_name}")
        print(f"{'='*80}\n")

        result = run_test(config_name, use_consistency, use_ransac)
        if result:
            all_results.append(result)

            print(f"\nResults for {config_name}:")
            print(f"  Average MATCH: {result['avg_match']:.1f}%")
            print(f"  Average NON-MATCH: {result['avg_non_match']:.1f}%")
            print(f"  Worst MATCH: {result['min_match']:.1f}%")
            print(f"  Best NON-MATCH: {result['max_non_match']:.1f}%")
            print(f"  Separation gap: {result['gap']:.1f}%")

    # Final comparison
    print(f"\n\n{'='*80}")
    print("FINAL COMPARISON")
    print(f"{'='*80}\n")

    print(f"{'Configuration':<40} {'Avg Match':<12} {'Avg Non':<12} {'Gap':<10}")
    print("-"*80)
    for r in all_results:
        print(f"{r['config']:<40} {r['avg_match']:>10.1f}% {r['avg_non_match']:>10.1f}% {r['gap']:>8.1f}%")

    # Find best configuration
    best_gap = max(all_results, key=lambda x: x['gap'])
    best_match = max(all_results, key=lambda x: x['avg_match'])

    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")
    print(f"\nBest separation: {best_gap['config']} (gap: {best_gap['gap']:.1f}%)")
    print(f"Highest match scores: {best_match['config']} (avg: {best_match['avg_match']:.1f}%)")

if __name__ == "__main__":
    main()
