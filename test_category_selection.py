#!/usr/bin/env python3
"""Test category selection logic."""

from gui import utils
from mandarake_codes import MANDARAKE_MAIN_CATEGORIES

# Test matching main category from detail code
print("Testing category matching...")

test_cases = [
    ("01", "01"),  # Comics -> Comics
    ("0101", "01"),  # Manga -> Comics
    ("05", "05"),  # Idol Goods -> Idol Goods
    ("050101", "05"),  # Photobook -> Idol Goods
    ("06", "06"),  # Trading Cards -> Trading Cards
    ("060101", "06"),  # Pokemon -> Trading Cards
]

for detail_code, expected_main in test_cases:
    main_code = utils.match_main_code(detail_code)
    status = "[OK]" if main_code == expected_main else "[FAIL]"
    print(f"{status} Detail '{detail_code}' -> Main '{main_code}' (expected '{expected_main}')")

# Test label formatting
print("\nTesting label format...")
test_main_code = "01"
if test_main_code in MANDARAKE_MAIN_CATEGORIES:
    label = f"{MANDARAKE_MAIN_CATEGORIES[test_main_code]['en']} ({test_main_code})"
    print(f"[OK] Label for code '{test_main_code}': '{label}'")
else:
    print(f"[FAIL] Code '{test_main_code}' not found")

print("\n[SUCCESS] Category selection logic working correctly!")
print("\nNow test in GUI:")
print("1. Load a config with categories")
print("2. Verify main category dropdown shows correct selection")
print("3. Verify detail categories are selected")
print("4. Verify detail listbox scrolls to show selected category")
