#!/usr/bin/env python3
"""Test Unicode handling in scraper"""

import json
from pathlib import Path
from mandarake_scraper import MandarakeScraper

# Create a test config with Japanese characters
test_config = {
    "keyword": "羽田あい",
    "category": "050801",
    "language": "ja",
    "fast": True,
    "resume": False,
    "debug": True,
    "csv": "test_unicode.csv",
    "mimic": True  # Force browser mimic
}

# Save test config
config_path = Path("test_unicode_config.json")
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(test_config, f, indent=2, ensure_ascii=False)

print(f"Test config saved to: {config_path}")
print("Config contains Japanese keyword for testing")

# Test scraper initialization
try:
    scraper = MandarakeScraper(str(config_path), use_mimic=True)
    print(f"Scraper initialized successfully")
    print(f"Browser mimic enabled: {scraper.use_mimic}")
    print(f"Browser mimic object: {type(scraper.browser_mimic)}")

    # Test URL construction
    url = scraper._build_search_url()
    print(f"Constructed search URL: {url}")

    # Test actual page fetching
    print("Testing page fetch with Japanese characters...")
    try:
        soup = scraper._fetch_page(url)
        if soup:
            print("[SUCCESS] Successfully fetched page with Japanese characters!")
            print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        else:
            print("[FAILED] Failed to fetch page")
    except Exception as fetch_error:
        print(f"[FAILED] Page fetch failed: {fetch_error}")
        import traceback
        traceback.print_exc()

except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()