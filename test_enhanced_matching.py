#!/usr/bin/env python3
"""Test enhanced CSV matching logic"""

from pathlib import Path
import json

# Copy the enhanced find_matching_csv logic
def _slugify(value: str) -> str:
    if not value:
        return 'all'
    value = str(value).strip()

    import unicodedata
    import hashlib
    import re

    try:
        normalized = unicodedata.normalize('NFKD', value)
        ascii_value = normalized.encode('ascii', 'ignore').decode('ascii')
        if ascii_value.strip():
            value = ascii_value
    except:
        pass

    if not value.isascii():
        hash_part = hashlib.md5(value.encode('utf-8')).hexdigest()[:8]
        ascii_parts = re.findall(r'[a-zA-Z0-9]+', value)
        if ascii_parts:
            value = '_'.join(ascii_parts) + '_' + hash_part
        else:
            value = 'unicode_' + hash_part

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", '_', value)
    value = value.strip('_')
    return value or 'all'

def _find_matching_csv(config: dict):
    """Test version of find_matching_csv"""
    results_dir = Path('results')
    if not results_dir.exists():
        return None

    # Get slugified components
    keyword = _slugify(str(config.get('keyword', 'search')))
    category = config.get('category')
    if isinstance(category, list):
        category = category[0] if category else ''
    category = _slugify(str(category or 'all'))
    shop = _slugify(str(config.get('shop', 'all')))

    print(f"  Slugified keyword: '{keyword}'")
    print(f"  Slugified category: '{category}'")
    print(f"  Slugified shop: '{shop}'")

    # BACKWARD COMPATIBILITY check
    original_keyword = str(config.get('keyword', 'search')).strip()
    if not original_keyword.isascii() and original_keyword:
        print(f"  Trying backward compatibility for non-ASCII keyword")

        # Look for pattern 'all_category_shop'
        old_pattern_exact = f"all_{category}_{shop}.csv"
        old_path = results_dir / old_pattern_exact
        print(f"  Checking: {old_pattern_exact}")
        if old_path.exists():
            print(f"  FOUND backward compatible exact match: {old_path}")
            return old_path

        # Look for pattern 'all_category_*'
        old_pattern_base = f"all_{category}_"
        print(f"  Checking pattern: {old_pattern_base}*")
        for csv_file in results_dir.glob('*.csv'):
            if csv_file.name.startswith(old_pattern_base):
                print(f"  FOUND backward compatible category match: {csv_file}")
                return csv_file

    return None

# Test with the actual config
try:
    with open('configs/all_050801_all.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    print("Testing enhanced CSV matching:")
    print(f"Config keyword: {len(config.get('keyword', ''))} characters")
    print(f"Config category: {config.get('category')}")
    print(f"Config shop: {config.get('shop', 'all')}")
    print()

    # List existing files
    results_dir = Path('results')
    existing_csvs = list(results_dir.glob('*.csv'))
    print(f"Existing CSV files: {[f.name for f in existing_csvs]}")
    print()

    # Test matching
    result = _find_matching_csv(config)
    if result:
        print(f"SUCCESS: Found matching CSV: {result}")
    else:
        print("FAILED: No matching CSV found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()