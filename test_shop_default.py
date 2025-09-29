#!/usr/bin/env python3
"""Test the new default shop behavior"""

import re
import unicodedata
import hashlib

def _slugify(value: str) -> str:
    if not value:
        return 'all'
    value = str(value).strip()

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

    # Handle shop with special default to '0'
    shop_value = config.get('shop', '0')
    if not shop_value or shop_value.strip() == '':
        shop_value = '0'
    shop = _slugify(str(shop_value))
    return f"{keyword}_{category}_{shop}.csv"

# Test cases
test_configs = [
    {
        'keyword': '羽田あい',
        'category': '050801',
        # No shop specified - should default to '0'
    },
    {
        'keyword': 'naruto',
        'category': '050801',
        'shop': 'nakano'
    },
    {
        'keyword': 'test',
        'category': '050801',
        'shop': ''  # Empty shop - should default to '0'
    },
    {
        'keyword': 'haneda ai',
        'category': ['050801', '050802'],  # List category
        'shop': '0'  # Explicit shop 0
    }
]

print("Testing new default shop behavior:")
for i, config in enumerate(test_configs):
    filename = _generate_csv_filename(config)
    shop_value = config.get('shop', '0')
    keyword = config.get('keyword', '')
    print(f"Test {i+1}:")
    print(f"  Config: keyword={len(keyword)} chars, category={config.get('category')}, shop='{shop_value}'")
    print(f"  Generated CSV: {filename}")
    print()