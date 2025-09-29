#!/usr/bin/env python3
"""Test CSV filename matching logic"""

from pathlib import Path
import json

# Simulate the new slugify function
import re
import unicodedata
import hashlib

def _slugify(value: str) -> str:
    if not value:
        return 'all'
    value = str(value).strip()

    # Handle Unicode characters better
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

def _generate_csv_filename(config: dict) -> str:
    """Generate CSV filename based on search parameters"""
    keyword = _slugify(str(config.get('keyword', 'search')))
    category = config.get('category')
    if isinstance(category, list):
        category = category[0] if category else ''
    category = _slugify(str(category or 'all'))
    shop = _slugify(str(config.get('shop', 'all')))
    return f"{keyword}_{category}_{shop}.csv"

# Test with existing config
try:
    with open('configs/all_050801_all.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    print("Loaded config:")
    keyword = config.get('keyword', '')
    print(f"  Keyword: {len(keyword)} characters")
    print(f"  Category: {config.get('category')}")
    print(f"  Shop: {config.get('shop', 'all')}")

    generated = _generate_csv_filename(config)
    print(f"Generated CSV filename: {generated}")

    # Check existing CSV files
    results_dir = Path('results')
    existing_csvs = list(results_dir.glob('*.csv'))
    print(f"Existing CSV files: {[f.name for f in existing_csvs]}")

    # Test pattern matching
    keyword = _slugify(str(config.get('keyword', 'search')))
    category = config.get('category')
    if isinstance(category, list):
        category = category[0] if category else ''
    category = _slugify(str(category or 'all'))

    pattern_base = f"{keyword}_{category}_"
    matches = [f for f in existing_csvs if f.name.startswith(pattern_base)]
    print(f"Pattern matches for '{pattern_base}': {[f.name for f in matches]}")

except Exception as e:
    print(f"Error: {e}")