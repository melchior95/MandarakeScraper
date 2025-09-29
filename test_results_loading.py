#!/usr/bin/env python3
"""Test results loading and image display"""

from pathlib import Path
import csv
import json

# Test the CSV matching logic
def test_csv_matching():
    # Load an existing config
    with open('configs/all_050801_all.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    print(f"Config loaded - keyword: {len(config.get('keyword', ''))} chars")

    # Test what CSV files exist
    results_dir = Path('results')
    csv_files = list(results_dir.glob('*.csv'))
    print(f"Available CSV files: {[f.name for f in csv_files]}")

    # Test manually loading a CSV
    csv_path = results_dir / 'all_050801_0.csv'  # We know this exists
    if csv_path.exists():
        print(f"Testing CSV load: {csv_path}")

        try:
            with csv_path.open('r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                print(f"CSV loaded successfully - {len(rows)} rows")

                if rows:
                    row = rows[0]
                    print(f"First row columns: {list(row.keys())}")
                    print(f"Has image_url: {'image_url' in row}")
                    print(f"Has local_image: {'local_image' in row}")

                    if 'image_url' in row and row['image_url']:
                        print(f"Image URL example: {row['image_url'][:50]}...")

        except Exception as e:
            print(f"Error loading CSV: {e}")
    else:
        print(f"CSV file not found: {csv_path}")

if __name__ == "__main__":
    test_csv_matching()