#!/usr/bin/env python3
"""Test the new slugify function"""

import re
import unicodedata
import hashlib

def _slugify(value: str) -> str:
    if not value:
        return 'all'
    value = str(value).strip()

    # Handle Unicode characters better - create readable ASCII representation
    try:
        # Try to normalize and convert to ASCII
        normalized = unicodedata.normalize('NFKD', value)
        ascii_value = normalized.encode('ascii', 'ignore').decode('ascii')
        if ascii_value.strip():
            value = ascii_value
    except:
        pass

    # If still contains non-ASCII, use a hash-based approach for unique identification
    if not value.isascii():
        hash_part = hashlib.md5(value.encode('utf-8')).hexdigest()[:8]
        # Try to extract any ASCII parts
        ascii_parts = re.findall(r'[a-zA-Z0-9]+', value)
        if ascii_parts:
            value = '_'.join(ascii_parts) + '_' + hash_part
        else:
            value = 'unicode_' + hash_part

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", '_', value)
    value = value.strip('_')
    return value or 'all'

# Test cases
test_cases = [
    "羽田あい",
    "naruto",
    "test search",
    "",
    "123",
    "あいうえお",
    "Haneda Ai",
    "ナルト"
]

print("Testing new slugify function:")
for i, test in enumerate(test_cases):
    result = _slugify(test)
    print(f"Test {i+1}: {len(test)} chars -> '{result}'")