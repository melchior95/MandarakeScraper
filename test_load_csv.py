#!/usr/bin/env python3
"""Test the Load CSV functionality"""

from pathlib import Path

def test_csv_files():
    """Check what CSV files are available for testing"""
    results_dir = Path('results')

    if not results_dir.exists():
        print("Results directory doesn't exist")
        return

    csv_files = list(results_dir.glob('*.csv'))
    print(f"Available CSV files in results directory:")

    for csv_file in csv_files:
        print(f"  - {csv_file.name}")

        # Check file size and row count
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"    Size: {csv_file.stat().st_size} bytes, {len(lines)} lines")

                # Check if it has the expected columns
                if lines:
                    header = lines[0].strip()
                    has_images = 'image_url' in header or 'local_image' in header
                    print(f"    Has image columns: {has_images}")

        except Exception as e:
            print(f"    Error reading file: {e}")

        print()

if __name__ == "__main__":
    test_csv_files()