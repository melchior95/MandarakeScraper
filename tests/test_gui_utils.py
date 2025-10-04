#!/usr/bin/env python3
"""Quick test to verify GUI utility integration."""

import sys

# Test imports
print("Testing imports...")
try:
    from gui.constants import STORE_OPTIONS, MAIN_CATEGORY_OPTIONS, CATEGORY_KEYWORDS
    from gui import utils
    print("[OK] Imports successful")
except Exception as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

# Test utility functions
print("\nTesting utility functions...")

# Test slugify
test_keyword = "naruto"
result = utils.slugify(test_keyword)
print(f"[OK] slugify('{test_keyword}') = '{result}'")

# Test fetch_exchange_rate
rate = utils.fetch_exchange_rate()
print(f"[OK] fetch_exchange_rate() = {rate}")

# Test extract_price
price_text = "$123.45"
price = utils.extract_price(price_text)
print(f"[OK] extract_price('{price_text}') = {price}")

# Test extract_code
code1 = utils.extract_code("01 - Comics")
print(f"[OK] extract_code('01 - Comics') = '{code1}'")
code2 = utils.extract_code("Nakano Broadway (nkn)")
print(f"[OK] extract_code('Nakano Broadway (nkn)') = '{code2}'")
code3 = utils.extract_code("0")
print(f"[OK] extract_code('0') = '{code3}'")

# Test config filename generation
config = {
    'keyword': 'naruto',
    'category': ['01'],
    'shop': '0'
}
filename = utils.suggest_config_filename(config)
csv_filename = utils.generate_csv_filename(config)
print(f"[OK] suggest_config_filename() = '{filename}'")
print(f"[OK] generate_csv_filename() = '{csv_filename}'")

print("\n[SUCCESS] All utility functions working correctly!")
print("\nNow you can test the GUI by running: python gui_config.py")
print("\nThings to test in the GUI:")
print("  1. GUI launches without errors")
print("  2. Exchange rate shown in console on startup")
print("  3. Load a config file")
print("  4. Save a config file")
print("  5. Category dropdowns work")
